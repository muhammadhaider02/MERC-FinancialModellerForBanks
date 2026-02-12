"""
Pydantic data models for Future Wallet simulation engine.
"""
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional, List


class AssetType(str, Enum):
    """Types of assets in the portfolio."""
    LIQUID = "liquid"
    ILLIQUID = "illiquid"
    YIELD = "yield"
    VOLATILE = "volatile"


class TransactionCategory(str, Enum):
    """Transaction categories."""
    INCOME = "income"
    EXPENSE = "expense"
    ASSET_PURCHASE = "asset_purchase"
    ASSET_SALE = "asset_sale"
    LOAN_PAYMENT = "loan_payment"
    TAX_PAYMENT = "tax_payment"


class Transaction(BaseModel):
    """Financial transaction model."""
    date: datetime
    amount: Decimal
    currency: str
    category: TransactionCategory
    description: str = ""
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class Asset(BaseModel):
    """Asset in the portfolio."""
    id: str
    name: str
    type: AssetType
    value: Decimal
    currency: str
    volatility: float = Field(ge=0.0, le=1.0)
    is_locked: bool = False
    lock_until: Optional[datetime] = None
    sale_penalty: float = Field(default=0.0, ge=0.0, le=1.0)  # Percentage penalty on sale
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat() if v else None
        }


class Liability(BaseModel):
    """Debt or liability."""
    id: str
    name: str
    principal: Decimal
    interest_rate: float = Field(ge=0.0)  # Annual interest rate
    monthly_payment: Decimal
    currency: str
    start_date: datetime
    remaining_balance: Decimal
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class IncomeSource(BaseModel):
    """Recurring income source."""
    id: str
    name: str
    amount: Decimal
    currency: str
    frequency: str = "monthly"  # daily, weekly, monthly, yearly
    
    class Config:
        json_encoders = {
            Decimal: float
        }


class ExpenseItem(BaseModel):
    """Recurring expense."""
    id: str
    name: str
    amount: Decimal
    currency: str
    frequency: str = "monthly"  # daily, weekly, monthly, yearly
    
    class Config:
        json_encoders = {
            Decimal: float
        }


class SimulationConfig(BaseModel):
    """Configuration for a simulation run."""
    start_date: datetime
    horizon_days: int = Field(gt=0)
    seed: int
    base_currency: str = "USD"
    currencies: List[str]
    initial_balance: Decimal = Decimal("0")
    
    @validator('horizon_days')
    def validate_horizon(cls, v):
        if v > 10950:  # 30 years
            raise ValueError('Horizon too long (max 30 years)')
        return v
    
    @validator('currencies')
    def validate_currencies(cls, v, values):
        if 'base_currency' in values and values['base_currency'] not in v:
            raise ValueError('Base currency must be in supported currencies list')
        return v
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class FinancialState(BaseModel):
    """Complete financial state at a point in time."""
    day: int
    date: datetime
    balance: Decimal
    assets: List[Asset]
    liabilities: List[Liability]
    credit_score: float = Field(ge=300, le=850)
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class SimulationResult(BaseModel):
    """Results from a completed simulation."""
    config: SimulationConfig
    final_balance: Decimal
    final_balance_5th: Decimal
    final_balance_95th: Decimal
    bankruptcy_probability: float = Field(ge=0.0, le=1.0)
    bankruptcy_day: Optional[int] = None
    final_credit_score: float
    final_nav: Decimal  # Net Asset Value
    final_liquidity_ratio: float
    
    class Config:
        json_encoders = {
            Decimal: float
        }
