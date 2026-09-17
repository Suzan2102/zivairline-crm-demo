"""
The Dashboard screen: how is the airline doing right now, and what is about to
go wrong. Everything here is read-only.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from .. import queries as q
from . import theme as t


def render() -> None:
    t.page_header(
        "Operations Dashboard",
        f"ZivAirline CRM  ·  {datetime.now():%A, %d %B %Y  ·  %H:%M}",
    )

    kpis = q.kpi_snapshot()
    _kpi_row(kpis)

    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        _revenue_trend()
    with right:
        _status_breakdown()

    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        _top_routes()
    with right:
        _channel_mix()

    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        _departure_board()
    with right:
        _attention_feed()


# --------------------------------------------------------------------------
# KPI row
# --------------------------------------------------------------------------
def _kpi_row(k: dict) -> None:
    cols = st.columns(5, gap="medium")

    with cols[0]:
        today, yesterday = k.get("flights_today", 0), k.get("flights_yesterday", 0)
        diff = today - yesterday
        t.kpi(
            "Flights today", f"{today}",
            delta=f"{diff:+d} vs yesterday" if diff else "same as yesterday",
            delta_good=None,
        )

    with cols[1]:
        load, prev = k.get("load_factor_30d") or 0, k.get("load_factor_prev") or 0
        diff = load - prev
        t.kpi(
            "Avg load factor", f"{load:.1f}%",
            delta=f"{diff:+.1f} pts vs prior 30d",
            delta_good=diff >= 0,
            hint="Seats sold vs available",
        )

    with cols[2]:
        rev, prev = k.get("revenue_30d") or 0, k.get("revenue_prev") or 0
        pct = ((rev - prev) / prev * 100) if prev else 0
        t.kpi(
            "Revenue, 30 days", t.money(rev),
            delta=f"{pct:+.1f}% vs prior 30d",
            delta_good=pct >= 0,
        )

    with cols[3]:
        t.kpi(
            "Active bookings", f"{k.get('active_bookings', 0):,}",
            hint=f"{k.get('customers', 0):,} customers on file",
        )

    with cols[4]:
        urgent = k.get("urgent_cases", 0)
        t.kpi(
            "Open service cases", f"{k.get('open_cases', 0):,}",
            delta=f"{urgent} high priority" if urgent else "none urgent",
            delta_good=urgent == 0,
        )


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def _revenue_trend() -> None:
    t.section("Revenue trend", "Booking value per day, last 30 days")
    df = q.revenue_by_day(30)
    if df.empty:
        t.empty_state("No bookings in the last 30 days.")
        return
    fig = t.line_chart(
        df, x="day", y="revenue",
        hover="<b>%{x|%d %b}</b><br>$%{y:,.0f}",
        height=268,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _status_breakdown() -> None:
    t.section("Flights by status", "Across the whole scheduling window")
    df = q.flight_status_breakdown()
    if df.empty:
        t.empty_state("No flights on file.")
        return
    fig = t.status_bar(df, "status", "flights", t.FLIGHT_STATUS_COLOR, height=268)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _top_routes() -> None:
    t.section("Top routes by revenue", "Tickets this agency sold")
    df = q.top_routes(8)
    if df.empty:
        t.empty_state("No ticket revenue yet.")
        return
    fig = t.ranked_bar(df, "leg", "revenue", lambda v: f"${v:,.0f}", height=270)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _channel_mix() -> None:
    t.section("Booking channels", "Where the business comes from")
    df = q.channel_mix()
    if df.empty:
        t.empty_state("No bookings on file.")
        return
    fig = t.ranked_bar(df, "channel", "revenue", lambda v: f"${v:,.0f}",
                       color=t.SERIES[1], height=270)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# --------------------------------------------------------------------------
# Lists
# --------------------------------------------------------------------------
def _departure_board() -> None:
    df = q.departures_today()
    t.section("Today's departures", f"{len(df)} flights scheduled")
    if df.empty:
        t.empty_state("No flights scheduled for today.")
        return

    board = df[["flight_number", "leg", "destination", "departs",
                "status", "gate", "load_factor", "our_passengers"]]
    st.dataframe(
        board,
        hide_index=True,
        width="stretch",
        height=360,
        column_config={
            "flight_number": st.column_config.TextColumn("Flight", width="small"),
            "leg": st.column_config.TextColumn("Route", width="small"),
            "destination": st.column_config.TextColumn("To", width="small"),
            "departs": st.column_config.TextColumn("Dep", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "gate": st.column_config.TextColumn("Gate", width="small"),
            "load_factor": st.column_config.ProgressColumn(
                "Load", format="%.0f%%", min_value=0, max_value=100
            ),
            "our_passengers": st.column_config.NumberColumn("Our pax", width="small"),
        },
    )


def _attention_feed() -> None:
    t.section("Needs attention", "Next 7 days")

    disrupted = q.disrupted_flights(7)
    cases = q.open_service_cases(5)

    if disrupted.empty and cases.empty:
        t.empty_state("Nothing outstanding. All flights on schedule.")
        return

    for _, row in disrupted.iterrows():
        cancelled = row["status"] == "Cancelled"
        when = datetime.strptime(row["departure_time"], "%Y-%m-%d %H:%M")
        detail = "cancelled" if cancelled else f"delayed {row['delay_minutes']} min"
        t.alert_row(
            f"{row['flight_number']}  {row['leg']} — {detail}",
            f"{when:%d %b, %H:%M}  ·  {row['affected_passengers']} of our passengers affected",
            level="critical" if cancelled else "serious",
        )

    for _, row in cases.iterrows():
        t.alert_row(
            f"{row['subject']}",
            f"{row['customer']} ({row['loyalty_tier']})  ·  {row['priority']} priority"
            f"  ·  {row['status']}  ·  {row['agent']}",
            level="critical" if row["priority"] == "High" else "warning",
        )
