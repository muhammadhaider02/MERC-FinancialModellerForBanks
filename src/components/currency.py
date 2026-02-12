"""
Multi-currency exchange system with daily volatility.
Rates are maintained as *base-currency rates* so that inverse
consistency is guaranteed (no round-trip drift from independent mutations).
"""
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List


class ExchangeRateManager:
    """Manages multi-currency exchange rates with deterministic volatility."""

    def __init__(self, base_currency: str, supported_currencies: List[str], seed: int = 42):
        self.base_currency = base_currency
        self.supported_currencies = supported_currencies
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # Store only base-currency rates: {currency: rate_vs_base}
        # e.g.  {"EUR": 0.92, "GBP": 0.79, "PKR": 278.50, "USD": 1.0}
        self._base_rates: Dict[str, float] = {}
        self._initialize_base_rates()

    # ------------------------------------------------------------------
    def _initialize_base_rates(self):
        """Seed the base rates (1 unit of base = X units of target)."""
        defaults = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "PKR": 278.50}
        for c in self.supported_currencies:
            self._base_rates[c] = defaults.get(c, 1.0)

    # ------------------------------------------------------------------
    def update_rates_daily(self, day: int, volatility: float = 0.01):
        """Apply a random‐walk to each base rate (deterministic per day)."""
        day_rng = np.random.RandomState(self.seed + day)
        for c in self.supported_currencies:
            if c == self.base_currency:
                continue
            change = day_rng.normal(0, volatility)
            self._base_rates[c] *= (1 + change)

    # ------------------------------------------------------------------
    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """
        Convert *amount* between any two supported currencies.

        Cross-rates are derived through the base currency,
        guaranteeing inverse consistency.
        """
        if from_currency == to_currency:
            return amount

        # from → base → to
        from_rate = self._base_rates.get(from_currency)
        to_rate = self._base_rates.get(to_currency)
        if from_rate is None or to_rate is None:
            raise ValueError(f"Unsupported currency pair {from_currency} → {to_currency}")

        cross = to_rate / from_rate
        converted = float(amount) * cross
        return Decimal(str(converted)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------
    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Derive the current cross rate."""
        from_rate = self._base_rates.get(from_currency)
        to_rate = self._base_rates.get(to_currency)
        if from_rate is None or to_rate is None:
            raise ValueError(f"Unsupported currency pair {from_currency} → {to_currency}")
        return Decimal(str(to_rate / from_rate))

    # ------------------------------------------------------------------
    def validate_precision(self, amount: Decimal, currency: str) -> bool:
        """True if amount has ≤ 2 decimal places."""
        decimal_str = str(amount)
        if "." in decimal_str:
            return len(decimal_str.split(".")[1]) <= 2
        return True
