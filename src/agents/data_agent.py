"""Data Agent: Load OHLCV and VIX data from CSV files into SQLite."""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.csv_loader import load_ohlcv_csv, load_vix_csv, list_csv_files, extract_symbol_from_filename, validate_ohlcv_data
from utils.helpers import get_logger
from db import get_connection

logger = get_logger(__name__)


class DataAgent:
    """Loads OHLCV and VIX data from CSV files into SQLite database."""
    
    def __init__(self, data_dir: str = "data/raw", db_path: str = "lammr.db"):
        self.data_dir = data_dir
        self.db_path = db_path
        self.conn = get_connection(db_path)
    
    def load_ohlcv_from_csv(self, symbol: str, csv_file: str) -> int:
        """
        Load OHLCV data from CSV file for a symbol.
        
        Returns: number of rows inserted/updated
        """
        try:
            df = load_ohlcv_csv(csv_file)
            
            # Validate data
            is_valid, issues = validate_ohlcv_data(df)
            if not is_valid:
                logger.warning(f"Data validation issues for {symbol}:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            
            # Insert into database
            cursor = self.conn.cursor()
            inserted = 0
            
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO ohlcv 
                        (symbol, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        row['unix_timestamp'],
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume']
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            
            self.conn.commit()
            
            # Update metadata
            self._update_metadata(symbol, 'ohlcv', df, csv_file)
            
            logger.info(f"✓ Loaded {inserted} OHLCV records for {symbol} from {csv_file}")
            return inserted
        
        except Exception as e:
            logger.error(f"Error loading {symbol} from {csv_file}: {e}")
            return 0
    
    def load_vix_from_csv(self, csv_file: str) -> int:
        """
        Load VIX data from CSV file.
        
        Returns: number of rows inserted/updated
        """
        try:
            df = load_vix_csv(csv_file)
            
            # Insert into database
            cursor = self.conn.cursor()
            inserted = 0
            
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO vix 
                        (timestamp, close)
                        VALUES (?, ?)
                    """, (
                        row['unix_timestamp'],
                        row['close']
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            
            self.conn.commit()
            
            # Update metadata
            self._update_metadata('VIX', 'vix', df, csv_file)
            
            logger.info(f"✓ Loaded {inserted} VIX records from {csv_file}")
            return inserted
        
        except Exception as e:
            logger.error(f"Error loading VIX from {csv_file}: {e}")
            return 0
    
    def _update_metadata(self, symbol: str, data_type: str, df: pd.DataFrame, source_file: str):
        """Update data_metadata table."""
        cursor = self.conn.cursor()
        
        first_date = pd.to_datetime(df['timestamp'].min()).strftime('%Y-%m-%d')
        last_date = pd.to_datetime(df['timestamp'].max()).strftime('%Y-%m-%d')
        record_count = len(df)
        
        cursor.execute("""
            INSERT OR REPLACE INTO data_metadata 
            (symbol, data_type, first_date, last_date, record_count, source_file)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (symbol, data_type, first_date, last_date, record_count, source_file))
        
        self.conn.commit()
    
    def discover_and_load_csvs(self) -> dict:
        """
        Auto-discover and load all OHLCV CSVs in data_dir (except vix.csv).
        
        Returns: dict of {symbol: record_count}
        """
        results = {}
        data_path = Path(self.data_dir)
        
        if not data_path.exists():
            logger.error(f"Data directory not found: {self.data_dir}")
            return results
        
        # Load all OHLCV CSVs
        for csv_file in list_csv_files(self.data_dir):
            symbol = extract_symbol_from_filename(csv_file.name)
            
            # Skip VIX file in this loop
            if symbol.upper() == 'VIX':
                continue
            
            records = self.load_ohlcv_from_csv(symbol, str(csv_file))
            results[symbol] = records
        
        # Load VIX separately
        vix_file = data_path / "vix.csv"
        if vix_file.exists():
            self.load_vix_from_csv(str(vix_file))
        
        return results
    
    def get_loaded_symbols(self) -> List[str]:
        """Get list of symbols currently in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol")
        return [row[0] for row in cursor.fetchall()]
    
    def get_data_summary(self):
        """Get summary of loaded data."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT symbol, first_date, last_date, record_count 
            FROM data_metadata 
            WHERE data_type = 'ohlcv'
            ORDER BY symbol
        """)
        return cursor.fetchall()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    import yaml
    
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    
    agent = DataAgent(
        data_dir=config['data_dir'],
        db_path=config['db_path']
    )
    
    logger.info("=" * 60)
    logger.info("DATA AGENT: Loading OHLCV and VIX data")
    logger.info("=" * 60)
    
    results = agent.discover_and_load_csvs()
    
    logger.info("\nLoad Summary:")
    for symbol, count in sorted(results.items()):
        logger.info(f"  {symbol}: {count} records")
    
    logger.info("\nData in Database:")
    for row in agent.get_data_summary():
        logger.info(f"  {row[0]}: {row[1]} to {row[2]} ({row[3]} records)")
    
    agent.close()
    logger.info("\n✓ Data Agent complete")
