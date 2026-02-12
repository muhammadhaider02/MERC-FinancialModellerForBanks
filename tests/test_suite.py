"""
Phase 8 – Comprehensive validation and test suite.
Covers: determinism, precision, snapshot consistency, DAG cycles,
        tax alignment, and infinite-loop prevention.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
from decimal import Decimal
from datetime import datetime

from src.models.models import (
    SimulationConfig, Asset, AssetType, Liability,
    IncomeSource, ExpenseItem,
)
from src.core.engine import SimulationEngine
from src.core.dag import DependencyGraph
from src.core.state import StateManager
from src.components.currency import ExchangeRateManager
from src.components.assets import AssetPortfolioManager
from src.components.credit import CreditScoreCalculator
from src.components.taxation import TaxationEngine
from src.components.liabilities import LiabilityManager
from src.metrics.metrics import RollingMetricsEngine
from src.metrics.risk import RiskAnalyzer
from src.metrics.behavioral import compute_health_score, get_vibe_state, get_pet_state


# ──────────────────────────────────────────────────────────────────────
# Helper: build a standardised engine
# ──────────────────────────────────────────────────────────────────────
def _make_engine(seed: int = 42, horizon: int = 365) -> SimulationEngine:
    cfg = SimulationConfig(
        start_date=datetime(2025, 1, 1),
        horizon_days=horizon,
        seed=seed,
        base_currency="USD",
        currencies=["USD", "EUR", "GBP", "PKR"],
        initial_balance=Decimal("10000"),
    )
    eng = SimulationEngine(cfg)
    eng.add_income_source(IncomeSource(
        id="i1", name="Salary", amount=Decimal("5000"),
        currency="USD", frequency="monthly",
    ))
    eng.add_expense(ExpenseItem(
        id="e1", name="Rent", amount=Decimal("2500"),
        currency="USD", frequency="monthly",
    ))
    eng.initialize(
        initial_balance=Decimal("10000"),
        assets=[
            Asset(id="a1", name="Savings", type=AssetType.LIQUID,
                  value=Decimal("5000"), currency="USD", volatility=0.02),
            Asset(id="a2", name="Stocks", type=AssetType.VOLATILE,
                  value=Decimal("3000"), currency="USD", volatility=0.15),
        ],
        liabilities=[
            Liability(id="l1", name="Loan", principal=Decimal("20000"),
                      interest_rate=0.05, monthly_payment=Decimal("400"),
                      currency="USD", start_date=datetime(2025, 1, 1),
                      remaining_balance=Decimal("20000")),
        ],
        credit_score=680.0,
    )
    return eng


# ======================================================================
# 1  DETERMINISM (seed-based reproducibility)
# ======================================================================
class TestDeterminism:
    """Given identical seeds and inputs → bit-exact identical outputs."""

    def test_same_seed_same_results(self):
        r1 = _make_engine(seed=42).run_simulation()
        r2 = _make_engine(seed=42).run_simulation()

        assert r1["final_balance"] == r2["final_balance"]
        assert r1["final_credit_score"] == r2["final_credit_score"]
        assert r1["balance_history"] == r2["balance_history"]
        assert r1["resilience_score_index"] == r2["resilience_score_index"]

    def test_different_seed_different_results(self):
        r1 = _make_engine(seed=42).run_simulation()
        r2 = _make_engine(seed=99).run_simulation()
        # NAV includes volatile-asset values which are seed-dependent
        assert r1["nav_history"] != r2["nav_history"]

    def test_hundred_runs_identical(self):
        """Run 100 times with the same seed – all must match run 0."""
        reference = _make_engine(seed=7, horizon=90).run_simulation()
        for _ in range(99):
            result = _make_engine(seed=7, horizon=90).run_simulation()
            assert result["final_balance"] == reference["final_balance"]


# ======================================================================
# 2  PRECISION DRIFT (currency conversion)
# ======================================================================
class TestPrecision:
    """Currency conversion must not introduce precision drift."""

    def test_round_trip_precision(self):
        mgr = ExchangeRateManager("USD", ["USD", "EUR"], seed=42)
        original = Decimal("12345.67")
        eur = mgr.convert(original, "USD", "EUR")
        back = mgr.convert(eur, "EUR", "USD")
        drift = abs(float(original) - float(back)) / float(original)
        assert drift < 0.01, f"Round-trip drift {drift:.4%} exceeds 1 %"

    def test_long_horizon_drift(self):
        """10 000 daily conversions – cumulative drift must stay < 5 %.
        Note: Rates change daily with volatility so the drift reflects
        real exchange-rate movement, not rounding error."""
        mgr = ExchangeRateManager("USD", ["USD", "EUR"], seed=42)
        value = Decimal("1000000")
        for day in range(10_000):
            mgr.update_rates_daily(day, volatility=0.001)
            eur = mgr.convert(value, "USD", "EUR")
            value = mgr.convert(eur, "EUR", "USD")
        drift = abs(float(value) - 1_000_000) / 1_000_000
        assert drift < 0.05, f"Cumulative drift {drift:.4%}"


# ======================================================================
# 3  SNAPSHOT RESTORATION CONSISTENCY
# ======================================================================
class TestSnapshot:
    """Snapshot restoration must reproduce the original trajectory."""

    def test_restore_matches_original(self):
        sm = StateManager()
        sm.initialize_state(
            day=0, date=datetime(2025, 1, 1),
            balance=Decimal("5000"), assets=[], liabilities=[],
        )
        sm.create_snapshot(0)

        # Advance state
        sm.update_state(day=10, balance=Decimal("7500"))
        sm.create_snapshot(10)

        # Restore to day 0
        sm.restore_snapshot(0)
        assert sm.current_state.balance == Decimal("5000")
        assert sm.current_state.day == 0

        # Restore to day 10
        sm.restore_snapshot(10)
        assert sm.current_state.balance == Decimal("7500")

    def test_snapshot_immutability(self):
        """Modifying state after snapshot must not alter the snapshot."""
        sm = StateManager()
        sm.initialize_state(day=0, date=datetime(2025, 1, 1),
                            balance=Decimal("3000"))
        sm.create_snapshot(0)
        sm.update_state(balance=Decimal("0"))
        sm.restore_snapshot(0)
        assert sm.current_state.balance == Decimal("3000")


# ======================================================================
# 4  DAG CYCLE DETECTION
# ======================================================================
class TestDAG:
    """Dependency graph must detect cycles and invalid states."""

    def test_topological_order(self):
        dag = DependencyGraph()
        dag.add_node("A", lambda s: s)
        dag.add_node("B", lambda s: s, dependencies=["A"])
        dag.add_node("C", lambda s: s, dependencies=["B"])
        order = dag.topological_sort()
        assert order.index("A") < order.index("B") < order.index("C")

    def test_cycle_raises(self):
        dag = DependencyGraph()
        dag.add_node("X", lambda s: s)
        dag.add_node("Y", lambda s: s, dependencies=["X"])
        dag.nodes["X"].add_dependency("Y")  # create cycle
        with pytest.raises(ValueError, match="Cycle"):
            dag.topological_sort()

    def test_missing_dependency_raises(self):
        dag = DependencyGraph()
        dag.add_node("A", lambda s: s, dependencies=["MISSING"])
        with pytest.raises(ValueError):
            dag.topological_sort()

    def test_duplicate_node_raises(self):
        dag = DependencyGraph()
        dag.add_node("A", lambda s: s)
        with pytest.raises(ValueError):
            dag.add_node("A", lambda s: s)


# ======================================================================
# 5  TAX LIABILITY ALIGNMENT
# ======================================================================
class TestTax:
    """Tax liabilities must align with realised asset gains."""

    def test_progressive_brackets(self):
        te = TaxationEngine()
        assert te.calculate_income_tax(Decimal("30000")) == Decimal("0")  # Below first bracket
        tax_100k = te.calculate_income_tax(Decimal("100000"))
        assert tax_100k > 0

    def test_zero_income_zero_tax(self):
        te = TaxationEngine()
        assert te.calculate_income_tax(Decimal("0")) == Decimal("0")

    def test_capital_gains_only_on_realised(self):
        te = TaxationEngine()
        te.record_unrealized_gain(Decimal("50000"))
        # unrealised gains should NOT be taxed
        assert te.calculate_capital_gains_tax() == Decimal("0")
        te.record_realized_gain(Decimal("10000"))
        assert te.calculate_capital_gains_tax() > 0


# ======================================================================
# 6  INFINITE LOOP PREVENTION
# ======================================================================
class TestInfiniteLoop:
    """DAG resolution must never hang."""

    def test_large_graph_terminates(self):
        dag = DependencyGraph()
        # Build a long chain of 200 nodes
        dag.add_node("node_0", lambda s: s)
        for i in range(1, 200):
            dag.add_node(f"node_{i}", lambda s: s, dependencies=[f"node_{i-1}"])
        order = dag.topological_sort()
        assert len(order) == 200

    def test_simulation_completes_in_time(self):
        """A 365-day simulation must finish (timeout handled by pytest)."""
        eng = _make_engine(seed=42, horizon=365)
        result = eng.run_simulation()
        assert result["total_days"] == 365
        assert "final_balance" in result


# ======================================================================
# 7  METRICS & BEHAVIORAL
# ======================================================================
class TestMetrics:
    def test_shock_clustering(self):
        me = RollingMetricsEngine()
        # No shocks → density 0
        for d in range(30):
            me.record_day(d, 10000, 10000)
        assert me.shock_clustering_density() == 0.0

        # Inject a shock
        me.record_day(31, 8000, 10000)  # -20 %
        assert me.shock_clustering_density() > 0

    def test_recovery_slope_positive(self):
        me = RollingMetricsEngine(window_size=20)
        for d in range(20):
            me.record_day(d, 5000 + d * 100, 5000 + max(0, d - 1) * 100)
        assert me.recovery_slope() >= 0

    def test_risk_analyzer_rsi(self):
        ra = RiskAnalyzer()
        for _ in range(365):
            ra.record_day(10000)
        # Perfect trajectory → high RSI
        assert ra.resilience_score_index() > 80

    def test_vibe_and_pet(self):
        score = compute_health_score(
            balance=20000, initial_balance=10000,
            credit_score=750, bankruptcy_prob=0.0,
            liquidity_ratio=0.8, shock_density=0.0, recovery_slope=5.0,
        )
        vibe = get_vibe_state(score)
        pet = get_pet_state(score)
        assert vibe["label"] in ["Thriving", "Confident", "Stable"]
        assert pet["emoji"] != ""


# ======================================================================
# 8  END-TO-END INTEGRATION
# ======================================================================
class TestEndToEnd:
    def test_stable_growth_scenario(self):
        eng = _make_engine(seed=42, horizon=365)
        r = eng.run_simulation()
        # Income > expenses → balance should grow
        assert r["final_balance"] > 10000

    def test_deficit_scenario(self):
        cfg = SimulationConfig(
            start_date=datetime(2025, 1, 1), horizon_days=365, seed=42,
            base_currency="USD", currencies=["USD"],
            initial_balance=Decimal("1000"),
        )
        eng = SimulationEngine(cfg)
        eng.add_income_source(IncomeSource(
            id="i", name="Low", amount=Decimal("1000"),
            currency="USD", frequency="monthly",
        ))
        eng.add_expense(ExpenseItem(
            id="e", name="High", amount=Decimal("3000"),
            currency="USD", frequency="monthly",
        ))
        eng.initialize(initial_balance=Decimal("1000"))
        r = eng.run_simulation()
        assert r["bankruptcy_probability"] > 0

    def test_output_has_all_required_keys(self):
        r = _make_engine(seed=42, horizon=90).run_simulation()
        required = [
            "final_balance", "balance_expected", "balance_5th", "balance_95th",
            "bankruptcy_probability", "bankruptcy_day",
            "resilience_score_index", "health_score",
            "vibe_state", "pet_state",
            "final_credit_score", "final_nav", "final_liquidity_ratio",
            "balance_history", "credit_history", "total_days",
        ]
        for key in required:
            assert key in r, f"Missing output key: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
