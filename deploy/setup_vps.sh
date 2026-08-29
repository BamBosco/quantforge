#!/usr/bin/env bash
# ==============================================================================
# QuantForge Studio — Automated 24/7 Linux VPS Deployment Script
# Supports Ubuntu 22.04 / 24.04 LTS
# ==============================================================================
set -e

echo "🚀 Starting QuantForge 24/7 VPS Deployment..."

# 1. Update system & install Python 3.12, git, sqlite3, curl
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv git sqlite3 curl build-essential

# 2. Setup Virtual Environment
PROJECT_DIR="$(pwd)"
echo "📦 Setting up Python Virtual Environment in ${PROJECT_DIR}..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# 3. Create Systemd Service for Bridge (Port 8765)
echo "⚙️ Creating QuantForge Bridge 24/7 Daemon Service..."
sudo bash -c "cat << 'SERVICE' > /etc/systemd/system/quantforge-bridge.service
[Unit]
Description=QuantForge Autonomous MT5 Live Bridge
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
Environment=\"PYTHONPATH=.:src\"
ExecStart=${PROJECT_DIR}/.venv/bin/python tools/run_candidate_007_mt5_live_bridge.py --port 8765 --auto-exec --balance 30.0 --symbol XAUUSD
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE"

# 4. Create Systemd Service for Web Dashboard (Port 8080)
echo "⚙️ Creating QuantForge Web Dashboard 24/7 Daemon Service..."
sudo bash -c "cat << 'SERVICE' > /etc/systemd/system/quantforge-dashboard.service
[Unit]
Description=QuantForge Studio Web Dashboard
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
Environment=\"PYTHONPATH=.:src\"
ExecStart=${PROJECT_DIR}/.venv/bin/python tools/paper_dashboard.py 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE"

# 5. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable quantforge-bridge
sudo systemctl enable quantforge-dashboard
sudo systemctl restart quantforge-bridge
sudo systemctl restart quantforge-dashboard

echo "================================================================="
echo "🎉 QUANTFORGE 24/7 VPS DEPLOYMENT COMPLETED!"
echo "================================================================="
echo "• Web Dashboard live at: http://$(curl -s ifconfig.me):8080"
echo "• MT5 Bridge running on: http://127.0.0.1:8765"
echo "• Status Check         : sudo systemctl status quantforge-bridge"
echo "================================================================="
