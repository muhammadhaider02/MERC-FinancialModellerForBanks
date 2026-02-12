"""
Financial state management with snapshot and restore capabilities.
"""
import json
import copy
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from src.models.models import FinancialState, Asset, Liability, Transaction


class StateManager:
    """Manages financial state with snapshot/restore capabilities."""
    
    def __init__(self):
        self.current_state: Optional[FinancialState] = None
        self.snapshots: Dict[int, FinancialState] = {}  # day -> state
        self.transaction_history: List[Transaction] = []
        self.metrics_history: Dict[int, Dict] = {}  # day -> metrics
    
    def initialize_state(self, day: int, date: datetime, balance: Decimal, 
                        assets: List[Asset] = None, liabilities: List[Liability] = None,
                        credit_score: float = 650.0):
        """Initialize the financial state."""
        self.current_state = FinancialState(
            day=day,
            date=date,
            balance=balance,
            assets=assets or [],
            liabilities=liabilities or [],
            credit_score=credit_score
        )
    
    def update_state(self, **kwargs):
        """Update current state with new values."""
        if not self.current_state:
            raise ValueError("State not initialized")
        
        # Create updated state
        state_dict = self.current_state.dict()
        state_dict.update(kwargs)
        self.current_state = FinancialState(**state_dict)
    
    def create_snapshot(self, day: int):
        """Create a snapshot of the current state."""
        if not self.current_state:
            raise ValueError("State not initialized")
        
        # Deep copy to ensure immutability
        self.snapshots[day] = copy.deepcopy(self.current_state)
    
    def restore_snapshot(self, day: int):
        """Restore state from a snapshot."""
        if day not in self.snapshots:
            raise ValueError(f"No snapshot found for day {day}")
        
        self.current_state = copy.deepcopy(self.snapshots[day])
    
    def add_transaction(self, transaction: Transaction):
        """Record a transaction."""
        self.transaction_history.append(transaction)
    
    def store_metrics(self, day: int, metrics: Dict):
        """Store metrics for a specific day."""
        self.metrics_history[day] = metrics
    
    def get_balance_history(self) -> List[tuple]:
        """Get balance history as list of (day, balance) tuples."""
        history = []
        for day in sorted(self.snapshots.keys()):
            snapshot = self.snapshots[day]
            history.append((day, float(snapshot.balance)))
        return history
    
    def get_credit_score_history(self) -> List[tuple]:
        """Get credit score history as list of (day, score) tuples."""
        history = []
        for day in sorted(self.snapshots.keys()):
            snapshot = self.snapshots[day]
            history.append((day, snapshot.credit_score))
        return history
    
    def serialize(self) -> str:
        """Serialize current state to JSON."""
        if not self.current_state:
            raise ValueError("State not initialized")
        
        return self.current_state.json()
    
    def deserialize(self, json_str: str):
        """Deserialize state from JSON."""
        self.current_state = FinancialState.parse_raw(json_str)
    
    def calculate_nav(self) -> Decimal:
        """Calculate Net Asset Value (total assets - total liabilities)."""
        if not self.current_state:
            return Decimal("0")
        
        total_assets = self.current_state.balance
        for asset in self.current_state.assets:
            total_assets += asset.value
        
        total_liabilities = Decimal("0")
        for liability in self.current_state.liabilities:
            total_liabilities += liability.remaining_balance
        
        return total_assets - total_liabilities
    
    def calculate_liquidity_ratio(self) -> float:
        """Calculate liquidity ratio (liquid assets / total assets)."""
        if not self.current_state:
            return 0.0
        
        liquid_assets = self.current_state.balance
        total_assets = self.current_state.balance
        
        for asset in self.current_state.assets:
            total_assets += asset.value
            if asset.type == "liquid" and not asset.is_locked:
                liquid_assets += asset.value
        
        if total_assets == 0:
            return 0.0
        
        return float(liquid_assets / total_assets)
    
    def validate_state(self) -> bool:
        """Validate state integrity."""
        if not self.current_state:
            return False
        
        # Check for negative balance (bankruptcy indicator)
        if self.current_state.balance < 0:
            return False
        
        # Validate credit score range
        if not (300 <= self.current_state.credit_score <= 850):
            return False
        
        return True
