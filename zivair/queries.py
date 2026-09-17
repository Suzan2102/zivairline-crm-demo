"""
The query layer: every question the UI asks the database lives here.

Rules of the layer
------------------
* The UI never writes SQL - it calls a function from this module.
* This module never draws anything - it returns DataFrames, dicts or scalars.
* Results are cached by Streamlit for a minute. Any screen that *writes* must
  call `clear_caches()` afterwards, otherwise it will keep reading stale rows.

All times in the database are local text ('YYYY-MM-DD HH:MM'), so 'now' in SQL
is always written as `datetime('now','localtime')`.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .database import query_df, query_one

CACHE_TTL = 60  # seconds

# `now` / `today` as SQLite expressions - spelled once, used everywhere.
NOW = "datetime('now','localtime')"
TODAY = "date('now','localtime')"

# Reused joins. Keeping them as constants stops the same 5-line JOIN from being
# retyped (and mistyped) in a dozen queries.
FLIGHT_JOIN = """
    FROM flights f
    JOIN routes   r ON r.route_id = f.route_id
    JOIN airports o ON o.iata = r.origin_iata
    JOIN airports d ON d.iata = r.destination_iata
    JOIN aircraft a ON a.tail_number = f.tail_number
"""


def clear_caches() -> None:
    """Drop every cached query result - call after any INSERT/UPDATE/DELETE."""
    st.cache_data.clear()


# --------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL)
def kpi_snapshot() -> dict:
    """
    The five numbers at the top of the dashboard, each with the equivalent
    figure for the previous period so the UI can show a delta.
    """
    row = query_one(
        f"""
        SELECT
          (SELECT COUNT(*) FROM flights
             WHERE date(departure_time) = {TODAY})                       AS flights_today,

          (SELECT COUNT(*) FROM flights
             WHERE date(departure_time) = date('now','localtime','-1 day')) AS flights_yesterday,

          (SELECT ROUND(AVG(1.0 * seats_sold / seats_total) * 100, 1) FROM flights
             WHERE status <> 'Cancelled'
               AND departure_time BETWEEN datetime('now','localtime','-30 days') AND {NOW}
          ) AS load_factor_30d,

          (SELECT ROUND(AVG(1.0 * seats_sold / seats_total) * 100, 1) FROM flights
             WHERE status <> 'Cancelled'
               AND departure_time BETWEEN datetime('now','localtime','-60 days')
                                      AND datetime('now','localtime','-30 days')
          ) AS load_factor_prev,

          (SELECT COALESCE(SUM(total_amount), 0) FROM bookings
             WHERE status <> 'Cancelled'
               AND booking_date >= datetime('now','localtime','-30 days')) AS revenue_30d,

          (SELECT COALESCE(SUM(total_amount), 0) FROM bookings
             WHERE status <> 'Cancelled'
               AND booking_date BETWEEN datetime('now','localtime','-60 days')
                                    AND datetime('now','localtime','-30 days')) AS revenue_prev,

          (SELECT COUNT(*) FROM bookings WHERE status = 'Confirmed')       AS active_bookings,

          (SELECT COUNT(*) FROM interactions
             WHERE status IN ('Open','In Progress'))                       AS open_cases,

          (SELECT COUNT(*) FROM interactions
             WHERE status IN ('Open','In Progress') AND priority = 'High') AS urgent_cases,

          (SELECT COUNT(*) FROM customers)                                 AS customers
        """
    )
    return dict(row) if row else {}


# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL)
def revenue_by_day(days: int = 30) -> pd.DataFrame:
    """Booking revenue per calendar day, for the trend line."""
    return query_df(
        f"""
        SELECT date(booking_date) AS day,
               ROUND(SUM(total_amount), 2) AS revenue,
               COUNT(*) AS bookings
        FROM bookings
        WHERE status <> 'Cancelled'
          AND booking_date >= date('now','localtime','-{int(days)} days')
        GROUP BY day
        ORDER BY day
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def load_factor_by_day(days: int = 30) -> pd.DataFrame:
    """Average load factor of the flights that departed on each day."""
    return query_df(
        f"""
        SELECT date(departure_time) AS day,
               ROUND(AVG(1.0 * seats_sold / seats_total) * 100, 1) AS load_factor,
               COUNT(*) AS flights
        FROM flights
        WHERE status <> 'Cancelled'
          AND departure_time BETWEEN date('now','localtime','-{int(days)} days') AND {NOW}
        GROUP BY day
        ORDER BY day
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def top_routes(limit: int = 8) -> pd.DataFrame:
    """Highest-earning routes, measured on the tickets this agency sold."""
    return query_df(
        """
        SELECT r.route_id,
               r.origin_iata || ' -> ' || r.destination_iata AS leg,
               d.city AS destination_city,
               COUNT(t.ticket_id) AS passengers,
               ROUND(SUM(t.fare), 2) AS revenue
        FROM tickets t
        JOIN flights  f ON f.flight_id = t.flight_id
        JOIN routes   r ON r.route_id = f.route_id
        JOIN airports d ON d.iata = r.destination_iata
        WHERE t.status <> 'Cancelled'
        GROUP BY r.route_id
        ORDER BY revenue DESC
        LIMIT ?
        """,
        (limit,),
    )


@st.cache_data(ttl=CACHE_TTL)
def channel_mix() -> pd.DataFrame:
    """How bookings reach the agency."""
    return query_df(
        """
        SELECT channel,
               COUNT(*) AS bookings,
               ROUND(SUM(total_amount), 2) AS revenue
        FROM bookings
        WHERE status <> 'Cancelled'
        GROUP BY channel
        ORDER BY revenue DESC
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def flight_status_breakdown() -> pd.DataFrame:
    """Flight counts per operational status, across the whole window."""
    return query_df(
        """
        SELECT status, COUNT(*) AS flights
        FROM flights
        GROUP BY status
        ORDER BY flights DESC
        """
    )


# --------------------------------------------------------------------------
# Operational lists
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL)
def departures_today() -> pd.DataFrame:
    """Today's board, in departure order."""
    return query_df(
        f"""
        SELECT f.flight_number,
               r.origin_iata || ' -> ' || r.destination_iata AS leg,
               d.city AS destination,
               substr(f.departure_time, 12, 5) AS departs,
               substr(f.arrival_time, 12, 5)   AS arrives,
               f.status,
               f.delay_minutes,
               f.gate,
               a.model AS aircraft,
               f.seats_sold,
               f.seats_total,
               ROUND(100.0 * f.seats_sold / f.seats_total, 1) AS load_factor,
               (SELECT COUNT(*) FROM tickets t
                 WHERE t.flight_id = f.flight_id AND t.status <> 'Cancelled') AS our_passengers
        {FLIGHT_JOIN}
        WHERE date(f.departure_time) = {TODAY}
        ORDER BY f.departure_time
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def disrupted_flights(days_ahead: int = 7) -> pd.DataFrame:
    """Upcoming flights that need the agent's attention: cancelled or delayed."""
    return query_df(
        f"""
        SELECT f.flight_id,
               f.flight_number,
               r.origin_iata || ' -> ' || r.destination_iata AS leg,
               f.departure_time,
               f.status,
               f.delay_minutes,
               -- On a cancelled flight every ticket is marked Cancelled too, so
               -- counting only live tickets there would always report zero.
               (SELECT COUNT(*) FROM tickets t
                 WHERE t.flight_id = f.flight_id
                   AND (t.status <> 'Cancelled' OR f.status = 'Cancelled')) AS affected_passengers
        {FLIGHT_JOIN}
        WHERE f.status IN ('Cancelled','Delayed')
          AND f.departure_time BETWEEN {NOW} AND datetime('now','localtime','+{int(days_ahead)} days')
        ORDER BY f.departure_time
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def open_service_cases(limit: int = 10) -> pd.DataFrame:
    """The service queue, worst first."""
    return query_df(
        """
        SELECT i.interaction_id,
               i.created_at,
               c.first_name || ' ' || c.last_name AS customer,
               c.loyalty_tier,
               i.topic,
               i.subject,
               i.priority,
               i.status,
               ag.full_name AS agent
        FROM interactions i
        JOIN customers c  ON c.customer_id = i.customer_id
        JOIN agents   ag  ON ag.agent_id = i.agent_id
        WHERE i.status IN ('Open','In Progress')
        ORDER BY CASE i.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,
                 i.created_at
        LIMIT ?
        """,
        (limit,),
    )


# --------------------------------------------------------------------------
# Small shared lookups (used by later phases too)
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL)
def data_window() -> dict:
    """First and last flight in the database - shown in the sidebar."""
    row = query_one(
        "SELECT MIN(date(departure_time)) AS first_day, "
        "       MAX(date(departure_time)) AS last_day, "
        "       COUNT(*) AS flights FROM flights"
    )
    return dict(row) if row else {}


# --------------------------------------------------------------------------
# Flights module (Phase 3)
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL)
def route_options() -> pd.DataFrame:
    """Every route, labelled for a dropdown."""
    return query_df(
        """
        SELECT r.route_id,
               r.origin_iata || ' -> ' || r.destination_iata || '  (' || d.city || ')' AS label
        FROM routes r
        JOIN airports d ON d.iata = r.destination_iata
        ORDER BY label
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def list_flights(
    start_date: str,
    end_date: str,
    statuses: tuple[str, ...] = (),
    route_id: str | None = None,
    flight_number: str | None = None,
    limit: int = 800,
) -> pd.DataFrame:
    """
    The flight board, filtered.

    The WHERE clause is assembled from whichever filters the agent actually set.
    Note that every value still goes in as a bound parameter - the only thing
    built by string concatenation is the number of '?' placeholders, never a
    value. That is what keeps this safe from SQL injection.
    """
    where = ["date(f.departure_time) BETWEEN ? AND ?"]
    params: list = [start_date, end_date]

    if statuses:
        where.append(f"f.status IN ({','.join('?' * len(statuses))})")
        params.extend(statuses)
    if route_id:
        where.append("f.route_id = ?")
        params.append(route_id)
    if flight_number:
        where.append("f.flight_number LIKE ?")
        params.append(f"%{flight_number.strip().upper()}%")

    params.append(limit)
    return query_df(
        f"""
        SELECT f.flight_id,
               f.flight_number,
               r.origin_iata || ' -> ' || r.destination_iata AS leg,
               d.city AS destination,
               date(f.departure_time) AS flight_date,
               substr(f.departure_time, 12, 5) AS departs,
               substr(f.arrival_time, 12, 5)   AS arrives,
               f.status,
               f.delay_minutes,
               f.gate,
               a.model AS aircraft,
               f.seats_total,
               f.seats_sold,
               ROUND(100.0 * f.seats_sold / f.seats_total, 1) AS load_factor,
               (SELECT COUNT(*) FROM tickets t
                 WHERE t.flight_id = f.flight_id
                   AND (t.status <> 'Cancelled' OR f.status = 'Cancelled')) AS our_passengers
        {FLIGHT_JOIN}
        WHERE {' AND '.join(where)}
        ORDER BY f.departure_time
        LIMIT ?
        """,
        params,
    )


@st.cache_data(ttl=CACHE_TTL)
def flight_detail(flight_id: str) -> dict:
    """Everything known about one flight, for the detail card."""
    row = query_one(
        f"""
        SELECT f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
               f.status, f.delay_minutes, f.gate, f.seats_total, f.seats_sold,
               f.base_fare, f.tail_number,
               r.route_id, r.origin_iata, r.destination_iata,
               r.distance_km, r.duration_minutes,
               o.city AS origin_city, o.name AS origin_name,
               d.city AS destination_city, d.name AS destination_name, d.country,
               a.model AS aircraft, a.body_type, a.year_built,
               a.seats_economy, a.seats_business
        {FLIGHT_JOIN}
        WHERE f.flight_id = ?
        """,
        (flight_id,),
    )
    return dict(row) if row else {}


@st.cache_data(ttl=CACHE_TTL)
def flight_manifest(flight_id: str) -> pd.DataFrame:
    """
    Who this agency has on board. Seats sort numerically: CAST('12A' AS INTEGER)
    is 12, so row 2 comes before row 12 instead of after it.
    """
    return query_df(
        """
        SELECT t.ticket_id,
               t.seat,
               t.cabin,
               c.first_name || ' ' || c.last_name AS passenger,
               c.customer_id,
               c.loyalty_tier,
               c.segment,
               c.passport_number,
               b.booking_id,
               b.channel,
               t.baggage_count,
               t.checked_in,
               t.status,
               t.fare
        FROM tickets t
        JOIN bookings  b ON b.booking_id = t.booking_id
        JOIN customers c ON c.customer_id = b.customer_id
        WHERE t.flight_id = ?
        ORDER BY CASE t.cabin WHEN 'Business' THEN 0 ELSE 1 END,
                 CAST(t.seat AS INTEGER), t.seat
        """,
        (flight_id,),
    )
