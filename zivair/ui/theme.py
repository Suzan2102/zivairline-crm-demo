"""
The look of the app: palette, CSS, and the small building blocks every screen
reuses (page header, KPI tiles, status badges, chart styling).

About the palette
-----------------
The colours below are a pre-validated data-visualisation palette: the eight
categorical hues are ordered so that every adjacent pair stays distinguishable
under colour-vision deficiency, and the status colours are deliberately kept
apart from the series colours so a "warning" can never be mistaken for a series.

Three rules the charts in this app follow:
  1. Categorical hues are assigned in fixed order, never cycled.
  2. Magnitude (a ranking) gets ONE hue, not eight - colour would be noise there.
  3. A status colour always ships with its text label, never colour alone.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- surfaces and ink -----------------------------------------------------
SURFACE = "#fcfcfb"      # cards and chart plotting area
PAGE = "#f9f9f7"         # page background
INK = "#0b0b0b"          # primary text
INK_SOFT = "#52514e"     # secondary text
MUTED = "#898781"        # axis labels, captions
GRID = "#e1e0d9"         # hairline gridlines
AXIS = "#c3c2b7"         # baseline
BORDER = "rgba(11,11,11,0.10)"

# --- brand ----------------------------------------------------------------
BRAND_DEEP = "#0d366b"   # header bar - the darkest step of the blue ramp
BRAND = "#2a78d6"        # primary accent

# --- categorical series (fixed order) -------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# --- status (reserved - never used as a series colour) --------------------
GOOD = "#0ca30c"
WARNING = "#fab219"
SERIOUS = "#ec835a"
CRITICAL = "#d03b3b"

FLIGHT_STATUS_COLOR = {
    "Scheduled": BRAND,
    "Boarding": WARNING,
    "Departed": "#4a3aa7",
    "Landed": GOOD,
    "Delayed": SERIOUS,
    "Cancelled": CRITICAL,
}

PRIORITY_COLOR = {"High": CRITICAL, "Medium": WARNING, "Low": MUTED}
TIER_COLOR = {"Platinum": "#4a3aa7", "Gold": "#eda100", "Silver": MUTED, "Basic": INK_SOFT}

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def rgba(hex_color: str, alpha: float) -> str:
    """Plotly only accepts rgba() for transparency - 8-digit hex is rejected."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
