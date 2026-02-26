-- LAMMR Strategy SQLite Schema

-- OHLCV Data Table
CREATE TABLE IF NOT EXISTS ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,       -- Unix timestamp
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timestamp ON ohlcv(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv(timestamp);

-- VIX Data Table
CREATE TABLE IF NOT EXISTS vix (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,       -- Unix timestamp
    close REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);
CREATE INDEX IF NOT EXISTS idx_vix_timestamp ON vix(timestamp);

-- Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,       -- Unix timestamp (signal date)
    signal_type TEXT NOT NULL,        -- 'BUY', 'SELL', 'EXIT', 'HOLD'
    z_score REAL,
    volume_ratio REAL,
    liquidity_score REAL,             -- 0.0-1.0
    composite_score REAL,
    confidence REAL,                  -- Alias for composite_score
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);

-- Portfolio Positions Table (current + historical)
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_timestamp INTEGER NOT NULL, -- Unix timestamp
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    position_value REAL NOT NULL,
    sizing_method TEXT,               -- 'fixed_fractional', 'volatility_adjusted', etc.
    stop_loss_price REAL,
    beta_estimate REAL,
    hedge_quantity REAL,              -- For SPY hedge
    status TEXT DEFAULT 'open',       -- 'open', 'closed'
    exit_timestamp INTEGER,
    exit_price REAL,
    pnl REAL,
    pnl_pct REAL,
    duration_bars INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_positions_symbol_status ON positions(symbol, status);
CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions(entry_timestamp);

-- Backtest Results Table
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_return_pct REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown_pct REAL,
    win_rate REAL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    profit_factor REAL,               -- Gross profit / Gross loss
    avg_win_pct REAL,
    avg_loss_pct REAL,
    avg_trade_duration_bars INTEGER,
    best_trade_pct REAL,
    worst_trade_pct REAL,
    consecutive_losses INTEGER,
    recovery_factor REAL,             -- Total profit / Max drawdown
    parameters TEXT,                  -- JSON of strategy parameters used
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backtest Trades Table
CREATE TABLE IF NOT EXISTS backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_result_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    entry_timestamp INTEGER NOT NULL,
    exit_timestamp INTEGER,
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    pnl REAL,
    pnl_pct REAL,
    duration_bars INTEGER,
    commissions_paid REAL,
    slippage REAL,
    FOREIGN KEY(backtest_result_id) REFERENCES backtest_results(id)
);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_result_id ON backtest_trades(backtest_result_id);

-- Daily Returns Table (for IC, decile analysis)
CREATE TABLE IF NOT EXISTS daily_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,       -- Unix timestamp (date)
    symbol TEXT,
    daily_return_pct REAL,
    backtest_result_id INTEGER,
    FOREIGN KEY(backtest_result_id) REFERENCES backtest_results(id)
);
CREATE INDEX IF NOT EXISTS idx_daily_returns_timestamp ON daily_returns(timestamp);

-- Monitoring Metrics Table
CREATE TABLE IF NOT EXISTS monitoring_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,       -- Unix timestamp
    rolling_sharpe_20 REAL,           -- 20-day rolling Sharpe
    rolling_sharpe_60 REAL,           -- 60-day rolling Sharpe
    current_drawdown_pct REAL,
    underwater_pct REAL,
    consecutive_losses INTEGER,
    trade_count_last_20_days INTEGER,
    win_rate_last_20_days REAL,
    alert_flag INTEGER DEFAULT 0,     -- 1 if alert triggered
    alert_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp ON monitoring_metrics(timestamp);

-- Data Source Metadata (track what was loaded)
CREATE TABLE IF NOT EXISTS data_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    data_type TEXT NOT NULL,          -- 'ohlcv', 'vix'
    first_date TEXT,
    last_date TEXT,
    record_count INTEGER,
    last_loaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file TEXT,
    UNIQUE(symbol, data_type)
);
