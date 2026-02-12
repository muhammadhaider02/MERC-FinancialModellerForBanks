"""
Asset portfolio management with liquidation logic.
"""
import numpy as np
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from src.models.models import Asset, AssetType


class AssetPortfolioManager:
    """Manages asset portfolio with valuation and liquidation."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
    
    def update_asset_values(self, assets: List[Asset], day: int) -> List[Asset]:
        """
        Update asset values based on volatility.
        
        Args:
            assets: List of assets to update
            day: Current simulation day
            
        Returns:
            Updated list of assets
        """
        day_rng = np.random.RandomState(self.seed + day)
        updated_assets = []
        
        for asset in assets:
            # Create a copy to avoid mutation
            updated_asset = asset.copy(deep=True)
            
            # Apply volatility based on asset type
            if asset.type == AssetType.VOLATILE:
                # High volatility assets
                change = day_rng.normal(0, asset.volatility)
                new_value = float(asset.value) * (1 + change)
                updated_asset.value = Decimal(str(max(0, new_value)))
            
            elif asset.type == AssetType.YIELD:
                # Yield-generating assets (steady growth)
                daily_yield = asset.volatility / 365  # Annual yield to daily
                new_value = float(asset.value) * (1 + daily_yield)
                updated_asset.value = Decimal(str(new_value))
            
            elif asset.type == AssetType.LIQUID:
                # Liquid assets maintain value with minimal volatility
                change = day_rng.normal(0, 0.001)  # 0.1% volatility
                new_value = float(asset.value) * (1 + change)
                updated_asset.value = Decimal(str(max(0, new_value)))
            
            # ILLIQUID assets maintain value (no daily changes)
            
            updated_assets.append(updated_asset)
        
        return updated_assets
    
    def check_lock_status(self, asset: Asset, current_date: datetime) -> bool:
        """
        Check if asset is locked.
        
        Args:
            asset: Asset to check
            current_date: Current simulation date
            
        Returns:
            True if asset is locked
        """
        if not asset.is_locked:
            return False
        
        if asset.lock_until and current_date >= asset.lock_until:
            return False
        
        return True
    
    def liquidate_assets(self, assets: List[Asset], required_amount: Decimal, 
                        current_date: datetime) -> tuple[List[Asset], Decimal, Decimal]:
        """
        Liquidate assets to cover deficit.
        
        Liquidation priority:
        1. Liquid unlocked assets
        2. Volatile unlocked assets
        3. Yield unlocked assets
        4. Illiquid unlocked assets (with penalty)
        
        Args:
            assets: Available assets
            required_amount: Amount needed
            current_date: Current date
            
        Returns:
            Tuple of (remaining_assets, amount_raised, total_penalty)
        """
        remaining_assets = []
        amount_raised = Decimal("0")
        total_penalty = Decimal("0")
        
        # Sort assets by liquidation priority
        liquid_assets = []
        volatile_assets = []
        yield_assets = []
        illiquid_assets = []
        locked_assets = []
        
        for asset in assets:
            if self.check_lock_status(asset, current_date):
                locked_assets.append(asset)
            elif asset.type == AssetType.LIQUID:
                liquid_assets.append(asset)
            elif asset.type == AssetType.VOLATILE:
                volatile_assets.append(asset)
            elif asset.type == AssetType.YIELD:
                yield_assets.append(asset)
            elif asset.type == AssetType.ILLIQUID:
                illiquid_assets.append(asset)
        
        # Liquidate in priority order
        priority_list = liquid_assets + volatile_assets + yield_assets + illiquid_assets
        
        for asset in priority_list:
            if amount_raised >= required_amount:
                remaining_assets.append(asset)
                continue
            
            # Calculate sale value with penalty
            sale_value = asset.value * (Decimal("1") - Decimal(str(asset.sale_penalty)))
            penalty = asset.value * Decimal(str(asset.sale_penalty))
            
            amount_raised += sale_value
            total_penalty += penalty
            
            # Asset is fully liquidated (not added to remaining)
        
        # Add locked assets back (cannot be liquidated)
        remaining_assets.extend(locked_assets)
        
        return remaining_assets, amount_raised, total_penalty
    
    def calculate_total_value(self, assets: List[Asset]) -> Decimal:
        """Calculate total value of all assets."""
        return sum((asset.value for asset in assets), Decimal("0"))
    
    def calculate_liquid_value(self, assets: List[Asset], current_date: datetime) -> Decimal:
        """Calculate total value of liquid, unlocked assets."""
        liquid_value = Decimal("0")
        for asset in assets:
            if asset.type == AssetType.LIQUID and not self.check_lock_status(asset, current_date):
                liquid_value += asset.value
        return liquid_value
