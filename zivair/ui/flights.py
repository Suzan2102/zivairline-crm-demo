"""
The Flights screen: find a flight, see its state, see who is on board.

Shape of the screen
-------------------
    filters  ->  summary tiles  ->  flight board  ->  detail of the selected flight

The board and the detail are driven by the same selection, so clicking a row
anywhere in the board swaps the card underneath it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from .. import config
from .. import queries as q
from . import theme as t

# Preset -> (days before today, days after today). None means "use the whole window".
DATE_PRESETS = {
    "Today": (0, 0),
    "Next 7 days": (0, 7),
    "Next 30 days": (0, 30),
    "Last 7 days": (7, 0),
    "Last 30 days": (30, 0),
    "Whole schedule": None,
}

BOARD_LIMIT = 800   # keep the table responsive; the UI says so when it bites


def render() -> None:
    t.page_header("Flight tracking", "Every ZivAirline flight, and who is on board")

    start, end, statuses, route_id, number = _filter_bar()
    board = q.list_flights(start, end, tuple(statuses), route_id, number, BOARD_LIMIT)

    _summary(board)
    if len(board) == BOARD_LIMIT:
        st.info(
            f"Showing the first {BOARD_LIMIT:,} flights. Narrow the period or the route "
            "to see the rest."
        )
    st.write("")

    if board.empty:
        t.empty_state("No flights match these filters. Widen the date range or clear a filter.")
        return

    flight_id = _flight_board(board)
    st.write("")
    _flight_detail(flight_id)


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
def _filter_bar() -> tuple[str, str, list[str], str | None, str | None]:
    c1, c2, c3, c4 = st.columns([1.1, 1.4, 1.6, 1], gap="medium")

    with c1:
        preset = st.selectbox("Period", list(DATE_PRESETS) + ["Custom range"], index=1)

    start, end = _preset_range(preset)
    if preset == "Custom range":
        with c1:
            window = q.data_window()
            picked = st.date_input(
                "Dates",
                value=(date.today(), date.today() + timedelta(days=7)),
                min_value=datetime.strptime(window["first_day"], "%Y-%m-%d").date(),
                max_value=datetime.strptime(window["last_day"], "%Y-%m-%d").date(),
                label_visibility="collapsed",
            )
            # date_input returns one date until the second one is picked.
            if isinstance(picked, tuple) and len(picked) == 2:
                start, end = picked[0].isoformat(), picked[1].isoformat()

    with c2:
        routes = q.route_options()
        labels = ["All routes"] + routes["label"].tolist()
        choice = st.selectbox("Route", labels)
        route_id = None if choice == "All routes" else \
            routes.loc[routes["label"] == choice, "route_id"].iloc[0]

    with c3:
        statuses = st.multiselect("Status", config.FLIGHT_STATUSES, default=[])

    with c4:
        number = st.text_input("Flight number", placeholder="ZV1...") or None

    return start, end, statuses, route_id, number


def _preset_range(preset: str) -> tuple[str, str]:
    if preset in DATE_PRESETS and DATE_PRESETS[preset] is not None:
        back, forward = DATE_PRESETS[preset]
        today = date.today()
        return (today - timedelta(days=back)).isoformat(), (today + timedelta(days=forward)).isoformat()
    window = q.data_window()          # "Whole schedule", and the default for "Custom range"
    return window["first_day"], window["last_day"]


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
def _summary(board: pd.DataFrame) -> None:
    cols = st.columns(4, gap="medium")
    flying = board[board["status"] != "Cancelled"] if not board.empty else board

    with cols[0]:
        t.kpi("Flights in view", f"{len(board):,}")
    with cols[1]:
        avg = flying["load_factor"].mean() if not flying.empty else 0
        t.kpi("Avg load factor", f"{avg:.1f}%", hint="Cancelled flights excluded")
    with cols[2]:
        disrupted = int((board["status"].isin(["Cancelled", "Delayed"])).sum()) if not board.empty else 0
        t.kpi("Disrupted", f"{disrupted}", delta=f"of {len(board)} flights",
              delta_good=disrupted == 0)
    with cols[3]:
        pax = int(board["our_passengers"].sum()) if not board.empty else 0
        t.kpi("Our passengers", f"{pax:,}", hint="Booked through this agency")


# --------------------------------------------------------------------------
# Board
# --------------------------------------------------------------------------
def _flight_board(board: pd.DataFrame) -> str:
    t.section("Flight board", f"{len(board)} flights · click a row to open it")

    event = st.dataframe(
        board,
        hide_index=True,
        width="stretch",
        height=380,
        on_select="rerun",
        selection_mode="single-row",
        key="flight_board",
        column_order=["flight_number", "leg", "destination", "flight_date", "departs",
                      "arrives", "status", "delay_minutes", "gate", "aircraft",
                      "load_factor", "our_passengers"],
        column_config={
            "flight_number": st.column_config.TextColumn("Flight", width="small"),
            "leg": st.column_config.TextColumn("Route", width="small"),
            "destination": st.column_config.TextColumn("To", width="small"),
            "flight_date": st.column_config.TextColumn("Date", width="small"),
            "departs": st.column_config.TextColumn("Dep", width="small"),
            "arrives": st.column_config.TextColumn("Arr", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "delay_minutes": st.column_config.NumberColumn("Delay", format="%d min", width="small"),
            "gate": st.column_config.TextColumn("Gate", width="small"),
            "aircraft": st.column_config.TextColumn("Aircraft"),
            "load_factor": st.column_config.ProgressColumn(
                "Load", format="%.0f%%", min_value=0, max_value=100
            ),
            "our_passengers": st.column_config.NumberColumn("Our pax", width="small"),
        },
    )

    rows = event.selection.rows if event and event.selection else []
    if rows:
        return board.iloc[rows[0]]["flight_id"]
    return board.iloc[0]["flight_id"]   # show the first flight until one is picked


# --------------------------------------------------------------------------
# Detail
# --------------------------------------------------------------------------
def _flight_detail(flight_id: str) -> None:
    f = q.flight_detail(flight_id)
    if not f:
        t.empty_state("That flight is no longer in the database.")
        return

    departure = datetime.strptime(f["departure_time"], "%Y-%m-%d %H:%M")
    arrival = datetime.strptime(f["arrival_time"], "%Y-%m-%d %H:%M")
    status_color = t.FLIGHT_STATUS_COLOR.get(f["status"], t.MUTED)

    t.section(
        f"{f['flight_number']}  ·  {f['origin_iata']} → {f['destination_iata']}",
        f"{f['origin_city']} to {f['destination_city']}, {f['country']} · {departure:%A, %d %B %Y}",
    )
    st.markdown(t.badge(f["status"], status_color), unsafe_allow_html=True)

    if f["status"] == "Cancelled":
        st.error("This flight is cancelled. Every ticket on it has been cancelled too.")
    elif f["delay_minutes"]:
        st.warning(
            f"Delayed by {f['delay_minutes']} minutes — "
            f"revised departure {departure + timedelta(minutes=f['delay_minutes']):%H:%M}."
        )

    hours, minutes = divmod(f["duration_minutes"], 60)
    t.fact_grid([
        ("Departs", f"{departure:%H:%M}"),
        ("Arrives", f"{arrival:%H:%M}"),
        ("Duration", f"{hours}h {minutes:02d}m"),
        ("Distance", f"{f['distance_km']:,} km"),
        ("Gate", f["gate"] or "—"),
        ("Aircraft", f"{f['aircraft']} ({f['tail_number']})"),
        ("Cabin", f"{f['seats_business']} business / {f['seats_economy']} economy"),
        ("Base fare", t.money(f["base_fare"])),
    ])

    manifest = q.flight_manifest(flight_id)
    left, right = st.columns([3, 1], gap="large")
    with left:
        _manifest_table(manifest, f)
    with right:
        _manifest_stats(manifest, f)


def _manifest_table(manifest: pd.DataFrame, f: dict) -> None:
    t.section("Passenger manifest", "Passengers this agency booked on the flight")
    if manifest.empty:
        t.empty_state("No passengers of ours on this flight.")
        return

    st.dataframe(
        manifest,
        hide_index=True,
        width="stretch",
        height=300,
        column_order=["seat", "cabin", "passenger", "loyalty_tier", "booking_id",
                      "channel", "baggage_count", "checked_in", "status", "fare"],
        column_config={
            "seat": st.column_config.TextColumn("Seat", width="small"),
            "cabin": st.column_config.TextColumn("Cabin", width="small"),
            "passenger": st.column_config.TextColumn("Passenger"),
            "loyalty_tier": st.column_config.TextColumn("Tier", width="small"),
            "booking_id": st.column_config.TextColumn("PNR", width="small"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "baggage_count": st.column_config.NumberColumn("Bags", width="small"),
            "checked_in": st.column_config.CheckboxColumn("Checked in", width="small"),
            "status": st.column_config.TextColumn("Ticket", width="small"),
            "fare": st.column_config.NumberColumn("Fare", format="$%.0f", width="small"),
        },
    )
    st.download_button(
        "Download manifest (CSV)",
        manifest.to_csv(index=False).encode("utf-8"),
        file_name=f"manifest_{f['flight_id']}.csv",
        mime="text/csv",
    )


def _manifest_stats(manifest: pd.DataFrame, f: dict) -> None:
    t.section("On this flight")

    live = manifest[manifest["status"] != "Cancelled"]
    business = int((live["cabin"] == "Business").sum())
    checked_in = int(live["checked_in"].sum())
    revenue = float(live["fare"].sum())

    t.fact_grid([
        ("Seats sold", f"{f['seats_sold']:,} of {f['seats_total']:,}"),
        ("Load factor", f"{100.0 * f['seats_sold'] / f['seats_total']:.0f}%"),
    ])
    t.fact_grid([
        ("Our passengers", f"{len(live)}"),
        ("Business / Economy", f"{business} / {len(live) - business}"),
        ("Checked in", f"{checked_in} of {len(live)}"),
        ("Our revenue", t.money(revenue)),
    ])

    cancelled = int((manifest["status"] == "Cancelled").sum())
    if cancelled:
        st.caption(f"{cancelled} cancelled ticket(s) are listed but excluded from these figures.")
