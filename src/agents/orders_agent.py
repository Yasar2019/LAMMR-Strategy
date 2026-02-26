"""Orders Agent: Generate orders.csv for manual execution (paper trading only)."""

import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import get_logger, unix_timestamp_to_date
from utils.config import load_config
from db import get_connection

logger = get_logger(__name__)


class OrdersAgent:
    """Generates executable orders from signals (paper trading only, no broker integration)."""
    
    def __init__(self, config_path: str = "config.yaml", db_path: str = "lammr.db"):
        self.config = load_config(config_path)
        self.db_path = db_path
        self.conn = get_connection(db_path)
        self.orders_dir = Path(self.config['orders_dir'])
        self.orders_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_orders_from_latest_signals(self) -> str:
        """
        Generate orders.csv from latest BUY/SELL signals.
        
        Returns: filepath of generated orders CSV
        """
        cursor = self.conn.cursor()
        
        # Get latest signals per symbol (most recent timestamp per symbol)
        cursor.execute("""
            SELECT symbol, timestamp, signal_type, z_score, composite_score
            FROM signals 
            WHERE (symbol, timestamp) IN (
                SELECT symbol, MAX(timestamp) FROM signals 
                WHERE signal_type IN ('BUY', 'SELL')
                GROUP BY symbol
            )
            ORDER BY symbol
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("No signals to convert to orders")
            return None
        
        # Build orders list
        orders = []
        for symbol, timestamp, signal_type, zscore, composite in rows:
            # Get current price
            cursor.execute("""
                SELECT close FROM ohlcv 
                WHERE symbol = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (symbol,))
            
            price_row = cursor.fetchone()
            current_price = price_row[0] if price_row else None
            
            if current_price is None:
                logger.warning(f"No price data for {symbol}")
                continue
            
            # Determine side and quantity
            if signal_type == 'BUY':
                side = 'BUY'
            elif signal_type == 'SELL':
                side = 'SELL'
            else:
                continue
            
            # Simple sizing: 100 shares (or adjust based on signal strength)
            quantity = max(1, int(100 * composite))
            limit_price = current_price * 1.01 if side == 'BUY' else current_price * 0.99
            
            orders.append({
                'timestamp': unix_timestamp_to_date(timestamp),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'limit_price': f"{limit_price:.2f}",
                'z_score': f"{zscore:.2f}",
                'confidence': f"{composite:.2f}"
            })
        
        # Write to CSV
        filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.orders_dir / filename
        
        if orders:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp', 'symbol', 'side', 'quantity', 'limit_price', 'z_score', 'confidence'
                ])
                writer.writeheader()
                writer.writerows(orders)
            
            logger.info(f"✓ Generated {len(orders)} orders to {filepath}")
        else:
            logger.warning("No valid orders generated")
        
        return str(filepath)
    
    def get_today_orders(self) -> pd.DataFrame:
        """Get today's generated orders (for dashboard)."""
        cursor = self.conn.cursor()
        
        # Get today's signals
        cursor.execute("""
            SELECT symbol, timestamp, signal_type, z_score, composite_score
            FROM signals 
            WHERE DATE(datetime(timestamp, 'unixepoch')) = DATE('now')
            AND signal_type IN ('BUY', 'SELL')
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=['symbol', 'timestamp', 'signal_type', 'z_score', 'composite_score'])
        
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.date
        
        return df
    
    def record_manual_execution(self, symbol: str, side: str, quantity: int, execution_price: float, timestamp: int = None):
        """
        Record a manually-executed order in the positions table (paper trading).
        
        Args:
            symbol: Stock symbol
            side: 'BUY' or 'SELL'
            quantity: Number of shares
            execution_price: Execution price per share
            timestamp: Unix timestamp (defaults to now)
        """
        import time
        if timestamp is None:
            timestamp = int(time.time())
        
        cursor = self.conn.cursor()
        
        if side.upper() == 'BUY':
            # Open new position
            position_value = quantity * execution_price
            cursor.execute("""
                INSERT INTO positions 
                (symbol, entry_timestamp, entry_price, quantity, position_value, sizing_method, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, timestamp, execution_price, quantity, position_value, 'manual', 'open'))
            
            logger.info(f"✓ Recorded BUY: {quantity} {symbol} @ ${execution_price:.2f}")
        
        elif side.upper() == 'SELL':
            # Close matching position (FIFO)
            cursor.execute("""
                SELECT id, entry_price, quantity 
                FROM positions 
                WHERE symbol = ? AND status = 'open'
                ORDER BY entry_timestamp
                LIMIT 1
            """, (symbol,))
            
            pos = cursor.fetchone()
            if pos:
                pos_id, entry_price, pos_qty = pos
                
                if quantity <= pos_qty:
                    pnl = (execution_price - entry_price) * quantity
                    pnl_pct = (execution_price - entry_price) / entry_price * 100
                    
                    cursor.execute("""
                        UPDATE positions 
                        SET exit_timestamp = ?, exit_price = ?, pnl = ?, pnl_pct = ?, status = 'closed'
                        WHERE id = ?
                    """, (timestamp, execution_price, pnl, pnl_pct, pos_id))
                    
                    logger.info(f"✓ Recorded SELL: {quantity} {symbol} @ ${execution_price:.2f} (PnL: ${pnl:.2f})")
        
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    agent = OrdersAgent()
    
    logger.info("=" * 60)
    logger.info("ORDERS AGENT: Generate executable orders (paper trading)")
    logger.info("=" * 60)
    
    filepath = agent.generate_orders_from_latest_signals()
    
    logger.info("\nOrders generated:")
    if filepath:
        df = pd.read_csv(filepath)
        print(df.to_string(index=False))
    
    agent.close()
    logger.info("\n✓ Orders Agent complete")
