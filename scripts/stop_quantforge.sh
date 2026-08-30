#!/bin/bash
# QuantForge Stop Script
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🛑 Stopping all QuantForge services..."
pkill -9 -f "run_candidate_007_mt5_live_bridge" 2>/dev/null || true
pkill -9 -f "paper_dashboard.py" 2>/dev/null || true
pkill -9 -f "run_telegram_assistant.py" 2>/dev/null || true
kill -9 $(lsof -t -i :8765) 2>/dev/null || true
kill -9 $(lsof -t -i :8080) 2>/dev/null || true
rm -f logs/*.pid
echo "✅ All QuantForge services stopped."
