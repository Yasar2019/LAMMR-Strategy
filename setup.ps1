# LAMMR Strategy - PowerShell Setup & Run Script
# Windows 11 PowerShell Edition
# Run: .\setup.ps1

param(
    [switch]$SkipSetup = $false,
    [switch]$RunAgents = $false,
    [switch]$LaunchDashboard = $false
)

function Write-Header {
    param([string]$text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host $text -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step {
    param([string]$text)
    Write-Host $text -ForegroundColor Green -NoNewline
    Write-Host " ✓" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$text)
    Write-Host $text -ForegroundColor Red
}

# ============================================================================
# SETUP PHASE
# ============================================================================

if (-not $SkipSetup) {
    Write-Header "LAMMR STRATEGY - WINDOWS POWERSHELL SETUP"
    
    # Check Python
    Write-Host "[1/5] Checking Python installation..."
    try {
        $pythonVersion = & python --version 2>&1
        Write-Step "Python found: $pythonVersion"
    } catch {
        Write-Error-Custom "ERROR: Python not found. Install Python 3.9+ from python.org"
        exit 1
    }
    
    # Create venv
    Write-Host "[2/5] Creating virtual environment..."
    if (Test-Path "venv") {
        Write-Step "Virtual environment already exists"
    } else {
        & python -m venv venv
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Virtual environment created"
        } else {
            Write-Error-Custom "ERROR: Failed to create venv"
            exit 1
        }
    }
    
    # Activate venv
    Write-Host "[3/5] Activating virtual environment..."
    & .\venv\Scripts\Activate.ps1
    Write-Step "Virtual environment activated"
    
    # Install dependencies
    Write-Host "[4/5] Installing dependencies..."
    & pip install --quiet --upgrade pip
    & pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Dependencies installed"
    } else {
        Write-Error-Custom "ERROR: Failed to install dependencies"
        exit 1
    }
    
    # Initialize database
    Write-Host "[5/5] Initializing SQLite database..."
    & python -m src.db
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Database initialized (lammr.db)"
    } else {
        Write-Error-Custom "ERROR: Failed to initialize database"
        exit 1
    }
    
    # Generate sample data
    Write-Host "[6/5] Generating sample data..."
    & python scripts\generate_sample_data.py
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Sample data generated"
    } else {
        Write-Error-Custom "WARNING: Sample data generation had issues"
    }
    
    Write-Header "✓ SETUP COMPLETE"
}

# ============================================================================
# RUN AGENTS PHASE
# ============================================================================

if ($RunAgents -or $LaunchDashboard) {
    Write-Header "LAMMR STRATEGY - RUNNING ALL AGENTS"
    
    # Ensure venv is active
    if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Error-Custom "ERROR: Virtual environment not found. Run setup first."
        exit 1
    }
    
    # Activate venv
    & .\venv\Scripts\Activate.ps1
    
    Write-Host "[1/6] DATA AGENT: Loading OHLCV and VIX from CSV..."
    & python -m src.agents.data_agent
    Write-Step "Data loaded"
    
    Write-Host "[2/6] SIGNAL AGENT: Computing Z-score reversal signals..."
    & python -m src.agents.signal_agent
    Write-Step "Signals generated"
    
    Write-Host "[3/6] PORTFOLIO AGENT: Position sizing and risk management..."
    & python -m src.agents.portfolio_agent
    Write-Step "Portfolio metrics computed"
    
    Write-Host "[4/6] ORDERS AGENT: Generating executable orders..."
    & python -m src.agents.orders_agent
    Write-Step "Orders generated"
    
    Write-Host "[5/6] BACKTEST AGENT: Running vectorized backtests..."
    & python -m src.agents.backtest_agent
    Write-Step "Backtests complete"
    
    Write-Host "[6/6] MONITOR AGENT: Computing monitoring metrics..."
    & python -m src.agents.monitor_agent
    Write-Step "Monitoring metrics computed"
    
    Write-Header "✓ ALL AGENTS COMPLETE"
}

# ============================================================================
# DASHBOARD PHASE
# ============================================================================

if ($LaunchDashboard) {
    Write-Header "LAUNCHING STREAMLIT DASHBOARD"
    
    Write-Host "Dashboard opening at: http://localhost:8501" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C in the terminal to stop the dashboard" -ForegroundColor Yellow
    Write-Host ""
    
    & .\venv\Scripts\Activate.ps1
    & streamlit run app.py
}

# ============================================================================
# QUICK START MENU
# ============================================================================

if (-not $RunAgents -and -not $LaunchDashboard -and -not $SkipSetup) {
    Write-Header "QUICK START MENU"
    
    Write-Host ""
    Write-Host "Setup complete! Choose next step:"
    Write-Host ""
    Write-Host "  1. Run all agents and launch dashboard"
    Write-Host "     .\setup.ps1 -RunAgents -LaunchDashboard"
    Write-Host ""
    Write-Host "  2. Run agents only"
    Write-Host "     .\setup.ps1 -SkipSetup -RunAgents"
    Write-Host ""
    Write-Host "  3. Launch dashboard only"
    Write-Host "     .\setup.ps1 -SkipSetup -LaunchDashboard"
    Write-Host ""
    Write-Host "  4. Run agents (Python script)"
    Write-Host "     python run_all_agents.py"
    Write-Host ""
    Write-Host "  5. Launch dashboard (Python script)"
    Write-Host "     streamlit run app.py"
    Write-Host ""
    Write-Host "  6. View data (database)"
    Write-Host "     sqlite3 lammr.db"
    Write-Host ""
    Write-Host "Or run individual agents:"
    Write-Host "     python -m src.agents.data_agent"
    Write-Host "     python -m src.agents.signal_agent"
    Write-Host "     python -m src.agents.orders_agent"
    Write-Host "     python -m src.agents.backtest_agent"
    Write-Host ""
}