def inject_css() -> None:
    """One stylesheet for the whole app. Called once per rerun from app.py."""
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {PAGE}; }}
        .block-container {{ padding-top: 1.6rem; max-width: 1400px; }}

        /* ---- page header ---- */
        .zv-header {{
            display: flex; align-items: center; gap: .9rem;
            background: {BRAND_DEEP};
            border-radius: 12px; padding: 1rem 1.3rem; margin-bottom: 1.25rem;
        }}
        .zv-logo {{
            width: 38px; height: 38px; border-radius: 9px; flex: 0 0 auto;
            background: {BRAND}; color: #fff; font-weight: 700; font-size: 1.05rem;
            display: flex; align-items: center; justify-content: center;
        }}
        .zv-header h1 {{ color: #fff; font-size: 1.28rem; margin: 0; font-weight: 650; }}
        .zv-header p  {{ color: #c9d8ec; font-size: .85rem; margin: .12rem 0 0; }}

        /* ---- KPI tiles ---- */
        .zv-kpi {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: .85rem 1rem; height: 100%; min-height: 122px;
        }}
        .zv-kpi .label {{
            color: {MUTED}; font-size: .72rem; font-weight: 600;
            letter-spacing: .05em; text-transform: uppercase;
        }}
        .zv-kpi .value {{
            color: {INK}; font-size: 1.75rem; font-weight: 640;
            line-height: 1.15; margin-top: .3rem;
        }}
        .zv-kpi .delta {{ font-size: .8rem; font-weight: 600; margin-top: .18rem; }}
        .zv-kpi .hint  {{ color: {MUTED}; font-size: .74rem; margin-top: .18rem; }}

        /* ---- section titles ---- */
        .zv-section {{
            color: {INK}; font-size: 1.02rem; font-weight: 640;
            margin: .4rem 0 .1rem;
        }}
        .zv-sub {{ color: {MUTED}; font-size: .8rem; margin: 0 0 .5rem; }}

        /* ---- badges ---- */
        .zv-badge {{
            display: inline-flex; align-items: center; gap: .35rem;
            padding: .12rem .5rem; border-radius: 999px;
            font-size: .74rem; font-weight: 600; white-space: nowrap;
        }}
        .zv-dot {{ width: .5rem; height: .5rem; border-radius: 999px; flex: 0 0 auto; }}

        /* ---- alert rows ---- */
        .zv-row {{
            background: {SURFACE}; border: 1px solid {BORDER};
            border-left: 3px solid {MUTED};
            border-radius: 9px; padding: .55rem .75rem; margin-bottom: .45rem;
        }}
        .zv-row .title {{ color: {INK}; font-size: .85rem; font-weight: 600; }}
        .zv-row .meta  {{ color: {MUTED}; font-size: .76rem; margin-top: .1rem; }}
        .zv-row.critical {{ border-left-color: {CRITICAL}; }}
        .zv-row.serious  {{ border-left-color: {SERIOUS}; }}
        .zv-row.warning  {{ border-left-color: {WARNING}; }}

        /* ---- fact grid (detail cards) ---- */
        .zv-facts {{
            display: flex; flex-wrap: wrap; gap: .85rem 2.2rem;
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: .9rem 1.15rem; margin-bottom: .6rem;
        }}
        .zv-facts .k {{
            color: {MUTED}; font-size: .68rem; font-weight: 600;
            letter-spacing: .05em; text-transform: uppercase;
        }}
        .zv-facts .v {{ color: {INK}; font-size: .95rem; font-weight: 600; margin-top: .12rem; }}

        /* ---- empty state ---- */
        .zv-empty {{
            color: {MUTED}; font-size: .85rem; text-align: center;
            padding: 1.6rem; border: 1px dashed {GRID}; border-radius: 10px;
        }}

        [data-testid="stSidebar"] {{ background: {SURFACE}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------
def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="zv-header">
          <div class="zv-logo">ZV</div>
          <div><h1>{title}</h1><p>{subtitle}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str | None = None) -> None:
    st.markdown(f'<div class="zv-section">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="zv-sub">{subtitle}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, delta: str | None = None,
        delta_good: bool | None = None, hint: str | None = None) -> None:
    """One KPI tile. `delta_good=None` renders the delta in neutral ink."""
    parts = [f'<div class="zv-kpi"><div class="label">{label}</div>',
             f'<div class="value">{value}</div>']
    if delta is not None:
        color = MUTED if delta_good is None else (GOOD if delta_good else CRITICAL)
        parts.append(f'<div class="delta" style="color:{color}">{delta}</div>')
    if hint:
        parts.append(f'<div class="hint">{hint}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def badge(text: str, color: str) -> str:
    """Return the HTML for a coloured pill. Always carries its own label."""
    return (
        f'<span class="zv-badge" style="background:{color}1a;color:{color}">'
        f'<span class="zv-dot" style="background:{color}"></span>{text}</span>'
    )


def alert_row(title: str, meta: str, level: str = "warning") -> None:
    st.markdown(
        f'<div class="zv-row {level}"><div class="title">{title}</div>'
        f'<div class="meta">{meta}</div></div>',
        unsafe_allow_html=True,
    )


def fact_grid(facts: list[tuple[str, str]]) -> None:
    """A row of label/value pairs - the header of a detail card."""
    cells = "".join(
        f'<div class="fact"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in facts
    )
    st.markdown(f'<div class="zv-facts">{cells}</div>', unsafe_allow_html=True)


def empty_state(message: str) -> None:
    st.markdown(f'<div class="zv-empty">{message}</div>', unsafe_allow_html=True)


def money(value: float) -> str:
    return f"${value:,.0f}"


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def style_figure(fig: go.Figure, height: int = 260, show_legend: bool = False) -> go.Figure:
    """The house style: recessive chrome, generous margins, no chart junk."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK_SOFT),
        showlegend=show_legend,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        hoverlabel=dict(font_family=FONT, font_size=12, bgcolor=SURFACE,
                        bordercolor=BORDER, font_color=INK),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="outside",
                     tickcolor=AXIS, tickfont=dict(color=MUTED, size=11), title=None)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
                     linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=11),
                     title=None)
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, hover: str,
               color: str = BRAND, height: int = 260) -> go.Figure:
    """Single-series trend line. One series needs no legend - the title names it."""
    fig = go.Figure(
        go.Scatter(
            x=df[x], y=df[y], mode="lines",
            line=dict(color=color, width=2, shape="spline", smoothing=0.4),
            fill="tozeroy", fillcolor=rgba(color, 0.08),
            hovertemplate=hover + "<extra></extra>",
            name=y,
        )
    )
    return style_figure(fig, height)


def ranked_bar(df: pd.DataFrame, category: str, value: str, label_fmt,
               color: str = BRAND, height: int = 260) -> go.Figure:
    """
    Horizontal ranking. Magnitude is the message, so it gets ONE hue and a
    direct label per bar - eight colours here would encode nothing.
    """
    data = df.iloc[::-1]  # plotly draws the first row at the bottom
    fig = go.Figure(
        go.Bar(
            x=data[value], y=data[category], orientation="h",
            marker=dict(color=color, cornerradius=4),
            text=[label_fmt(v) for v in data[value]],
            textposition="outside", textfont=dict(color=INK_SOFT, size=11),
            cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )
    fig = style_figure(fig, height)
    fig.update_layout(hovermode="closest", bargap=0.35)
    fig.update_xaxes(showgrid=False, showticklabels=False, linecolor="rgba(0,0,0,0)",
                     ticks="", range=[0, float(data[value].max()) * 1.22])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_SOFT, size=12))
    return fig


def status_bar(df: pd.DataFrame, category: str, value: str, color_map: dict,
               height: int = 260) -> go.Figure:
    """
    Like `ranked_bar`, but the categories ARE statuses, so each keeps its
    reserved status colour. The category label sits beside every bar, so the
    colour is never the only carrier of meaning.
    """
    data = df.iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=data[value], y=data[category], orientation="h",
            marker=dict(color=[color_map.get(s, MUTED) for s in data[category]],
                        cornerradius=4),
            text=[f"{v:,}" for v in data[value]],
            textposition="outside", textfont=dict(color=INK_SOFT, size=11),
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,} flights<extra></extra>",
        )
    )
    fig = style_figure(fig, height)
    fig.update_layout(hovermode="closest", bargap=0.35)
    fig.update_xaxes(showgrid=False, showticklabels=False, linecolor="rgba(0,0,0,0)",
                     ticks="", range=[0, float(data[value].max()) * 1.22])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_SOFT, size=12))
    return fig
