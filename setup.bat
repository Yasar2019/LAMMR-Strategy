@echo off
REM LAMMR Strategy - Windows Batch Setup Script
REM Run this file to set up the project

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo LAMMR Strategy - Windows Setup
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM 1. Create virtual environment
echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

REM 2. Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate venv
    pause
    exit /b 1
)

REM 3. Install dependencies
echo [3/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM 4. Initialize database
echo [4/5] Initializing database...
python -m src.db
if errorlevel 1 (
    echo ERROR: Failed to initialize database
    pause
    exit /b 1
)

REM 5. Generate sample data
echo [5/5] Generating sample data...
python scripts/generate_sample_data.py
if errorlevel 1 (
    echo ERROR: Failed to generate sample data
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo.
echo 1. Load data and run all agents:
echo    python run_all_agents.py
echo.
echo 2. Launch Streamlit dashboard:
echo    streamlit run app.py
echo.
echo Dashboard will open at: http://localhost:8501
echo.
echo Note: Virtual environment is already activated.
echo       To deactivate later, run: deactivate
echo.
pause
