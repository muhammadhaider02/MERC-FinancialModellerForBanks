"""
MERC – Financial Simulation Dashboard
"""
import streamlit as st
import numpy as np
import math
import pandas as pd
from decimal import Decimal
from datetime import datetime
from src.models.models import (
    SimulationConfig, Asset, AssetType, Liability,
    IncomeSource, ExpenseItem,
)
from src.core.engine import SimulationEngine
from src.components.currency import ExchangeRateManager
from src.visualization.charts import (
    plot_balance_trajectory, plot_credit_score, plot_nav_trajectory,
    plot_health_gauge, plot_rsi_gauge, plot_collapse_density,
    plot_liquidity, COLORS,
)

# ── Page config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="MERC",
    page_icon="FW",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Exchange rate ticker data ───────────────────────────────────────
@st.cache_data(ttl=60)
def get_ticker_rates():
    """Generate current and previous exchange rates for the ticker bar."""
    mgr = ExchangeRateManager("USD", ["USD", "EUR", "GBP", "PKR"], seed=42)
    day_offset = (datetime.now() - datetime(2025, 1, 1)).days

    # Yesterday's rates (for direction arrows)
    mgr_prev = ExchangeRateManager("USD", ["USD", "EUR", "GBP", "PKR"], seed=42)
    mgr_prev.update_rates_daily(max(0, day_offset - 1), volatility=0.005)
    prev = {
        "EUR/USD": float(mgr_prev.get_rate("EUR", "USD")),
        "GBP/USD": float(mgr_prev.get_rate("GBP", "USD")),
        "USD/PKR": float(mgr_prev.get_rate("USD", "PKR")),
    }

    # Today's rates
    mgr.update_rates_daily(day_offset, volatility=0.005)
    eur_usd = float(mgr.get_rate("EUR", "USD"))
    gbp_usd = float(mgr.get_rate("GBP", "USD"))
    usd_pkr = float(mgr.get_rate("USD", "PKR"))

    rates = {
        "EUR/USD": eur_usd,
        "GBP/USD": gbp_usd,
        "USD/PKR": usd_pkr,
        "EUR/GBP": round(eur_usd / gbp_usd, 4),
        "GBP/PKR": round(gbp_usd * usd_pkr, 2),
        "EUR/PKR": round(eur_usd * usd_pkr, 2),
    }
    prev["EUR/GBP"] = round(prev["EUR/USD"] / prev["GBP/USD"], 4)
    prev["GBP/PKR"] = round(prev["GBP/USD"] * prev["USD/PKR"], 2)
    prev["EUR/PKR"] = round(prev["EUR/USD"] * prev["USD/PKR"], 2)
    return rates, prev

ticker_rates, ticker_prev = get_ticker_rates()

# ── Custom CSS – Binance Dark Theme ────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: #0B0E11;
}

/* Kill top whitespace */
.stMainBlockContainer, .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
.stApp > footer, .stApp [data-testid="stBottom"] {
    display: none !important;
}
.stMainBlockContainer {
    margin-bottom: -80px !important;
}
.stApp > header + div {
    padding-top: 0 !important;
}
[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
}
.st-emotion-cache-z5fcl4 {
    padding-top: 0 !important;
}

