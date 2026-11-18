"""ECRT dashboard (Streamlit). Run with `uv run ecrt-ui`.

The data comes from one shared Connection (see connection.py): simulated mock data, or the Uno over USB serial. Use the Connection
panel at the bottom of the page to scan for the port that carries the data feed, connect, disconnect or switch to mock data. To
start already connected, set ECRT_FEED=serial and ECRT_PORT=/dev/ttyACM0 (or ECRT_PORT=auto to scan at start) before starting.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from ecrt_pi_scratch.connection import Connection
from ecrt_pi_scratch.feed import N_RELAYS, candidate_ports, scan_ports, settings_from_env
from ecrt_pi_scratch.tariff import PERIODS, Tariff

HISTORY = 900                      # readings kept for the charts

st.set_page_config(page_title="ECRT", layout="wide")


@st.cache_resource(show_spinner="Starting the data feed…", on_release=lambda c: c.close())
def get_connection() -> Connection:
    return Connection(settings_from_env())


conn = get_connection()


def init_state() -> None:
    st.session_state.setdefault("history", deque(maxlen=HISTORY))
    st.session_state.setdefault("kwh", {p: 0.0 for p in PERIODS})
    st.session_state.setdefault("cost", {p: 0.0 for p in PERIODS})
    st.session_state.setdefault("last_t", None)
    st.session_state.setdefault("seq", 0)                # the newest reading this session has taken from the connection


def clear_state() -> None:
    for k in ("history", "kwh", "cost", "last_t", "seq"):
        st.session_state.pop(k, None)
    init_state()


def reset_state() -> None:
    """The Reset button: start again from now, not from the readings the connection still holds."""
    clear_state()
    st.session_state.seq = conn.latest_seq


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


def on_relay(channel: int) -> None:
    conn.set_relay(channel, st.session_state[f"relay{channel}"])


# ---------------------------------------------------------------- session setup
def sync_generation() -> None:
    """The data source changed (connect, disconnect, mock): start the session afresh so old and new readings are not mixed."""
    init_state()
    if st.session_state.get("gen") != conn.generation:
        clear_state()
        st.session_state.gen = conn.generation


sync_generation()
refresh = st.session_state.get("refresh", 1.0)
tariff = Tariff({p: st.session_state.get(f"rate_{p}", default) for p, default in Tariff().rates.items()})


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
    sync_generation()                                    # a connect or disconnect may have happened since the last full run
    for n, r in conn.readings_since(s.seq):
        record(r, tariff)
        s.seq = n
    connected = conn.kind != "none"
    if not connected:
        st.warning(conn.error or "Not connected. Open Connection below to scan for the data feed and connect, or use mock data.")
    if not s.history:
        if connected:
            st.info("Waiting for the first reading…")
        return
    last = s.history[-1]
    age = datetime.now().timestamp() - last.t
    now = datetime.now()

    # status line
    period = tariff.period_at(now)
    rate = tariff.rate_at(now)
    st.caption(f"Source: **{conn.describe()}** · last reading {age:.0f} s ago · tariff now: **{period}** at R{rate:.2f}/kWh")
    if connected and age > 3 * refresh + 2:
        st.warning("No new readings: check the data source.")
    if connected and not last.ok:
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
        state = conn.relays()
        cols = st.columns(N_RELAYS)
        for ch in range(1, N_RELAYS + 1):
            s[f"relay{ch}"] = state[ch - 1]               # follow what the feed says the relay is doing
            cols[ch - 1].toggle(f"Channel {ch}", key=f"relay{ch}", on_change=on_relay, args=(ch,), disabled=not connected)

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


# ---------------------------------------------------------------- connection panel
def do_connect() -> None:
    conn.connect_serial(st.session_state["port"], int(st.session_state["baud"]))


@st.fragment(run_every=2)
def connection_status() -> None:
    st.markdown(f"**{conn.describe()}**")
    if conn.error:
        st.error(conn.error)


with st.expander("Connection"):
    connection_status()
    left, right = st.columns([2, 3])
    with left:
        st.number_input("Baud", min_value=300, max_value=2_000_000, value=conn.baud, step=300, key="baud")
        if st.button("Scan for data feed"):
            with st.spinner("Scanning serial ports (a few seconds)…"):
                found = scan_ports(int(st.session_state["baud"]), skip=(conn.port,) if conn.kind == "serial" else ())
            st.session_state["scan"] = [asdict(p) for p in found]
            feeds = [p.device for p in found if p.status == "feed"]
            if feeds:                                     # preselect the port that carries the data
                st.session_state["port"] = feeds[0]
        options = list(dict.fromkeys([*(p["device"] for p in st.session_state.get("scan", [])),
                                      *(d for d, _, _ in candidate_ports())]))
        if conn.kind == "serial" and conn.port not in options:
            options.insert(0, conn.port)
        if st.session_state.get("port") is None and options:
            st.session_state["port"] = options[0]
        st.selectbox("Port", options, key="port", accept_new_options=True)    # or type a path such as /dev/serial/by-id/…
        b_connect, b_disconnect, b_mock = st.columns(3)
        b_connect.button("Connect", on_click=do_connect, disabled=not st.session_state.get("port"))
        b_disconnect.button("Disconnect", on_click=conn.disconnect, disabled=conn.kind != "serial")
        b_mock.button("Use mock data", on_click=conn.use_mock, disabled=conn.kind == "mock")
    with right:
        scan = st.session_state.get("scan")
        if scan is None:
            st.caption("Press Scan to find which port carries the data feed.")
        elif not scan:
            st.caption("No serial devices found.")
        else:
            table = pd.DataFrame(scan)[["device", "usb_id", "description", "status", "detail"]]
            st.dataframe(table, width="stretch", hide_index=True)


# ---------------------------------------------------------------- settings panel (last on the page)
with st.expander("Settings"):
    col_refresh, col_tariff = st.columns(2)
    with col_refresh:
        st.slider("Refresh (s)", 0.5, 5.0, 1.0, 0.5, key="refresh")
        st.button("Reset history and cost", on_click=reset_state)
    with col_tariff:
        st.caption("Tariff (placeholder rates, R/kWh)")
        for name, default in Tariff().rates.items():
            st.number_input(name, min_value=0.0, value=default, step=0.05, format="%.2f", key=f"rate_{name}")
