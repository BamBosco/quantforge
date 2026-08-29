@echo off
REM ==============================================================================
REM QuantForge Studio — Automated 24/7 Windows VPS Deployment Launcher
REM ==============================================================================
title QuantForge Studio 24/7 Autonomous Runner

echo [1/3] Setting up Python Virtual Environment...
if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo [2/3] Starting Live MT5 Bridge on Port 8765...
start "QuantForge Bridge" cmd /k "set PYTHONPATH=.;src && python tools\run_candidate_007_mt5_live_bridge.py --port 8765 --auto-exec --balance 30.0 --symbol XAUUSD"

echo [3/3] Starting Web Dashboard on Port 8080...
start "QuantForge Dashboard" cmd /k "set PYTHONPATH=.;src && python tools\paper_dashboard.py 8080"

echo.
echo =================================================================
echo 🎉 QuantForge 24/7 Engine is now RUNNING!
echo • Dashboard URL: http://localhost:8080
echo • MT5 Bridge   : http://localhost:8765
echo =================================================================
pause
