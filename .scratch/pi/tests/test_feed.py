import json
import time

import pytest

from ecrt_pi_scratch.feed import N_RELAYS, FeedSettings, MockFeed, SerialFeed, make_feed


class FakeSerial:
    """Stands in for a pyserial port: bytes queued in `incoming` are what the Uno 'sent'; `written` collects what the Pi sent."""

    def __init__(self):
        self.incoming = b""
        self.written = b""

    @property
    def in_waiting(self):
        return len(self.incoming)

    def read(self, n):
        data, self.incoming = self.incoming[:n], self.incoming[n:]
        return data

    def write(self, data):
        self.written += data

    def close(self):
        pass


def line(**kw):
    return (json.dumps(kw) + "\n").encode()


# ---------------------------------------------------------------- mock
def test_mock_answers_immediately_and_relays_add_load():
    f = MockFeed(interval=0.0, seed=1)
    idle = f.poll()[0]
    assert idle.ok and not any(idle.relays)
    f.set_relay(3, True)
    loaded = f.poll()[0]
    assert loaded.relays == (False, False, True, False)
    assert loaded.power > idle.power + 1500          # channel 3 is the 2.2 kW load
    assert f.relays() == (False, False, True, False)


def test_mock_energy_only_grows():
    f = MockFeed(interval=0.0, seed=2)
    first = f.poll()[0].energy
    time.sleep(0.01)
    assert f.poll()[0].energy > first


# ---------------------------------------------------------------- serial protocol
def test_serial_parses_a_reading():
    ser = FakeSerial()
    ser.incoming = line(v=230.1, i=1.234, p=283.9, e=12.345, f=50.0, pf=0.98, r=[0, 1, 0, 0])
    r = SerialFeed("fake", ser=ser).poll()[0]
    assert (r.voltage, r.current, r.power, r.energy, r.frequency, r.pf) == (230.1, 1.234, 283.9, 12.345, 50.0, 0.98)
    assert r.relays == (False, True, False, False) and r.ok


def test_serial_handles_split_lines_and_garbage():
    ser = FakeSerial()
    feed = SerialFeed("fake", ser=ser)
    whole = line(v=230, i=1, p=230, e=1, f=50, pf=1, r=[0, 0, 0, 0])
    ser.incoming = b"not json\n" + whole[:10]
    assert feed.poll() == []                         # garbage skipped, half a line kept
    assert feed.bad_lines == 1
    ser.incoming = whole[10:] + b"[1, 2]\n"           # rest of the line, then valid JSON that is not an object
    assert len(feed.poll()) == 1 and feed.bad_lines == 2


def test_serial_null_fields_mean_the_meter_did_not_answer():
    ser = FakeSerial()
    ser.incoming = line(v=None, i=None, p=None, e=None, f=None, pf=None, r=[1, 0, 0, 0])
    r = SerialFeed("fake", ser=ser).poll()[0]
    assert not r.ok and r.power is None and r.relays[0]


def test_serial_set_relay_writes_a_command_and_reports_it_until_confirmed():
    ser = FakeSerial()
    feed = SerialFeed("fake", ser=ser)
    feed.set_relay(2, True)
    assert json.loads(ser.written) == {"relay": 2, "on": 1}
    assert feed.relays()[1] is True                  # optimistic until the Uno says otherwise
    ser.incoming = line(v=230, i=1, p=230, e=1, f=50, pf=1, r=[0, 1, 0, 0])
    feed.poll()
    assert feed.relays()[1] is True and not feed._pending   # confirmed


# ---------------------------------------------------------------- choosing a feed
def test_make_feed():
    assert make_feed(FeedSettings("mock")).name == "mock"
    with pytest.raises(ValueError):
        make_feed(FeedSettings("nope"))
    assert N_RELAYS == 4
