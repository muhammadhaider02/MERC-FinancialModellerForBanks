"""
Progressive taxation system with realized/unrealized gains tracking.
"""
from decimal import Decimal
from typing import List, Dict
import yaml


class TaxationEngine:
    """Manages progressive taxation and capital gains."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.brackets = []
        self.load_config(config_path)
        self.realized_gains: Decimal = Decimal("0")
        self.unrealized_gains: Decimal = Decimal("0")
    
    def load_config(self, config_path: str):
        """Load tax brackets from configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.brackets = config['taxation']['progressive_brackets']
        except Exception as e:
            # Default brackets if config fails
            self.brackets = [
                {'threshold': 0, 'rate': 0.0},
                {'threshold': 50000, 'rate': 0.10},
                {'threshold': 100000, 'rate': 0.20},
                {'threshold': 200000, 'rate': 0.30}
            ]
    
    def calculate_income_tax(self, annual_income: Decimal) -> Decimal:
        """
        Calculate progressive income tax.
        
        Args:
            annual_income: Total annual income
            
        Returns:
            Total tax owed
        """
        if annual_income <= 0:
            return Decimal("0")
        
        tax_owed = Decimal("0")
        remaining_income = annual_income
        
        # Sort brackets by threshold
        sorted_brackets = sorted(self.brackets, key=lambda x: x['threshold'])
        
        for i, bracket in enumerate(sorted_brackets):
            threshold = Decimal(str(bracket['threshold']))
            rate = Decimal(str(bracket['rate']))
            
            # Determine the income in this bracket
            if i < len(sorted_brackets) - 1:
                next_threshold = Decimal(str(sorted_brackets[i + 1]['threshold']))
                bracket_income = min(remaining_income, next_threshold - threshold)
            else:
                bracket_income = remaining_income
            
            if bracket_income > 0:
                tax_owed += bracket_income * rate
                remaining_income -= bracket_income
            
            if remaining_income <= 0:
                break
        
        return tax_owed
    
    def record_realized_gain(self, gain: Decimal):
        """Record a realized capital gain."""
        self.realized_gains += gain
    
    def record_unrealized_gain(self, gain: Decimal):
        """Record an unrealized capital gain."""
        self.unrealized_gains += gain
    
    def calculate_capital_gains_tax(self, rate: float = 0.15) -> Decimal:
        """
        Calculate capital gains tax on realized gains.
        
        Args:
            rate: Capital gains tax rate (default 15%)
            
        Returns:
            Tax owed on realized gains
        """
        if self.realized_gains <= 0:
            return Decimal("0")
        
        return self.realized_gains * Decimal(str(rate))
    
    def apply_annual_tax(self, annual_income: Decimal, 
                        include_capital_gains: bool = True) -> Decimal:
        """
        Calculate total annual tax liability.
        
        Args:
            annual_income: Total annual income
            include_capital_gains: Whether to include capital gains tax
            
        Returns:
            Total tax owed
        """
        income_tax = self.calculate_income_tax(annual_income)
        
        total_tax = income_tax
        
        if include_capital_gains:
            capital_gains_tax = self.calculate_capital_gains_tax()
            total_tax += capital_gains_tax
        
        return total_tax
    
    def reset_annual_gains(self):
        """Reset realized and unrealized gains (called at year end)."""
        self.realized_gains = Decimal("0")
        self.unrealized_gains = Decimal("0")
    
    def get_effective_tax_rate(self, annual_income: Decimal) -> float:
        """
        Calculate effective tax rate.
        
        Args:
            annual_income: Total annual income
            
        Returns:
            Effective tax rate as percentage
        """
        if annual_income <= 0:
            return 0.0
        
        tax_owed = self.calculate_income_tax(annual_income)
        return float(tax_owed / annual_income)
