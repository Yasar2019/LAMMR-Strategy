"""Signal Agent: Compute Z-score reversal signals with liquidity filters."""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.indicators import (
    compute_zscore, compute_volume_ratio, compute_liquidity_score, compute_composite_score
)
from utils.helpers import get_logger
from utils.config import load_config
from db import get_connection

logger = get_logger(__name__)


class SignalAgent:
    """Computes Z-score based reversal signals with liquidity filters."""
    
    def __init__(self, config_path: str = "config.yaml", db_path: str = "lammr.db"):
        self.config = load_config(config_path)
        self.db_path = db_path
        self.conn = get_connection(db_path)
    
    def generate_signals_for_symbol(self, symbol: str, lookback_days: int = 100) -> int:
        """
        Generate signals for a symbol.
        
        Returns: number of signals inserted
        """
        try:
            # Get OHLCV data
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume 
                FROM ohlcv 
                WHERE symbol = ? 
                ORDER BY timestamp
            """, (symbol,))
            
            rows = cursor.fetchall()
            if len(rows) < self.config['zscore_lookback']:
                logger.warning(f"Insufficient data for {symbol} (< {self.config['zscore_lookback']} bars)")
                return 0
            
            # Build DataFrame
            df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # Compute indicators
            df['zscore'] = compute_zscore(df['close'], self.config['zscore_lookback'])
            df['volume_ratio'] = compute_volume_ratio(df['volume'], self.config['volume_filter_lookback'])
            df['liquidity_score'] = compute_liquidity_score(
                df['volume'],
                df['volume_ratio'],
                self.config['min_volume_ma'],
                self.config['volume_filter_lookback']
            )
            df['composite_score'] = compute_composite_score(
                df['zscore'],
                df['liquidity_score'],
                self.config['zscore_weight'],
                self.config['liquidity_weight']
            )
            
            # Generate signals
            signals_inserted = 0
            
            for idx in range(self.config['zscore_lookback'], len(df)):
                row = df.iloc[idx]
                timestamp = int(row['timestamp'])
                zscore = float(row['zscore'])
                composite = float(row['composite_score'])
                
                # Skip if no signal confidence
                if composite < self.config['min_confidence']:
                    continue
                
                signal_type = None
                reason = None
                
                # Buy signal: Z-score oversold + good liquidity
                if zscore < self.config['zscore_buy_threshold']:
                    signal_type = 'BUY'
                    reason = f"Oversold (Z={zscore:.2f}), Liquidity={composite:.2f}"
                
                # Sell signal: Z-score overbought + good liquidity
                elif zscore > self.config['zscore_sell_threshold']:
                    signal_type = 'SELL'
                    reason = f"Overbought (Z={zscore:.2f}), Liquidity={composite:.2f}"
                
                # Exit signal: Z-score at mean
                elif abs(zscore) < self.config['zscore_exit_threshold']:
                    signal_type = 'EXIT'
                    reason = f"Mean reversion (Z={zscore:.2f})"
                
                # Insert signal
                if signal_type:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO signals 
                            (symbol, timestamp, signal_type, z_score, volume_ratio, 
                             liquidity_score, composite_score, confidence, reason)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            symbol,
                            timestamp,
                            signal_type,
                            zscore,
                            float(row['volume_ratio']),
                            float(row['liquidity_score']),
                            composite,
                            composite,
                            reason
                        ))
                        signals_inserted += 1
                    except sqlite3.IntegrityError:
                        pass
            
            self.conn.commit()
            logger.info(f"✓ Generated {signals_inserted} signals for {symbol}")
            return signals_inserted
        
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return 0
    
    def generate_signals_for_all_symbols(self) -> dict:
        """Generate signals for all symbols in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        results = {}
        for symbol in symbols:
            count = self.generate_signals_for_symbol(symbol)
            results[symbol] = count
        
        return results
    
    def get_recent_signals(self, symbol: str = None, limit: int = 20) -> pd.DataFrame:
        """Get recent signals (for dashboard)."""
        cursor = self.conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT symbol, timestamp, signal_type, z_score, liquidity_score, 
                       composite_score, reason
                FROM signals 
                WHERE symbol = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT symbol, timestamp, signal_type, z_score, liquidity_score, 
                       composite_score, reason
                FROM signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=['symbol', 'timestamp', 'signal_type', 
                                          'z_score', 'liquidity_score', 'composite_score', 'reason'])
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        return df
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    agent = SignalAgent()
    
    logger.info("=" * 60)
    logger.info("SIGNAL AGENT: Computing Z-score reversal signals")
    logger.info("=" * 60)
    
    results = agent.generate_signals_for_all_symbols()
    
    logger.info("\nSignal Summary:")
    for symbol, count in sorted(results.items()):
        logger.info(f"  {symbol}: {count} signals")
    
    logger.info("\nRecent Signals (all symbols):")
    recent = agent.get_recent_signals(limit=10)
    print(recent.to_string())
    
    agent.close()
    logger.info("\n✓ Signal Agent complete")
