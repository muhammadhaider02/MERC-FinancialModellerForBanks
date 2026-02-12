"""
Main simulation engine – orchestrates all components.
Deterministic: identical seed + inputs → bit-exact identical outputs.
"""
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.models.models import (
    SimulationConfig, FinancialState, Asset, Liability,
    IncomeSource, ExpenseItem, Transaction, TransactionCategory,
)
from src.core.state import StateManager
from src.core.dag import DependencyGraph
from src.components.currency import ExchangeRateManager
from src.components.assets import AssetPortfolioManager
from src.components.credit import CreditScoreCalculator
from src.components.taxation import TaxationEngine
from src.components.liabilities import LiabilityManager
from src.metrics.metrics import RollingMetricsEngine
from src.metrics.risk import RiskAnalyzer
from src.outputs.outputs import OutputGenerator


class SimulationEngine:
    """Main deterministic financial simulation engine."""

    def __init__(self, config: SimulationConfig):
        self.config = config

        # Core managers
        self.state_manager = StateManager()
        self.currency_manager = ExchangeRateManager(
            config.base_currency, config.currencies, config.seed
        )
        self.asset_manager = AssetPortfolioManager(config.seed)
        self.credit_calculator = CreditScoreCalculator()
        self.tax_engine = TaxationEngine()
        self.liability_manager = LiabilityManager()

        # Metrics & risk
        self.metrics_engine = RollingMetricsEngine(window_size=90)
        self.risk_analyzer = RiskAnalyzer()

        # DAG for component execution order
        self.dag = DependencyGraph()
        self._build_dag()

        # Determinism
        np.random.seed(config.seed)

        # Cash-flow sources
        self.income_sources: List[IncomeSource] = []
        self.expense_items: List[ExpenseItem] = []

        # Tracking arrays (one entry per simulated day)
        self.balance_history: List[float] = []
        self.credit_history: List[float] = []
        self.nav_history: List[float] = []
        self.liquidity_history: List[float] = []

    def _build_dag(self):
        """Build the dependency graph for component execution order."""
        self.dag.add_node("exchange_rates", lambda ctx: self._step_exchange_rates(ctx))
        self.dag.add_node("income_expenses", lambda ctx: self._step_income_expenses(ctx),
                          dependencies=["exchange_rates"])
        self.dag.add_node("asset_valuation", lambda ctx: self._step_asset_valuation(ctx),
                          dependencies=["exchange_rates"])
        self.dag.add_node("liability_accrual", lambda ctx: self._step_liability_accrual(ctx),
                          dependencies=["exchange_rates"])
        self.dag.add_node("monthly_payments", lambda ctx: self._step_monthly_payments(ctx),
                          dependencies=["liability_accrual", "income_expenses"])
        self.dag.add_node("annual_tax", lambda ctx: self._step_annual_tax(ctx),
                          dependencies=["income_expenses"])
        self.dag.add_node("deficit_liquidation", lambda ctx: self._step_deficit_liquidation(ctx),
                          dependencies=["monthly_payments", "annual_tax", "asset_valuation"])
        self.dag.add_node("credit_update", lambda ctx: self._step_credit_update(ctx),
                          dependencies=["deficit_liquidation", "monthly_payments"])
        self.dag.add_node("commit_state", lambda ctx: self._step_commit_state(ctx),
                          dependencies=["credit_update"])
        self.dag.add_node("metrics_tracking", lambda ctx: self._step_metrics_tracking(ctx),
                          dependencies=["commit_state"])
        self.dag.add_node("snapshot", lambda ctx: self._step_snapshot(ctx),
                          dependencies=["metrics_tracking"])

    # ------------------------------------------------------------------
    # DAG step functions
    # ------------------------------------------------------------------
    def _step_exchange_rates(self, ctx: Dict) -> Dict:
        self.currency_manager.update_rates_daily(ctx["day"])
        return ctx

    def _step_income_expenses(self, ctx: Dict) -> Dict:
        income = self._process_income(ctx["day"])
        expenses = self._process_expenses(ctx["day"])
        ctx["income"] = income
        ctx["expenses"] = expenses
        ctx["new_balance"] = ctx["state"].balance + income - expenses
        ctx["annual_income_acc"] += income
        return ctx

    def _step_asset_valuation(self, ctx: Dict) -> Dict:
        ctx["updated_assets"] = self.asset_manager.update_asset_values(
            ctx["state"].assets, ctx["day"])
        return ctx

    def _step_liability_accrual(self, ctx: Dict) -> Dict:
        ctx["updated_liabilities"] = self.liability_manager.accrue_daily_interest(
            ctx["state"].liabilities, ctx["current_date"])
        return ctx

    def _step_monthly_payments(self, ctx: Dict) -> Dict:
        day = ctx["day"]
        if day % 30 == 0 and day > 0:
            payment = self.liability_manager.calculate_monthly_obligations(
                ctx["updated_liabilities"])
            ctx["new_balance"] -= payment
            on_time = ctx["new_balance"] >= 0
            self.credit_calculator.record_payment(on_time)
        return ctx

    def _step_annual_tax(self, ctx: Dict) -> Dict:
        day = ctx["day"]
        if day % 365 == 0 and day > 0:
            tax = self.tax_engine.apply_annual_tax(ctx["annual_income_acc"])
            ctx["new_balance"] -= tax
            ctx["annual_income_acc"] = Decimal("0")
            self.tax_engine.reset_annual_gains()
        return ctx

    def _step_deficit_liquidation(self, ctx: Dict) -> Dict:
        if ctx["new_balance"] < 0:
            deficit = abs(ctx["new_balance"])
            # Track asset values before liquidation for realized gains
            pre_liquidation_value = self.asset_manager.calculate_total_value(
                ctx["updated_assets"])
            ctx["updated_assets"], raised, penalty = self.asset_manager.liquidate_assets(
                ctx["updated_assets"], deficit, ctx["current_date"])
            post_liquidation_value = self.asset_manager.calculate_total_value(
                ctx["updated_assets"])
            # Record realized gain from liquidation (sale proceeds - cost basis)
            realized_gain = raised - (pre_liquidation_value - post_liquidation_value) + penalty
            if realized_gain > 0:
                self.tax_engine.record_realized_gain(realized_gain)
            ctx["new_balance"] += raised
        return ctx

    def _step_credit_update(self, ctx: Dict) -> Dict:
        total_debt = self.liability_manager.calculate_total_debt(
            ctx["updated_liabilities"])
        monthly_income = self._process_income(0) * Decimal("30")
        debt_ratio = self.credit_calculator.calculate_debt_ratio(
            total_debt, monthly_income)
        total_asset_val = self.asset_manager.calculate_total_value(
            ctx["updated_assets"])
        self.credit_calculator.update_score(
            debt_ratio, ctx["new_balance"], total_asset_val,
            had_default=(ctx["new_balance"] < 0),
        )
        return ctx

    def _step_commit_state(self, ctx: Dict) -> Dict:
        self.state_manager.update_state(
            day=ctx["day"],
            date=ctx["current_date"],
            balance=ctx["new_balance"],
            assets=ctx["updated_assets"],
            liabilities=ctx["updated_liabilities"],
            credit_score=self.credit_calculator.get_score(),
        )
        return ctx

    def _step_metrics_tracking(self, ctx: Dict) -> Dict:
        cur_balance = float(ctx["new_balance"])
        self.metrics_engine.record_day(ctx["day"], cur_balance, ctx["prev_balance"])
        self.risk_analyzer.record_day(cur_balance)

        nav = float(self.state_manager.calculate_nav())
        liq = self.state_manager.calculate_liquidity_ratio()

        self.balance_history.append(cur_balance)
        self.credit_history.append(self.credit_calculator.get_score())
        self.nav_history.append(nav)
        self.liquidity_history.append(liq)
        return ctx

    def _step_snapshot(self, ctx: Dict) -> Dict:
        if ctx["day"] % 30 == 0:
            self.state_manager.create_snapshot(ctx["day"])
        return ctx

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def add_income_source(self, income: IncomeSource):
        self.income_sources.append(income)

    def add_expense(self, expense: ExpenseItem):
        self.expense_items.append(expense)

    def initialize(
        self,
        initial_balance: Decimal,
        assets: Optional[List[Asset]] = None,
        liabilities: Optional[List[Liability]] = None,
        credit_score: float = 650.0,
    ):
        self.state_manager.initialize_state(
            day=0,
            date=self.config.start_date,
            balance=initial_balance,
            assets=assets or [],
            liabilities=liabilities or [],
            credit_score=credit_score,
        )
        self.credit_calculator.score = credit_score

    # ------------------------------------------------------------------
    # Internal income / expense helpers
    # ------------------------------------------------------------------
    def _daily_amount(self, amount: Decimal, frequency: str, day: int) -> Decimal:
        """Convert a recurring amount to a daily figure based on frequency."""
        if frequency == "daily":
            return amount
        if frequency == "weekly":
            return amount if day % 7 == 0 else Decimal("0")
        if frequency == "monthly":
            return amount if day % 30 == 0 else Decimal("0")
        if frequency == "yearly":
            return amount if day % 365 == 0 else Decimal("0")
        return Decimal("0")

    def _process_income(self, day: int) -> Decimal:
        total = Decimal("0")
        for src in self.income_sources:
            amt = self._daily_amount(src.amount, src.frequency, day)
            if src.currency != self.config.base_currency:
                amt = self.currency_manager.convert(
                    amt, src.currency, self.config.base_currency
                )
            total += amt
        return total

    def _process_expenses(self, day: int) -> Decimal:
        total = Decimal("0")
        for exp in self.expense_items:
            amt = self._daily_amount(exp.amount, exp.frequency, day)
            if exp.currency != self.config.base_currency:
                amt = self.currency_manager.convert(
                    amt, exp.currency, self.config.base_currency
                )
            total += amt
        return total

    # ------------------------------------------------------------------
    # Main simulation loop
    # ------------------------------------------------------------------
    def run_simulation(self) -> Dict:
        """Run the complete simulation and return a results dict."""
        current_date = self.config.start_date
        annual_income_accumulator = Decimal("0")

        # Resolve execution order once via DAG topological sort
        execution_order = self.dag.topological_sort()

        for day in range(self.config.horizon_days):
            state = self.state_manager.current_state
            prev_balance = float(state.balance)

            # Build context dict for DAG steps
            ctx = {
                "day": day,
                "state": state,
                "prev_balance": prev_balance,
                "current_date": current_date,
                "new_balance": state.balance,
                "updated_assets": list(state.assets),
                "updated_liabilities": list(state.liabilities),
                "income": Decimal("0"),
                "expenses": Decimal("0"),
                "annual_income_acc": annual_income_accumulator,
            }

            # Execute all DAG nodes in resolved order
            for node_name in execution_order:
                node = self.dag.nodes[node_name]
                ctx = node.execute(ctx)

            # Carry forward the annual income accumulator
            annual_income_accumulator = ctx["annual_income_acc"]

            current_date += timedelta(days=1)

        # ── Assemble output via OutputGenerator ──────────────────────
        return OutputGenerator.generate(
            balance_history=self.balance_history,
            credit_history=self.credit_history,
            nav_history=self.nav_history,
            liquidity_history=self.liquidity_history,
            risk_snapshot=self.risk_analyzer.snapshot(),
            metrics_snapshot=self.metrics_engine.snapshot(),
            initial_balance=float(self.config.initial_balance),
            total_days=self.config.horizon_days,
        )

    # ------------------------------------------------------------------
    # Simulation branching – what-if scenarios from snapshots
    # ------------------------------------------------------------------
    def branch_from_snapshot(self, snapshot_day: int, **overrides) -> 'SimulationEngine':
        """
        Create a branched simulation from a snapshot for what-if analysis.

        Args:
            snapshot_day: Day of the snapshot to branch from
            **overrides: Overrides for the branched engine (e.g. income, expenses)

        Returns:
            A new SimulationEngine configured to continue from the snapshot
        """
        if snapshot_day not in self.state_manager.snapshots:
            raise ValueError(f"No snapshot found for day {snapshot_day}")

        snapshot_state = self.state_manager.snapshots[snapshot_day]
        remaining_days = self.config.horizon_days - snapshot_day

        import copy
        branch_config = copy.deepcopy(self.config)
        branch_config.horizon_days = remaining_days
        branch_config.start_date = snapshot_state.date

        branch_engine = SimulationEngine(branch_config)

        # Copy income/expense sources (allow overrides)
        branch_engine.income_sources = copy.deepcopy(
            overrides.get("income_sources", self.income_sources))
        branch_engine.expense_items = copy.deepcopy(
            overrides.get("expense_items", self.expense_items))

        # Initialize from snapshot state
        branch_engine.initialize(
            initial_balance=snapshot_state.balance,
            assets=copy.deepcopy(snapshot_state.assets),
            liabilities=copy.deepcopy(snapshot_state.liabilities),
            credit_score=snapshot_state.credit_score,
        )

        return branch_engine

    @staticmethod
    def merge_results(*results_list: Dict) -> Dict:
        """
        Merge and compare results from multiple simulation branches.

        Args:
            *results_list: Result dicts from multiple simulation runs

        Returns:
            Merged comparison dict with per-branch metrics and aggregates
        """
        if not results_list:
            raise ValueError("At least one result set is required")

        merged = {
            "branch_count": len(results_list),
            "branches": [],
            "comparison": {},
        }

        balances = []
        credit_scores = []
        navs = []
        bankruptcy_probs = []

        for i, result in enumerate(results_list):
            branch_summary = {
                "branch_id": i,
                "final_balance": result["final_balance"],
                "final_credit_score": result["final_credit_score"],
                "final_nav": result["final_nav"],
                "bankruptcy_probability": result["bankruptcy_probability"],
                "resilience_score_index": result["resilience_score_index"],
                "health_score": result["health_score"],
                "vibe_state": result["vibe_state"]["label"],
            }
            merged["branches"].append(branch_summary)
            balances.append(result["final_balance"])
            credit_scores.append(result["final_credit_score"])
            navs.append(result["final_nav"])
            bankruptcy_probs.append(result["bankruptcy_probability"])

        merged["comparison"] = {
            "best_final_balance": max(balances),
            "worst_final_balance": min(balances),
            "avg_final_balance": sum(balances) / len(balances),
            "best_credit_score": max(credit_scores),
            "worst_credit_score": min(credit_scores),
            "best_nav": max(navs),
            "worst_nav": min(navs),
            "avg_bankruptcy_prob": sum(bankruptcy_probs) / len(bankruptcy_probs),
        }

        return merged
