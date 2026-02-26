# LAMMR Quantitative Strategy

A complete local Windows Python application for the LAMMR quantitative mean-reversion trading strategy.

**Status: Local Paper Trading Only | No Broker Integration | Personal Research**

## Overview

LAMMR is a deterministic, signal-driven trading strategy based on:
- **Z-Score Reversal**: Identifies oversold/overbought conditions using rolling Z-scores
- **Liquidity Filtering**: Rejects signals in illiquid markets
- **Portfolio Sizing**: Risk-managed position sizing with drawdown caps
- **Backtesting**: Vectorized historical testing with realistic costs and slippage

The system uses a **multi-agent architecture**:
1. **data_agent**: Loads OHLCV + VIX from local CSV files
2. **signal_agent**: Computes Z-score and liquidity-based signals
3. **portfolio_agent**: Position sizing, beta estimation, hedging (paper)
4. **orders_agent**: Generates orders.csv for manual review
5. **backtest_agent**: Vectorized daily backtesting
6. **monitor_agent**: Rolling Sharpe, IC, alerts

All results stored in SQLite. Interactive Streamlit dashboard for monitoring and analysis.

## Stack

- **Language**: Python 3.9+
- **Database**: SQLite (single file: `lammr.db`)
- **UI**: Streamlit (web-based dashboard)
- **Computation**: Pandas, NumPy, SciPy
- **Charts**: Plotly (interactive)
- **Config**: YAML

## Quick Start (Windows 11 PowerShell)

### 1. Setup (One-Time)

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m src.db

# Generate sample data (optional)
python scripts/generate_sample_data.py
```

### 2. Load Data

```powershell
# Either use generated sample data, or:
# Place your CSV files in data/raw/
#   - AAPL.csv, SPY.csv, etc. (OHLCV data)
#   - vix.csv (volatility index)

python -m src.agents.data_agent
```

### 3. Generate Signals & Orders

```powershell
python -m src.agents.signal_agent
python -m src.agents.orders_agent
```

### 4. Run Backtest

```powershell
python -m src.agents.backtest_agent
```

### 5. Launch Dashboard

```powershell
streamlit run app.py
```

Dashboard opens at `http://localhost:8501`

## CSV Data Format

### Stock OHLCV (e.g., `AAPL.csv`)

```
timestamp,open,high,low,close,volume
2023-01-01,150.0,152.1,149.5,151.5,1000000
2023-01-02,151.5,153.2,151.0,152.1,1100000
```

**Requirements:**
- Columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`
- Timestamp: `YYYY-MM-DD` (or `YYYY-MM-DD HH:MM:SS`)
- All prices/volumes: numeric
- Sorted by timestamp, no duplicates

### VIX Index (`vix.csv`)

```
timestamp,close
2023-01-01,18.5
2023-01-02,17.2
```

**Requirements:**
- Columns: `timestamp`, `close`
- Same date format as OHLCV

### Free Data Sources

- **Yahoo Finance**: `pip install yfinance`
- **Quandl**: Community datasets
- **FRED**: Macro data (free API key)
- **IEX Cloud**: Limited free tier

### Example: Download with yfinance

```python
import yfinance as yf

data = yf.download(['AAPL', 'SPY'], start='2022-01-01', end='2024-12-31')
data.to_csv('data/raw/SYMBOL.csv')
```

## Configuration

Edit `config.yaml` to customize strategy parameters:

```yaml
# Z-Score Thresholds
zscore_lookback: 20
zscore_buy_threshold: -1.5      # Buy when oversold
zscore_sell_threshold: 1.5      # Sell when overbought

# Position Sizing
position_size_pct: 0.02          # Risk 2% per trade
max_positions: 10
max_drawdown_pct: 15.0           # Stop trading if DD > 15%

# Costs
slippage_bps: 1                  # 1 basis point slippage
commission_bps: 1                # 1 basis point commission

