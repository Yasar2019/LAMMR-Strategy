"""CSV data loading and validation utilities."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


def load_ohlcv_csv(file_path: str) -> pd.DataFrame:
    """
    Load OHLCV CSV file.
    
    Expected columns: timestamp, open, high, low, close, volume
    Timestamp can be YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
    """
    df = pd.read_csv(file_path)
    
    # Validate columns
    required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {file_path}: {missing}")
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['unix_timestamp'] = df['timestamp'].astype(np.int64) // 10**9
    
    # Convert to numeric
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop nulls
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df[['timestamp', 'unix_timestamp', 'open', 'high', 'low', 'close', 'volume']]


def load_vix_csv(file_path: str) -> pd.DataFrame:
    """
    Load VIX CSV file.
    
    Expected columns: timestamp, close
    """
    df = pd.read_csv(file_path)
    
    # Validate columns
    required = ['timestamp', 'close']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {file_path}: {missing}")
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['unix_timestamp'] = df['timestamp'].astype(np.int64) // 10**9
    
    # Convert to numeric
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    # Drop nulls
    df = df.dropna(subset=['close'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df[['timestamp', 'unix_timestamp', 'close']]


def list_csv_files(data_dir: str, pattern: str = "*.csv") -> list:
    """List all CSV files in data directory."""
    return sorted(Path(data_dir).glob(pattern))


def extract_symbol_from_filename(filename: str) -> str:
    """Extract symbol from filename (e.g., 'AAPL.csv' -> 'AAPL')."""
    return Path(filename).stem.upper()


def validate_ohlcv_data(df: pd.DataFrame) -> Tuple[bool, list]:
    """
    Validate OHLCV data for anomalies.
    
    Returns: (is_valid, list_of_issues)
    """
    issues = []
    
    # Check high >= low
    if (df['high'] < df['low']).any():
        issues.append("High < Low in some rows")
    
    # Check close is between high and low
    invalid_close = (df['close'] > df['high']) | (df['close'] < df['low'])
    if invalid_close.any():
        issues.append(f"Close outside [low, high] range in {invalid_close.sum()} rows")
    
    # Check volume >= 0
    if (df['volume'] < 0).any():
        issues.append("Negative volume detected")
    
    # Check OHLC >= 0
    for col in ['open', 'high', 'low', 'close']:
        if (df[col] <= 0).any():
            issues.append(f"Non-positive values in {col}")
    
    return len(issues) == 0, issues


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        df = load_ohlcv_csv(csv_file)
        print(df.head())
        print(f"\nShape: {df.shape}")
        valid, issues = validate_ohlcv_data(df)
        if valid:
            print("✓ Data validation passed")
        else:
            print("✗ Data validation issues:")
            for issue in issues:
                print(f"  - {issue}")
