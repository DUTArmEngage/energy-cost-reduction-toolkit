import time

from fakes import FakeSerial, line

from ecrt_pi_scratch.connection import Connection
from ecrt_pi_scratch.feed import FeedSettings, PortInfo, SerialFeed

GOOD = line(230, 1, 230, 1, 50, 1)


def factory_for(fake):
    return lambda port, baud: SerialFeed(port, baud, ser=fake)


def wait_for(condition, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.02)
    return False


def make(settings=None, **kw):
    return Connection(settings or FeedSettings("mock"), interval=0.01, **kw)


def test_starts_on_mock_data_with_a_reading_ready():
    c = make()
    try:
        assert c.kind == "mock" and c.describe() == "Mock data"
        assert c.readings_since(0)                         # the first reading is there before the thread has run
    finally:
        c.close()


def test_connect_reads_the_port_and_disconnect_releases_it():
    fake = FakeSerial()
    c = make(serial_factory=factory_for(fake))
    try:
        generation = c.generation
        assert c.connect_serial("/dev/ttyACM0", 115200) is True
        assert c.kind == "serial" and c.describe() == "Connected to /dev/ttyACM0 at 115200 baud"
        assert c.generation == generation + 1              # sessions start afresh
        fake.incoming = GOOD
        assert wait_for(lambda: c.readings_since(0))
        c.disconnect()
        assert c.kind == "none" and c.describe() == "Not connected" and fake.closed
    finally:
        c.close()


def test_connect_failure_is_reported_and_leaves_it_disconnected():
    def busy(port, baud):
        raise OSError("Device or resource busy")

    c = make(serial_factory=busy)
    try:
        assert c.connect_serial("/dev/ttyACM0", 115200) is False
        assert c.kind == "none" and "busy" in c.error and "/dev/ttyACM0" in c.error
    finally:
        c.close()


def test_a_pulled_cable_marks_the_connection_lost():
    fake = FakeSerial()
    c = make(serial_factory=factory_for(fake))
    try:
        c.connect_serial("/dev/ttyACM0", 115200)
        fake.fail_with = OSError("device disconnected")
        assert wait_for(lambda: c.kind == "none")
        assert c.error.startswith("Connection lost") and "device disconnected" in c.error
        c.set_relay(1, True)                               # harmless when not connected
        assert c.relays() == (False,) * 4
    finally:
        c.close()


def test_switching_between_mock_and_serial_changes_the_generation():
    c = make(serial_factory=factory_for(FakeSerial()))
    try:
        g0 = c.generation
        c.connect_serial("/dev/ttyACM0", 115200)
        c.use_mock()
        assert c.kind == "mock" and c.generation == g0 + 2
    finally:
        c.close()


def test_auto_scans_for_the_feed_and_connects_to_it():
    fake = FakeSerial()
    found = [PortInfo("/dev/ttyACM1", "", "Uno", "feed"), PortInfo("/dev/ttyUSB0", "", "other", "silent")]
    c = make(serial_factory=factory_for(fake), scanner=lambda baud: found)
    try:
        assert c.connect_serial("auto", 115200) is True and c.port == "/dev/ttyACM1"
        c.set_relay(2, True)
        assert fake.written == b"R,2,1\n"
    finally:
        c.close()


def test_auto_with_no_feed_says_so():
    c = make(scanner=lambda baud: [PortInfo("/dev/ttyUSB0", "", "other", "silent")])
    try:
        assert c.connect_serial("auto", 115200) is False
        assert c.kind == "none" and "No data feed found" in c.error
    finally:
        c.close()


def test_started_in_serial_mode_from_the_settings():
    fake = FakeSerial()
    c = Connection(FeedSettings("serial", "/dev/ttyACM0", 115200), interval=0.01, serial_factory=factory_for(fake))
    try:
        assert c.kind == "serial" and c.port == "/dev/ttyACM0"
    finally:
        c.close()
