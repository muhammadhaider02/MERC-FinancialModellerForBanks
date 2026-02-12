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

        for day in range(self.config.horizon_days):
            state = self.state_manager.current_state
            prev_balance = float(state.balance)

            # 1 ── Exchange rates
            self.currency_manager.update_rates_daily(day)

            # 2 ── Income & expenses
            income = self._process_income(day)
            expenses = self._process_expenses(day)
            new_balance = state.balance + income - expenses
            annual_income_accumulator += income

            # 3 ── Asset valuation
            updated_assets = self.asset_manager.update_asset_values(state.assets, day)

            # 4 ── Liability interest accrual
            updated_liabilities = self.liability_manager.accrue_daily_interest(
                state.liabilities, current_date
            )

            # 5 ── Monthly liability payments
            if day % 30 == 0 and day > 0:
                payment = self.liability_manager.calculate_monthly_obligations(
                    updated_liabilities
                )
                new_balance -= payment
                on_time = new_balance >= 0
                self.credit_calculator.record_payment(on_time)

            # 6 ── Annual tax deduction
            if day % 365 == 0 and day > 0:
                tax = self.tax_engine.apply_annual_tax(annual_income_accumulator)
                new_balance -= tax
                annual_income_accumulator = Decimal("0")
                self.tax_engine.reset_annual_gains()

            # 7 ── Deficit → liquidate assets
            if new_balance < 0:
                deficit = abs(new_balance)
                updated_assets, raised, _ = self.asset_manager.liquidate_assets(
                    updated_assets, deficit, current_date
                )
                new_balance += raised

            # 8 ── Update credit score
            total_debt = self.liability_manager.calculate_total_debt(updated_liabilities)
            monthly_income = self._process_income(0) * Decimal("30")
            debt_ratio = self.credit_calculator.calculate_debt_ratio(total_debt, monthly_income)
            total_asset_val = self.asset_manager.calculate_total_value(updated_assets)
            self.credit_calculator.update_score(
                debt_ratio, new_balance, total_asset_val,
                had_default=(new_balance < 0),
            )

            # 9 ── Commit state
            self.state_manager.update_state(
                day=day,
                date=current_date,
                balance=new_balance,
                assets=updated_assets,
                liabilities=updated_liabilities,
                credit_score=self.credit_calculator.get_score(),
            )

            # 10 ── Metrics & risk tracking
            cur_balance = float(new_balance)
            self.metrics_engine.record_day(day, cur_balance, prev_balance)
            self.risk_analyzer.record_day(cur_balance)

            nav = float(self.state_manager.calculate_nav())
            liq = self.state_manager.calculate_liquidity_ratio()

            self.balance_history.append(cur_balance)
            self.credit_history.append(self.credit_calculator.get_score())
            self.nav_history.append(nav)
            self.liquidity_history.append(liq)

            # 11 ── Snapshot every 30 days
            if day % 30 == 0:
                self.state_manager.create_snapshot(day)

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
