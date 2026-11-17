"""Data feeds for the ECRT Pi side: one interface, two interchangeable sources.

    MockFeed    simulated meter and relays, no hardware needed
    SerialFeed  the real Arduino Uno over USB serial

Both implement `Feed`, so the UI only ever talks to a Feed. To switch from mock to the Uno, change the data source (sidebar,
or the ECRT_FEED / ECRT_PORT / ECRT_BAUD environment variables): no UI code changes.

PROVISIONAL serial protocol (JSON lines at 115200 baud; the Uno firmware does not speak it yet, and nothing here is final):
    Uno -> Pi, about 1 Hz:   {"v":230.1,"i":1.234,"p":283.9,"e":12.345,"f":50.0,"pf":0.98,"r":[0,1,0,0]}
        v volts, i amps, p watts, e kWh (PZEM accumulated), f Hz, pf power factor, r relay states (1 = on, channels 1 to 4).
        A field is null when the PZEM did not answer.
    Pi -> Uno, on demand:    {"relay":2,"on":1}
        relay is 1 to 4. The Uno applies it and reports the new state in the next "r".
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Protocol

N_RELAYS = 4


@dataclass(frozen=True)
class Reading:
    t: float                        # unix time on the Pi when the reading was received
    voltage: float | None           # V
    current: float | None           # A
    power: float | None             # W
    energy: float | None            # kWh, accumulated by the meter
    frequency: float | None         # Hz
    pf: float | None                # power factor
    relays: tuple[bool, ...]        # True = channel on
    ok: bool = True                 # False when the meter did not answer


class Feed(Protocol):
    name: str

    def poll(self) -> list[Reading]:
        """Return the readings that arrived since the last call (possibly none). Never blocks."""

    def relays(self) -> tuple[bool, ...]:
        """Best known relay states (includes a command that was just sent and not yet confirmed)."""

    def set_relay(self, channel: int, on: bool) -> None:
        """Switch channel 1..N_RELAYS."""

    def close(self) -> None: ...


# ---------------------------------------------------------------- mock
class MockFeed:
    """Simulated meter: a small base load plus the four channels, each with a made-up nominal power."""

    name = "mock"
    LOADS_W = (1800.0, 900.0, 2200.0, 350.0)    # fictional appliances: channel 1 to 4
    BASE_W = 120.0

    def __init__(self, interval: float = 1.0, seed: int | None = None):
        self._rnd = random.Random(seed)
        self._interval = interval
        self._on = [False] * N_RELAYS
        self._energy = 12.0
        self._last = time.time() - interval          # the first poll answers at once
        self._phase = self._rnd.random() * 6.28

    def poll(self) -> list[Reading]:
        now = time.time()
        dt = now - self._last
        if dt < self._interval:
            return []
        self._last = now
        v = 230 + 3 * math.sin(now / 37 + self._phase) + self._rnd.gauss(0, 0.4)
        p = self.BASE_W * (1 + 0.1 * math.sin(now / 11)) + self._rnd.gauss(0, 3)
        for load, on in zip(self.LOADS_W, self._on, strict=True):
            if on:
                p += load * (0.97 + 0.06 * self._rnd.random())
        p = max(p, 0.0)
        pf = 0.92 + 0.05 * math.sin(now / 53) if p > 200 else 0.75
        self._energy += p * dt / 3.6e6
        return [Reading(now, v, p / (v * pf), p, self._energy, 50.0 + self._rnd.gauss(0, 0.02), pf, tuple(self._on))]

    def relays(self) -> tuple[bool, ...]:
        return tuple(self._on)

    def set_relay(self, channel: int, on: bool) -> None:
        self._on[channel - 1] = on

    def close(self) -> None:
        pass


# ---------------------------------------------------------------- serial
class SerialFeed:
    """The real Uno over USB serial, speaking the provisional JSON-lines protocol described at the top of this file."""

    name = "serial"

    def __init__(self, port: str, baud: int = 115200, ser=None):
        """`ser` is any object with in_waiting, read(), write() and close(): given one, no port is opened (used by the tests)."""
        if ser is None:
            import serial  # pyserial: imported here so the mock needs no serial port

            ser = serial.Serial(port, baud, timeout=0, write_timeout=1)
            time.sleep(2.0)                             # opening the port resets an Uno: let it boot
            ser.reset_input_buffer()
        self._ser = ser
        self._buf = b""
        self._relays = (False,) * N_RELAYS
        self._pending: dict[int, tuple[bool, float]] = {}   # channel -> (requested state, time sent)
        self.bad_lines = 0
        self.last_reading_t: float | None = None

    def poll(self) -> list[Reading]:
        data = self._ser.read(self._ser.in_waiting)
        if not data:
            return []
        self._buf += data
        *lines, self._buf = self._buf.split(b"\n")
        out = []
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            r = self._parse(raw)
            if r is None:
                self.bad_lines += 1
            else:
                out.append(r)
        return out

    def _parse(self, raw: bytes) -> Reading | None:
        try:
            o = json.loads(raw)
            if not isinstance(o, dict):
                return None
            rel = o.get("r")
            if isinstance(rel, list) and len(rel) == N_RELAYS:
                self._relays = tuple(bool(x) for x in rel)
                for ch, (want, _t) in list(self._pending.items()):
                    if self._relays[ch - 1] == want:
                        del self._pending[ch]           # the Uno confirmed it
            v, i, p, e, f, pf = (o.get(k) for k in ("v", "i", "p", "e", "f", "pf"))
            ok = p is not None
            now = time.time()
            self.last_reading_t = now
            return Reading(now, v, i, p, e, f, pf, self._relays, ok)
        except (ValueError, TypeError):
            return None

    def relays(self) -> tuple[bool, ...]:
        state = list(self._relays)
        now = time.time()
        for ch, (want, t) in list(self._pending.items()):
            if now - t > 3.0:
                del self._pending[ch]                   # no confirmation: fall back to what the Uno reports
            else:
                state[ch - 1] = want
        return tuple(state)

    def set_relay(self, channel: int, on: bool) -> None:
        self._pending[channel] = (on, time.time())
        self._ser.write((json.dumps({"relay": channel, "on": int(on)}) + "\n").encode())

    def close(self) -> None:
        self._ser.close()


# ---------------------------------------------------------------- choosing a feed
@dataclass(frozen=True)
class FeedSettings:
    kind: str = "mock"                  # "mock" or "serial"
    port: str = "/dev/ttyACM0"
    baud: int = 115200


def settings_from_env() -> FeedSettings:
    return FeedSettings(os.environ.get("ECRT_FEED", "mock"), os.environ.get("ECRT_PORT", "/dev/ttyACM0"),
                        int(os.environ.get("ECRT_BAUD", "115200")))


def make_feed(s: FeedSettings) -> Feed:
    if s.kind == "mock":
        return MockFeed()
    if s.kind == "serial":
        return SerialFeed(s.port, s.baud)
    raise ValueError(f"unknown feed kind {s.kind!r}")


def serial_ports() -> list[str]:
    from serial.tools import list_ports

    return [p.device for p in list_ports.comports()]
