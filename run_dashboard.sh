#!/bin/bash
# QuantForge Visual Paper Trading Studio Launcher
cd "$(dirname "$0")"
echo "Starting QuantForge Studio on http://127.0.0.1:8080..."
open "http://127.0.0.1:8080" 2>/dev/null || true
PYTHONPATH=.:src .venv/bin/python tools/paper_dashboard.py 8080