# Backtest
backtest_start_date: "2022-01-01"
backtest_end_date: "2025-12-31"
stock_initial_capital: 100000
```

## Project Structure

```
LAMMR-Strategy/
├── app.py                          # Streamlit dashboard
├── config.yaml                     # Strategy configuration
├── requirements.txt                # Python dependencies
├── QUICKSTART.ps1                  # PowerShell setup guide
├── README.md                       # This file
├── run_all_agents.py               # Run all agents sequentially
├── lammr.db                        # SQLite database (created)
│
├── src/
│   ├── agents/
│   │   ├── data_agent.py           # CSV → SQLite loader
│   │   ├── signal_agent.py         # Z-score signal generation
│   │   ├── portfolio_agent.py      # Position sizing & risk mgmt
│   │   ├── orders_agent.py         # Order generation
│   │   ├── backtest_agent.py       # Vectorized backtesting
│   │   └── monitor_agent.py        # Performance monitoring
│   │
│   ├── utils/
│   │   ├── indicators.py           # Signal computation (Z-score, etc)
│   │   ├── portfolio.py            # Position sizing functions
│   │   ├── csv_loader.py           # CSV validation & loading
│   │   ├── config.py               # Config file handling
│   │   └── helpers.py              # Logging, timestamp utilities
│   │
│   └── db/
│       ├── __init__.py             # Database connection & init
│       ├── schema.sql              # SQLite schema
│       └── __main__.py             # Entry point for db init
│
├── scripts/
│   └── generate_sample_data.py     # Create example CSV files
│
├── data/
│   ├── raw/                        # Input: place CSV files here
│   │   └── examples/               # Example CSV format files
│   ├── orders/                     # Output: generated orders CSVs
│   └── backtest/                   # Output: backtest results CSVs
│
└── notebooks/                      # (Jupyter notebooks, optional)
```

## Database Schema

### Core Tables

- **ohlcv**: Daily OHLCV data for all symbols
- **vix**: VIX volatility index daily data
- **signals**: Generated BUY/SELL/EXIT signals
- **positions**: Open and closed positions (paper trading)

### Analysis Tables

- **backtest_results**: Backtest metrics (Sharpe, drawdown, etc)
- **backtest_trades**: Individual trade records
- **daily_returns**: Daily P&L breakdown
- **monitoring_metrics**: Rolling Sharpe, alerts

### Metadata

- **data_metadata**: Track what data was loaded and when

## Agent Workflows

### Data Loading

```
CSV files → data_agent → Validation → SQLite (ohlcv, vix)
```

### Signal Generation

```
OHLCV → signal_agent → Z-score calc → Liquidity score → Composite score → signals table
```

### Position Sizing

```
Signal + Entry price → portfolio_agent → Fixed fractional OR Vol-adjusted sizing → Position size
```

### Order Generation

```
Signals → orders_agent → Format orders → orders.csv (manual execution)
```

### Backtesting

```
Historical OHLCV + Signals → backtest_agent → Vectorized simulation → Metrics + Trades
```

### Monitoring

```
Trades → monitor_agent → Rolling Sharpe, Drawdown, IC, Alerts → Dashboard
```

## Dashboard Features

### Pages

1. **Overview**: Loaded symbols, signal counts, position summaries
2. **Signals**: Recent BUY/SELL/EXIT signals with Z-scores and confidence
3. **Backtest Results**: Historical test metrics and equity curves
4. **Portfolio**: Open positions and today's generated orders
5. **Monitoring**: Rolling Sharpe, drawdown, alerts
6. **Settings**: Strategy parameter reference
7. **Run Agents**: Buttons to manually trigger agent execution

### Key Metrics Displayed

- Total symbols loaded
- Signal count and types
- Win rate, Sharpe ratio, max drawdown
- Rolling Sharpe (20-day)
- Consecutive losses
- Strategy alerts

## Deterministic Trading Rules

The strategy uses **NO machine learning or AI**. All decisions are rule-based:

```python
if z_score < -1.5 and liquidity_score > 0.65:
    signal = 'BUY'
elif z_score > 1.5 and liquidity_score > 0.65:
    signal = 'SELL'
elif abs(z_score) < 0.3:
    signal = 'EXIT'
else:
    signal = 'HOLD'
```

Position sizing is deterministic:
```python
quantity = (account_value * position_size_pct) / entry_price
```

## Paper Trading Only

- **No broker integration**: Orders are saved to CSV
- **Manual execution**: Review orders and execute manually if desired
- **Position tracking**: Database tracks all paper positions and P&L
- **No auto-execution**: Everything is for personal research/analysis

## Backtest Features

- **Vectorized**: Fast processing (not event-driven)
- **Realistic costs**: Slippage (1 bps) + commission (1 bps)
- **Historical signals**: Uses same signal logic on historical data
- **Daily frequency**: Daily bars (supports OHLCV only)
- **Trade log**: Detailed per-trade metrics

### Backtest Metrics

- Total return (%)
- Sharpe ratio
- Sortino ratio
- Max drawdown (%)
- Win rate (%)
- Profit factor
- Trade count
- Best/worst trade

## Performance Monitoring

- **Rolling Sharpe**: 20-day rolling Sharpe ratio
- **Rolling drawdown**: Current underwater %
- **Information Coefficient (IC)**: Signal strength vs actual returns
- **Decile returns**: Performance by signal confidence levels
- **Consecutive losses**: Alert if N losses in a row

## Windows Requirements

- Python 3.9+ (tested on 3.10, 3.11, 3.12)
- Windows 11 (or 10/Server 2019+)
- PowerShell 7+ (or 5.1)
- ~500MB disk space (for venv + db)

## Troubleshooting

### Module not found errors
```powershell
# Ensure venv is activated:
.\venv\Scripts\Activate.ps1

# Check Python path:
python -c "import sys; print(sys.path)"
```

### Streamlit won't start
```powershell
# Check if port 8501 is in use:
netstat -ano | findstr :8501

# Use different port:
streamlit run app.py --server.port 8502
```

### No data loading
- Check CSV format in `data/raw/examples/`
- Verify timestamps are `YYYY-MM-DD`
- Check for duplicate timestamps or invalid prices
- Run: `python scripts/generate_sample_data.py` to test with sample data

### Database locked
```powershell
# Delete and reinitialize:
Remove-Item lammr.db -ErrorAction SilentlyContinue
python -m src.db
```

## Future Enhancements (Optional)

- Intraday data (hourly/minute bars)
- Multiple timeframes simultaneously
- Machine learning signal blending (opt-in)
- Risk models (VaR, CVaR)
- Portfolio correlation analysis
- Walk-forward optimization
- Live market data ingestion (yfinance polling)
- Paper trading account sync
- More sophisticated hedging (sector correlation)

## License

Personal research / educational use only.

## Support

For questions or issues:
1. Check CSV format in `data/raw/examples/README.md`
2. Review logs in `lammr.log`
3. Inspect database: `sqlite3 lammr.db ".tables"`

---

**LAMMR Strategy** | Local | Windows | Paper Trading | SQLite + Streamlit
