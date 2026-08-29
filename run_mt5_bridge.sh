#!/bin/bash
set -e

# Change to project root directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "======================================================="
echo "  🚀 Starting QuantForge MT5 Live Bridge (BTCUSD/XAUUSD)"
echo "======================================================="

# Run the live bridge runner
PYTHONPATH=.:src .venv/bin/python tools/run_candidate_007_mt5_live_bridge.py --port 8765 "$@"
