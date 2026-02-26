"""Monitor Agent: Rolling Sharpe, IC, decile returns, alerts."""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.indicators import compute_sharpe
from utils.helpers import get_logger
from utils.config import load_config
from db import get_connection

logger = get_logger(__name__)


class MonitorAgent:
    """Monitoring and alert system for strategy performance."""
    
    def __init__(self, config_path: str = "config.yaml", db_path: str = "lammr.db"):
        self.config = load_config(config_path)
        self.db_path = db_path
        self.conn = get_connection(db_path)
    
    def compute_rolling_metrics(self, window: int = 20) -> dict:
        """Compute rolling metrics (Sharpe, drawdown, etc.) for monitoring."""
        cursor = self.conn.cursor()
        
        # Get positions and calculate daily PnL
        cursor.execute("""
            SELECT entry_timestamp, exit_timestamp, pnl 
            FROM positions 
            WHERE status = 'closed'
            ORDER BY exit_timestamp
        """)
        
        closed_positions = cursor.fetchall()
        
        if len(closed_positions) < window:
            logger.warning(f"Insufficient closed positions for rolling metrics (need {window}, have {len(closed_positions)})")
            return {}
        
        # Group by day and sum PnL
        daily_pnl = {}
        for entry_ts, exit_ts, pnl in closed_positions:
            exit_date = pd.to_datetime(exit_ts, unit='s').date()
            daily_pnl[exit_date] = daily_pnl.get(exit_date, 0) + pnl
        
        dates = sorted(daily_pnl.keys())
        pnl_series = pd.Series([daily_pnl[d] for d in dates], index=dates)
        
        # Compute rolling returns
        returns = pnl_series / self.config['stock_initial_capital']
        
        # Rolling Sharpe
        rolling_sharpe = returns.rolling(window=window).apply(
            lambda x: compute_sharpe(pd.Series(x)) if len(x) > 1 else 0
        )
        
        # Rolling drawdown
        cumulative_pnl = pnl_series.cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        rolling_dd = drawdown.rolling(window=window).min()
        rolling_dd_pct = (rolling_dd / running_max).rolling(window=window).min() * 100
        
        return {
            'rolling_sharpe': rolling_sharpe.to_dict(),
            'rolling_drawdown_pct': rolling_dd_pct.to_dict(),
            'daily_pnl': daily_pnl,
            'latest_sharpe': rolling_sharpe.iloc[-1] if len(rolling_sharpe) > 0 else 0,
            'latest_dd_pct': rolling_dd_pct.iloc[-1] if len(rolling_dd_pct) > 0 else 0
        }
    
    def compute_information_coefficient(self, symbol: str) -> float:
        """
        Compute Information Coefficient (IC) between signal timing and returns.
        
        High IC = signals predict returns well
        """
        cursor = self.conn.cursor()
        
        # Get signals and subsequent returns
        cursor.execute("""
            SELECT timestamp, z_score, composite_score
            FROM signals 
            WHERE symbol = ? AND signal_type = 'BUY'
            ORDER BY timestamp
        """, (symbol,))
        
        signals = cursor.fetchall()
        if len(signals) < 2:
            return 0.0
        
        # Get OHLCV data
        cursor.execute("""
            SELECT timestamp, close 
            FROM ohlcv 
            WHERE symbol = ?
            ORDER BY timestamp
        """, (symbol,))
        
        ohlcv = cursor.fetchall()
        ohlcv_df = pd.DataFrame(ohlcv, columns=['timestamp', 'close'])
        
        # For each signal, get next 5-day return
        signal_scores = []
        returns_list = []
        
        for sig_ts, zscore, composite in signals:
            # Find price at signal
            sig_price = ohlcv_df[ohlcv_df['timestamp'] == sig_ts]['close'].values
            if len(sig_price) == 0:
                continue
            
            # Find price 5 days later
            future_prices = ohlcv_df[ohlcv_df['timestamp'] > sig_ts].head(5)
            if len(future_prices) == 0:
                continue
            
            future_price = future_prices.iloc[-1]['close']
            ret = (future_price - sig_price[0]) / sig_price[0]
            
            signal_scores.append(composite)
            returns_list.append(ret)
        
        if len(signal_scores) < 2:
            return 0.0
        
        # Correlation between signal score and subsequent return
        ic = np.corrcoef(signal_scores, returns_list)[0, 1]
        return ic if not np.isnan(ic) else 0.0
    
    def compute_decile_returns(self, symbol: str, deciles: int = 5) -> dict:
        """
        Compute returns by signal strength deciles.
        
        High decile = strong signals, check if they have better returns
        """
        cursor = self.conn.cursor()
        
        # Get signals with returns
        cursor.execute("""
            SELECT s.timestamp, s.composite_score, o.close
            FROM signals s
            JOIN ohlcv o ON s.symbol = o.symbol AND s.timestamp = o.timestamp
            WHERE s.symbol = ? AND s.signal_type = 'BUY'
            ORDER BY s.timestamp
        """, (symbol,))
        
        data = cursor.fetchall()
        if len(data) < deciles:
            return {}
        
        df = pd.DataFrame(data, columns=['timestamp', 'composite_score', 'close'])
        
        # Create deciles by signal strength
        df['decile'] = pd.qcut(df['composite_score'], q=deciles, labels=False, duplicates='drop')
        
        # Get next-day returns
        future_closes = []
        for idx in range(len(df) - 1):
            next_close = df.iloc[idx + 1]['close']
            future_closes.append(next_close)
        
        future_closes.append(df.iloc[-1]['close'])  # Pad last
        df['future_close'] = future_closes
        df['return'] = (df['future_close'] - df['close']) / df['close']
        
        # Average return by decile
        decile_returns = df.groupby('decile')['return'].mean().to_dict()
        
        return decile_returns
    
    def check_alerts(self) -> list:
        """Check for alert conditions."""
        alerts = []
        
        # Alert 1: Rolling Sharpe below threshold
        rolling = self.compute_rolling_metrics(20)
        if rolling.get('latest_sharpe', 0) < self.config['alert_threshold_sharpe']:
            alerts.append({
                'type': 'LOW_SHARPE',
                'message': f"Rolling Sharpe {rolling.get('latest_sharpe', 0):.2f} < {self.config['alert_threshold_sharpe']}",
                'severity': 'WARNING'
            })
        
        # Alert 2: Drawdown exceeded
        if rolling.get('latest_dd_pct', 0) < -self.config['alert_threshold_dd']:
            alerts.append({
                'type': 'HIGH_DRAWDOWN',
                'message': f"Drawdown {rolling.get('latest_dd_pct', 0):.2f}% > {self.config['alert_threshold_dd']}%",
                'severity': 'CRITICAL'
            })
        
        # Alert 3: Consecutive losses
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pnl FROM positions 
            WHERE status = 'closed'
            ORDER BY exit_timestamp DESC 
            LIMIT ?
        """, (self.config['consecutive_loss_limit'],))
        
        recent_trades = [row[0] for row in cursor.fetchall()]
        if len(recent_trades) == self.config['consecutive_loss_limit']:
            if all(p < 0 for p in recent_trades):
                alerts.append({
                    'type': 'CONSECUTIVE_LOSSES',
                    'message': f"{self.config['consecutive_loss_limit']} consecutive losses detected",
                    'severity': 'WARNING'
                })
        
        return alerts
    
    def get_monitoring_dashboard_data(self) -> dict:
        """Get all monitoring data for dashboard."""
        rolling = self.compute_rolling_metrics(20)
        alerts = self.check_alerts()
        
        return {
            'rolling_sharpe': rolling.get('latest_sharpe', 0),
            'rolling_drawdown_pct': rolling.get('latest_dd_pct', 0),
            'alerts': alerts,
            'daily_pnl': rolling.get('daily_pnl', {}),
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    agent = MonitorAgent()
    
    logger.info("=" * 60)
    logger.info("MONITOR AGENT: Performance monitoring and alerts")
    logger.info("=" * 60)
    
    dashboard = agent.get_monitoring_dashboard_data()
    
    logger.info(f"\nRolling Sharpe (20-day): {dashboard['rolling_sharpe']:.2f}")
    logger.info(f"Rolling Drawdown: {dashboard['rolling_drawdown_pct']:.2f}%")
    
    if dashboard['alerts']:
        logger.info("\n⚠ ALERTS:")
        for alert in dashboard['alerts']:
            logger.warning(f"  [{alert['severity']}] {alert['message']}")
    else:
        logger.info("\n✓ No alerts")
    
    agent.close()
    logger.info("\n✓ Monitor Agent complete")
