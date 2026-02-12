"""
Risk analysis engine – bankruptcy probability, RSI, stress testing.
"""
import numpy as np
from typing import List, Dict, Optional


class RiskAnalyzer:
    """Analyses financial risk from simulation trajectories."""

    def __init__(self):
        self._balance_history: List[float] = []
        self._deficit_days: int = 0
        self._total_days: int = 0
        self._worst_drawdown: float = 0.0
        self._peak_balance: float = 0.0

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def record_day(self, balance: float):
        """Feed one day of balance data."""
        self._balance_history.append(balance)
        self._total_days += 1

        if balance < 0:
            self._deficit_days += 1

        # Track peak & drawdown
        if balance > self._peak_balance:
            self._peak_balance = balance
        if self._peak_balance > 0:
            drawdown = (self._peak_balance - balance) / self._peak_balance
            self._worst_drawdown = max(self._worst_drawdown, drawdown)

    # ------------------------------------------------------------------
    # Bankruptcy probability
    # ------------------------------------------------------------------
    def bankruptcy_probability(self) -> float:
        """
        Proportion of days spent in deficit, used as a simple proxy
        for the probability of financial collapse over the horizon.
        """
        if self._total_days == 0:
            return 0.0
        return self._deficit_days / self._total_days

    def bankruptcy_timing(self) -> Optional[int]:
        """Day on which the balance first went negative, or None."""
        for i, b in enumerate(self._balance_history):
            if b < 0:
                return i
        return None

    # ------------------------------------------------------------------
    # Resilience Score Index (RSI)
    # ------------------------------------------------------------------
    def resilience_score_index(self) -> float:
        """
        RSI ∈ [0, 100].  Combines:
          • (1 − bankruptcy_prob)        weight 0.40
          • (1 − worst_drawdown)         weight 0.30
          • recovery_ratio               weight 0.30

        Higher = more resilient.
        """
        bp = self.bankruptcy_probability()
        dd = min(1.0, self._worst_drawdown)

        # Recovery ratio: how well the balance recovered from its worst point
        if len(self._balance_history) < 2:
            recovery = 1.0
        else:
            min_bal = min(self._balance_history)
            final_bal = self._balance_history[-1]
            if self._peak_balance > 0 and min_bal < self._peak_balance:
                recovery = max(0, (final_bal - min_bal) / (self._peak_balance - min_bal))
            else:
                recovery = 1.0

        rsi = (0.40 * (1 - bp) + 0.30 * (1 - dd) + 0.30 * recovery) * 100
        return max(0, min(100, rsi))

    # ------------------------------------------------------------------
    # Collapse timing density
    # ------------------------------------------------------------------
    def collapse_timing_density(self, bins: int = 12) -> Dict:
        """
        Break the horizon into *bins* equal periods and return the
        fraction of deficit days in each bin – gives a temporal density
        of when collapse is most likely.
        """
        if not self._balance_history:
            return {"bins": [], "density": []}

        arr = np.array(self._balance_history)
        chunk_size = max(1, len(arr) // bins)
        densities = []
        labels = []
        for i in range(bins):
            start = i * chunk_size
            end = min(start + chunk_size, len(arr))
            chunk = arr[start:end]
            if len(chunk) == 0:
                break
            deficit_frac = float(np.sum(chunk < 0) / len(chunk))
            densities.append(deficit_frac)
            labels.append(f"Period {i + 1}")

        return {"bins": labels, "density": densities}

    # ------------------------------------------------------------------
    # Aggregate snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict:
        """Full risk snapshot."""
        return {
            "bankruptcy_probability": self.bankruptcy_probability(),
            "bankruptcy_timing_day": self.bankruptcy_timing(),
            "resilience_score_index": self.resilience_score_index(),
            "worst_drawdown": self._worst_drawdown,
            "deficit_days": self._deficit_days,
            "total_days": self._total_days,
            "collapse_density": self.collapse_timing_density(),
        }
