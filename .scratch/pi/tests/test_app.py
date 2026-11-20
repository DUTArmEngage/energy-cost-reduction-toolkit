from pathlib import Path

import pytest
import streamlit as st
from fakes import FakeSerial, line
from streamlit.testing.v1 import AppTest

import ecrt_pi_scratch.connection as connection_module
import ecrt_pi_scratch.feed as feed_module

APP = Path(__file__).resolve().parents[1] / "src" / "ecrt_pi_scratch" / "app.py"
GOOD = line(230, 1, 230, 1, 50, 1)


@pytest.fixture(autouse=True)
def fresh_connection(monkeypatch):
    """The app keeps one shared connection: start every test with a new one (the old one is closed on release). It opens a
    fake Uno that has sent one line, so the page has a reading to show."""
    real_feed = feed_module.SerialFeed
    monkeypatch.setattr(connection_module, "SerialFeed", lambda port, baud: real_feed(port, baud, ser=FakeSerial(GOOD)))
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def run():
    return AppTest.from_file(str(APP), default_timeout=30).run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def test_app_renders_with_a_reading_from_the_uno():
    at = run()
    assert not at.exception
    labels = {m.label for m in at.metric}
    assert {"Power", "Voltage", "Current", "Cost since start"} <= labels
    assert len(at.toggle) == 4                       # one per relay channel


def test_toggling_a_channel_switches_the_relay():
    at = run()
    at.toggle[1].set_value(True).run()                # the second toggle is channel 2
    assert not at.exception
    assert at.session_state["relay2"] is True


def test_settings_are_last_and_still_drive_the_page():
    at = run()
    assert at.expander[-1].label == "Settings"        # the panel is the last thing on the page
    for period in ("peak", "standard", "off-peak"):   # whichever period it is now, the caption shows the new rate
        at.number_input(key=f"rate_{period}").set_value(7.77)
    at.run()
    assert not at.exception
    assert any("R7.77/kWh" in c.value for c in at.caption)


def test_cost_table_is_not_in_an_accordion():
    at = run()
    assert [e.label for e in at.expander] == ["Connection", "Settings"]
    assert any(s.value == "Cost by tariff period" for s in at.subheader)


def test_connection_panel_scan_disconnect_and_reconnect(monkeypatch):
    real_feed = feed_module.SerialFeed
    monkeypatch.setattr(feed_module, "candidate_ports", lambda: [("/dev/ttyFAKE", "Fake Uno", "2341:0043")])
    monkeypatch.setattr(feed_module, "_open_serial", lambda device, baud: FakeSerial(GOOD))
    monkeypatch.setattr(connection_module, "SerialFeed", lambda port, baud: real_feed(port, baud, ser=FakeSerial()))

    at = run()
    assert any("Connected to /dev/ttyACM0" in m.value for m in at.markdown)       # opened at start
    assert not any(b.label == "Use mock data" for b in at.button)                  # there is no mock any more
    button(at, "Disconnect").click().run()
    assert any("Not connected" in m.value for m in at.markdown)

    button(at, "Scan for data feed").click().run()                       # finds the port that carries the data
    assert not at.exception
    table = next(d.value for d in at.dataframe if "device" in d.value.columns)
    assert list(table["status"]) == ["feed"] and list(table["device"]) == ["/dev/ttyFAKE"]
    assert at.selectbox(key="port").value == "/dev/ttyFAKE"              # and preselects it

    button(at, "Connect").click().run()
    assert any("Connected to /dev/ttyFAKE at 115200 baud" in m.value for m in at.markdown)
    assert not button(at, "Disconnect").disabled

    button(at, "Disconnect").click().run()
    assert any("Not connected" in m.value for m in at.markdown)
    assert any("Not connected" in w.value for w in at.warning)           # the page says so too


def test_a_failed_connect_shows_the_error(monkeypatch):
    def busy(port, baud):
        raise OSError("Device or resource busy")

    monkeypatch.setattr(feed_module, "candidate_ports", lambda: [("/dev/ttyFAKE", "Fake Uno", "")])
    monkeypatch.setattr(connection_module, "SerialFeed", busy)
    at = run()
    button(at, "Connect").click().run()
    assert any("busy" in e.value for e in at.error)


def test_page_starts_without_a_uno_and_says_so(monkeypatch):
    def missing(port, baud):
        raise OSError("No such file or directory")

    monkeypatch.setattr(connection_module, "SerialFeed", missing)
    st.cache_resource.clear()
    at = run()
    assert not at.exception
    assert any("No such file" in w.value for w in at.warning)
    assert any("Not connected" in m.value for m in at.markdown)
