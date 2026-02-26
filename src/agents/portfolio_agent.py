"""Portfolio Agent: Sizing, caps, beta estimation, hedge sizing (paper only)."""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.portfolio import (
    calculate_fixed_fractional_size,
    calculate_volatility_adjusted_size,
    apply_position_limits,
    apply_drawdown_stop,
    estimate_beta,
    calculate_hedge_size
)
from utils.indicators import compute_atr
from utils.helpers import get_logger
from utils.config import load_config
from db import get_connection

logger = get_logger(__name__)


class PortfolioAgent:
    """Manages portfolio sizing, position limits, beta estimation, and hedging (paper only)."""
    
    def __init__(self, config_path: str = "config.yaml", db_path: str = "lammr.db"):
        self.config = load_config(config_path)
        self.db_path = db_path
        self.conn = get_connection(db_path)
        self.account_value = self.config.get('stock_initial_capital', 100000)
    
    def size_position(self, symbol: str, entry_price: float, use_volatility_adjusted: bool = False) -> int:
        """
        Calculate position size for a symbol.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price per share
            use_volatility_adjusted: Use vol-adjusted sizing if True
        
        Returns:
            Quantity (shares)
        """
        if use_volatility_adjusted:
            # Get ATR for volatility-adjusted sizing
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT high, low, close 
                FROM ohlcv 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 14
            """, (symbol,))
            
            rows = cursor.fetchall()
            if len(rows) < 14:
                # Fall back to fixed fractional
                return calculate_fixed_fractional_size(self.account_value, entry_price, self.config['position_size_pct'])
            
            df = pd.DataFrame(rows[::-1], columns=['high', 'low', 'close'])
            atr = compute_atr(df['high'], df['low'], df['close'], 14).iloc[-1]
            
            return calculate_volatility_adjusted_size(
                self.account_value,
                entry_price,
                atr,
                self.config['position_size_pct']
            )
        else:
            # Fixed fractional
            return calculate_fixed_fractional_size(
                self.account_value,
                entry_price,
                self.config['position_size_pct']
            )
    
    def estimate_hedge_for_position(self, symbol: str, quantity: int, entry_price: float) -> dict:
        """
        Estimate beta and SPY hedge for a position.
        
        Returns: {
            'beta': beta_coefficient,
            'spy_hedge_qty': quantity_to_short_spy,
            'hedge_value': notional_value_of_hedge
        }
        """
        # Try to get historical returns
        cursor = self.conn.cursor()
        
        # Get symbol returns
        cursor.execute("""
            SELECT close 
            FROM ohlcv 
            WHERE symbol = ? 
            ORDER BY timestamp
            LIMIT 252
        """, (symbol,))
        
        symbol_closes = [row[0] for row in cursor.fetchall()]
        
        # Get SPY returns
        cursor.execute("""
            SELECT close 
            FROM ohlcv 
            WHERE symbol = 'SPY' 
            ORDER BY timestamp
            LIMIT 252
        """)
        
        spy_closes = [row[0] for row in cursor.fetchall()]
        
        if len(symbol_closes) < 20 or len(spy_closes) < 20:
            logger.warning(f"Insufficient data for beta estimation of {symbol}")
            return {
                'beta': 1.0,
                'spy_hedge_qty': 0,
                'hedge_value': 0
            }
        
        # Calculate returns
        symbol_returns = pd.Series(symbol_closes).pct_change().dropna()
        spy_returns = pd.Series(spy_closes).pct_change().dropna()
        
        # Align series
        aligned = pd.concat([symbol_returns, spy_returns], axis=1).dropna()
        
        if len(aligned) < 10:
            return {
                'beta': 1.0,
                'spy_hedge_qty': 0,
                'hedge_value': 0
            }
        
        # Estimate beta
        beta = estimate_beta(aligned.iloc[:, 0], aligned.iloc[:, 1])
        
        # Get current SPY price (or use last available)
        cursor.execute("SELECT close FROM ohlcv WHERE symbol = 'SPY' ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        spy_price = row[0] if row else entry_price  # Fallback to stock price
        
        # Calculate hedge
        hedge_qty = calculate_hedge_size(quantity, entry_price, beta, spy_price)
        hedge_value = abs(hedge_qty * spy_price)
        
        return {
            'beta': beta,
            'spy_hedge_qty': hedge_qty,
            'hedge_value': hedge_value
        }
    
    def calculate_portfolio_metrics(self) -> dict:
        """Calculate current portfolio metrics."""
        cursor = self.conn.cursor()
        
        # Get open positions
        cursor.execute("""
            SELECT symbol, quantity, entry_price, entry_timestamp, stop_loss_price
            FROM positions 
            WHERE status = 'open'
        """)
        
        open_positions = cursor.fetchall()
        
        # Calculate current portfolio value
        current_value = self.account_value
        position_count = len(open_positions)
        total_position_value = 0
        
        for symbol, qty, entry_price, _, stop_loss in open_positions:
            # Get current price
            cursor.execute("""
                SELECT close FROM ohlcv 
                WHERE symbol = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            current_price = row[0] if row else entry_price
            
            position_value = qty * current_price
            total_position_value += position_value
        
        current_cash = self.account_value - total_position_value
        
        # Calculate drawdown
        if current_value < self.account_value:
            dd_pct = (self.account_value - current_value) / self.account_value * 100
        else:
            dd_pct = 0
        
        return {
            'account_value': self.account_value,
            'current_value': current_value,
            'cash': current_cash,
            'positions_count': position_count,
            'position_value': total_position_value,
            'max_drawdown_pct': self.config['max_drawdown_pct'],
            'current_drawdown_pct': dd_pct,
            'should_stop_trading': apply_drawdown_stop(current_value, self.account_value, self.config['max_drawdown_pct'])
        }
    
    def check_position_limits(self, new_positions: dict) -> dict:
        """Check and apply position limits."""
        return apply_position_limits(
            new_positions,
            self.account_value,
            self.config['max_position_size_pct'],
            self.config['max_positions']
        )
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    agent = PortfolioAgent()
    
    logger.info("=" * 60)
    logger.info("PORTFOLIO AGENT: Position sizing and risk management")
    logger.info("=" * 60)
    
    # Example sizing
    entry_price = 150.0
    qty = agent.size_position('AAPL', entry_price)
    logger.info(f"\nExample: Entry price ${entry_price} -> {qty} shares")
    
    # Example hedge estimation
    hedge_info = agent.estimate_hedge_for_position('AAPL', qty, entry_price)
    logger.info(f"Beta estimate: {hedge_info['beta']:.2f}")
    logger.info(f"SPY hedge qty (short): {hedge_info['spy_hedge_qty']}")
    logger.info(f"Hedge value: ${hedge_info['hedge_value']:,.2f}")
    
    # Portfolio metrics
    metrics = agent.calculate_portfolio_metrics()
    logger.info(f"\nPortfolio Metrics:")
    logger.info(f"  Account Value: ${metrics['account_value']:,.2f}")
    logger.info(f"  Positions: {metrics['positions_count']}")
    logger.info(f"  Drawdown: {metrics['current_drawdown_pct']:.2f}%")
    logger.info(f"  Stop Trading: {metrics['should_stop_trading']}")
    
    agent.close()
    logger.info("\n✓ Portfolio Agent complete")
