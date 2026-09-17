"""
The Customers screen: find a passenger, and see everything about them.

    filters -> customer list -> the 360 card of the selected customer

This is the first screen that *writes*: it can add a customer and edit one.
Both paths go through `queries.create_customer` / `queries.update_customer`,
which clear the read caches, so the list refreshes instead of showing the row
as it was a minute ago.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from .. import config, rules
from .. import queries as q
from . import theme as t

SELECTED = "customers_selected_id"   # session-state key for the open customer


def render() -> None:
    t.page_header("Customers", "Who is this passenger, and what are they worth to us")

    search, tiers, segments, countries = _filter_bar()
    people = q.list_customers(search, tuple(tiers), tuple(segments), tuple(countries))

    _new_customer_form()

    if people.empty:
        t.empty_state("No customer matches these filters.")
        return

    customer_id = _customer_list(people)
    st.write("")
    _profile(customer_id)


# --------------------------------------------------------------------------
# Filters and list
# --------------------------------------------------------------------------
def _filter_bar() -> tuple[str | None, list[str], list[str], list[str]]:
    c1, c2, c3, c4 = st.columns([1.6, 1.2, 1.2, 1.4], gap="medium")
    with c1:
        search = st.text_input("Search", placeholder="Name, email, phone or CU-00123") or None
    with c2:
        tiers = st.multiselect("Loyalty tier", config.LOYALTY_TIERS)
    with c3:
        segments = st.multiselect("Segment", config.CUSTOMER_SEGMENTS)
    with c4:
        countries = st.multiselect("Country", q.country_options())
    return search, tiers, segments, countries


def _customer_list(people: pd.DataFrame) -> str:
    t.section("Customers", f"{len(people)} match · most valuable first · click a row to open")

    event = st.dataframe(
        people,
        hide_index=True,
        width="stretch",
        height=300,
        on_select="rerun",
        selection_mode="single-row",
        key="customer_list",
        column_order=["customer_id", "name", "email", "country", "city", "segment",
                      "loyalty_tier", "loyalty_points", "bookings", "flights_flown",
                      "lifetime_value"],
        column_config={
            "customer_id": st.column_config.TextColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Name"),
            "email": st.column_config.TextColumn("Email"),
            "country": st.column_config.TextColumn("Country", width="small"),
            "city": st.column_config.TextColumn("City", width="small"),
            "segment": st.column_config.TextColumn("Segment", width="small"),
            "loyalty_tier": st.column_config.TextColumn("Tier", width="small"),
            "loyalty_points": st.column_config.NumberColumn("Points", format="%d", width="small"),
            "bookings": st.column_config.NumberColumn("Bookings", width="small"),
            "flights_flown": st.column_config.NumberColumn("Flown", width="small"),
            "lifetime_value": st.column_config.NumberColumn("Lifetime value", format="$%.0f"),
        },
    )

    rows = event.selection.rows if event and event.selection else []
    if rows:
        st.session_state[SELECTED] = people.iloc[rows[0]]["customer_id"]
    # Keep the open customer across reruns, as long as they survive the filters.
    if st.session_state.get(SELECTED) in set(people["customer_id"]):
        return st.session_state[SELECTED]
    return people.iloc[0]["customer_id"]


# --------------------------------------------------------------------------
# The 360 card
# --------------------------------------------------------------------------
def _profile(customer_id: str) -> None:
    c = q.customer_profile(customer_id)
    if not c:
        t.empty_state("That customer is no longer in the database.")
        return

    t.section(f"{c['name']}  ·  {c['customer_id']}",
              f"Customer since {c['member_since']} · {c['city']}, {c['country']}")
    st.markdown(
        t.badge(c["loyalty_tier"], t.TIER_COLOR.get(c["loyalty_tier"], t.MUTED))
        + "&nbsp;&nbsp;"
        + t.badge(c["segment"], t.SERIES[0] if c["segment"] == "Leisure" else t.SERIES[6]),
        unsafe_allow_html=True,
    )

    _profile_kpis(c)
    t.fact_grid([
        ("Email", c["email"]),
        ("Phone", c["phone"]),
        ("Date of birth", c["birth_date"]),
        ("Passport", c["passport_number"]),
        ("Marketing", "Opted in" if c["marketing_optin"] else "Opted out"),
        ("Last flight", _pretty(c["last_flight"])),
        ("Next flight", _pretty(c["next_flight"])),
    ])

    flights_tab, bookings_tab, service_tab = st.tabs(
        ["Flight history", "Bookings", "Service log"]
    )
    with flights_tab:
        _flights(customer_id)
    with bookings_tab:
        _bookings(customer_id)
    with service_tab:
        _service_log(customer_id)

    _edit_form(c)


def _profile_kpis(c: dict) -> None:
    cols = st.columns(4, gap="medium")
    with cols[0]:
        t.kpi("Lifetime value", t.money(c["lifetime_value"]),
              hint=f"{c['bookings']} bookings")
    with cols[1]:
        t.kpi("Flights flown", f"{c['flights_flown']}", hint="Completed tickets")
    with cols[2]:
        nxt, needed = rules.points_to_next_tier(c["loyalty_points"])
        t.kpi("Loyalty points", f"{c['loyalty_points']:,}",
              hint=f"{needed:,} to {nxt}" if nxt else "Top tier reached")
    with cols[3]:
        open_cases = c["open_cases"]
        t.kpi("Open service cases", f"{open_cases}",
              delta="needs attention" if open_cases else "all clear",
              delta_good=open_cases == 0)


def _pretty(value: str | None) -> str:
    if not value:
        return "—"
    return f"{datetime.strptime(value, '%Y-%m-%d %H:%M'):%d %b %Y, %H:%M}"


# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
def _flights(customer_id: str) -> None:
    df = q.customer_flights(customer_id)
    if df.empty:
        t.empty_state("This customer has never flown with us.")
        return
    flown = int((df["ticket_status"] == "Flown").sum())
    upcoming = int((df["ticket_status"] == "Confirmed").sum())
    st.caption(f"{len(df)} tickets · {flown} flown · {upcoming} upcoming · "
               f"{int(df.loc[df['ticket_status'] == 'Flown', 'distance_km'].sum()):,} km flown")
    st.dataframe(
        df, hide_index=True, width="stretch", height=280,
        column_order=["departure_time", "flight_number", "leg", "destination", "cabin",
                      "seat", "fare", "ticket_status", "flight_status", "booking_id"],
        column_config={
            "departure_time": st.column_config.TextColumn("Departure"),
            "flight_number": st.column_config.TextColumn("Flight", width="small"),
            "leg": st.column_config.TextColumn("Route", width="small"),
            "destination": st.column_config.TextColumn("To", width="small"),
            "cabin": st.column_config.TextColumn("Cabin", width="small"),
            "seat": st.column_config.TextColumn("Seat", width="small"),
            "fare": st.column_config.NumberColumn("Fare", format="$%.0f", width="small"),
            "ticket_status": st.column_config.TextColumn("Ticket", width="small"),
            "flight_status": st.column_config.TextColumn("Flight status", width="small"),
            "booking_id": st.column_config.TextColumn("PNR", width="small"),
        },
    )


def _bookings(customer_id: str) -> None:
    df = q.customer_bookings(customer_id)
    if df.empty:
        t.empty_state("No bookings on file.")
        return
    st.dataframe(
        df, hide_index=True, width="stretch", height=280,
        column_order=["booking_id", "booking_date", "channel", "agent", "tickets",
                      "status", "payment_status", "total_amount", "notes"],
        column_config={
            "booking_id": st.column_config.TextColumn("PNR", width="small"),
            "booking_date": st.column_config.TextColumn("Booked"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "agent": st.column_config.TextColumn("Agent"),
            "tickets": st.column_config.NumberColumn("Legs", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "payment_status": st.column_config.TextColumn("Payment", width="small"),
            "total_amount": st.column_config.NumberColumn("Total", format="$%.0f", width="small"),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )


def _service_log(customer_id: str) -> None:
    df = q.customer_interactions(customer_id)
    if df.empty:
        t.empty_state("This customer has never contacted us.")
        return
    open_cases = df[df["status"] != "Resolved"]
    st.caption(f"{len(df)} contacts · {len(open_cases)} still open")
    st.dataframe(
        df, hide_index=True, width="stretch", height=280,
        column_order=["created_at", "channel", "topic", "subject", "priority",
                      "status", "agent", "resolved_at", "booking_id"],
        column_config={
            "created_at": st.column_config.TextColumn("Opened"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "topic": st.column_config.TextColumn("Topic", width="small"),
            "subject": st.column_config.TextColumn("Subject"),
            "priority": st.column_config.TextColumn("Priority", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "agent": st.column_config.TextColumn("Agent"),
            "resolved_at": st.column_config.TextColumn("Resolved"),
            "booking_id": st.column_config.TextColumn("PNR", width="small"),
        },
    )


# --------------------------------------------------------------------------
# Forms (the write paths)
# --------------------------------------------------------------------------
def _customer_fields(prefix: str, existing: dict | None = None) -> dict:
    """The shared field layout of the add and the edit form."""
    e = existing or {}
    countries = q.country_options()

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        first = st.text_input("First name *", value=e.get("first_name", ""), key=f"{prefix}_first")
        last = st.text_input("Last name *", value=e.get("last_name", ""), key=f"{prefix}_last")
        email = st.text_input("Email *", value=e.get("email", ""), key=f"{prefix}_email")
    with c2:
        phone = st.text_input("Phone", value=e.get("phone", ""), key=f"{prefix}_phone")
        country = st.selectbox(
            "Country", countries,
            index=countries.index(e["country"]) if e.get("country") in countries else 0,
            key=f"{prefix}_country",
        )
        city = st.text_input("City", value=e.get("city", ""), key=f"{prefix}_city")
    with c3:
        birth = st.date_input(
            "Date of birth",
            value=_as_date(e.get("birth_date"), date(1990, 1, 1)),
            min_value=date(1920, 1, 1), max_value=date.today(),
            key=f"{prefix}_birth",
        )
        passport = st.text_input("Passport number", value=e.get("passport_number", ""),
                                 key=f"{prefix}_passport")
        segment = st.selectbox(
            "Segment", config.CUSTOMER_SEGMENTS,
            index=config.CUSTOMER_SEGMENTS.index(e.get("segment", "Leisure")),
            key=f"{prefix}_segment",
        )

    c4, c5 = st.columns([1, 2], gap="medium")
    with c4:
        points = st.number_input("Loyalty points", min_value=0, step=100,
                                 value=int(e.get("loyalty_points", 0)), key=f"{prefix}_points")
    with c5:
        optin = st.checkbox("Opted in to marketing", value=bool(e.get("marketing_optin", False)),
                            key=f"{prefix}_optin")
        # The tier is derived, never typed - rule BR-6.
        st.caption(f"Loyalty tier is derived from the points: **{rules.tier_for_points(points)}**")

    return {
        "first_name": first.strip(), "last_name": last.strip(), "email": email.strip(),
        "phone": phone.strip(), "birth_date": birth.isoformat(), "country": country,
        "city": city.strip(), "passport_number": passport.strip(), "segment": segment,
        "loyalty_points": int(points), "marketing_optin": optin,
    }


def _validate(data: dict, exclude_customer_id: str | None = None) -> list[str]:
    problems = []
    if not data["first_name"] or not data["last_name"]:
        problems.append("First and last name are required.")
    if "@" not in data["email"] or "." not in data["email"].split("@")[-1]:
        problems.append("A valid email address is required.")
    elif q.email_taken(data["email"], exclude_customer_id):
        problems.append(f"Another customer already uses {data['email']}.")
    return problems


def _new_customer_form() -> None:
    with st.expander("Add a new customer"):
        with st.form("new_customer", clear_on_submit=False):
            data = _customer_fields("new")
            submitted = st.form_submit_button("Create customer", type="primary")

        if submitted:
            problems = _validate(data)
            if problems:
                for p in problems:
                    st.error(p)
                return
            data["member_since"] = date.today().isoformat()
            customer_id = q.create_customer(data)
            st.session_state[SELECTED] = customer_id
            st.success(f"Created {customer_id} — {data['first_name']} {data['last_name']}.")
            st.rerun()


def _edit_form(c: dict) -> None:
    with st.expander(f"Edit {c['name']}"):
        with st.form(f"edit_{c['customer_id']}"):
            data = _customer_fields(f"edit_{c['customer_id']}", c)
            submitted = st.form_submit_button("Save changes", type="primary")

        if submitted:
            problems = _validate(data, exclude_customer_id=c["customer_id"])
            if problems:
                for p in problems:
                    st.error(p)
                return
            q.update_customer(c["customer_id"], data)
            st.success(f"Saved {c['customer_id']}.")
            st.rerun()


def _as_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    return datetime.strptime(value, "%Y-%m-%d").date()
