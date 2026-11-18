import time
from types import SimpleNamespace

from fakes import FakeSerial, line

from ecrt_pi_scratch.feed import (
    MockFeed,
    SerialFeed,
    candidate_ports,
    parse_line,
    probe_port,
    scan_ports,
)


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
    ser.incoming = line(230.1, 1.234, 283.9, 12.345, 50.0, 0.98, (0, 1, 0, 0))
    r = SerialFeed("fake", ser=ser).poll()[0]
    assert (r.voltage, r.current, r.power, r.energy, r.frequency, r.pf) == (230.1, 1.234, 283.9, 12.345, 50.0, 0.98)
    assert r.relays == (False, True, False, False) and r.ok


def test_serial_handles_split_lines_and_garbage():
    ser = FakeSerial()
    feed = SerialFeed("fake", ser=ser)
    whole = line(230, 1, 230, 1, 50, 1)
    ser.incoming = b"not csv\n" + whole[:10]
    assert feed.poll() == []                         # garbage skipped, half a line kept
    assert feed.bad_lines == 1
    ser.incoming = whole[10:] + b"1,2,3\n"            # rest of the line, then a line with the wrong number of fields
    assert len(feed.poll()) == 1 and feed.bad_lines == 2


def test_serial_rejects_bad_numbers_and_relay_values():
    ser = FakeSerial()
    feed = SerialFeed("fake", ser=ser)
    ser.incoming = b"230,1,230,1,50,1,0,0,0,2\n"     # relay state 2
    ser.incoming += b"abc,1,230,1,50,1,0,0,0,0\n"    # not a number
    ser.incoming += b"230,1,230,1,50,1,0,0,0\n"      # nine fields
    ser.incoming += b"volts,amps,watts,kwh,hz,pf,r1,r2,r3,r4\n"   # no header in the protocol: rejected
    assert feed.poll() == [] and feed.bad_lines == 4


def test_serial_empty_fields_mean_the_meter_did_not_answer():
    ser = FakeSerial()
    ser.incoming = line(r=(1, 0, 0, 0))               # ,,,,,,1,0,0,0
    r = SerialFeed("fake", ser=ser).poll()[0]
    assert not r.ok and r.power is None and r.relays[0]


def test_serial_set_relay_writes_a_command_and_reports_it_until_confirmed():
    ser = FakeSerial()
    feed = SerialFeed("fake", ser=ser)
    feed.set_relay(2, True)
    assert ser.written == b"R,2,1\n"
    assert feed.relays()[1] is True                  # optimistic until the Uno says otherwise
    ser.incoming = line(230, 1, 230, 1, 50, 1, (0, 1, 0, 0))
    feed.poll()
    assert feed.relays()[1] is True and not feed._pending   # confirmed


# ---------------------------------------------------------------- parsing one line
def test_parse_line():
    parsed = parse_line(b"230.1,1.234,283.9,12.345,50.0,0.98,0,1,0,0")
    assert parsed == (230.1, 1.234, 283.9, 12.345, 50.0, 0.98, (False, True, False, False))
    assert parse_line(b",,,,,,1,0,0,0")[:6] == (None,) * 6                  # the meter did not answer
    assert parse_line(b"nan,1,230,1,50,1,0,0,0,0") is None                  # not a finite number
    assert parse_line(b"230,1,230,1,50,1,0,0,0,7") is None                  # relay state must be 0 or 1
    assert parse_line(b"230,1,230,1,50,1,0,0,0") is None                    # nine fields
    assert parse_line(b"volts,amps,watts,kwh,hz,pf,r1,r2,r3,r4") is None    # a header is not part of the protocol
    assert parse_line(b"\xff\xfe") is None


# ---------------------------------------------------------------- finding the port that carries the data feed
GOOD = line(230, 1, 230, 1, 50, 1)


def test_probe_finds_the_feed():
    assert probe_port("/dev/x", listen_s=1, opener=lambda d, b: FakeSerial(GOOD)) == ("feed", "")


def test_probe_ignores_a_partial_first_line():
    assert probe_port("/dev/x", listen_s=1, opener=lambda d, b: FakeSerial(b"0.98,0,0,0,0\n" + GOOD))[0] == "feed"


def test_probe_silent_port():
    status, detail = probe_port("/dev/x", listen_s=0.2, opener=lambda d, b: FakeSerial(b"hello world\n"))
    assert status == "silent" and "no valid data line" in detail


def test_probe_open_error_and_read_error_are_reported_not_raised():
    def busy(device, baud):
        raise OSError("Device or resource busy")

    assert probe_port("/dev/x", opener=busy) == ("error", "OSError: Device or resource busy")
    assert probe_port("/dev/x", listen_s=1, opener=lambda d, b: FakeSerial(fail_with=OSError("gone")))[0] == "error"


def test_probe_closes_the_port():
    fake = FakeSerial(GOOD)
    probe_port("/dev/x", listen_s=1, opener=lambda d, b: fake)
    assert fake.closed


def test_scan_ports_puts_the_feed_first_and_skips_ports_in_use():
    ports = [("/dev/ttyACM1", "Silent board", "1a86:7523"), ("/dev/ttyACM0", "Arduino Uno", "2341:0043"),
             ("/dev/ttyUSB0", "Busy", ""), ("/dev/ttyUSB1", "Ours", "")]
    ports_by_name = {"/dev/ttyACM0": FakeSerial(GOOD), "/dev/ttyACM1": FakeSerial(b"")}

    def opener(device, baud):
        if device == "/dev/ttyUSB0":
            raise PermissionError("denied")
        return ports_by_name[device]

    found = scan_ports(listen_s=0.3, skip=("/dev/ttyUSB1",), ports=ports, opener=opener)
    assert [(p.device, p.status) for p in found] == [("/dev/ttyACM0", "feed"), ("/dev/ttyUSB1", "in use"),
                                                    ("/dev/ttyACM1", "silent"), ("/dev/ttyUSB0", "error")]
    assert found[0].usb_id == "2341:0043" and "denied" in found[-1].detail


def test_scan_with_no_ports():
    assert scan_ports(ports=[]) == []


def test_candidate_ports_leaves_out_the_onboard_uarts(monkeypatch):
    fake = [SimpleNamespace(device="/dev/ttyS0", description="n/a", vid=None, pid=None, hwid="n/a"),
            SimpleNamespace(device="/dev/ttyACM0", description="Arduino Uno", vid=0x2341, pid=0x43, hwid="USB VID:PID=2341:0043")]
    monkeypatch.setattr("serial.tools.list_ports.comports", lambda: fake)
    assert candidate_ports() == [("/dev/ttyACM0", "Arduino Uno", "2341:0043")]
