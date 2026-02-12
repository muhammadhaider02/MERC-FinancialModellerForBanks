"""
Rolling metrics computation system.
Tracks shock clustering density, recovery slope, and financial health indicators.
"""
import numpy as np
from typing import List, Dict, Optional
from collections import deque


class RollingMetricsEngine:
    """Computes rolling financial metrics from balance and event history."""

    def __init__(self, window_size: int = 90):
        """
        Args:
            window_size: Number of days for rolling window calculations.
        """
        self.window_size = window_size
        self._balance_window: deque = deque(maxlen=window_size)
        self._shock_events: List[Dict] = []  # {day, magnitude}
        self._recovery_events: List[Dict] = []  # {start_day, end_day, slope}

    # ------------------------------------------------------------------
    # Core ingestion
    # ------------------------------------------------------------------
    def record_day(self, day: int, balance: float, prev_balance: float):
        """Feed a single day's data into the metrics engine."""
        self._balance_window.append(balance)

        # Detect shocks: balance drop > 5 % in a single day
        if prev_balance > 0:
            pct_change = (balance - prev_balance) / prev_balance
            if pct_change < -0.05:
                self._shock_events.append({
                    "day": day,
                    "magnitude": abs(pct_change),
                    "absolute_drop": prev_balance - balance,
                })

    # ------------------------------------------------------------------
    # Shock Clustering Density
    # ------------------------------------------------------------------
    def shock_clustering_density(self, lookback_days: int = 30) -> float:
        """
        Frequency × average intensity of financial shocks in the recent window.

        Returns a value ≥ 0 where higher = more clustered / severe shocks.
        """
        if not self._shock_events:
            return 0.0

        latest_day = self._shock_events[-1]["day"]
        recent = [s for s in self._shock_events if s["day"] > latest_day - lookback_days]

        if not recent:
            return 0.0

        frequency = len(recent) / lookback_days
        avg_magnitude = np.mean([s["magnitude"] for s in recent])
        return float(frequency * avg_magnitude)

    # ------------------------------------------------------------------
    # Recovery Slope
    # ------------------------------------------------------------------
    def recovery_slope(self) -> float:
        """
        Rate of balance restoration after the most recent deficit.

        Returns the slope ($/day) of the recovery segment.  0.0 if no
        recovery detected yet.
        """
        window = list(self._balance_window)
        if len(window) < 3:
            return 0.0

        # Find most recent trough (min in the window)
        min_idx = int(np.argmin(window))
        if min_idx >= len(window) - 1:
            return 0.0  # trough is at the end → no recovery yet

        recovery_segment = window[min_idx:]
        if len(recovery_segment) < 2:
            return 0.0

        # Linear fit over the recovery segment
        x = np.arange(len(recovery_segment), dtype=float)
        slope, _ = np.polyfit(x, recovery_segment, 1)
        return max(0.0, float(slope))  # only positive = recovery

    # ------------------------------------------------------------------
    # Rolling volatility
    # ------------------------------------------------------------------
    def rolling_volatility(self) -> float:
        """Standard‐deviation of daily balance changes in the window."""
        window = list(self._balance_window)
        if len(window) < 2:
            return 0.0
        changes = np.diff(window)
        return float(np.std(changes))

    # ------------------------------------------------------------------
    # Aggregate snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict:
        """Return a dictionary of all current metric values."""
        return {
            "shock_clustering_density": self.shock_clustering_density(),
            "recovery_slope": self.recovery_slope(),
            "rolling_volatility": self.rolling_volatility(),
            "total_shocks": len(self._shock_events),
        }
