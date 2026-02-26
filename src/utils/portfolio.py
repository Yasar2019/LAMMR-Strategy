"""Portfolio sizing and risk management utilities."""

import numpy as np
import pandas as pd


def calculate_fixed_fractional_size(
    account_value: float,
    entry_price: float,
    risk_pct: float = 0.02
) -> int:
    """
    Calculate position size using fixed fractional method.
    
    Allocate risk_pct of account per position.
    
    Args:
        account_value: Current account value ($)
        entry_price: Entry price per share
        risk_pct: Risk percentage per trade (default 2%)
    
    Returns:
        Quantity (shares) to buy
    """
    position_value = account_value * risk_pct
    quantity = position_value / entry_price
    return int(quantity)


def calculate_volatility_adjusted_size(
    account_value: float,
    entry_price: float,
    atr: float,
    target_risk_pct: float = 0.02
) -> int:
    """
    Calculate position size using volatility-adjusted method.
    
    Larger ATR (more volatile) = smaller position
    Smaller ATR (less volatile) = larger position
    
    Args:
        account_value: Current account value ($)
        entry_price: Entry price per share
        atr: Average True Range
        target_risk_pct: Target risk percentage (default 2%)
    
    Returns:
        Quantity (shares) to buy
    """
    if atr == 0:
        return calculate_fixed_fractional_size(account_value, entry_price, target_risk_pct)
    
    # Risk per share = ATR * some multiplier (e.g., 2x)
    risk_per_share = atr * 2
    
    # Max loss per trade
    max_loss = account_value * target_risk_pct
    
    # Quantity = max_loss / risk_per_share
    quantity = max_loss / risk_per_share / entry_price
    
    return int(quantity)


def apply_position_limits(
    quantities: dict,
    account_value: float,
    max_position_pct: float = 5.0,
    max_positions: int = 10
) -> dict:
    """
    Apply portfolio-level position limits.
    
    Args:
        quantities: Dict of {symbol: quantity}
        account_value: Current account value
        max_position_pct: Max % of account per position
        max_positions: Max number of concurrent positions
    
    Returns:
        Capped quantities dict
    """
    limited = {}
    sorted_symbols = sorted(quantities.keys(), key=lambda s: quantities[s], reverse=True)
    
    for i, symbol in enumerate(sorted_symbols):
        if i >= max_positions:
            # Exceeds max position count
            limited[symbol] = 0
        else:
            # Cap to max_position_pct
            max_value = account_value * (max_position_pct / 100.0)
            # Assuming we need price; for now just apply % cap
            limited[symbol] = int(quantities[symbol] * (max_position_pct / 100.0))
    
    return limited


def apply_drawdown_stop(
    current_equity: float,
    peak_equity: float,
    max_dd_pct: float = 15.0
) -> bool:
    """
    Check if max drawdown limit is exceeded.
    
    Args:
        current_equity: Current portfolio value
        peak_equity: Peak portfolio value
        max_dd_pct: Max drawdown threshold (%)
    
    Returns:
        True if should stop trading (DD exceeded)
    """
    if peak_equity == 0:
        return False
    
    dd_pct = (current_equity - peak_equity) / peak_equity * 100
    return dd_pct < -max_dd_pct


def estimate_beta(
    symbol_returns: pd.Series,
    market_returns: pd.Series
) -> float:
    """
    Estimate beta of symbol vs market (SPY).
    
    Beta = Cov(symbol, market) / Var(market)
    
    Args:
        symbol_returns: Daily returns of symbol
        market_returns: Daily returns of market index
    
    Returns:
        Beta coefficient
    """
    # Align series
    aligned = pd.concat([symbol_returns, market_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 1.0
    
    covariance = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    market_variance = aligned.iloc[:, 1].var()
    
    if market_variance == 0:
        return 1.0
    
    beta = covariance / market_variance
    return beta


def calculate_hedge_size(
    main_position_qty: int,
    main_price: float,
    beta: float,
    spy_price: float
) -> int:
    """
    Calculate SPY hedge quantity to neutralize beta exposure.
    
    Hedge = (Position Value * Beta) / SPY Price
    
    Args:
        main_position_qty: Quantity of main position
        main_price: Price of main position
        beta: Beta coefficient
        spy_price: Current SPY price
    
    Returns:
        SPY quantity to short (negative for hedge)
    """
    position_value = main_position_qty * main_price
    hedge_value = position_value * beta
    hedge_qty = hedge_value / spy_price
    
    return -int(hedge_qty)  # Short SPY to hedge


if __name__ == "__main__":
    # Example
    account = 100000
    entry_price = 150.0
    atr = 2.5
    
    size_fixed = calculate_fixed_fractional_size(account, entry_price, 0.02)
    size_vol = calculate_volatility_adjusted_size(account, entry_price, atr, 0.02)
    
    print(f"Fixed fractional size: {size_fixed} shares")
    print(f"Volatility-adjusted size: {size_vol} shares")
