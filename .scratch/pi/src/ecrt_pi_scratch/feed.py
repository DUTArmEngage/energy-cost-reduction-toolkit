"""The data feed of the ECRT Pi side: the real Arduino Uno over USB serial (SerialFeed). The UI talks to the `Feed` interface.
The port and baud rate come from the Connection panel, or from the ECRT_PORT / ECRT_BAUD environment variables at start.

PROVISIONAL serial protocol (CSV lines at 115200 baud; the Uno firmware in firmware/arduino speaks it, and nothing here is final):
    Uno -> Pi, about 1 Hz: one line of ten comma-separated numbers. No header line and no field names are ever sent: the
    order below is a convention both sides know, fixed in this file and in the Uno firmware.
        1 volts, 2 amps, 3 watts, 4 kWh (the PZEM's accumulated energy), 5 Hz, 6 power factor, 7 to 10 relay 1 to 4 (1 = on)
        e.g.  230.1,1.234,283.9,12.345,50.0,0.98,0,1,0,0
        The first six fields are empty when the PZEM did not answer:  ,,,,,,0,1,0,0
    Pi -> Uno, on demand:                R,channel,state
        e.g.  R,2,1   (channel 1 to 4, state 1 = on, 0 = off). The Uno applies it and reports the new state in the next line.
    Lines that do not fit (wrong field count, non-numbers, relay states other than 0 or 1) are skipped and counted.
"""
from __future__ import annotations

import math
import os
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


# ---------------------------------------------------------------- serial
def _plausible(nums) -> bool:
    """Limits of a PZEM-004T V4 100 A. Anything outside is a damaged reading: one 180 MW value once added 50 kWh."""
    v, a, w, e, f, pf = nums
    return (None not in nums and 80 <= v <= 280 and 0 <= a <= 120 and 0 <= w <= 30000 and 45 <= f <= 65 and 0 <= pf <= 1
            and 0 <= e <= 9999)


def parse_line(raw: bytes):
    """One CSV line -> (voltage, current, power, energy, frequency, pf, relays), or None if it does not fit the protocol."""
    try:
        fields = raw.decode("ascii").split(",")
        if len(fields) != 6 + N_RELAYS:
            return None
        nums = tuple(float(x) if x.strip() else None for x in fields[:6])
        rel = [x.strip() for x in fields[6:]]
    except (ValueError, UnicodeDecodeError):
        return None
    if any(x not in ("0", "1") for x in rel) or any(n is not None and not math.isfinite(n) for n in nums):
        return None
    if any(n is not None for n in nums) and not _plausible(nums):
        nums = (None,) * 6                           # a corrupted frame that passed the CRC: count it as "meter did not answer"
    return (*nums, tuple(x == "1" for x in rel))


class SerialFeed:
    """The real Uno over USB serial, speaking the provisional CSV protocol described at the top of this file."""

    name = "serial"

    def __init__(self, port: str, baud: int = 115200, ser=None):
        """`ser` is any object with in_waiting, read(), write() and close(): given one, no port is opened (used by the tests)."""
        if ser is None:
            import serial  # pyserial: imported here so importing this module needs no serial support

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
        parsed = parse_line(raw)
        if parsed is None:
            return None
        v, i, p, e, f, pf, relays = parsed
        self._relays = relays
        for ch, (want, _t) in list(self._pending.items()):
            if relays[ch - 1] == want:
                del self._pending[ch]                       # the Uno confirmed it
        now = time.time()
        self.last_reading_t = now
        return Reading(now, v, i, p, e, f, pf, relays, p is not None)

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
        self._ser.write(f"R,{channel},{int(on)}\n".encode())

    def close(self) -> None:
        self._ser.close()


# ---------------------------------------------------------------- choosing a feed
@dataclass(frozen=True)
class FeedSettings:
    port: str = "/dev/ttyACM0"          # or "auto": scan for the data feed at start
    baud: int = 115200


def settings_from_env() -> FeedSettings:
    return FeedSettings(os.environ.get("ECRT_PORT", "/dev/ttyACM0"), int(os.environ.get("ECRT_BAUD", "115200")))


# ---------------------------------------------------------------- finding the port that carries the data feed
@dataclass(frozen=True)
class PortInfo:
    device: str
    usb_id: str            # "vid:pid" of a USB serial device, or ""
    description: str
    status: str            # "feed" (a valid data line arrived), "silent", "error" or "in use"
    detail: str = ""


def candidate_ports() -> list[tuple[str, str, str]]:
    """(device, description, usb id) for every serial port with real hardware behind it. The on-board ttyS* UARTs are left out."""
    from serial.tools import list_ports

    out = []
    for p in list_ports.comports():
        if p.vid is None and (p.hwid or "n/a") == "n/a":
            continue
        usb = f"{p.vid:04x}:{p.pid:04x}" if p.vid is not None else ""
        out.append((p.device, p.description or "", usb))
    return sorted(out)


def _open_serial(device: str, baud: int):
    import serial

    return serial.Serial(device, baud, timeout=0)


def probe_port(device: str, baud: int = 115200, listen_s: float = 5.0, opener=None) -> tuple[str, str]:
    """Open a port and listen for a valid data line. Returns (status, detail); status is "feed", "silent" or "error".

    Opening a port resets an Arduino, so it takes a couple of seconds to start sending: the default listen time covers that.
    """
    try:
        ser = (opener or _open_serial)(device, baud)
    except Exception as e:                                  # busy, no permission, unplugged …
        return "error", f"{type(e).__name__}: {e}"
    try:
        buf, deadline = b"", time.time() + listen_s
        while time.time() < deadline:
            n = ser.in_waiting
            if not n:
                time.sleep(0.05)
                continue
            buf += ser.read(n)
            *lines, buf = buf.split(b"\n")
            if any(parse_line(line.strip()) is not None for line in lines):
                return "feed", ""
        return "silent", f"no valid data line within {listen_s:.0f} s"
    except Exception as e:
        return "error", f"{type(e).__name__}: {e}"
    finally:
        try:
            ser.close()
        except Exception:
            pass


def scan_ports(baud: int = 115200, listen_s: float = 5.0, skip=(), ports=None, opener=None) -> list[PortInfo]:
    """Probe every candidate port at once and say which one carries the data feed. Ports in `skip` (in use) are not opened."""
    from concurrent.futures import ThreadPoolExecutor

    cands = candidate_ports() if ports is None else ports
    if not cands:
        return []

    def one(c):
        device, description, usb = c
        if device in skip:
            return PortInfo(device, usb, description, "in use", "open in this app")
        status, detail = probe_port(device, baud, listen_s, opener)
        return PortInfo(device, usb, description, status, detail)

    with ThreadPoolExecutor(max_workers=len(cands)) as pool:
        found = list(pool.map(one, cands))
    order = {"feed": 0, "in use": 1, "silent": 2, "error": 3}
    return sorted(found, key=lambda r: (order[r.status], r.device))
