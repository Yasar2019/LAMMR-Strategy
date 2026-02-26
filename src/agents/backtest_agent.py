"""Backtest Agent: Vectorized backtesting with costs and slippage."""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.indicators import (
    compute_sharpe, compute_sortino, compute_max_drawdown, 
    compute_win_rate, compute_profit_factor
)
from utils.helpers import get_logger, unix_timestamp_to_date
from utils.config import load_config
from db import get_connection

logger = get_logger(__name__)


class BacktestAgent:
    """Vectorized backtesting engine with slippage and commissions."""
    
    def __init__(self, config_path: str = "config.yaml", db_path: str = "lammr.db"):
        self.config = load_config(config_path)
        self.db_path = db_path
        self.conn = get_connection(db_path)
        self.backtest_dir = Path(self.config['backtest_dir'])
        self.backtest_dir.mkdir(exist_ok=True, parents=True)
    
    def backtest_symbol(self, symbol: str, start_date: str = None, end_date: str = None) -> dict:
        """
        Run backtest on a single symbol using signals.
        
        Args:
            symbol: Stock symbol
            start_date: YYYY-MM-DD (default from config)
            end_date: YYYY-MM-DD (default from config)
        
        Returns:
            {
                'symbol': symbol,
                'metrics': {...},
                'trades': [...],
                'equity_curve': [...]
            }
        """
        start_date = start_date or self.config['backtest_start_date']
        end_date = end_date or self.config['backtest_end_date']
        
        cursor = self.conn.cursor()
        
        # Get OHLCV data for period
        cursor.execute("""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv 
            WHERE symbol = ?
            AND DATE(datetime(timestamp, 'unixepoch')) >= ?
            AND DATE(datetime(timestamp, 'unixepoch')) <= ?
            ORDER BY timestamp
        """, (symbol, start_date, end_date))
        
        ohlcv_rows = cursor.fetchall()
        if len(ohlcv_rows) < 2:
            logger.warning(f"Insufficient OHLCV data for {symbol} ({start_date} to {end_date})")
            return None
        
        # Get signals for period
        cursor.execute("""
            SELECT timestamp, signal_type, z_score, composite_score
            FROM signals 
            WHERE symbol = ?
            AND DATE(datetime(timestamp, 'unixepoch')) >= ?
            AND DATE(datetime(timestamp, 'unixepoch')) <= ?
            ORDER BY timestamp
        """, (symbol, start_date, end_date))
        
        signal_rows = cursor.fetchall()
        signals_df = pd.DataFrame(signal_rows, columns=['timestamp', 'signal_type', 'z_score', 'composite_score'])
        
        # Build OHLCV dataframe
        df = pd.DataFrame(ohlcv_rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Merge with signals
        df = df.merge(signals_df, on='timestamp', how='left')
        df['signal_type'] = df['signal_type'].fillna('HOLD')
        
        # Simulate positions
        trades = []
        equity_curve = [self.config['stock_initial_capital']]
        position = None  # (entry_idx, entry_price, quantity)
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            current_price = row['close']
            signal = row['signal_type']
            
            # Process signal
            if signal == 'BUY' and position is None:
                # Enter long
                quantity = int(self.config['stock_initial_capital'] * self.config['position_size_pct'] / current_price)
                position = {
                    'entry_idx': idx,
                    'entry_price': current_price,
                    'entry_time': row['timestamp'],
                    'quantity': quantity,
                    'entry_pnl': equity_curve[-1]
                }
            
            elif signal in ('SELL', 'EXIT') and position is not None:
                # Exit long
                entry_price = position['entry_price']
                qty = position['quantity']
                
                # Apply slippage and commission
                exit_price = current_price * (1 - self.config['slippage_bps'] / 10000)
                commission = qty * entry_price * self.config['commission_bps'] / 10000
                commission += qty * exit_price * self.config['commission_bps'] / 10000
                
                pnl = (exit_price - entry_price) * qty - commission
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                
                trade = {
                    'symbol': symbol,
                    'entry_idx': position['entry_idx'],
                    'exit_idx': idx,
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'quantity': qty,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'duration_bars': idx - position['entry_idx']
                }
                trades.append(trade)
                
                # Update equity
                current_equity = position['entry_pnl'] + pnl
                equity_curve.append(current_equity)
                
                position = None
        
        # Calculate metrics
        equity_series = pd.Series(equity_curve)
        daily_returns = equity_series.pct_change().dropna()
        
        if len(trades) == 0:
            logger.warning(f"No completed trades for {symbol}")
            return None
        
        pnl_list = [t['pnl'] for t in trades]
        
        metrics = {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'total_return_pct': (equity_curve[-1] - self.config['stock_initial_capital']) / self.config['stock_initial_capital'] * 100,
            'sharpe_ratio': compute_sharpe(daily_returns) if len(daily_returns) > 0 else 0,
            'sortino_ratio': compute_sortino(daily_returns) if len(daily_returns) > 0 else 0,
            'max_drawdown_value': compute_max_drawdown(equity_series)[0],
            'max_drawdown_pct': compute_max_drawdown(equity_series)[1],
            'total_trades': len(trades),
            'winning_trades': sum(1 for t in trades if t['pnl'] > 0),
            'losing_trades': sum(1 for t in trades if t['pnl'] < 0),
            'win_rate': compute_win_rate(pnl_list),
            'profit_factor': compute_profit_factor(pnl_list),
            'avg_win': np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if any(t['pnl'] > 0 for t in trades) else 0,
            'avg_loss': np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if any(t['pnl'] < 0 for t in trades) else 0,
            'best_trade': max(pnl_list) if pnl_list else 0,
            'worst_trade': min(pnl_list) if pnl_list else 0,
        }
        
        return {
            'symbol': symbol,
            'metrics': metrics,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def backtest_all_symbols(self, start_date: str = None, end_date: str = None) -> dict:
        """Backtest all symbols."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        results = {}
        for symbol in symbols:
            result = self.backtest_symbol(symbol, start_date, end_date)
            if result:
                results[symbol] = result
        
        return results
    
    def save_backtest_results(self, backtest_result: dict, run_name: str = None):
        """Save backtest results to database and CSV."""
        if not run_name:
            run_name = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        symbol = backtest_result['symbol']
        metrics = backtest_result['metrics']
        trades = backtest_result['trades']
        
        cursor = self.conn.cursor()
        
        # Insert backtest result
        cursor.execute("""
            INSERT INTO backtest_results 
            (run_name, start_date, end_date, total_return_pct, sharpe_ratio, sortino_ratio,
             max_drawdown_pct, win_rate, total_trades, winning_trades, losing_trades,
             profit_factor, avg_win_pct, avg_loss_pct, best_trade_pct, worst_trade_pct,
             parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_name,
            metrics['start_date'],
            metrics['end_date'],
            metrics['total_return_pct'],
            metrics['sharpe_ratio'],
            metrics['sortino_ratio'],
            metrics['max_drawdown_pct'],
            metrics['win_rate'],
            metrics['total_trades'],
            metrics['winning_trades'],
            metrics['losing_trades'],
            metrics['profit_factor'],
            np.mean([t['pnl_pct'] for t in trades if t['pnl'] > 0]) if any(t['pnl'] > 0 for t in trades) else 0,
            np.mean([t['pnl_pct'] for t in trades if t['pnl'] < 0]) if any(t['pnl'] < 0 for t in trades) else 0,
            metrics['best_trade'],
            metrics['worst_trade'],
            json.dumps({'symbol': symbol})
        ))
        
        self.conn.commit()
        
        logger.info(f"✓ Saved backtest results for {symbol}")
    
    def get_backtest_summary(self, symbol: str = None) -> pd.DataFrame:
        """Get backtest summary (for dashboard)."""
        cursor = self.conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT run_name, start_date, end_date, total_return_pct, sharpe_ratio,
                       max_drawdown_pct, win_rate, total_trades, profit_factor
                FROM backtest_results 
                WHERE parameters LIKE ?
                ORDER BY run_timestamp DESC
            """, (f'%"{symbol}"%',))
        else:
            cursor.execute("""
                SELECT run_name, start_date, end_date, total_return_pct, sharpe_ratio,
                       max_drawdown_pct, win_rate, total_trades, profit_factor
                FROM backtest_results 
                ORDER BY run_timestamp DESC
            """)
        
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=['run_name', 'start_date', 'end_date', 'total_return_pct',
                                         'sharpe_ratio', 'max_drawdown_pct', 'win_rate', 'total_trades',
                                         'profit_factor'])
        
        return df
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    agent = BacktestAgent()
    
    logger.info("=" * 60)
    logger.info("BACKTEST AGENT: Vectorized backtesting")
    logger.info("=" * 60)
    
    # Backtest first symbol as example
    cursor = agent.conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM ohlcv LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        symbol = row[0]
        logger.info(f"\nBacktesting {symbol}...")
        
        result = agent.backtest_symbol(symbol)
        
        if result:
            metrics = result['metrics']
            logger.info(f"\nBacktest Metrics for {symbol}:")
            logger.info(f"  Total Return: {metrics['total_return_pct']:.2f}%")
            logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
            logger.info(f"  Trades: {metrics['total_trades']}")
            logger.info(f"  Win Rate: {metrics['win_rate']:.1%}")
            logger.info(f"  Profit Factor: {metrics['profit_factor']:.2f}")
            
            agent.save_backtest_results(result)
    
    agent.close()
    logger.info("\n✓ Backtest Agent complete")
