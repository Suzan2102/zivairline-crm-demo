"""
ZivAirline CRM - Streamlit entry point.

Run with:  streamlit run app.py

This file does three things and nothing else: configure the page, make sure the
database exists, and wire the navigation. Every screen lives in `zivair/ui/`.
"""

from __future__ import annotations

import streamlit as st

from zivair import config
from zivair.database import database_exists
from zivair.ui import customers, dashboard, flights, placeholders, theme

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _database_missing_screen() -> None:
    """Shown instead of the app when the demo database has not been built yet."""
    theme.page_header("ZivAirline CRM", "The demo database has not been generated yet")
    st.error(f"No database found at `{config.DB_PATH}`.")
    st.markdown("Generate the synthetic data first, then reload this page:")
    st.code("python -m zivair.seed_data", language="bash")


def _sidebar() -> None:
    from zivair import queries as q

    st.sidebar.markdown(f"### ✈️ {config.AIRLINE_NAME}")
    st.sidebar.caption("Travel agent CRM")

    window = q.data_window()
    if window:
        st.sidebar.divider()
        st.sidebar.caption(
            f"**{window['flights']:,} flights** on file\n\n"
            f"{window['first_day']} → {window['last_day']}"
        )
    st.sidebar.divider()
    if st.sidebar.button("Refresh data", width="stretch"):
        q.clear_caches()
        st.rerun()
    st.sidebar.caption("Demo data. Regenerate with `python -m zivair.seed_data`.")


def main() -> None:
    theme.inject_css()

    if not database_exists():
        _database_missing_screen()
        return

    _sidebar()

    pages = [
        st.Page(dashboard.render, title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page(flights.render, title="Flights", icon=":material/flight:"),
        st.Page(customers.render, title="Customers", icon=":material/group:"),
        st.Page(placeholders.bookings, title="Bookings", icon=":material/confirmation_number:"),
        st.Page(placeholders.reports, title="Reports", icon=":material/bar_chart:"),
    ]
    st.navigation(pages).run()


main()
