"""
Screens that are still on the roadmap. They are real pages in the navigation so
the shape of the finished product is visible from day one - each one says which
phase delivers it and what it will do.
"""

from __future__ import annotations

import streamlit as st

from . import theme as t

_PLANNED = {
    "Bookings": (
        5,
        "Booking management",
        [
            "Book a customer onto a flight, choosing from free seats only",
            "Automatic pricing by cabin, distance, lead time and loyalty tier",
            "Change a seat, check a passenger in, cancel a booking",
            "Look up a booking by its PNR",
        ],
    ),
    "Reports": (
        6,
        "Reports and analytics",
        [
            "Revenue by route and by destination",
            "Booking channel mix over time",
            "Loyalty tier distribution",
            "Agent performance, and CSV export",
        ],
    ),
}


def _render(name: str) -> None:
    phase, title, bullets = _PLANNED[name]
    t.page_header(title, f"Planned for Phase {phase}")
    st.info(f"**{name}** arrives in Phase {phase}. Planned scope:")
    for b in bullets:
        st.markdown(f"- {b}")
    st.caption("Dashboard, Flights and Customers are already built - try them from the sidebar.")


def bookings() -> None:
    _render("Bookings")


def reports() -> None:
    _render("Reports")
