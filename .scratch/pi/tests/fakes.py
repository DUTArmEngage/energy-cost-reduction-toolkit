"""Test doubles shared by the test modules."""


class FakeSerial:
    """Stands in for a pyserial port: bytes queued in `incoming` are what the Uno 'sent'; `written` collects what the Pi sent."""

    def __init__(self, incoming=b"", fail_with=None):
        self.incoming = incoming
        self.written = b""
        self.fail_with = fail_with                       # an exception to raise on the next read (the cable was pulled)
        self.closed = False

    @property
    def in_waiting(self):
        if self.fail_with is not None:
            raise self.fail_with
        return len(self.incoming)

    def read(self, n):
        data, self.incoming = self.incoming[:n], self.incoming[n:]
        return data

    def write(self, data):
        self.written += data

    def close(self):
        self.closed = True


def line(v="", i="", p="", e="", f="", pf="", r=(0, 0, 0, 0)):
    """One line the Uno would send: volts,amps,watts,kwh,hz,pf,r1,r2,r3,r4 (empty = the meter did not answer)."""
    return (",".join(str(x) for x in (v, i, p, e, f, pf, *r)) + "\n").encode()
