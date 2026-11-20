"""The one data connection of the app, shared by every browser session.

A serial port can only be opened once, and several browsers can be looking at the dashboard, so the feed lives here, not in a
page. A small background thread reads it continuously (which also keeps the serial buffer drained when nobody is watching) and
keeps the recent readings; each session asks for the readings newer than the last one it saw.

States: "serial" (connected to the Uno) and "none" (not connected: never opened, disconnected by the
user, or the connection was lost).
"""
from __future__ import annotations

import threading
from collections import deque

from ecrt_pi_scratch.feed import N_RELAYS, FeedSettings, Reading, SerialFeed, scan_ports


class Connection:
    HISTORY = 2000                                           # readings kept for sessions to catch up from

    def __init__(self, settings: FeedSettings, interval: float = 0.1, serial_factory=None, scanner=None):
        self._factory = serial_factory                       # (port, baud) -> Feed; None means SerialFeed
        self._scanner = scanner                              # (baud) -> list[PortInfo]; None means scan_ports
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._buf: deque[tuple[int, Reading]] = deque(maxlen=self.HISTORY)
        self._seq = 0
        self.feed = None
        self.kind = "none"
        self.port = settings.port
        self.baud = settings.baud
        self.error: str | None = None
        self.generation = 0                                  # changes whenever the source changes: sessions start afresh

        self.connect_serial(settings.port, settings.baud)      # on failure: not connected, with the reason in `error`
        self._poll_once()
        self._thread = threading.Thread(target=self._run, args=(interval,), daemon=True, name="ecrt-feed")
        self._thread.start()

    # ------------------------------------------------------------ choosing the source
    def connect_serial(self, port: str, baud: int) -> bool:
        """Open `port` (or scan for the data feed when port is "auto"). Returns False, with `error` set, if it fails."""
        with self._lock:
            self._close_feed()
            self.kind, self.baud = "none", int(baud)
            if port == "auto":
                scan = self._scanner or scan_ports
                found = [p for p in scan(self.baud) if p.status == "feed"]
                if not found:
                    self.error = "No data feed found on any serial port."
                    return False
                port = found[0].device
            try:
                feed = (self._factory or SerialFeed)(port, self.baud)
            except Exception as e:                           # busy, no permission, unplugged …
                self.error = f"Could not open {port}: {e}"
                return False
            self._set(feed, "serial", port)
            return True

    def disconnect(self) -> None:
        with self._lock:
            self._close_feed()
            self.kind, self.error = "none", None

    def _set(self, feed, kind: str, port: str | None) -> None:
        self._close_feed()
        self.feed, self.kind, self.error = feed, kind, None
        if port:
            self.port = port
        self._buf.clear()
        self.generation += 1

    def _close_feed(self) -> None:
        feed, self.feed = self.feed, None
        if feed is not None:
            try:
                feed.close()
            except Exception:
                pass

    def _lose(self, e: Exception) -> None:
        self._close_feed()
        self.kind, self.error = "none", f"Connection lost: {e}"

    # ------------------------------------------------------------ reading
    def _poll_once(self) -> None:
        with self._lock:
            if self.feed is None:
                return
            try:
                readings = self.feed.poll()
            except Exception as e:                           # the cable was pulled, the device went away …
                self._lose(e)
                return
            for r in readings:
                self._seq += 1
                self._buf.append((self._seq, r))

    def _run(self, interval: float) -> None:
        while not self._stop.wait(interval):
            self._poll_once()

    @property
    def latest_seq(self) -> int:
        return self._seq

    def readings_since(self, seq: int) -> list[tuple[int, Reading]]:
        with self._lock:
            return [(n, r) for n, r in self._buf if n > seq]

    # ------------------------------------------------------------ relays
    def relays(self) -> tuple[bool, ...]:
        with self._lock:
            return self.feed.relays() if self.feed is not None else (False,) * N_RELAYS

    def set_relay(self, channel: int, on: bool) -> None:
        with self._lock:
            if self.feed is None:
                return
            try:
                self.feed.set_relay(channel, on)
            except Exception as e:
                self._lose(e)

    # ------------------------------------------------------------ status
    def describe(self) -> str:
        if self.kind == "serial":
            return f"Connected to {self.port} at {self.baud} baud"
        return "Not connected"

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            self._close_feed()
