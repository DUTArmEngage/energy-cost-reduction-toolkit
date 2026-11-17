"""ECRT dashboard (Streamlit). Run with `uv run ecrt-ui`.

The UI only talks to a Feed (see feed.py), so the mock source and the real Uno over serial are interchangeable: pick the
data source in the Settings panel, or set ECRT_FEED=serial ECRT_PORT=/dev/ttyACM0 before starting.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from ecrt_pi_scratch.feed import N_RELAYS, FeedSettings, make_feed, serial_ports, settings_from_env
from ecrt_pi_scratch.tariff import PERIODS, Tariff

HISTORY = 900                      # readings kept for the charts

st.set_page_config(page_title="ECRT", layout="wide")


@st.cache_resource(show_spinner="Opening the data source…")
def get_feed(kind: str, port: str, baud: int):
    return make_feed(FeedSettings(kind, port, baud))


def init_state() -> None:
    st.session_state.setdefault("history", deque(maxlen=HISTORY))
    st.session_state.setdefault("kwh", {p: 0.0 for p in PERIODS})
    st.session_state.setdefault("cost", {p: 0.0 for p in PERIODS})
    st.session_state.setdefault("last_t", None)


def reset_state() -> None:
    for k in ("history", "kwh", "cost", "last_t"):
        st.session_state.pop(k, None)
    init_state()


def record(reading, tariff: Tariff) -> None:
    """Add a reading to the history and integrate its power over the time since the previous one into energy and cost."""
    s = st.session_state
    s.history.append(reading)
    if reading.power is not None and s.last_t is not None:
        dt = max(0.0, reading.t - s.last_t)
        when = datetime.fromtimestamp(reading.t)
        period, kwh = tariff.period_at(when), reading.power * dt / 3.6e6
        s.kwh[period] += kwh
        s.cost[period] += kwh * tariff.rates[period]
    s.last_t = reading.t


def fmt(v, unit: str, digits: int = 1) -> str:
    return "–" if v is None else f"{v:.{digits}f} {unit}".strip()


def on_relay(feed, channel: int) -> None:
    feed.set_relay(channel, st.session_state[f"relay{channel}"])


# ---------------------------------------------------------------- settings values
# The Settings panel is drawn at the bottom of the page, but the data source, refresh rate and tariff are needed before that:
# read them back from the widgets' saved state (keys below), falling back to the defaults on the first run.
init_state()
env = settings_from_env()
kind = st.session_state.get("kind", env.kind)
port = st.session_state.get("port", env.port)
baud = st.session_state.get("baud", env.baud)
refresh = st.session_state.get("refresh", 1.0)
tariff = Tariff({p: st.session_state.get(f"rate_{p}", default) for p, default in Tariff().rates.items()})

try:
    feed = get_feed(kind, port, int(baud))
except Exception as e:                              # port missing, busy, no permission …
    st.error(f"Could not open the {kind} data source: {e}")
    st.stop()


# ---------------------------------------------------------------- live view
def line_chart(df: pd.DataFrame, col: str, title: str, height: int, zero: bool = True):
    """Line chart with a time-of-day axis (st.line_chart shows fractional seconds)."""
    return (alt.Chart(df.reset_index())
            .mark_line()
            .encode(x=alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M:%S", tickCount=6)),
                    y=alt.Y(f"{col}:Q", title=title, scale=alt.Scale(zero=zero)))
            .properties(height=height))


def live() -> None:
    s = st.session_state
    for r in feed.poll():
        record(r, tariff)
    if not s.history:
        st.info("Waiting for the first reading…")
        return
    last = s.history[-1]
    age = datetime.now().timestamp() - last.t
    now = datetime.now()

    # status line
    src = f"Source: **{feed.name}**" + (f" · skipped lines: {feed.bad_lines}" if feed.name == "serial" else "")
    period = tariff.period_at(now)
    st.caption(f"{src} · last reading {age:.0f} s ago · tariff now: **{period}** at R{tariff.rate_at(now):.2f}/kWh")
    if age > 3 * refresh + 2:
        st.warning("No new readings: check the data source.")
    if not last.ok:
        st.warning("The meter did not answer (PZEM read error).")

    # live numbers next to the cost
    live_box, cost_box = st.columns([5, 3])
    with live_box.container(border=True):
        c = st.columns(5)
        c[0].metric("Power", fmt(last.power, "W", 0))
        c[1].metric("Voltage", fmt(last.voltage, "V"))
        c[2].metric("Current", fmt(last.current, "A", 2))
        c[3].metric("Frequency", fmt(last.frequency, "Hz"))
        c[4].metric("Power factor", fmt(last.pf, "", 2))
    with cost_box.container(border=True):
        total_kwh, total_cost = sum(s.kwh.values()), sum(s.cost.values())
        c = st.columns(2)
        c[0].metric("Cost since start", f"R{total_cost:.2f}")
        c[1].metric("Energy since start", f"{total_kwh:.3f} kWh")

    # relay controls: one row, channels in order
    with st.container(border=True):
        state = feed.relays()
        cols = st.columns(N_RELAYS)
        for ch in range(1, N_RELAYS + 1):
            s[f"relay{ch}"] = state[ch - 1]               # follow what the feed says the relay is doing
            cols[ch - 1].toggle(f"Channel {ch}", key=f"relay{ch}", on_change=on_relay, args=(feed, ch))

    # charts
    df = pd.DataFrame({"time": [datetime.fromtimestamp(r.t) for r in s.history],
                       "power": [r.power for r in s.history],
                       "voltage": [r.voltage for r in s.history],
                       "current": [r.current for r in s.history]}).set_index("time")
    st.altair_chart(line_chart(df, "power", "Power (W)", 300), width="stretch")
    v_col, i_col = st.columns(2)
    v_col.altair_chart(line_chart(df, "voltage", "Voltage (V)", 200, zero=False), width="stretch")
    i_col.altair_chart(line_chart(df, "current", "Current (A)", 200), width="stretch")

    st.subheader("Cost by tariff period")
    st.dataframe(pd.DataFrame({"kWh": s.kwh, "Cost (R)": s.cost}).round(4), width="stretch")


st.fragment(run_every=refresh)(live)()

# ---------------------------------------------------------------- settings panel (last on the page)
with st.expander("Settings"):
    col_src, col_refresh, col_tariff = st.columns(3)
    with col_src:
        st.radio("Data source", ["mock", "serial"], index=["mock", "serial"].index(kind), horizontal=True, key="kind")
        if kind == "serial":
            ports = serial_ports()
            if env.port not in ports:
                ports.insert(0, env.port)
            st.selectbox("Serial port", ports, key="port")
            st.number_input("Baud", value=env.baud, step=9600, key="baud")
    with col_refresh:
        st.slider("Refresh (s)", 0.5, 5.0, 1.0, 0.5, key="refresh")
        st.button("Reset history and cost", on_click=reset_state)
    with col_tariff:
        st.caption("Tariff (placeholder rates, R/kWh)")
        for name, default in Tariff().rates.items():
            st.number_input(name, min_value=0.0, value=default, step=0.05, format="%.2f", key=f"rate_{name}")
