"""
Plotly chart generators – Binance-themed, professional.
"""
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from typing import List, Dict


# ── Binance palette ─────────────────────────────────────────────────
COLORS = {
    "primary":   "#F0B90B",   # Binance yellow
    "secondary": "#0ECB81",   # green (positive)
    "accent":    "#F6465D",   # red (negative)
    "warning":   "#F0B90B",   # yellow
    "surface":   "#181A20",   # main bg
    "card":      "#2B3139",   # card bg
    "text":      "#EAECEF",
    "muted":     "#848E9C",
    "gradient_start": "#F0B90B",
    "gradient_end":   "#0ECB81",
}

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
    margin=dict(l=40, r=20, t=50, b=40),
    hovermode="x unified",
)


def _base_layout(**overrides) -> dict:
    d = {**LAYOUT_DEFAULTS}
    d.update(overrides)
    return d


# ======================================================================
# 1  Balance Trajectory
# ======================================================================
def plot_balance_trajectory(balance_history: List[float], total_days: int) -> go.Figure:
    days = list(range(total_days))
    bal = np.array(balance_history[:total_days])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=bal,
        mode="lines",
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(240,185,11,0.10)",
        name="Balance",
        hovertemplate="Day %{x}<br>$%{y:,.0f}<extra></extra>",
    ))

    # Trend line
    z = np.polyfit(days, bal, 1)
    trend = np.polyval(z, days)
    fig.add_trace(go.Scatter(
        x=days, y=trend,
        mode="lines",
        line=dict(color=COLORS["warning"], width=1.5, dash="dash"),
        name="Trend",
        hoverinfo="skip",
    ))

    fig.update_layout(
        **_base_layout(title=None),
        xaxis=dict(title="Days", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Balance ($)", gridcolor="rgba(255,255,255,0.06)", tickprefix="$"),
        showlegend=False,
        height=360,
    )
    return fig


# ======================================================================
# 2  Credit Score Evolution
# ======================================================================
def plot_credit_score(credit_history: List[float], total_days: int) -> go.Figure:
    days = list(range(total_days))
    scores = credit_history[:total_days]

    fig = go.Figure()

    # Background zones
    zones = [
        (750, 850, "rgba(14,203,129,0.08)", "Excellent"),
        (700, 750, "rgba(240,185,11,0.08)", "Good"),
        (650, 700, "rgba(240,185,11,0.06)", "Fair"),
        (300, 650, "rgba(246,70,93,0.08)", "Poor"),
    ]
    for lo, hi, color, label in zones:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=color, line_width=0,
                      annotation_text=label, annotation_position="top left",
                      annotation_font_size=10, annotation_font_color=COLORS["muted"])

    fig.add_trace(go.Scatter(
        x=days, y=scores,
        mode="lines",
        line=dict(color=COLORS["secondary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(14,203,129,0.08)",
        hovertemplate="Day %{x}<br>Score: %{y:.0f}<extra></extra>",
    ))

    fig.update_layout(
        **_base_layout(title=None),
        xaxis=dict(title="Days", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Credit Score", range=[300, 850], gridcolor="rgba(255,255,255,0.06)"),
        showlegend=False,
        height=360,
    )
    return fig


# ======================================================================
# 3  NAV Trajectory
# ======================================================================
def plot_nav_trajectory(nav_history: List[float], total_days: int) -> go.Figure:
    days = list(range(total_days))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=nav_history[:total_days],
        mode="lines",
        line=dict(color=COLORS["warning"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(240,185,11,0.08)",
        hovertemplate="Day %{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **_base_layout(title=None),
        xaxis=dict(title="Days", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Net Asset Value ($)", gridcolor="rgba(255,255,255,0.06)", tickprefix="$"),
        showlegend=False,
        height=360,
    )
    return fig


# ======================================================================
# 4  Health Score Gauge
# ======================================================================
def plot_health_gauge(health_score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        number=dict(suffix="/100", font=dict(size=36, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COLORS["muted"]),
            bar=dict(color=COLORS["primary"]),
            bgcolor=COLORS["card"],
            borderwidth=0,
            steps=[
                dict(range=[0, 30], color="rgba(246,70,93,0.25)"),
                dict(range=[30, 60], color="rgba(240,185,11,0.20)"),
                dict(range=[60, 100], color="rgba(14,203,129,0.20)"),
            ],
        ),
    ))
    fig.update_layout(
        **_base_layout(title=None, margin=dict(l=30, r=30, t=30, b=10)),
        height=250,
    )
    return fig


# ======================================================================
# 5  Resilience Score Gauge
# ======================================================================
def plot_rsi_gauge(rsi: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi,
        number=dict(suffix="/100", font=dict(size=36, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COLORS["muted"]),
            bar=dict(color=COLORS["secondary"]),
            bgcolor=COLORS["card"],
            borderwidth=0,
            steps=[
                dict(range=[0, 30], color="rgba(246,70,93,0.25)"),
                dict(range=[30, 60], color="rgba(240,185,11,0.20)"),
                dict(range=[60, 100], color="rgba(14,203,129,0.20)"),
            ],
        ),
    ))
    fig.update_layout(
        **_base_layout(title=None, margin=dict(l=30, r=30, t=30, b=10)),
        height=250,
    )
    return fig


# ======================================================================
# 6  Collapse-timing density (bar)
# ======================================================================
def plot_collapse_density(collapse_density: Dict) -> go.Figure:
    bins = collapse_density.get("bins", [])
    density = collapse_density.get("density", [])
    colors = [COLORS["accent"] if d > 0.1 else COLORS["primary"] for d in density]
    fig = go.Figure(go.Bar(
        x=bins, y=[d * 100 for d in density],
        marker_color=colors,
        hovertemplate="%{x}<br>Risk: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **_base_layout(title=None),
        xaxis=dict(title="Timeline Period"),
        yaxis=dict(title="Deficit Risk (%)", gridcolor="rgba(255,255,255,0.06)"),
        showlegend=False,
        height=300,
    )
    return fig


# ======================================================================
# 7  Liquidity over time
# ======================================================================
def plot_liquidity(liquidity_history: List[float], total_days: int) -> go.Figure:
    days = list(range(total_days))
    pct = [v * 100 for v in liquidity_history[:total_days]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=pct,
        mode="lines",
        line=dict(color=COLORS["accent"], width=2),
        fill="tozeroy",
        fillcolor="rgba(246,70,93,0.08)",
        hovertemplate="Day %{x}<br>%{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **_base_layout(title=None),
        xaxis=dict(title="Days", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Liquidity Ratio (%)", gridcolor="rgba(255,255,255,0.06)", range=[0, 105]),
        showlegend=False,
        height=300,
    )
    return fig
