#!/bin/bash
# QuantForge Master Engine Launcher
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p logs data/paper_mode

PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "=================================================================="
echo "🚀 Starting QuantForge Master Engine & Services..."
echo "=================================================================="

# 1. Kill any existing instances to avoid port conflicts
pkill -9 -f "run_candidate_007_mt5_live_bridge" 2>/dev/null || true
pkill -9 -f "paper_dashboard.py" 2>/dev/null || true
pkill -9 -f "run_telegram_assistant.py" 2>/dev/null || true
kill -9 $(lsof -t -i :8765) 2>/dev/null || true
kill -9 $(lsof -t -i :8080) 2>/dev/null || true
sleep 1

# 2. Start Live MT5 Auto-Execution Bridge (Port 8765)
echo "🛰️ [1/3] Starting MT5 Auto-Execution Bridge on http://127.0.0.1:8765..."
PYTHONPATH=.:src PYTHONUNBUFFERED=1 nohup "$PYTHON" tools/run_candidate_007_mt5_live_bridge.py --host 127.0.0.1 --port 8765 --symbol BTCUSDm > logs/bridge.log 2>&1 &
echo $! > logs/bridge.pid

# 3. Start Studio Web Dashboard (Port 8080)
echo "📊 [2/3] Starting QuantForge Web Cockpit on http://127.0.0.1:8080..."
PYTHONPATH=.:src PYTHONUNBUFFERED=1 nohup "$PYTHON" tools/paper_dashboard.py 8080 > logs/dashboard.log 2>&1 &
echo $! > logs/dashboard.pid

# 4. Start Telegram Interactive AI Assistant
echo "🤖 [3/3] Starting Telegram AI Assistant (@bamquantforgebot)..."
PYTHONPATH=.:src PYTHONUNBUFFERED=1 nohup "$PYTHON" tools/run_telegram_assistant.py > logs/telegram.log 2>&1 &
echo $! > logs/telegram.pid

sleep 2

echo "=================================================================="
echo "✅ All QuantForge Services Successfully Online & Synced!"
echo "• MT5 Live Bridge : http://127.0.0.1:8765/v1/mt5/snapshots"
echo "• Web Cockpit     : http://127.0.0.1:8080"
echo "• Telegram Bot    : @bamquantforgebot"
echo "• Logs Directory  : $PROJECT_DIR/logs/"
echo "=================================================================="