/* Force ALL text to be visible */
.stApp, .stApp p, .stApp span, .stApp div, .stApp label,
.stApp .stMarkdown, .stApp .stMarkdown p,
.stApp .stMarkdown span,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
    color: #EAECEF !important;
}
.stApp h1, [data-testid="stMarkdownContainer"] h1 { color: #FFFFFF !important; font-weight: 700 !important; }
.stApp h2, [data-testid="stMarkdownContainer"] h2 { color: #FFFFFF !important; font-weight: 600 !important; }
.stApp h3, [data-testid="stMarkdownContainer"] h3 { color: #F0B90B !important; font-weight: 600 !important; }
.stApp h4, [data-testid="stMarkdownContainer"] h4 { color: #F0B90B !important; font-weight: 600 !important; }
.stApp h5, [data-testid="stMarkdownContainer"] h5 { color: #d4a30a !important; }
.stApp strong, [data-testid="stMarkdownContainer"] strong { color: #FFFFFF !important; }
.stApp em, [data-testid="stMarkdownContainer"] em { color: #B7BDC6 !important; }
.stCaption, .stApp .stCaption p { color: #5E6673 !important; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0B0E11;
    border-right: 1px solid #2B3139;
}
section[data-testid="stSidebar"] * {
    color: #EAECEF !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #F0B90B !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] em {
    color: #B7BDC6 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #1E2329;
    border-radius: 8px;
    padding: 4px;
    border: 1px solid #2B3139;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    color: #848E9C;
    font-weight: 500;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: rgba(240,185,11,0.12) !important;
    color: #F0B90B !important;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 16px 20px;
}
div[data-testid="stMetric"] label {
    color: #B7BDC6 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-weight: 500 !important;
}

/* Buttons */
.stButton > button {
    background: #F0B90B !important;
    color: #181A20 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px 28px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: #d4a30a !important;
    box-shadow: 0 4px 12px rgba(240,185,11,0.25) !important;
}

/* Dividers */
hr { border-color: #2B3139 !important; }

/* Ticker bar */
@keyframes ticker-scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.ticker-bar {
    background: #1E2329;
    border-bottom: 1px solid #2B3139;
    border-top: 1px solid #2B3139;
    padding: 10px 0;
    margin-bottom: 20px;
    overflow: hidden;
    position: relative;
}
.ticker-track {
    display: flex;
    gap: 48px;
    align-items: center;
    width: max-content;
    animation: ticker-scroll 30s linear infinite;
}
.ticker-track:hover {
    animation-play-state: paused;
}
.ticker-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.84rem;
    white-space: nowrap;
}
.ticker-pair {
    color: #FFFFFF;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.ticker-rate {
    font-weight: 600;
    font-family: 'Inter', monospace;
    font-size: 0.88rem;
}
.ticker-up {
    color: #0ECB81;
}
.ticker-down {
    color: #F6465D;
}
.ticker-flat {
    color: #B7BDC6;
}
.ticker-arrow {
    font-size: 0.72rem;
    margin-left: 2px;
}
.ticker-pct {
    font-size: 0.72rem;
    margin-left: 2px;
    font-weight: 500;
}
.ticker-sep {
    color: #2B3139;
    font-size: 0.6rem;
    margin: 0 4px;
}

/* Data card */
.data-card {
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 24px;
    text-align: center;
}
.data-card-left {
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 24px;
    text-align: left;
}
.grade-lg {
    font-size: 2.8rem;
    font-weight: 700;
    color: #F0B90B !important;
    line-height: 1;
    margin-bottom: 4px;
    font-family: 'Inter', monospace;
}
.grade-label {
    font-size: 1.1rem;
    font-weight: 600;
    color: #FFFFFF !important;
}
.grade-desc {
    font-size: 0.85rem;
    color: #B7BDC6 !important;
    margin-top: 4px;
}
.grade-sub {
    margin-top: 10px;
    color: #F0B90B !important;
    font-size: 0.95rem;
    font-weight: 600;
}

/* Feature card */
.feature-card {
    padding: 12px 16px;
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 6px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
}
.feature-card:hover {
    border-color: #F0B90B;
}
.feature-title {
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 0.88rem;
}
.feature-desc {
    color: #B7BDC6 !important;
    font-size: 0.78rem;
}

/* Scenario card row (horizontal) */
.scenario-card-row {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.2s, transform 0.2s;
}
.scenario-card-row:hover {
    border-color: #F0B90B;
    transform: translateX(4px);
}
.scenario-icon {
    font-size: 1.5rem;
}

/* Scenario card (legacy vertical) */
.scenario-card {
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    min-height: 100px;
    transition: border-color 0.2s, transform 0.2s;
}
.scenario-card:hover {
    border-color: #F0B90B;
    transform: translateY(-2px);
}
.scenario-name {
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 0.85rem;
}
.scenario-desc {
    color: #B7BDC6 !important;
    font-size: 0.75rem;
    margin-top: 6px;
}

/* Quick calc */
.quick-calc {
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 20px;
}
.quick-calc-title {
    color: #F0B90B !important;
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 12px;
}
.quick-calc-result {
    color: #FFFFFF !important;
    font-weight: 700;
    font-size: 1.4rem;
    margin-top: 8px;
}

/* Rate row */
.rate-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 6px;
    margin-bottom: 6px;
    transition: border-color 0.2s;
}
.rate-row:hover {
    border-color: #F0B90B;
}
.rate-pair {
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 0.88rem;
    min-width: 80px;
}
.rate-value {
    color: #F0B90B !important;
    font-weight: 700;
    font-size: 0.92rem;
    font-family: 'Inter', monospace;
}

/* Stat row */
.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #2B3139;
}
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #B7BDC6 !important; font-size: 0.88rem; }
.stat-value { color: #FFFFFF !important; font-weight: 600; font-size: 0.88rem; }

/* Section header */
.section-head {
    color: #FFFFFF !important;
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2B3139;
}

/* Selectbox / Input styling */
.stSelectbox label, .stNumberInput label, .stSlider label {
    color: #B7BDC6 !important;
}

/* Info box */
.stAlert {
    background: #1E2329 !important;
    border: 1px solid #2B3139 !important;
    color: #EAECEF !important;
}

/* Expander */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
    color: #EAECEF !important;
    background: #1E2329 !important;
    border-color: #2B3139 !important;
}
.streamlit-expanderContent,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: #181A20 !important;
    border-color: #2B3139 !important;
}
[data-testid="stExpander"] {
    background: #1E2329 !important;
    border: 1px solid #2B3139 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] svg {
    fill: #F0B90B !important;
}

/* Dataframe / Exchange Rate Table */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div {
    background: #1E2329 !important;
    border-radius: 8px !important;
}
[data-testid="stDataFrame"] [data-testid="glideDataEditor"] {
    background: #1E2329 !important;
    border: 1px solid #2B3139 !important;
    border-radius: 8px !important;
}
/* Header row */
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] [role="columnheader"] {
    background: #181A20 !important;
    color: #F0B90B !important;
    font-weight: 600 !important;
    border-color: #2B3139 !important;
}
/* Data cells */
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] [role="gridcell"] {
    background: #1E2329 !important;
    color: #EAECEF !important;
    border-color: #2B3139 !important;
}
/* Hover effect on rows */
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
    background: #2B3139 !important;
}
/* Glide data editor canvas background */
[data-testid="stDataFrame"] canvas {
    background: #1E2329 !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# Ticker bar – scrolling exchange rates (6 pairs)
# ══════════════════════════════════════════════════════════════════════
ticker_items = ""
for pair, rate in ticker_rates.items():
    fmt = f"{rate:.4f}" if rate < 10 else f"{rate:.2f}"
    prev_rate = ticker_prev.get(pair, rate)
    diff = rate - prev_rate
    pct = (diff / prev_rate * 100) if prev_rate != 0 else 0
    if diff > 0:
        arrow = '<span class="ticker-arrow ticker-up">&#9650;</span>'
        cls = "ticker-up"
        pct_str = f'<span class="ticker-pct ticker-up">+{pct:.2f}%</span>'
    elif diff < 0:
        arrow = '<span class="ticker-arrow ticker-down">&#9660;</span>'
        cls = "ticker-down"
        pct_str = f'<span class="ticker-pct ticker-down">{pct:.2f}%</span>'
    else:
        arrow = '<span class="ticker-arrow ticker-flat">&#9644;</span>'
        cls = "ticker-flat"
        pct_str = '<span class="ticker-pct ticker-flat">0.00%</span>'
    ticker_items += f'<div class="ticker-item"><span class="ticker-pair">{pair}</span><span class="ticker-rate {cls}">{fmt}</span>{arrow}{pct_str}</div><span class="ticker-sep">|</span>'
# Duplicate for seamless scroll loop
ticker_html = f'<div class="ticker-bar"><div class="ticker-track">{ticker_items}{ticker_items}</div></div>'
st.markdown(ticker_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("# MERC")
    st.markdown("*Financial Simulation Engine*")
    st.markdown("---")

    # ── Scenario presets ────────────────────────────────────────────
    st.markdown("### Scenario")
    scenario = st.selectbox(
        "Start with a preset or customize",
        ["Custom Setup", "Young Professional", "Growing Family",
         "Fresh Graduate", "Debt Recovery"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Time horizon ────────────────────────────────────────────────
    st.markdown("### Projection Period")
    horizon_years = st.slider("Years to simulate", 1, 10, 3, help="How far into the future to project")
    horizon_days = horizon_years * 365

    st.markdown("---")

    # ── Preset or custom values ─────────────────────────────────────
    presets = {
        "Custom Setup":           dict(balance=10000, income=5000, expenses=3000, credit=680, asset_val=8000, asset_type="Liquid", liability_amt=0, liability_rate=0.0, liability_pmt=0),
        "Young Professional":     dict(balance=15000, income=6500, expenses=3500, credit=720, asset_val=10000, asset_type="Volatile", liability_amt=25000, liability_rate=4.5, liability_pmt=500),
        "Growing Family":         dict(balance=25000, income=9000, expenses=7000, credit=740, asset_val=35000, asset_type="Illiquid", liability_amt=150000, liability_rate=3.8, liability_pmt=1200),
        "Fresh Graduate":         dict(balance=2000, income=3500, expenses=2800, credit=620, asset_val=1000, asset_type="Liquid", liability_amt=35000, liability_rate=5.5, liability_pmt=400),
        "Debt Recovery":          dict(balance=500, income=4000, expenses=3800, credit=520, asset_val=2000, asset_type="Liquid", liability_amt=45000, liability_rate=8.0, liability_pmt=600),
    }
    p = presets[scenario]

    # ── Financial Profile ───────────────────────────────────────────
    st.markdown("### Financial Profile")
    initial_balance = st.number_input("Starting Cash ($)", min_value=0, value=p["balance"], step=500)
    monthly_income  = st.number_input("Monthly Income ($)", min_value=0, value=p["income"], step=100)
    monthly_expenses = st.number_input("Monthly Expenses ($)", min_value=0, value=p["expenses"], step=100)
    initial_credit   = st.slider("Current Credit Score", 300, 850, p["credit"])

    st.markdown("---")

    # ── Assets ──────────────────────────────────────────────────────
    st.markdown("### Assets")
    asset_value = st.number_input("Total Asset Value ($)", min_value=0, value=p["asset_val"], step=1000)
    asset_type_label = st.selectbox("Primary Asset Type", ["Liquid", "Illiquid", "Yield", "Volatile"],
                                     index=["Liquid","Illiquid","Yield","Volatile"].index(p["asset_type"]))
    asset_type_map = {
        "Liquid": (AssetType.LIQUID, 0.02),
        "Illiquid": (AssetType.ILLIQUID, 0.01),
        "Yield": (AssetType.YIELD, 0.05),
        "Volatile": (AssetType.VOLATILE, 0.15),
    }
    at, av = asset_type_map[asset_type_label]

    st.markdown("---")

    # ── Liabilities ─────────────────────────────────────────────────
    st.markdown("### Liabilities")
    liability_amount = st.number_input("Outstanding Debt ($)", min_value=0, value=p["liability_amt"], step=1000)
    liability_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=30.0, value=p["liability_rate"], step=0.5)
    liability_payment = st.number_input("Monthly Payment ($)", min_value=0, value=p["liability_pmt"], step=50)

    st.markdown("---")

    # ── Run button ──────────────────────────────────────────────────
    run_sim = st.button("Run Simulation", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# Main area
# ══════════════════════════════════════════════════════════════════════
if run_sim:
    with st.spinner("Running simulation…"):
        # Build config (seed is fixed for determinism – hidden from user)
        cfg = SimulationConfig(
            start_date=datetime(2025, 1, 1),
            horizon_days=horizon_days,
            seed=42,
            base_currency="USD",
            currencies=["USD", "EUR", "GBP", "PKR"],
            initial_balance=Decimal(str(initial_balance)),
        )
        engine = SimulationEngine(cfg)

        engine.add_income_source(IncomeSource(
            id="inc_main", name="Income",
            amount=Decimal(str(monthly_income)),
            currency="USD", frequency="monthly",
        ))
        engine.add_expense(ExpenseItem(
            id="exp_main", name="Expenses",
            amount=Decimal(str(monthly_expenses)),
            currency="USD", frequency="monthly",
        ))

        assets = []
        if asset_value > 0:
            assets.append(Asset(
                id="asset_1", name=f"{asset_type_label} Assets",
                type=at, value=Decimal(str(asset_value)),
                currency="USD", volatility=av,
            ))

        liabilities = []
        if liability_amount > 0:
            liabilities.append(Liability(
                id="lia_1", name="Debt",
                principal=Decimal(str(liability_amount)),
                interest_rate=liability_rate / 100,
                monthly_payment=Decimal(str(max(liability_payment, 1))),
                currency="USD",
                start_date=datetime(2025, 1, 1),
                remaining_balance=Decimal(str(liability_amount)),
            ))

        engine.initialize(
            initial_balance=Decimal(str(initial_balance)),
            assets=assets,
            liabilities=liabilities,
            credit_score=float(initial_credit),
        )

        results = engine.run_simulation()

    # ── Header ───────────────────────────────────────────────────────
    st.markdown(f"# {horizon_years}-Year Financial Projection")
    st.markdown(f"Scenario: **{scenario}**")
    st.markdown("---")

    # ── Top-line KPIs ───────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    balance_change = results["final_balance"] - initial_balance
    balance_delta = f"+${balance_change:,.0f}" if balance_change >= 0 else f"-${abs(balance_change):,.0f}"

    col1.metric("Final Balance", f"${results['final_balance']:,.0f}", balance_delta)
    col2.metric("Credit Score", f"{results['final_credit_score']:.0f}", f"{results['final_credit_score'] - initial_credit:+.0f}")

    bp = results["bankruptcy_probability"]
    risk_label = "Low" if bp < 0.05 else "Medium" if bp < 0.2 else "High"
    col3.metric("Bankruptcy Risk", risk_label, f"{bp * 100:.1f}%")
    col4.metric("Resilience (RSI)", f"{results['resilience_score_index']:.0f}/100")
    col5.metric("Net Worth (NAV)", f"${results['final_nav']:,.0f}")

    st.markdown("---")

    # ── Financial Status & Stability Grade ──────────────────────────
    vibe = results["vibe_state"]
    pet = results["pet_state"]

    v_col, p_col = st.columns(2)
    with v_col:
        st.markdown(f"""
        <div class="data-card">
            <div class="grade-lg">{vibe['emoji']}</div>
            <div class="grade-label">{vibe['label']}</div>
            <div class="grade-desc">{vibe['description']}</div>
            <div class="grade-sub">
                Health Score: {results['health_score']:.0f}/100
            </div>
        </div>
        """, unsafe_allow_html=True)
    with p_col:
        st.markdown(f"""
        <div class="data-card">
            <div class="grade-lg">{pet['emoji']}</div>
            <div class="grade-label">{pet['label']}</div>
            <div class="grade-desc">{pet['description']}</div>
            <div class="grade-sub">
                Stability Grade
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ── Charts ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Balance", "Credit Score", "Net Worth", "Risk", "Liquidity"
    ])

    with tab1:
        st.markdown("#### Balance Trajectory")
        st.plotly_chart(
            plot_balance_trajectory(results["balance_history"], results["total_days"]),
            use_container_width=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Expected Balance", f"${results['balance_expected']:,.0f}")
        c2.metric("Best Case (95th pct)", f"${results['balance_95th']:,.0f}")
        c3.metric("Worst Case (5th pct)", f"${results['balance_5th']:,.0f}")

    with tab2:
        st.markdown("#### Credit Score Evolution")
        st.plotly_chart(
            plot_credit_score(results["credit_history"], results["total_days"]),
            use_container_width=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Final Score", f"{results['final_credit_score']:.0f}")
        c2.metric("Highest", f"{results['credit_max']:.0f}")
        c3.metric("Lowest", f"{results['credit_min']:.0f}")

    with tab3:
        st.markdown("#### Net Asset Value Over Time")
        st.plotly_chart(
            plot_nav_trajectory(results["nav_history"], results["total_days"]),
            use_container_width=True,
        )

    with tab4:
        st.markdown("#### Risk Assessment")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("##### Financial Health")
            st.plotly_chart(plot_health_gauge(results["health_score"]), use_container_width=True)
        with g2:
            st.markdown("##### Resilience Index")
            st.plotly_chart(plot_rsi_gauge(results["resilience_score_index"]), use_container_width=True)

        st.markdown("##### Collapse Risk Timeline")
        collapse = results.get("collapse_density", {})
        if collapse.get("bins"):
            st.plotly_chart(plot_collapse_density(collapse), use_container_width=True)
        else:
            st.info("No significant collapse risk detected across the timeline")

        # Extra risk stats
        r1, r2, r3 = st.columns(3)
        r1.metric("Worst Drawdown", f"{results['worst_drawdown'] * 100:.1f}%")
        deficit_days = results["risk_snapshot"].get("deficit_days", 0)
        r2.metric("Days in Deficit", str(deficit_days))
        bt = results.get("bankruptcy_day")
        r3.metric("First Deficit Day", str(bt) if bt else "None")

    with tab5:
        st.markdown("#### Liquidity Ratio Over Time")
        st.plotly_chart(
            plot_liquidity(results["liquidity_history"], results["total_days"]),
            use_container_width=True,
        )
        st.metric("Final Liquidity Ratio", f"{results['final_liquidity_ratio'] * 100:.1f}%")

    # ── Summary section ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Projection Summary")

    sum1, sum2 = st.columns(2)
    with sum1:
        st.markdown(f"""
        <div class="data-card-left">
            <div class="section-head" style="color:#F0B90B;">Key Findings</div>
            <div class="stat-row"><span class="stat-label">Starting Cash</span><span class="stat-value">${initial_balance:,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">Projected Final Balance</span><span class="stat-value">${results['final_balance']:,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">Net Change</span><span class="stat-value" style="color:{'#0ECB81' if balance_change>=0 else '#F6465D'}">{balance_delta}</span></div>
            <div class="stat-row"><span class="stat-label">Monthly Savings Rate</span><span class="stat-value">${monthly_income - monthly_expenses:,.0f}/mo</span></div>
            <div class="stat-row"><span class="stat-label">Projection Period</span><span class="stat-value">{horizon_years} year(s)</span></div>
        </div>
        """, unsafe_allow_html=True)
    with sum2:
        st.markdown(f"""
        <div class="data-card-left">
            <div class="section-head" style="color:#F0B90B;">Risk Profile</div>
            <div class="stat-row"><span class="stat-label">Bankruptcy Probability</span><span class="stat-value">{bp*100:.1f}%</span></div>
            <div class="stat-row"><span class="stat-label">Resilience Score</span><span class="stat-value">{results['resilience_score_index']:.0f}/100</span></div>
            <div class="stat-row"><span class="stat-label">Health Score</span><span class="stat-value">{results['health_score']:.0f}/100</span></div>
            <div class="stat-row"><span class="stat-label">Financial Status</span><span class="stat-value">{vibe['label']}</span></div>
            <div class="stat-row"><span class="stat-label">Stability Grade</span><span class="stat-value">{pet['emoji']} — {pet['label']}</span></div>
        </div>
        """, unsafe_allow_html=True)

else:
    # ── Welcome screen ──────────────────────────────────────────────
    hero_col1, hero_col2 = st.columns([3, 2], gap="large")
    with hero_col1:
        st.markdown("""
        <div style="padding: 20px 0 10px 0;">
            <div style="font-size: 2.4rem; font-weight: 700; color: #FFFFFF; line-height: 1.1;">MERC</div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #F0B90B; margin-top: 6px;">Financial Projection Engine</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        Simulate your financial future with **daily precision**.
        Model income, expenses, assets, debts, and see how your
        wealth evolves over the next **1 to 10 years**.
        """)
        st.markdown("Configure your scenario in the sidebar and press **Run Simulation**.")

        # Quick stats row
        qs1, qs2, qs3, qs4 = st.columns(4)
        qs1.metric("Currencies", "4", "Live rates")
        qs2.metric("Max Horizon", "10 yrs", "3,650 days")
        qs3.metric("Scenarios", "5", "Presets")
        qs4.metric("Precision", "Daily", "Bit-exact")

    with hero_col2:
        features = [
            ("⚡", "Deterministic Engine", "Bit-exact reproducible projections"),
            ("💱", "Multi-Currency", "USD, EUR, GBP, PKR with daily volatility"),
            ("📊", "Credit Modeling", "Dynamic score evolution (300 - 850)"),
            ("🛡️", "Risk Analysis", "Bankruptcy probability and resilience scoring"),
            ("💡", "Health Metrics", "Quantitative financial health indicators"),
            ("🏦", "Asset Portfolio", "Liquid, illiquid, yield and volatile assets"),
        ]
        for icon, title, desc in features:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-title">{icon} {title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Interactive tools before running simulation ─────────────────
    tool1, tool2, tool3 = st.columns(3)

    with tool1:
        st.markdown('<div class="quick-calc-title">Savings Calculator</div>', unsafe_allow_html=True)
        calc_income = st.number_input("Monthly Income", min_value=0, value=5000, step=100, key="calc_inc")
        calc_expense = st.number_input("Monthly Expenses", min_value=0, value=3000, step=100, key="calc_exp")
        calc_years = st.selectbox("Period", [1, 2, 3, 5, 10], index=2, key="calc_yr")
        savings_monthly = calc_income - calc_expense
        savings_total = savings_monthly * 12 * calc_years
        color = "#0ECB81" if savings_monthly >= 0 else "#F6465D"
        st.markdown(f'<div class="quick-calc-result" style="color:{color}">${savings_total:,.0f}</div>', unsafe_allow_html=True)
        st.caption(f"${savings_monthly:,.0f}/mo over {calc_years} yr")

    with tool2:
        st.markdown('<div class="quick-calc-title">Currency Converter</div>', unsafe_allow_html=True)
        conv_amount = st.number_input("Amount (USD)", min_value=0.0, value=1000.0, step=100.0, key="conv_amt")
        conv_target = st.selectbox("Convert to", ["EUR", "GBP", "PKR"], key="conv_tgt")
        pair_key = f"USD/{conv_target}" if f"USD/{conv_target}" in ticker_rates else None
        if pair_key:
            converted = conv_amount * ticker_rates[pair_key]
        else:
            # Reverse lookup
            rev_key = f"{conv_target}/USD"
            if rev_key in ticker_rates:
                converted = conv_amount / ticker_rates[rev_key]
            else:
                converted = conv_amount
        st.markdown(f'<div class="quick-calc-result" style="color:#F0B90B">{conv_target} {converted:,.2f}</div>', unsafe_allow_html=True)
        rate_display = ticker_rates.get(pair_key or f"{conv_target}/USD", 1.0)
        st.caption(f"Rate: {rate_display:.4f}")

    with tool3:
        st.markdown('<div class="quick-calc-title">Debt Payoff Estimator</div>', unsafe_allow_html=True)
        debt_amt = st.number_input("Debt Amount ($)", min_value=0, value=25000, step=1000, key="debt_amt")
        debt_rate = st.number_input("Annual Rate (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.5, key="debt_rate")
        debt_pmt = st.number_input("Monthly Payment ($)", min_value=1, value=500, step=50, key="debt_pmt")
        if debt_pmt > 0 and debt_amt > 0:
            monthly_r = debt_rate / 100 / 12
            if monthly_r > 0:
                try:
                    months = math.ceil(-math.log(1 - (monthly_r * debt_amt / debt_pmt)) / math.log(1 + monthly_r))
                    years_est = months / 12
                    st.markdown(f'<div class="quick-calc-result" style="color:#0ECB81">{years_est:.1f} years</div>', unsafe_allow_html=True)
                    st.caption(f"{months} months to payoff")
                except (ValueError, ZeroDivisionError):
                    st.markdown('<div class="quick-calc-result" style="color:#F6465D">Payment too low</div>', unsafe_allow_html=True)
                    st.caption("Increase monthly payment")
            else:
                months = math.ceil(debt_amt / debt_pmt)
                st.markdown(f'<div class="quick-calc-result" style="color:#0ECB81">{months / 12:.1f} years</div>', unsafe_allow_html=True)
                st.caption(f"{months} months to payoff")

    st.markdown("---")

    # ── Preset Scenarios + Exchange Rates side by side ───────────────
    left_panel, right_panel = st.columns([3, 2], gap="large")

    with left_panel:
        st.markdown("### Preset Scenarios")
        scenarios_info = [
            ("🧑‍💼", "Young Professional", "$6,500/mo income, student debt"),
            ("👨‍👩‍👧‍👦", "Growing Family", "$9,000/mo, mortgage, illiquid assets"),
            ("🎓", "Fresh Graduate", "$3,500/mo, high student debt"),
            ("🔄", "Debt Recovery", "$4,000/mo, severe debt load"),
        ]
        for icon, name, desc in scenarios_info:
            st.markdown(f"""
            <div class="scenario-card-row">
                <span class="scenario-icon">{icon}</span>
                <div>
                    <div class="scenario-name">{name}</div>
                    <div class="scenario-desc">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with right_panel:
        st.markdown("### Live Exchange Rates")
        for pair, rate in ticker_rates.items():
            fmt = f"{rate:.4f}" if rate < 10 else f"{rate:.2f}"
            prev_rate = ticker_prev.get(pair, rate)
            diff = rate - prev_rate
            pct = (diff / prev_rate * 100) if prev_rate != 0 else 0
            if diff > 0:
                arrow = "▲"
                color = "#0ECB81"
                sign = "+"
            elif diff < 0:
                arrow = "▼"
                color = "#F6465D"
                sign = ""
            else:
                arrow = "━"
                color = "#B7BDC6"
                sign = ""
            st.markdown(f"""
            <div class="rate-row">
                <span class="rate-pair">{pair}</span>
                <span class="rate-value">{fmt}</span>
                <span style="color:{color}; font-size:0.8rem; font-weight:600;">{arrow} {sign}{pct:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
