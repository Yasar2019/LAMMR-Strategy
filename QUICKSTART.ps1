# LAMMR Strategy - PowerShell Setup & Run Guide

# ============================================================================
# SETUP: Create Virtual Environment and Install Dependencies
# ============================================================================

# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# ============================================================================
# DATABASE: Initialize SQLite Database
# ============================================================================

# 4. Initialize database (creates lammr.db with schema)
python -m src.db

# ============================================================================
# DATA: Generate Sample Data (Optional) or Load Your Own
# ============================================================================

# 5a. Generate sample data for testing
python scripts/generate_sample_data.py

# 5b. OR place your CSV files in data/raw/ and skip sample generation
# Format: SYMBOL.csv (columns: timestamp, open, high, low, close, volume)
#         vix.csv (columns: timestamp, close)

# ============================================================================
# AGENTS: Run Individual Agents (One-Time Setup)
# ============================================================================

# 6. Load OHLCV and VIX data from CSVs
python -m src.agents.data_agent

# 7. Generate Z-score signals
python -m src.agents.signal_agent

# 8. Generate orders (for today)
python -m src.agents.orders_agent

# 9. Run backtest
python -m src.agents.backtest_agent

# 10. Check monitoring alerts
python -m src.agents.monitor_agent

# ============================================================================
# DASHBOARD: Launch Streamlit Web Interface
# ============================================================================

# 11. Start Streamlit dashboard
streamlit run app.py

# Dashboard will open at: http://localhost:8501

# ============================================================================
# QUICK START: All-in-One Commands (Copy & Paste)
# ============================================================================

# Setup (first time only):
# python -m venv venv
# .\venv\Scripts\Activate.ps1
# pip install -r requirements.txt
# python -m src.db
# python scripts/generate_sample_data.py

# Run today's analysis:
# python -m src.agents.data_agent
# python -m src.agents.signal_agent
# python -m src.agents.orders_agent
# streamlit run app.py

# ============================================================================
# NOTES
# ============================================================================

# - Database: lammr.db (SQLite, single file)
# - Data directory: data/raw/ (place your CSVs here)
# - Orders: data/orders/ (generated orders.csv files)
# - Config: config.yaml (strategy parameters)
# - Logs: lammr.log (agent execution logs)

# - All trading is PAPER ONLY (no broker integration)
# - Orders are generated to CSV for manual review
# - Database tracks all signals, positions, and backtest results

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If you get "module not found" errors:
# - Ensure venv is activated: .\venv\Scripts\Activate.ps1
# - Verify Python path: python -c "import sys; print(sys.path)"

# If Streamlit won't start:
# - Check if port 8501 is in use: netstat -ano | findstr :8501
# - Kill process: taskkill /PID <PID> /F
# - Or specify different port: streamlit run app.py --server.port 8502

# If no data loaded:
# - Check CSV format matches examples in data/raw/examples/
# - Verify timestamps are YYYY-MM-DD
# - Check data/raw/ contains *.csv files

# ============================================================================
