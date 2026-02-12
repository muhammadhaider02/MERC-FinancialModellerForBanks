"""
Simulation output generator – assembles the final results packet.
"""
import numpy as np
from typing import List, Dict
from src.metrics.behavioral import compute_health_score, get_vibe_state, get_pet_state


class OutputGenerator:
    """Produces the required output data-packet from a completed simulation."""

    @staticmethod
    def generate(
        balance_history: List[float],
        credit_history: List[float],
        nav_history: List[float],
        liquidity_history: List[float],
        risk_snapshot: Dict,
        metrics_snapshot: Dict,
        initial_balance: float,
        total_days: int,
    ) -> Dict:
        """
        Build the complete result dictionary expected by the UI.

        Returns every metric required by VIBECODE.md §4.
        """
        bal = np.array(balance_history)
        credit = np.array(credit_history)
        nav = np.array(nav_history) if nav_history else np.array([0.0])
        liq = np.array(liquidity_history) if liquidity_history else np.array([0.0])

        # ── Finality ────────────────────────────────────────────────
        final_balance = float(bal[-1]) if len(bal) else 0.0
        balance_exp = float(np.mean(bal))
        balance_5th = float(np.percentile(bal, 5))
        balance_95th = float(np.percentile(bal, 95))

        # ── Risk ────────────────────────────────────────────────────
        bankruptcy_prob = risk_snapshot.get("bankruptcy_probability", 0.0)
        bankruptcy_day = risk_snapshot.get("bankruptcy_timing_day")
        rsi = risk_snapshot.get("resilience_score_index", 100.0)
        worst_drawdown = risk_snapshot.get("worst_drawdown", 0.0)
        collapse_density = risk_snapshot.get("collapse_density", {})

        # ── Health / Behavioral ─────────────────────────────────────
        health_score = compute_health_score(
            balance=final_balance,
            initial_balance=initial_balance,
            credit_score=float(credit[-1]) if len(credit) else 650.0,
            bankruptcy_prob=bankruptcy_prob,
            liquidity_ratio=float(liq[-1]) if len(liq) else 0.0,
            shock_density=metrics_snapshot.get("shock_clustering_density", 0.0),
            recovery_slope=metrics_snapshot.get("recovery_slope", 0.0),
        )
        vibe = get_vibe_state(health_score)
        pet = get_pet_state(health_score)

        # ── Scores ──────────────────────────────────────────────────
        final_credit = float(credit[-1]) if len(credit) else 650.0
        credit_min = float(np.min(credit)) if len(credit) else 650.0
        credit_max = float(np.max(credit)) if len(credit) else 650.0

        # ── Assets ──────────────────────────────────────────────────
        final_nav = float(nav[-1]) if len(nav) else 0.0
        final_liquidity = float(liq[-1]) if len(liq) else 0.0

        return {
            # Finality
            "final_balance": final_balance,
            "balance_expected": balance_exp,
            "balance_5th": balance_5th,
            "balance_95th": balance_95th,

            # Risk
            "bankruptcy_probability": bankruptcy_prob,
            "bankruptcy_day": bankruptcy_day,
            "resilience_score_index": rsi,
            "worst_drawdown": worst_drawdown,
            "collapse_density": collapse_density,

            # Health
            "health_score": health_score,
            "vibe_state": vibe,
            "pet_state": pet,

            # Scores
            "final_credit_score": final_credit,
            "credit_min": credit_min,
            "credit_max": credit_max,

            # Assets
            "final_nav": final_nav,
            "final_liquidity_ratio": final_liquidity,

            # Time-series (for charts)
            "balance_history": balance_history,
            "credit_history": credit_history,
            "nav_history": nav_history,
            "liquidity_history": liquidity_history,
            "total_days": total_days,

            # Metrics detail
            "metrics_snapshot": metrics_snapshot,
            "risk_snapshot": risk_snapshot,
        }
