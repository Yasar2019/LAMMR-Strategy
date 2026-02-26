"""Utility functions for indicators and signal computation."""

import numpy as np
import pandas as pd


def compute_zscore(prices: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Compute Z-score of prices over lookback window.
    
    Z = (price - rolling_mean) / rolling_std
    """
    rolling_mean = prices.rolling(window=lookback).mean()
    rolling_std = prices.rolling(window=lookback).std()
    zscore = (prices - rolling_mean) / rolling_std
    return zscore


def compute_volume_ratio(volumes: pd.Series, lookback: int = 20) -> pd.Series:
    """Compute current volume as ratio to rolling average volume."""
    volume_ma = volumes.rolling(window=lookback).mean()
    ratio = volumes / volume_ma
    return ratio.fillna(1.0)


def compute_liquidity_score(
    volumes: pd.Series, 
    volume_ratios: pd.Series,
    min_volume_ma: float = 100000,
    lookback: int = 20
) -> pd.Series:
    """
    Compute liquidity score (0.0-1.0).
    
    Higher volume and volume ratio = higher liquidity.
    """
    volume_ma = volumes.rolling(window=lookback).mean()
    
    # Normalize volume to 0-1 (using percentile)
    vol_pct = volume_ma / volume_ma.max() if volume_ma.max() > 0 else pd.Series(0, index=volume_ma.index)
    vol_pct = vol_pct.clip(0, 1)
    
    # Normalize volume ratio to 0-1 (clip at 2x)
    vol_ratio_norm = (volume_ratios / 2.0).clip(0, 1)
    
    # Composite: 60% volume, 40% ratio
    liquidity = (0.6 * vol_pct + 0.4 * vol_ratio_norm).fillna(0)
    
    # Apply minimum volume filter
    liquidity = liquidity.where(volume_ma >= min_volume_ma, 0)
    
    return liquidity


def compute_composite_score(
    zscore: pd.Series,
    liquidity_score: pd.Series,
    zscore_weight: float = 0.7,
    liquidity_weight: float = 0.3
) -> pd.Series:
    """
    Compute composite signal score (0.0-1.0).
    
    Combines Z-score extremeness and liquidity.
    """
    # Normalize Z-score to 0-1 (max extremeness at ±3)
    zscore_abs_norm = (np.abs(zscore) / 3.0).clip(0, 1)
    
    # Composite
    composite = (zscore_weight * zscore_abs_norm + liquidity_weight * liquidity_score).fillna(0)
    
    return composite.clip(0, 1)


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 14) -> pd.Series:
    """Compute Average True Range."""
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=lookback).mean()
    return atr


def compute_returns(close: pd.Series) -> pd.Series:
    """Compute daily log returns."""
    return np.log(close / close.shift(1))


def compute_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Compute Sharpe ratio (assuming 0% risk-free rate)."""
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    excess_return = returns.mean()
    volatility = returns.std()
    sharpe = excess_return / volatility * np.sqrt(periods_per_year)
    return sharpe


def compute_sortino(returns: pd.Series, target_return: float = 0.0, periods_per_year: int = 252) -> float:
    """Compute Sortino ratio (downside deviation only)."""
    excess_return = returns.mean() - target_return
    downside = returns[returns < target_return]
    downside_dev = downside.std() if len(downside) > 0 else returns.std()
    if downside_dev == 0:
        return 0.0
    sortino = excess_return / downside_dev * np.sqrt(periods_per_year)
    return sortino


def compute_max_drawdown(equity_curve: pd.Series) -> tuple:
    """
    Compute max drawdown and its percentage.
    
    Returns: (max_dd_value, max_dd_pct)
    """
    running_max = equity_curve.expanding().max()
    drawdown = equity_curve - running_max
    max_dd_value = drawdown.min()
    max_dd_pct = (max_dd_value / running_max.max() * 100) if running_max.max() != 0 else 0
    return max_dd_value, max_dd_pct


def compute_win_rate(pnl_list: list) -> float:
    """Compute win rate from PnL list."""
    if len(pnl_list) == 0:
        return 0.0
    wins = sum(1 for p in pnl_list if p > 0)
    return wins / len(pnl_list)


def compute_profit_factor(pnl_list: list) -> float:
    """Compute profit factor (total wins / total losses)."""
    gross_profit = sum(p for p in pnl_list if p > 0)
    gross_loss = abs(sum(p for p in pnl_list if p < 0))
    if gross_loss == 0:
        return 0.0 if gross_profit == 0 else np.inf
    return gross_profit / gross_loss
