"""
Credit scoring system based on debt ratios and payment punctuality.
"""
from decimal import Decimal
from typing import List
from src.models.models import Liability


class CreditScoreCalculator:
    """Calculates and evolves credit score."""
    
    def __init__(self, initial_score: float = 650.0):
        self.score = initial_score
        self.payment_history: List[bool] = []  # True = on-time, False = late
        self.min_score = 300.0
        self.max_score = 850.0
    
    def calculate_debt_ratio(self, total_debt: Decimal, monthly_income: Decimal) -> float:
        """
        Calculate debt-to-income ratio.
        
        Args:
            total_debt: Total outstanding debt
            monthly_income: Monthly income
            
        Returns:
            Debt ratio (0.0 to 1.0+)
        """
        if monthly_income == 0:
            return float('inf') if total_debt > 0 else 0.0
        
        return float(total_debt / (monthly_income * 12))  # Annual income
    
    def record_payment(self, on_time: bool):
        """Record a payment (on-time or late)."""
        self.payment_history.append(on_time)
        
        # Keep only last 24 months of history
        if len(self.payment_history) > 24:
            self.payment_history.pop(0)
    
    def calculate_punctuality_score(self) -> float:
        """
        Calculate punctuality score based on payment history.
        
        Returns:
            Score from 0.0 (all late) to 1.0 (all on-time)
        """
        if not self.payment_history:
            return 1.0  # No history = neutral
        
        on_time_count = sum(self.payment_history)
        return on_time_count / len(self.payment_history)
    
    def update_score(self, debt_ratio: float, balance: Decimal, 
                    total_assets: Decimal, had_default: bool = False):
        """
        Update credit score based on financial factors.
        
        Credit score formula:
        - Debt ratio impact: -200 points at 100% ratio
        - Punctuality impact: +50 points for perfect history
        - Asset impact: +30 points for high assets
        - Default penalty: -100 points
        
        Args:
            debt_ratio: Current debt-to-income ratio
            balance: Current balance
            total_assets: Total asset value
            had_default: Whether a default occurred
        """
        # Start from current score
        new_score = self.score
        
        # Debt ratio impact (negative)
        if debt_ratio > 0:
            debt_penalty = min(200, debt_ratio * 200)
            new_score -= debt_penalty * 0.1  # Gradual impact
        
        # Punctuality impact (positive)
        punctuality = self.calculate_punctuality_score()
        punctuality_bonus = (punctuality - 0.5) * 50  # -25 to +25
        new_score += punctuality_bonus * 0.1
        
        # Asset/balance impact (positive)
        if total_assets > 0:
            asset_bonus = min(30, float(total_assets) / 10000)
            new_score += asset_bonus * 0.1
        
        # Balance impact
        if balance > 0:
            balance_bonus = min(20, float(balance) / 5000)
            new_score += balance_bonus * 0.1
        elif balance < 0:
            # Negative balance is very bad
            new_score -= 50
        
        # Default penalty
        if had_default:
            new_score -= 100
        
        # Clamp to valid range
        self.score = max(self.min_score, min(self.max_score, new_score))
    
    def get_score(self) -> float:
        """Get current credit score."""
        return self.score
    
    def get_credit_rating(self) -> str:
        """
        Get credit rating category.
        
        Returns:
            Rating: Excellent, Good, Fair, Poor, Very Poor
        """
        if self.score >= 750:
            return "Excellent"
        elif self.score >= 700:
            return "Good"
        elif self.score >= 650:
            return "Fair"
        elif self.score >= 600:
            return "Poor"
        else:
            return "Very Poor"
