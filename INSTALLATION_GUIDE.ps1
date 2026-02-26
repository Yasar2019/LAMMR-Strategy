#!/usr/bin/env powershell
# LAMMR Strategy - Complete Installation & Operation Guide
# For Windows 11 PowerShell

<#
.SYNOPSIS
    Complete installation and operation guide for LAMMR trading strategy

.DESCRIPTION
    This file documents all commands needed to set up and run the system.
    Copy/paste commands directly into PowerShell.

.NOTES
    Requires: Python 3.9+, Windows 11 (or 10/Server 2019+)
    Time: ~10 minutes for setup
    Disk: ~500MB (venv + db + sample data)
#>

# ============================================================================
# 1. INITIAL SETUP (Run Once)
# ============================================================================

# Open PowerShell in the LAMMR-Strategy directory
# cd C:\Users\Asus\LAMMR-Strategy

# Option A: Automated setup (recommended)
.\setup.ps1

# Option B: Manual setup
# ============================================================================

# Step 1: Create virtual environment
python -m venv venv

# Step 2: Activate virtual environment
.\venv\Scripts\Activate.ps1

# Step 3: Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Initialize database
python -m src.db

# Step 5: Generate sample data (optional)
python scripts\generate_sample_data.py

# ============================================================================
# 2. DAILY WORKFLOW - Run Today's Analysis & Launch Dashboard
# ============================================================================

# Option A: Combined command (recommended)
.\setup.ps1 -SkipSetup -RunAgents -LaunchDashboard

# Option B: Step-by-step

# Step 1: Activate venv
.\venv\Scripts\Activate.ps1

# Step 2: Run all agents
python run_all_agents.py

# Step 3: Launch dashboard
streamlit run app.py

# ============================================================================
# 3. INDIVIDUAL AGENT COMMANDS
# ============================================================================

# Activate venv (if not already active)
.\venv\Scripts\Activate.ps1

# Load data from CSV files
python -m src.agents.data_agent

# Generate signals
python -m src.agents.signal_agent

# Size positions and estimate beta
python -m src.agents.portfolio_agent

# Generate orders
python -m src.agents.orders_agent

# Run backtest
python -m src.agents.backtest_agent

# Check monitoring alerts
python -m src.agents.monitor_agent

# ============================================================================
# 4. DASHBOARD ACCESS
# ============================================================================

# Launch Streamlit UI
streamlit run app.py

# Opens automatically at: http://localhost:8501
# Press Ctrl+C to stop

# Or specify different port:
streamlit run app.py --server.port 8502

# ============================================================================
# 5. DATA MANAGEMENT
# ============================================================================

# Generate sample CSV files (for testing)
python scripts\generate_sample_data.py

# View generated sample data
Get-ChildItem data\raw\*.csv

# Check data in database
sqlite3 lammr.db "SELECT symbol, COUNT(*) as count FROM ohlcv GROUP BY symbol;"

# Reset database (WARNING: deletes all data)
Remove-Item lammr.db -Force
python -m src.db

# ============================================================================
# 6. VIEWING RESULTS
# ============================================================================

# View generated orders
Get-ChildItem data\orders\*.csv | Select-Object -Last 1 | Get-Content

# View backtest results
Get-ChildItem data\backtest\*.csv

# View logs
Get-Content lammr.log -Tail 50

# ============================================================================
# 7. TROUBLESHOOTING COMMANDS
# ============================================================================

# Check Python version
python --version

# Check if venv is activated (should show venv path)
Get-Command python

# List installed packages
pip list

# Check if port 8501 is in use
netstat -ano | findstr :8501

# Kill process on port 8501 (if needed)
$process = Get-Process | Where-Object { $_.Id -eq <PID> }
Stop-Process -InputObject $process -Force

# View Python path
python -c "import sys; print(sys.path)"

# Test database connection
python -c "from src.db import get_connection; conn = get_connection('lammr.db'); print('✓ DB OK')"

# ============================================================================
# 8. CONFIGURATION
# ============================================================================

# View current settings
Get-Content config.yaml

# Edit settings (opens in default editor)
notepad config.yaml

# Or with VS Code
code config.yaml

# After editing, restart agents to apply changes

# ============================================================================
# 9. CSV DATA PREPARATION
# ============================================================================

# Check sample CSV format
Get-Content data\raw\examples\EXAMPLE_OHLCV.csv

Get-ChildItem data\raw\examples\

# Copy your own CSVs into data/raw/
# Format: SYMBOL.csv with columns: timestamp, open, high, low, close, volume

# Example: Download AAPL data with Python
<# 
pip install yfinance
python -c "
import yfinance as yf
data = yf.download('AAPL', start='2022-01-01', end='2024-12-31')
data.to_csv('data/raw/AAPL.csv')
print('Downloaded AAPL data')
"
#>

# ============================================================================
# 10. DEACTIVATE VIRTUAL ENVIRONMENT
# ============================================================================

# When done, deactivate venv (optional)
deactivate

# Or use Ctrl+C to stop any running process

# ============================================================================
# QUICK REFERENCE - Copy/Paste These
# ============================================================================

<#
# First time setup:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.db
python scripts\generate_sample_data.py

# Daily run:
.\venv\Scripts\Activate.ps1
python run_all_agents.py
streamlit run app.py

# Alternative daily run:
.\setup.ps1 -SkipSetup -RunAgents -LaunchDashboard
#>

# ============================================================================
# FILE LOCATIONS
# ============================================================================

<#
Strategy Configuration: .\config.yaml
Database: .\lammr.db
Sample Data: .\data\raw\
Generated Orders: .\data\orders\
Backtest Results: .\data\backtest\
Logs: .\lammr.log

Source Code:
  - Agents: .\src\agents\
  - Utilities: .\src\utils\
  - Database: .\src\db\

Scripts:
  - Sample Data Gen: .\scripts\generate_sample_data.py
  - Run All Agents: .\run_all_agents.py
  - Dashboard: .\app.py
#>
