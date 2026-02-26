# LAMMR Strategy - System Architecture

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                  │
│  CSV Files (OHLCV per symbol) + VIX CSV                                │
│  Location: data/raw/*.csv                                              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │         DATA AGENT (data_agent.py)           │
        ├──────────────────────────────────────────────┤
        │ • Discover CSV files in data/raw/            │
        │ • Validate OHLCV format                      │
        │ • Parse timestamps                           │
        │ • Insert into SQLite (duplicate handling)    │
        │ • Track metadata                             │
        └──────────────────────────┬───────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │   SQLITE DATABASE        │
                    │   (lammr.db)             │
                    ├──────────────────────────┤
                    │ • ohlcv (price data)     │
                    │ • vix                    │
                    │ • signals                │
                    │ • positions              │
                    │ • backtest_results       │
                    │ • + 6 more tables        │
                    └──────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
    │  SIGNAL AGENT    │  │ PORTFOLIO AGENT│  │  ORDERS AGENT    │
    │ (signal_agent.py)│  │(portfolio_a.py)│  │(orders_agent.py) │
    ├──────────────────┤  ├────────────────┤  ├──────────────────┤
    │• Compute Z-score │  │• Size positions│  │• Generate orders │
    │• Volume ratios   │  │• Beta estimate │  │• Record execution│
    │• Liquidity score │  │• SPY hedge     │  │• Save orders CSV │
    │• Composite score │  │• Drawdown chks │  │• Track P&L       │
    │• BUY/SELL signals│  │• Risk caps     │  │                  │
    └────────┬─────────┘  └────────┬───────┘  └──────────┬───────┘
             │                     │                     │
             └─────────────────────┴─────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │   SQLITE DATABASE        │
                    │   (Updated records)      │
                    ├──────────────────────────┤
                    │ • signals table          │
                    │ • positions table        │
                    │ • orders CSV files       │
                    └──────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
    │ BACKTEST AGENT   │  │ MONITOR AGENT  │  │ STREAMLIT UI     │
    │(backtest_agent.py│  │(monitor_agent.)│  │  (app.py)        │
    ├──────────────────┤  ├────────────────┤  ├──────────────────┤
    │• Replay signals  │  │• Rolling Sharpe│  │ • Overview page  │
    │• Historical test │  │• Rolling DD%   │  │ • Signals page   │
    │• Slippage+comm   │  │• Alert system  │  │ • Backtest page  │
    │• Equity curves   │  │• IC calculation│  │ • Portfolio page │
    │• Trade log       │  │• Decile returns│  │ • Monitor page   │
    │• Metrics        │  │                │  │ • Settings page  │
    │  (Sharpe, etc)   │  │                │  │ • Run Agents page│
    └────────┬─────────┘  └────────┬───────┘  └──────────┬───────┘
             │                     │                     │
             └─────────────────────┴─────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │   OUTPUT & DISPLAY       │
                    ├──────────────────────────┤
                    │ • Backtest Results CSV   │
                    │ • Orders CSV             │
                    │ • Dashboard (Web UI)     │
                    │ • Alerts                 │
                    │ • Metrics                │
                    │ • Logs (lammr.log)       │
                    └──────────────────────────┘
```

---

## Agent Communication Architecture

```
                        ┌─────────────────┐
                        │  SQLite DB      │
                        │  (Single Source │
                        │   of Truth)     │
                        └────────┬────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
          ┌──────▼────────┐ ┌────▼────────┐ ┌──┴──────────────┐
          │ DATA AGENT    │ │ SIGNAL AGENT│ │ OTHER AGENTS    │
          │               │ │             │ │ (Portfolio,     │
          │ Write: ohlcv, │ │ Write:      │ │  Orders,        │
          │       vix,    │ │ signals     │ │  Backtest,      │
          │   metadata    │ │             │ │  Monitor)       │
          │               │ │ Read: ohlcv │ │                 │
          │ Read: (none   │ │             │ │ Query: all      │
          │  during load) │ │             │ │ tables as       │
          └───────────────┘ └─────────────┘ │ needed          │
                                            │                 │
                                            └─────────────────┘

No direct agent-to-agent communication.
All coordination via SQLite database.
```

---

## Agent Execution Flow

```
1. DATA LOADING PHASE
   ┌─────────────────────────────────┐
   │ data_agent.py                   │
   │ • Discover CSVs in data/raw/    │
   │ • Load OHLCV data               │
   │ • Load VIX data                 │
   │ • Validate & store              │
   └─────────────────────────────────┘
                  │
                  ▼ (Database populated)

2. SIGNAL GENERATION PHASE
   ┌─────────────────────────────────┐
   │ signal_agent.py                 │
   │ • Read OHLCV from DB            │
   │ • Compute Z-scores              │
   │ • Compute liquidity scores      │
   │ • Generate signals              │
   │ • Store signals in DB           │
   └─────────────────────────────────┘
                  │
                  ▼ (Signals available)

3. PORTFOLIO & ORDERS PHASE (Parallel)
   ┌─────────────────────────────────┐
   │ portfolio_agent.py              │
   │ • Size positions                │
   │ • Estimate beta                 │
   │ • Calculate hedges              │
   └─────────────────────────────────┘
   ┌─────────────────────────────────┐
   │ orders_agent.py                 │
   │ • Read signals from DB          │
   │ • Generate orders CSV           │
   │ • Record positions              │
   └─────────────────────────────────┘
                  │
                  ▼ (Orders ready for review)

4. BACKTEST & MONITORING PHASE (Parallel)
   ┌─────────────────────────────────┐
   │ backtest_agent.py               │
   │ • Replay signals                │
   │ • Simulate trading              │
   │ • Calculate metrics             │
   │ • Store results                 │
   └─────────────────────────────────┘
   ┌─────────────────────────────────┐
   │ monitor_agent.py                │
   │ • Calculate rolling metrics     │
   │ • Check alert conditions        │
   │ • Analyze signal quality        │
   └─────────────────────────────────┘
                  │
                  ▼ (All results in DB)

5. DISPLAY PHASE
   ┌─────────────────────────────────┐
   │ Streamlit Dashboard (app.py)    │
   │ • Query all DB tables           │
   │ • Render 7 pages                │
   │ • Display metrics               │
   │ • Trigger agents manually       │
   └─────────────────────────────────┘
                  │
                  ▼
            Web Browser
        http://localhost:8501
```

---

## Module Dependency Graph

```
┌──────────────────────────────────────────────────────────────┐
│                       app.py (Dashboard)                      │
├──────────────────────────────────────────────────────────────┤
│  ├─ Import: All 6 agents                                     │
│  ├─ Import: db (connection)                                  │
│  └─ Import: config                                           │
└───────┬────────────────────────────────────────────────────┬─┘
        │                                                    │
        ▼                                                    ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│  Each Agent Module       │  │    Shared Dependencies       │
│  (data, signal, etc)     │  │                              │
├──────────────────────────┤  ├──────────────────────────────┤
│ ├─ Import: db            │  │ ├─ db/__init__.py            │
│ ├─ Import: config        │  │ │  └─ schema.sql             │
│ ├─ Import: helpers       │  │ │                            │
│ ├─ Import: indicators    │  │ ├─ config.py                │
│ ├─ Import: csv_loader    │  │ ├─ indicators.py            │
│ ├─ Import: portfolio     │  │ ├─ csv_loader.py            │
│ └─ Import: (pandas,      │  │ ├─ portfolio.py             │
│    numpy, sqlite3)       │  │ └─ helpers.py               │
└──────────────────────────┘  │                              │
                              │ (External: pandas, numpy,   │
                              │  plotly, streamlit, etc)    │
                              └──────────────────────────────┘
```

---

## Data Model

```
CSV Files (Input)
    ├─ AAPL.csv
    ├─ MSFT.csv
    ├─ GOOGL.csv
    ├─ TSLA.csv
    ├─ SPY.csv
    └─ vix.csv

         │
         ▼ (data_agent)

SQLite Tables
    ├─ ohlcv (symbol, timestamp, OHLC, volume)
    ├─ vix (timestamp, close)
    │
    ├─ signals (symbol, timestamp, signal_type, z_score, confidence)
    ├─ positions (symbol, entry/exit, prices, P&L)
    │
    ├─ backtest_results (metrics per run)
    ├─ backtest_trades (individual trades)
    ├─ daily_returns (daily P&L)
    ├─ monitoring_metrics (rolling metrics)
    │
    └─ data_metadata (tracks what was loaded)

         │
         ▼ (Queries)

Dashboard Display
    ├─ Metrics (Sharpe, DD, etc.)
    ├─ Charts (equity curves, etc.)
    ├─ Tables (signals, trades, etc.)
    └─ Alerts (thresholds exceeded)
```

---

## Signal Generation Logic

```
For each symbol:
    For each bar (where lookback conditions met):
        
        z_score = (close - mean(close)) / std(close)
        volume_ma = mean(volume)
        volume_ratio = volume / volume_ma
        liquidity_score = f(volume_ma, volume_ratio)
        composite_score = (0.7 * |z_score| + 0.3 * liquidity_score)
        
        IF z_score < buy_threshold AND liquidity_score > min_confidence:
            signal = BUY
        ELSE IF z_score > sell_threshold AND liquidity_score > min_confidence:
            signal = SELL
        ELSE IF abs(z_score) < exit_threshold:
            signal = EXIT
        ELSE:
            signal = HOLD (no record)
        
        IF signal != HOLD:
            INSERT into signals table
```

---

## Backtest Logic

```
For each symbol:
    Load historical OHLCV
    Load signals for symbol
    
    position = None
    equity = starting_capital
    
    For each bar (in chronological order):
        IF signal == BUY AND position == None:
            quantity = equity * position_size / price
            position = (entry_price, quantity)
            equity -= slippage + commission
        
        ELSE IF signal == SELL AND position != None:
            P&L = (exit_price - entry_price) * quantity - costs
            equity += P&L
            Record trade (entry, exit, P&L)
            position = None
    
    Calculate metrics:
        Sharpe = mean_return / std_return * sqrt(252)
        Sortino = mean_return / downside_std * sqrt(252)
        Max DD = max_drawdown / peak_equity
        Win Rate = winning_trades / total_trades
        Profit Factor = sum(wins) / sum(losses)
```

---

## Dashboard Page Structure

```
http://localhost:8501
│
├─ Sidebar Navigation
│  └─ Buttons to select page
│
├─ Page 1: Overview
│  ├─ Metrics (Symbols loaded, Signal count, etc.)
│  └─ Data summary table
│
├─ Page 2: Signals
│  ├─ Filter by symbol
│  ├─ Limit selector
│  └─ Signals dataframe
│
├─ Page 3: Backtest Results
│  └─ Backtest metrics table
│
├─ Page 4: Portfolio
│  ├─ Open positions table
│  └─ Today's orders table
│
├─ Page 5: Monitoring
│  ├─ Rolling Sharpe metric box
│  ├─ Rolling DD metric box
│  └─ Alerts (color-coded by severity)
│
├─ Page 6: Settings
│  └─ Parameter display (read-only)
│
└─ Page 7: Run Agents
   ├─ Load Data button
   ├─ Generate Signals button
   ├─ Generate Orders button
   └─ Run Backtest button
```

---

## File Size Estimates

```
Python Code:
  src/agents/          ~1,000 lines
  src/utils/           ~700 lines
  src/db/              ~300 lines
  app.py               ~400 lines
  scripts/             ~150 lines
  Total:              ~2,550 lines

Configuration:
  config.yaml          ~60 lines
  requirements.txt     ~10 lines
  Schema/SQL           ~200 lines
  Total:              ~270 lines

Documentation:
  README.md           ~1,200 lines
  Guides              ~400 lines
  Comments            ~200 lines
  Total:             ~1,800 lines

Total: ~4,600 lines equivalent

Disk space:
  Code + Config: ~200 KB
  venv:          ~300 MB
  Database:      ~5 MB (empty, grows with data)
  Sample data:   ~20 MB (500 bars x 5 symbols)
  Total:         ~500 MB
```

---

## Deployment Architecture

```
User's Computer (Windows 11)
│
├─ C:\Users\Asus\LAMMR-Strategy\
│  ├─ Python venv/              (isolated environment)
│  ├─ src/                      (all code)
│  ├─ lammr.db                  (SQLite, single file)
│  ├─ config.yaml               (parameters)
│  ├─ data/
│  │  ├─ raw/                   (input CSVs)
│  │  ├─ orders/                (output orders CSVs)
│  │  └─ backtest/              (output results CSVs)
│  └─ logs/                     (lammr.log)
│
├─ (No external dependencies)
├─ (No network required)
├─ (No paid APIs)
└─ (No broker accounts)

Execution:
  Terminal → PowerShell → Python → Agents → SQLite
                                      ↓
                                  Streamlit
                                      ↓
                                  Web Browser
```

---

This is the complete architecture for LAMMR Strategy.
All components are modular, database-driven, and Windows-compatible.
