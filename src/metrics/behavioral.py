"""
Qualitative behavioral indicators – Financial Status & Stability Grade.
Derived from quantitative volatility and balance health metrics.
"""
from typing import Dict


# ── Financial Status ────────────────────────────────────────────────
VIBE_THRESHOLDS = [
    # (min_score, label, icon, description)
    (90, "Thriving",   "A+", "Portfolio showing strong sustained growth"),
    (75, "Confident",  "A",  "Solid financial position with healthy trajectory"),
    (60, "Stable",     "B+", "Steady state with manageable risk exposure"),
    (45, "Cautious",   "B",  "Elevated risk; tighter controls recommended"),
    (30, "Stressed",   "C",  "Financial strain detected; corrective action needed"),
    (15, "Critical",   "D",  "Severe distress; immediate intervention required"),
    (0,  "Collapsed",  "F",  "Financial collapse has occurred"),
]

# ── Stability Grade ─────────────────────────────────────────────────
PET_STAGES = [
    # (min_score, stage, grade, description)
    (90, "Exceptional Stability", "S",  "Top-tier financial resilience"),
    (75, "Strong Stability",     "A",  "Well-positioned for long-term growth"),
    (60, "Moderate Stability",   "B+", "Acceptable risk profile"),
    (45, "Low Stability",        "B",  "Watchlist — monitor closely"),
    (30, "Fragile",              "C",  "Below threshold — needs attention"),
    (15, "Unstable",             "D",  "High-risk — take action now"),
    (0,  "Critical",             "F",  "Recovery plan required"),
]


def _lookup(score: float, table):
    for min_score, label, emoji, desc in table:
        if score >= min_score:
            return {"label": label, "emoji": emoji, "description": desc, "score": round(score, 1)}
    last = table[-1]
    return {"label": last[1], "emoji": last[2], "description": last[3], "score": round(score, 1)}


def compute_health_score(
    balance: float,
    initial_balance: float,
    credit_score: float,
    bankruptcy_prob: float,
    liquidity_ratio: float,
    shock_density: float,
    recovery_slope: float,
) -> float:
    """
    Combine multiple signals into a 0-100 health score.

    Weights (total = 1.0):
        balance_growth  0.20
        credit          0.20
        no_bankruptcy    0.20
        liquidity        0.15
        low_shock        0.15
        recovery         0.10
    """
    # Balance growth component (0-100)
    if initial_balance > 0:
        growth_ratio = balance / initial_balance
        balance_score = min(100, max(0, growth_ratio * 50))  # 2× = 100
    else:
        balance_score = 50 if balance >= 0 else 0

    # Credit component (300-850 → 0-100)
    credit_component = max(0, min(100, (credit_score - 300) / 5.5))

    # Bankruptcy component (0 or 1 → 100 or 0)
    bankruptcy_component = (1 - bankruptcy_prob) * 100

    # Liquidity component (0-1 → 0-100)
    liquidity_component = min(100, liquidity_ratio * 100)

    # Shock component – lower is better
    shock_component = max(0, 100 - shock_density * 1000)

    # Recovery component – higher slope is better (capped)
    recovery_component = min(100, recovery_slope * 10)

    score = (
        0.20 * balance_score
        + 0.20 * credit_component
        + 0.20 * bankruptcy_component
        + 0.15 * liquidity_component
        + 0.15 * shock_component
        + 0.10 * recovery_component
    )
    return max(0, min(100, score))


def get_vibe_state(health_score: float) -> Dict:
    """Return the qualitative Vibe State for a given health score (0-100)."""
    return _lookup(health_score, VIBE_THRESHOLDS)


def get_pet_state(health_score: float) -> Dict:
    """Return the gamified Pet State for a given health score (0-100)."""
    return _lookup(health_score, PET_STAGES)
