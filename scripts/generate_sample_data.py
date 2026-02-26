"""Sample Data Generator for LAMMR Strategy.

Creates realistic OHLCV and VIX CSV files for testing.
Run this to generate example data before running the strategy.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys


def generate_ohlcv_csv(symbol: str, num_days: int = 500, output_dir: str = "data/raw"):
    """
    Generate realistic OHLCV data.
    
    Creates price data with realistic mean reversion properties.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Starting values
    np.random.seed(hash(symbol) % 2**32)
    dates = pd.date_range(end=datetime.now(), periods=num_days, freq='D')
    
    # Realistic price movement with mean reversion
    close_price = 150.0  # Starting price
    closes = [close_price]
    
    for _ in range(1, num_days):
        # Mean reversion: price tends to revert to 150
        mean = 150.0
        # Random walk with drift toward mean
        change = np.random.normal(0, 2.0) + (mean - close_price) * 0.01
        close_price = close_price * (1 + change / 100)
        close_price = max(50, min(300, close_price))  # Bounds
        closes.append(close_price)
    
    closes = np.array(closes)
    
    # Generate OHLC from close
    opens = closes + np.random.normal(0, 1.5, num_days)
    highs = np.maximum(np.maximum(opens, closes) + np.abs(np.random.normal(0, 2, num_days)), 
                        np.maximum(opens, closes))
    lows = np.minimum(np.minimum(opens, closes) - np.abs(np.random.normal(0, 2, num_days)), 
                       np.minimum(opens, closes))
    
    # Volumes
    volumes = np.random.lognormal(mean=15, sigma=0.5, size=num_days)
    
    # Build DataFrame
    df = pd.DataFrame({
        'timestamp': dates.strftime('%Y-%m-%d'),
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes.astype(int)
    })
    
    output_file = Path(output_dir) / f"{symbol}.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Generated {symbol}.csv ({num_days} days) -> {output_file}")
    return output_file


def generate_vix_csv(num_days: int = 500, output_dir: str = "data/raw"):
    """Generate VIX data (mean-reverting around 18)."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=num_days, freq='D')
    
    # VIX mean-reverts around 18
    vix = [18.0]
    for _ in range(1, num_days):
        change = np.random.normal(0, 1.2) + (18 - vix[-1]) * 0.05
        vix.append(max(10, min(80, vix[-1] + change)))
    
    df = pd.DataFrame({
        'timestamp': dates.strftime('%Y-%m-%d'),
        'close': vix
    })
    
    output_file = Path(output_dir) / "vix.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Generated vix.csv ({num_days} days) -> {output_file}")
    return output_file


def generate_example_csv_formats(output_dir: str = "data/raw/examples"):
    """Create example CSV format files with explanations."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # OHLCV example
    ohlcv_example = pd.DataFrame({
        'timestamp': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'open': [150.0, 151.5, 150.8],
        'high': [152.1, 153.2, 152.5],
        'low': [149.5, 151.0, 150.2],
        'close': [151.5, 152.1, 151.8],
        'volume': [1000000, 1100000, 950000]
    })
    
    ohlcv_example.to_csv(Path(output_dir) / "EXAMPLE_OHLCV.csv", index=False)
    print(f"✓ Created EXAMPLE_OHLCV.csv format reference")
    
    # VIX example
    vix_example = pd.DataFrame({
        'timestamp': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'close': [18.5, 17.2, 19.1]
    })
    
    vix_example.to_csv(Path(output_dir) / "EXAMPLE_VIX.csv", index=False)
    print(f"✓ Created EXAMPLE_VIX.csv format reference")
    
    # README
    readme = """# CSV Data Format

## OHLCV Files (Stock Price Data)

**Filename:** `SYMBOL.csv` (e.g., AAPL.csv, SPY.csv)

**Required Columns:**
- timestamp: Date in YYYY-MM-DD format
- open: Opening price
- high: Highest price of the day
- low: Lowest price of the day
- close: Closing price
- volume: Trading volume (shares)

**Example:**
```
timestamp,open,high,low,close,volume
2023-01-01,150.0,152.1,149.5,151.5,1000000
2023-01-02,151.5,153.2,151.0,152.1,1100000
```

## VIX File (Volatility Index)

**Filename:** `vix.csv`

**Required Columns:**
- timestamp: Date in YYYY-MM-DD format
- close: VIX closing value

**Example:**
```
timestamp,close
2023-01-01,18.5
2023-01-02,17.2
```

## Important Notes

1. **Timestamps must be in YYYY-MM-DD format** (can include HH:MM:SS if needed)
2. **All price/volume columns must be numeric**
3. **Data must be sorted by timestamp (ascending)**
4. **No duplicate timestamps per symbol**
5. **Place all CSVs in `data/raw/` directory**

## How to Obtain Data

### Free Options:
- **Yahoo Finance**: Use `yfinance` library or download CSV from website
- **FRED API**: For macro data (free API key required)
- **IEX Cloud**: Some free tier data
- **Quandl**: Community datasets (free tier)

### Example: Download with yfinance

```python
import yfinance as yf
import pandas as pd

# Download data
data = yf.download('AAPL', start='2022-01-01', end='2024-12-31')

# Save to CSV
data.to_csv('data/raw/AAPL.csv')
```

## Data Requirements for Strategy

- **Minimum history:** At least 50 trading days per symbol
- **Recommended:** 1-2 years of history for reliable Z-score signals
- **Frequency:** Daily data (intraday not supported in base version)
- **Time zone:** UTC recommended (will be converted automatically)
"""
    
    with open(Path(output_dir) / "README.md", 'w') as f:
        f.write(readme)
    
    print(f"✓ Created README.md with data format guide")


if __name__ == "__main__":
    print("=" * 60)
    print("LAMMR Sample Data Generator")
    print("=" * 60)
    
    # Generate example data for 5 symbols
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
    
    for symbol in symbols:
        generate_ohlcv_csv(symbol, num_days=500)
    
    # Generate VIX
    generate_vix_csv(num_days=500)
    
    # Generate format examples
    generate_example_csv_formats()
    
    print("\n" + "=" * 60)
    print("✓ Sample data generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review data in: data/raw/")
    print("2. Or download your own data and place in: data/raw/")
    print("3. Run: python -m src.agents.data_agent")
