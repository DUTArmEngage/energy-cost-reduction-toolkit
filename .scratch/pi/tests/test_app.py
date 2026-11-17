from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src" / "ecrt_pi_scratch" / "app.py"


@pytest.fixture(autouse=True)
def fresh_feed():
    """The app caches its feed across sessions: start every test with a new one so the first poll answers at once."""
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def test_app_renders_with_the_mock_feed():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    labels = {m.label for m in at.metric}
    assert {"Power", "Voltage", "Current", "Cost since start"} <= labels
    assert len(at.toggle) == 4                       # one per relay channel


def test_toggling_a_channel_switches_the_relay():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.toggle[1].set_value(True).run()                # the second toggle is channel 2
    assert not at.exception
    assert at.session_state["relay2"] is True


def test_settings_are_last_and_still_drive_the_page():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert at.expander[-1].label == "Settings"        # the panel is the last thing on the page
    for period in ("peak", "standard", "off-peak"):   # whichever period it is now, the caption shows the new rate
        at.number_input(key=f"rate_{period}").set_value(7.77)
    at.run()
    assert not at.exception
    assert any("R7.77/kWh" in c.value for c in at.caption)


def test_cost_table_is_not_in_an_accordion():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert [e.label for e in at.expander] == ["Settings"]
    assert any(s.value == "Cost by tariff period" for s in at.subheader)
