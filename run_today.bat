@echo off
REM LAMMR Strategy - Quick Run Script
REM This script runs all agents in sequence, then launches Streamlit

setlocal enabledelayedexpansion

REM Activate virtual environment
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo LAMMR Strategy - Running All Agents
echo ============================================================
echo.

echo [1/6] Loading data from CSV files...
python -m src.agents.data_agent
if errorlevel 1 echo ERROR: Data agent failed

echo.
echo [2/6] Generating signals...
python -m src.agents.signal_agent
if errorlevel 1 echo ERROR: Signal agent failed

echo.
echo [3/6] Computing portfolio metrics...
python -m src.agents.portfolio_agent
if errorlevel 1 echo ERROR: Portfolio agent failed

echo.
echo [4/6] Generating orders...
python -m src.agents.orders_agent
if errorlevel 1 echo ERROR: Orders agent failed

echo.
echo [5/6] Running backtest...
python -m src.agents.backtest_agent
if errorlevel 1 echo ERROR: Backtest agent failed

echo.
echo [6/6] Computing monitoring metrics...
python -m src.agents.monitor_agent
if errorlevel 1 echo ERROR: Monitor agent failed

echo.
echo ============================================================
echo All agents complete! Launching Streamlit dashboard...
echo ============================================================
echo.

timeout /t 2

streamlit run app.py

pause
