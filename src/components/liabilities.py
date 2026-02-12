"""
Liability and debt management with interest accrual.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List
from src.models.models import Liability


class LiabilityManager:
    """Manages debts and liabilities with interest accrual."""
    
    def __init__(self):
        pass
    
    def accrue_daily_interest(self, liabilities: List[Liability], current_date: datetime) -> List[Liability]:
        """
        Accrue daily interest on all liabilities.
        
        Args:
            liabilities: List of liabilities
            current_date: Current simulation date
            
        Returns:
            Updated liabilities with accrued interest
        """
        updated_liabilities = []
        
        for liability in liabilities:
            # Create a copy
            updated_liability = liability.copy(deep=True)
            
            # Calculate daily interest rate
            annual_rate = Decimal(str(liability.interest_rate))
            daily_rate = annual_rate / Decimal("365")
            
            # Accrue interest
            interest = updated_liability.remaining_balance * daily_rate
            updated_liability.remaining_balance += interest
            
            updated_liabilities.append(updated_liability)
        
        return updated_liabilities
    
    def process_payment(self, liability: Liability, payment_amount: Decimal, 
                       on_time: bool = True) -> tuple[Liability, bool]:
        """
        Process a payment on a liability.
        
        Args:
            liability: Liability to pay
            payment_amount: Amount to pay
            on_time: Whether payment is on time
            
        Returns:
            Tuple of (updated_liability, is_paid_off)
        """
        updated_liability = liability.copy(deep=True)
        
        # Apply payment to balance
        updated_liability.remaining_balance -= payment_amount
        
        # Check if paid off
        is_paid_off = updated_liability.remaining_balance <= 0
        
        if is_paid_off:
            updated_liability.remaining_balance = Decimal("0")
        
        return updated_liability, is_paid_off
    
    def calculate_monthly_obligations(self, liabilities: List[Liability]) -> Decimal:
        """
        Calculate total monthly payment obligations.
        
        Args:
            liabilities: List of liabilities
            
        Returns:
            Total monthly payment amount
        """
        total = Decimal("0")
        for liability in liabilities:
            total += liability.monthly_payment
        return total
    
    def calculate_total_debt(self, liabilities: List[Liability]) -> Decimal:
        """
        Calculate total outstanding debt.
        
        Args:
            liabilities: List of liabilities
            
        Returns:
            Total debt amount
        """
        total = Decimal("0")
        for liability in liabilities:
            total += liability.remaining_balance
        return total
    
    def check_default_risk(self, balance: Decimal, monthly_payment: Decimal) -> bool:
        """
        Check if there's risk of default.
        
        Args:
            balance: Current balance
            monthly_payment: Required monthly payment
            
        Returns:
            True if at risk of default
        """
        return balance < monthly_payment
    
    def restructure_debt(self, liability: Liability, new_interest_rate: float, 
                        new_monthly_payment: Decimal) -> Liability:
        """
        Restructure a debt with new terms.
        
        Args:
            liability: Liability to restructure
            new_interest_rate: New interest rate
            new_monthly_payment: New monthly payment
            
        Returns:
            Restructured liability
        """
        restructured = liability.copy(deep=True)
        restructured.interest_rate = new_interest_rate
        restructured.monthly_payment = new_monthly_payment
        return restructured
