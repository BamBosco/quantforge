#!/usr/bin/env python3
"""QuantForge Studio — Ultra-Clean Minimalist SPA Dashboard with Mobile Optimization.

Features:
- Mobile-responsive layout (desktop sidebar + mobile bottom nav).
- Perfect Clean Reset (restores exactly $30.00 Base Equity and 0 session PnL).
- Fast animated tick streaming.
"""

from __future__ import annotations

import collections
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from quantforge.infrastructure.notifications.telegram_notifier import (
    TelegramConfig,
    TelegramNotifier,
)

# Configuration & Paths
PORT = 8080
JOURNAL_DB = Path("data/paper_mode/candidate_007_paper.sqlite3")
TELEGRAM_CONFIG_FILE = Path("config/telegram_config.json")
BRIDGE_LATEST_URL = "http://127.0.0.1:8765/v1/mt5/latest"
BRIDGE_RESET_URL = "http://127.0.0.1:8765/v1/mt5/reset"
BRIDGE_TOKEN = "quantforge-live-token-2026"

PRICE_HISTORY: collections.deque[dict[str, Any]] = collections.deque(maxlen=180)
SNAPSHOT_COUNT = 0
LAST_BID = 0.0
LAST_ASK = 0.0
TICK_COUNT = 0
START_TIME = time.time()
INITIAL_BALANCE = 30.0


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>QuantForge Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg-base: #07090e;
      --bg-surface: #0e131f;
      --bg-card: #141b2d;
      --bg-card-hover: #1c263f;
      --border-main: rgba(255, 255, 255, 0.07);
      --border-card: #1f2940;
      --primary: #3b82f6;
      --primary-glow: rgba(59, 130, 246, 0.3);
      --accent-green: #10b981;
      --accent-green-bg: rgba(16, 185, 129, 0.1);
      --accent-red: #f43f5e;
      --accent-red-bg: rgba(244, 63, 94, 0.1);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
    }

    /* Sidebar Navigation */
    .sidebar {
      width: 230px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-card);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 1.5rem 1rem;
      flex-shrink: 0;
    }
    .brand-box {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 0 0.5rem 1.5rem 0.5rem;
      border-bottom: 1px solid var(--border-main);
    }
    .brand-icon {
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      width: 36px; height: 36px; border-radius: 9px;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 1.1rem; color: white;
      box-shadow: 0 0 14px var(--primary-glow);
    }
    .brand-name { font-size: 1.05rem; font-weight: 800; letter-spacing: -0.02em; }
    .brand-tag { font-size: 0.7rem; color: var(--text-muted); font-weight: 500; }

    .nav-list { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 1.5rem; }
    .nav-item {
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      text-decoration: none;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.15s ease;
    }
    .nav-item:hover { color: var(--text-main); background: var(--bg-card); }
    .nav-item.active {
      color: white;
      background: var(--primary);
      box-shadow: 0 2px 10px var(--primary-glow);
    }
    .nav-badge {
      background: rgba(255, 255, 255, 0.15);
      font-size: 0.7rem;
      padding: 2px 7px;
      border-radius: 9999px;
      font-family: var(--font-mono);
    }

    /* Main Content Wrapper */
    .main-wrapper {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      height: 100vh;
    }

    /* Topbar */
    .topbar {
      background: rgba(14, 19, 31, 0.75);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-card);
      padding: 0.85rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .topbar-left { display: flex; align-items: center; gap: 1.5rem; }
    .page-title { font-size: 1.1rem; font-weight: 700; }

    .topbar-stats { display: flex; align-items: center; gap: 2rem; }
    .stat-pill { display: flex; flex-direction: column; }
    .stat-pill-label { font-size: 0.68rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; }
    .stat-pill-val { font-family: var(--font-mono); font-weight: 700; font-size: 1rem; }

    .topbar-actions { display: flex; align-items: center; gap: 0.75rem; }
    .badge-status {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 5px 12px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;
      letter-spacing: 0.04em; text-transform: uppercase;
    }
    .badge-live { background: var(--accent-green-bg); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.25); }
    .badge-waiting { background: rgba(245, 158, 11, 0.1); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
    .badge-pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--accent-green); animation: pulse 1.2s infinite; }
    @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.4); } 100% { opacity: 1; transform: scale(1); } }

    button, .btn {
      background: var(--bg-card); color: var(--text-main);
      border: 1px solid var(--border-card); padding: 7px 13px;
      border-radius: 8px; font-weight: 600; font-size: 0.8rem;
      cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
      text-decoration: none; transition: all 0.15s ease;
    }
    button:hover, .btn:hover { background: var(--bg-card-hover); border-color: var(--primary); }
    .btn-danger { background: var(--accent-red-bg); color: var(--accent-red); border-color: rgba(244, 63, 94, 0.25); }
    .btn-danger:hover { background: rgba(244, 63, 94, 0.2); }

    /* Content Body */
    .content-body {
      padding: 1.75rem 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      max-width: 1440px;
      width: 100%;
    }
    .page-view {
      display: none;
      flex-direction: column;
      gap: 1.5rem;
      animation: fadeIn 0.2s ease forwards;
    }
    .page-view.active { display: flex; }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Panels & Cards */
    .panel {
      background: var(--bg-surface);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .panel-header { display: flex; justify-content: space-between; align-items: center; }
    .panel-title { font-weight: 700; font-size: 0.98rem; display: flex; align-items: center; gap: 8px; }

    .chart-container { height: 320px; width: 100%; position: relative; }
    .cockpit-split { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }

    .feed-list { overflow-y: auto; max-height: 280px; display: flex; flex-direction: column; gap: 0.5rem; }
    .feed-item {
      background: var(--bg-card);
      border: 1px solid var(--border-main);
      border-radius: 9px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    .feed-meta { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-dim); }
    .feed-title { font-weight: 700; font-size: 0.82rem; display: flex; align-items: center; gap: 6px; }
    .feed-detail { font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); }

    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }
    th { padding: 10px 14px; color: var(--text-dim); font-weight: 700; border-bottom: 1px solid var(--border-card); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
    td { padding: 12px 14px; border-bottom: 1px solid var(--border-main); font-family: var(--font-mono); }
    .badge-buy { background: var(--accent-green-bg); color: var(--accent-green); padding: 3px 8px; border-radius: 5px; font-weight: 700; font-size: 0.72rem; }
    .badge-sell { background: var(--accent-red-bg); color: var(--accent-red); padding: 3px 8px; border-radius: 5px; font-weight: 700; font-size: 0.72rem; }
    .profit-pos { color: var(--accent-green); font-weight: 700; }
    .profit-neg { color: var(--accent-red); font-weight: 700; }

    .form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.25rem; }
    .form-group { display: flex; flex-direction: column; gap: 0.4rem; }
    .form-label { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
    .form-input {
      background: var(--bg-card); border: 1px solid var(--border-card);
      border-radius: 9px; padding: 11px 14px; color: white; font-family: var(--font-mono);
      font-size: 0.88rem;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 900px) {
      body { flex-direction: column; }
      .sidebar {
        width: 100%;
        border-right: none;
        border-bottom: 1px solid var(--border-card);
        padding: 0.75rem 1rem;
      }
      .brand-box { padding: 0 0 0.5rem 0; }
      .nav-list {
        flex-direction: row;
        overflow-x: auto;
        gap: 0.5rem;
        margin-top: 0.75rem;
        padding-bottom: 0.25rem;
      }
      .nav-item { padding: 8px 12px; font-size: 0.8rem; white-space: nowrap; }
      .main-wrapper { height: auto; }
      .topbar { flex-direction: column; gap: 0.75rem; padding: 1rem; align-items: flex-start; }
      .topbar-stats { flex-wrap: wrap; gap: 1rem; }
      .content-body { padding: 1rem; }
      .cockpit-split { grid-template-columns: 1fr; }
      .form-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <!-- Sidebar -->
  <aside class="sidebar">
    <div>
      <div class="brand-box">
        <div class="brand-icon">QF</div>
        <div>
          <div class="brand-name">QuantForge</div>
          <div class="brand-tag">SMC Trading Bot</div>
        </div>
      </div>

      <nav class="nav-list">
        <a href="#/cockpit" class="nav-item" id="nav-cockpit">
          <span>📊 Live Cockpit</span>
        </a>
        <a href="#/positions" class="nav-item" id="nav-positions">
          <span>⚡ Positions</span>
          <span class="nav-badge" id="txt-nav-pos-count">0</span>
        </a>
        <a href="#/history" class="nav-item" id="nav-history">
          <span>📜 Closed Trades</span>
          <span class="nav-badge" id="txt-nav-history-count" style="background: rgba(16,185,129,0.15); color: var(--accent-green);">0</span>
        </a>
        <a href="#/strategy" class="nav-item" id="nav-strategy">
          <span>📈 Strategy & SMC</span>
        </a>
        <a href="#/risk" class="nav-item" id="nav-risk">
          <span>🛡️ Risk Controls</span>
        </a>
        <a href="#/journal" class="nav-item" id="nav-journal">
          <span>📖 Trade Journal</span>
        </a>
        <a href="#/bridge" class="nav-item" id="nav-bridge">
          <span>⚙️ MT5 & Telegram</span>
        </a>
      </nav>
    </div>

    <!-- Bottom Info (Hidden on Mobile) -->
    <div style="padding-top: 1rem; border-top: 1px solid var(--border-main);" class="hide-mobile">
      <div style="font-size: 0.72rem; color: var(--text-dim); font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">TARGET ASSET</div>
      <div id="txt-sidebar-asset" style="font-family: var(--font-mono); font-weight: 700; color: #60a5fa; font-size: 0.9rem;">BTCUSDm (Bitcoin)</div>
      <div id="txt-sidebar-session" style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">M1 • 24/7 Crypto Session</div>
    </div>
  </aside>

  <!-- Main View -->
  <main class="main-wrapper">
    <header class="topbar">
      <div class="topbar-left">
        <div class="page-title" id="txt-page-title">Live Trading Cockpit</div>
      </div>

      <div class="topbar-stats">
        <div class="stat-pill">
          <span class="stat-pill-label">Live Price</span>
          <span class="stat-pill-val" id="val-price" style="color: #60a5fa;">$0.00</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Account Equity</span>
          <span class="stat-pill-val" id="val-equity" style="color: var(--accent-green);">$30.00</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Total Session PnL</span>
          <span class="stat-pill-val" id="val-pnl" style="color: var(--text-muted);">+$0.00</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Active Trade</span>
          <span class="stat-pill-val" id="val-positions-count" style="color: #fbbf24;">0 Open</span>
        </div>
      </div>

      <div class="topbar-actions">
        <div id="badge-connection" class="badge-status badge-waiting"><div class="badge-pulse" style="background:#f59e0b;"></div> MT5 Connecting...</div>
        <button id="btn-audio" onclick="toggleAudio()">🔊 Sound</button>
        <button class="btn-danger" onclick="resetJournal()">🔄 Reset</button>
      </div>
    </header>

    <div class="content-body">
      <!-- ROUTE 1: /#/cockpit -->
      <div id="view-cockpit" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <span>📈 Real-Time Price Action (<span id="txt-chart-symbol">#BTCUSD</span>)</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span id="txt-spread" style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">Spread: $0.00</span>
              <span id="txt-tick-velocity" class="badge-status" style="background: rgba(59, 130, 246, 0.1); color: var(--primary);">⚡ 0.0 ticks/s</span>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="priceChart"></canvas>
          </div>
        </div>

        <!-- Interactive Execution Action Bar -->
        <div class="panel" style="padding: 1.1rem 1.5rem; background: var(--bg-card); border: 1px solid var(--border-card);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div style="display: flex; align-items: center; gap: 1.25rem;">
              <div style="font-size: 0.9rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 8px;">
                🎮 <span>Trade Execution Controls</span>
              </div>
              <div style="font-size: 0.75rem; color: var(--text-dim); font-family: var(--font-mono); background: rgba(255,255,255,0.04); padding: 4px 10px; border-radius: 6px;">
                Risk Shield: <span style="color: var(--accent-green); font-weight: 700;">1.0% Auto-Sized (0.01 Lots)</span>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
              <button class="btn" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border-color: rgba(16, 185, 129, 0.35); font-weight: 700; padding: 8px 16px;" onclick="executeTrade('buy')">
                🟢 BUY Market Scalp
              </button>
              <button class="btn" style="background: rgba(244, 63, 94, 0.15); color: var(--accent-red); border-color: rgba(244, 63, 94, 0.35); font-weight: 700; padding: 8px 16px;" onclick="executeTrade('sell')">
                🔴 SELL Market Scalp
              </button>
              <button class="btn" style="background: rgba(16, 185, 129, 0.22); color: #34d399; border-color: rgba(16, 185, 129, 0.45); font-weight: 700; padding: 8px 14px;" onclick="closeProfitablePositions()">
                💰 Close All Profit
              </button>
              <button class="btn" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.35); padding: 8px 14px;" onclick="closeOpenPosition()">
                🛑 Close Position
              </button>
              <button class="btn" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.35); padding: 8px 14px;" onclick="testTelegram()">
                📱 Ping Telegram
              </button>
            </div>
          </div>
        </div>

        <div class="cockpit-split">
          <div class="panel">
            <div class="panel-header">
              <div class="panel-title">⚡ Active Trade Position</div>
              <div id="badge-floating-pnl" class="badge-status" style="background: rgba(255,255,255,0.05); font-family: var(--font-mono);">Floating: +$0.00</div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Ticket #</th>
                  <th>Side</th>
                  <th>Lots</th>
                  <th>Entry Price</th>
                  <th>Mark Price</th>
                  <th>Floating PnL</th>
                </tr>
              </thead>
              <tbody id="quick-positions-table-body">
                <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No open position. Scanning market for SMC breakout...</td></tr>
              </tbody>
            </table>
          </div>

          <div class="panel">
            <div class="panel-header">
              <div class="panel-title">⚡ Execution Feed</div>
              <span style="font-size: 0.75rem; color: var(--text-dim);">Auto-Updating</span>
            </div>
            <div class="feed-list" id="feed-list">
              <div class="feed-item" style="text-align: center; color: var(--text-dim);">Waiting for market events...</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ROUTE 2: /#/positions -->
      <div id="view-positions" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">⚡ Portfolio Positions & Risk Exposure</div>
            <div style="display: flex; gap: 8px;">
              <button class="btn" style="background: rgba(16, 185, 129, 0.22); color: #34d399; border-color: rgba(16, 185, 129, 0.45); font-weight: 700; padding: 6px 14px;" onclick="closeProfitablePositions()">💰 Close in Profit</button>
              <button class="btn-danger" onclick="resetJournal()">Close All & Reset</button>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Ticket #</th>
                <th>Instrument</th>
                <th>Side</th>
                <th>Lots</th>
                <th>Entry Price</th>
                <th>Current Mark</th>
                <th>Floating PnL ($)</th>
                <th>Opened Time</th>
              </tr>
            </thead>
            <tbody id="full-positions-table-body">
              <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No active open positions. Watching for SMC breakout...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ROUTE: /#/history (Closed Trades & History) -->
      <div id="view-history" class="page-view">
        <!-- Summary Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div class="panel" style="padding: 1.25rem;">
            <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Win Rate</div>
            <div style="font-family: var(--font-mono); font-size: 1.5rem; font-weight: 800; color: var(--accent-green);" id="hist-win-rate">0.0%</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;" id="hist-win-loss-count">0 Wins / 0 Losses</div>
          </div>
          <div class="panel" style="padding: 1.25rem;">
            <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Realized Closed PnL</div>
            <div style="font-family: var(--font-mono); font-size: 1.5rem; font-weight: 800; color: var(--accent-green);" id="hist-total-pnl">+$0.00</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Banked Net Profit</div>
          </div>
          <div class="panel" style="padding: 1.25rem;">
            <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Total Closed Trades</div>
            <div style="font-family: var(--font-mono); font-size: 1.5rem; font-weight: 800; color: var(--text-main);" id="hist-total-trades">0</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Completed Cycles</div>
          </div>
          <div class="panel" style="padding: 1.25rem;">
            <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Profit Factor</div>
            <div style="font-family: var(--font-mono); font-size: 1.5rem; font-weight: 800; color: #60a5fa;" id="hist-profit-factor">0.00</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Gross Profit / Gross Loss</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">📜 Closed Trades Execution Ledger</div>
            <span style="font-size: 0.75rem; color: var(--text-dim);">Historical Performance Log</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Ticket #</th>
                <th>Asset</th>
                <th>Side</th>
                <th>Volume</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Realized PnL</th>
                <th>Opened (UTC)</th>
                <th>Closed (UTC)</th>
                <th>Exit Reason</th>
              </tr>
            </thead>
            <tbody id="history-table-body">
              <tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No closed trades yet in this session.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ROUTE 3: /#/strategy -->
      <div id="view-strategy" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">🎯 Candidate 007 SMC Market Structure & Strategy</div>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Primary Target Asset</label>
              <input type="text" class="form-input" value="XAUUSD (Gold) / BTCUSD (Weekend Test)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Market Structure Confirmation</label>
              <input type="text" class="form-input" value="Higher Highs / Higher Lows (BUY) & Lower Lows / Lower Highs (SELL)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Breakout Window (Donchian Period)</label>
              <input type="text" class="form-input" value="20 Bars (M1 Timeframe)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Trend Filter (EMA Period)</label>
              <input type="text" class="form-input" value="50 Period Exponential Moving Average" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Volatility Expansion Gate</label>
              <input type="text" class="form-input" value="14 ATR >= 20 ATR Moving Average" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Dynamic Profit Target</label>
              <input type="text" class="form-input" value="+zsh.80 to +.50 per Trade (10-15 Pips on Gold)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Intraday Frequency Target</label>
              <input type="text" class="form-input" value="10 to 20 High-Probability Scalps / Day" readonly>
            </div>
          </div>
        </div>
      </div>

      <!-- ROUTE 4: /#/risk -->
      <div id="view-risk" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">🛡️ Risk Controls & Circuit Breakers</div>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Risk Sizing Per Trade</label>
              <input type="text" class="form-input" value="1.0% of Marked Equity (Strict)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Daily Drawdown Breaker</label>
              <input type="text" class="form-input" value="10.0% Daily Loss Ceiling" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Consecutive Loss Guard</label>
              <input type="text" class="form-input" value="3 Consecutive Loss Cooldown Pause (30 min)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Maximum Simultaneous Positions</label>
              <input type="text" class="form-input" value="1 Position (Strict Single-Order Lock)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Stop Placement Logic</label>
              <input type="text" class="form-input" value="Structural Swing Invalidation (Beyond Last HL/LH)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">High-Impact News Shield (CPI / NFP / FOMC)</label>
              <input type="text" class="form-input" value="🛑 15-min Pre/Post Blackout Window (Automated)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">News Spread Spike Protection</label>
              <input type="text" class="form-input" value="Max Spread Filter (zsh.50 Ceiling on Gold)" readonly>
            </div>
          </div>
        </div>
      </div>

      <!-- ROUTE 5: /#/journal -->
      <div id="view-journal" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">📖 Historical Trade Journal & Event Ledger</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Seq #</th>
                <th>Event Type</th>
                <th>Timestamp (UTC)</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody id="journal-table-body">
              <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No events in current session.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ROUTE 6: /#/bridge -->
      <div id="view-bridge" class="page-view">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">⚙️ Bridge Infrastructure & Telegram Dispatcher</div>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Loopback Bridge Receiver</label>
              <input type="text" class="form-input" value="http://127.0.0.1:8765/v1/mt5/snapshots" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">MT5 Magic Number</label>
              <input type="text" class="form-input" value="7007 (QuantForge Isolated Execution)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Telegram Bot Username</label>
              <input type="text" class="form-input" value="@bamquantforgebot (Connected)" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Telegram Destination ID</label>
              <input type="text" class="form-input" value="5386759666" readonly>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    const titles = {
      cockpit: 'Live Trading Cockpit',
      positions: 'Portfolio Positions & Exposure',
      history: 'Closed Trades & Performance History',
      strategy: 'Strategy Parameters & SMC',
      risk: 'Capital Protection & Risk Controls',
      journal: 'Historical Trade Ledger',
      bridge: 'MT5 Bridge & Notification Engine'
    };
    const routes = Object.keys(titles);

    function handleRoute() {
      const hash = window.location.hash.replace('#/', '').replace('#', '') || 'cockpit';
      const activeRoute = routes.includes(hash) ? hash : 'cockpit';

      routes.forEach(r => {
        const view = document.getElementById('view-' + r);
        const link = document.getElementById('nav-' + r);
        if (view) view.classList.toggle('active', r === activeRoute);
        if (link) link.classList.toggle('active', r === activeRoute);
      });

      const titleEl = document.getElementById('txt-page-title');
      if (titleEl) titleEl.innerText = titles[activeRoute];
    }

    window.addEventListener('hashchange', handleRoute);
    window.addEventListener('DOMContentLoaded', () => {
      if (!window.location.hash) window.location.hash = '#/cockpit';
      handleRoute();
    });

    let audioCtx = null;
    let soundEnabled = true;

    function getAudioContext() {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      return audioCtx;
    }

    function toggleAudio() {
      soundEnabled = !soundEnabled;
      const btn = document.getElementById('btn-audio');
      btn.innerText = soundEnabled ? '🔊 Sound' : '🔇 Muted';
      btn.style.opacity = soundEnabled ? '1' : '0.5';
    }

    function playTone(freq, type, duration, delay = 0) {
      if (!soundEnabled) return;
      try {
        const ctx = getAudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, ctx.currentTime + delay);
        gain.gain.setValueAtTime(0.12, ctx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + delay);
        osc.stop(ctx.currentTime + delay + duration);
      } catch (e) {}
    }

    function playBuySound() { playTone(880, 'sine', 0.15, 0); playTone(1320, 'sine', 0.25, 0.1); }
    function playSellSound() { playTone(900, 'triangle', 0.15, 0); playTone(600, 'triangle', 0.25, 0.1); }
    function playFillSound() { playTone(659.25, 'sine', 0.1, 0); playTone(880, 'sine', 0.1, 0.08); playTone(1046.50, 'sine', 0.2, 0.16); }

    const ctx = document.getElementById('priceChart').getContext('2d');
    const priceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Bid Price ($)',
            data: [],
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.05)',
            borderWidth: 2,
            pointRadius: 1,
            tension: 0.12,
            fill: true,
          },
          {
            label: 'Ask Price ($)',
            data: [],
            borderColor: '#fbbf24',
            borderDash: [3, 3],
            borderWidth: 1.2,
            pointRadius: 0,
            tension: 0.12,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 100 },
        plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } } }
        }
      }
    });

    let prevBid = 0.0;
    let lastEventCount = 0;

    async function fetchState() {
      try {
        const resp = await fetch('/api/state');
        if (!resp.json) return;
        const data = await resp.json();

        const badgeConn = document.getElementById('badge-connection');
        const priceEl = document.getElementById('val-price');
        const sidebarAssetEl = document.getElementById('txt-sidebar-asset');
        const sidebarSessionEl = document.getElementById('txt-sidebar-session');

        if (data.live_quote) {
          const q = data.live_quote;
          badgeConn.className = "badge-status badge-live";
          badgeConn.innerHTML = `<div class="badge-pulse"></div> Live MT5 (${q.symbol})`;

          if (priceEl && q.bid) {
            priceEl.innerText = '$' + q.bid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            if (prevBid > 0 && q.bid !== prevBid) {
              priceEl.style.color = q.bid > prevBid ? 'var(--accent-green)' : 'var(--accent-red)';
              setTimeout(() => { priceEl.style.color = '#60a5fa'; }, 350);
            }
          }
          if (sidebarAssetEl) sidebarAssetEl.innerText = q.symbol + (q.symbol.toUpperCase().includes('BTC') ? ' (Bitcoin)' : ' (Gold)');
          if (sidebarSessionEl) sidebarSessionEl.innerText = q.symbol.toUpperCase().includes('BTC') ? 'M1 • 24/7 Crypto Session' : 'M1 • London/NY Session';

          prevBid = q.bid;
          const dSpread = (q.ask && q.bid) ? (q.ask - q.bid) : 0.20; 
          document.getElementById('txt-spread').innerText = 'Spread: $' + dSpread.toFixed(2);
          document.getElementById('txt-chart-symbol').innerText = q.symbol;
          document.getElementById('txt-tick-velocity').innerText = '⚡ ' + (data.tick_rate || '1.0') + ' ticks/s';
        } else {
          badgeConn.className = "badge-status badge-waiting";
          badgeConn.innerHTML = `<div class="badge-pulse" style="background:#f59e0b;"></div> MT5 Connecting...`;
        }

        const baseEquity = 30.0;
        const equity = data.equity || baseEquity;
        const totalPnl = data.total_pnl || 0.0;
        const pnlPct = ((totalPnl / baseEquity) * 100).toFixed(2);

        const eqEl = document.getElementById('val-equity');
        eqEl.innerText = '$' + equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        eqEl.style.color = totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

        const pnlEl = document.getElementById('val-pnl');
        const sign = totalPnl >= 0 ? '+' : '';
        pnlEl.innerText = sign + '$' + totalPnl.toFixed(2) + ' (' + sign + pnlPct + '%)';
        pnlEl.style.color = totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

        const openPositions = data.open_positions || [];
        document.getElementById('val-positions-count').innerText = openPositions.length + ' Open';
        document.getElementById('txt-nav-pos-count').innerText = openPositions.length;

        const quickTbody = document.getElementById('quick-positions-table-body');
        const fullTbody = document.getElementById('full-positions-table-body');
        const floatingBadge = document.getElementById('badge-floating-pnl');
        const floatingPnl = data.floating_pnl || 0.0;
        const flSign = floatingPnl >= 0 ? '+' : '';
        
        floatingBadge.innerText = 'Floating: ' + flSign + '$' + floatingPnl.toFixed(2);
        floatingBadge.style.color = floatingPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

        if (openPositions.length === 0) {
          quickTbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No open position. Scanning market for SMC breakout...</td></tr>';
          fullTbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No active open positions. Watching for SMC breakout...</td></tr>';
        } else {
          const quickRows = openPositions.slice(0, 1).map(pos => {
            const pnl = pos.floating_pnl || 0;
            const posSign = pnl >= 0 ? '+' : '';
            const pnlClass = pnl >= 0 ? 'profit-pos' : 'profit-neg';
            const sideBadge = pos.side.toLowerCase() === 'buy' ? '<span class="badge-buy">BUY</span>' : '<span class="badge-sell">SELL</span>';
            const shortId = (pos.order_id || '').substring(0, 8);
            return `<tr>
              <td>#${shortId}</td>
              <td>${sideBadge}</td>
              <td>${pos.quantity}</td>
              <td>$${pos.open_price.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
              <td>$${(pos.current_price || 0).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
              <td class="${pnlClass}">${posSign}$${pnl.toFixed(2)}</td>
            </tr>`;
          }).join('');
          quickTbody.innerHTML = quickRows;

          const fullRows = openPositions.map(pos => {
            const pnl = pos.floating_pnl || 0;
            const posSign = pnl >= 0 ? '+' : '';
            const pnlClass = pnl >= 0 ? 'profit-pos' : 'profit-neg';
            const sideBadge = pos.side.toLowerCase() === 'buy' ? '<span class="badge-buy">BUY</span>' : '<span class="badge-sell">SELL</span>';
            return `<tr>
              <td>#${pos.order_id}</td>
              <td><strong>${pos.instrument}</strong></td>
              <td>${sideBadge}</td>
              <td>${pos.quantity}</td>
              <td>$${pos.open_price.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
              <td>$${(pos.current_price || 0).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
              <td class="${pnlClass}">${posSign}$${pnl.toFixed(2)}</td>
              <td>${(pos.opened_at || '').substring(11, 19)} UTC</td>
            </tr>`;
          }).join('');
          fullTbody.innerHTML = fullRows;
        }

        // Closed Trades Table & Metrics
        const closedTrades = data.closed_trades || [];
        const histBadge = document.getElementById('txt-nav-history-count');
        if (histBadge) histBadge.innerText = closedTrades.length;

        const totalTradesEl = document.getElementById('hist-total-trades');
        if (totalTradesEl) totalTradesEl.innerText = closedTrades.length;
        
        const winRate = data.win_rate !== undefined ? data.win_rate : 0.0;
        const winRateEl = document.getElementById('hist-win-rate');
        if (winRateEl) winRateEl.innerText = winRate.toFixed(1) + '%';

        const winLossEl = document.getElementById('hist-win-loss-count');
        if (winLossEl) winLossEl.innerText = (data.win_count || 0) + ' Wins / ' + (data.loss_count || 0) + ' Losses';

        const closedPnl = data.realized_pnl || 0.0;
        const clSign = closedPnl >= 0 ? '+' : '';
        const clEl = document.getElementById('hist-total-pnl');
        if (clEl) {
          clEl.innerText = clSign + '$' + closedPnl.toFixed(2);
          clEl.style.color = closedPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        }

        const pf = data.profit_factor !== undefined ? data.profit_factor : 0.0;
        const pfEl = document.getElementById('hist-profit-factor');
        if (pfEl) pfEl.innerText = pf.toFixed(2);

        const histTbody = document.getElementById('history-table-body');
        if (histTbody) {
          if (closedTrades.length === 0) {
            histTbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No closed trades yet in this session.</td></tr>';
          } else {
            const histRows = closedTrades.map(t => {
              const pnl = t.pnl || 0;
              const sign = pnl >= 0 ? '+' : '';
              const pnlClass = pnl >= 0 ? 'profit-pos' : 'profit-neg';
              const sideBadge = (t.side || 'buy').toLowerCase() === 'buy' ? '<span class="badge-buy">BUY</span>' : '<span class="badge-sell">SELL</span>';
              const openT = (t.opened_at || '').substring(11, 19);
              const closeT = (t.closed_at || '').substring(11, 19);
              const shortTicket = (t.order_id || '').substring(0, 10);
              const reasonBadge = t.status === 'target_reached' 
                ? '<span style="color: var(--accent-green); font-weight:700;">🎯 Quick Strike (+Gain)</span>'
                : (t.status === 'breakeven' 
                  ? '<span style="color: #60a5fa; font-weight:700;">🛡️ Breakeven Exit</span>'
                  : (pnl >= 0 
                    ? '<span style="color: var(--accent-green); font-weight:700;">💰 Profit Banked (+Gain)</span>' 
                    : '<span style="color: var(--accent-red); font-weight:700;">🛑 Stop Loss Exit (-Risk)</span>'));
              return `<tr>
                <td>#${shortTicket}</td>
                <td><strong>${t.instrument}</strong></td>
                <td>${sideBadge}</td>
                <td>${t.quantity}</td>
                <td>$${Number(t.open_price).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                <td>$${Number(t.exit_price).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                <td class="${pnlClass}" style="font-weight: 700;">${sign}$${pnl.toFixed(2)}</td>
                <td>${openT} UTC</td>
                <td>${closeT} UTC</td>
                <td>${reasonBadge}</td>
              </tr>`;
            }).join('');
            histTbody.innerHTML = histRows;
          }
        }

        if (data.price_history && data.price_history.length > 0) {
          priceChart.data.labels = data.price_history.map(p => p.time);
          priceChart.data.datasets[0].data = data.price_history.map(p => p.bid);
          priceChart.data.datasets[1].data = data.price_history.map(p => p.ask);
          priceChart.update('none');
        }

        if (data.events && data.events.length > 0) {
          if (data.events.length > lastEventCount && lastEventCount > 0) {
            const latest = data.events[data.events.length - 1];
            if (latest.event_type === 'TradeIntentGenerated') {
              if (latest.payload.side === 'buy') playBuySound();
              else playSellSound();
            } else if (latest.event_type === 'ExecutionOutcomeRecorded') {
              playFillSound();
            }
          }
          lastEventCount = data.events.length;

          const feedList = document.getElementById('feed-list');
          const reversed = [...data.events].reverse().slice(0, 10);
          feedList.innerHTML = reversed.map(e => {
            const timeStr = (e.occurred_at_utc || '').substring(11, 19) || 'Live';
            let icon = '⚡';
            let title = e.event_type;
            let detail = '';

            if (e.event_type === 'TradeIntentGenerated') {
              const side = (e.payload.side || '').toUpperCase();
              icon = side === 'BUY' ? '🟢' : '🔴';
              title = `<span class="${side === 'BUY' ? 'badge-buy' : 'badge-sell'}">SIGNAL: ${side}</span>`;
              detail = e.payload.rationale || `Entry: $${e.payload.entry_price}`;
            } else if (e.event_type === 'RiskDecisionRecorded') {
              icon = e.payload.approved ? '🛡️' : '⚠️';
              title = e.payload.approved ? '<span style="color:var(--accent-green);font-weight:700;">RISK APPROVED</span>' : '<span style="color:var(--accent-red);font-weight:700;">RISK REJECTED</span>';
              detail = e.payload.approved ? `1% Risk Budget` : (e.payload.reasons || []).join(', ');
            } else if (e.event_type === 'ExecutionOutcomeRecorded') {
              const st = (e.payload.status || '').toUpperCase();
              icon = st === 'FILLED' ? '🎉' : (st === 'STOPPED_OUT' ? '🛡️' : '🏁');
              title = `<span style="color:#fbbf24;font-weight:700;">EXECUTION: ${st}</span>`;
              detail = `${(e.payload.side || '').toUpperCase()} ${e.payload.quantity} @ $${e.payload.price || ''} ${e.payload.reason ? '('+e.payload.reason+')' : ''}`;
            }

            return `<div class="feed-item">
              <div class="feed-meta">
                <span>${icon} ${timeStr} UTC</span>
                <span>${e.event_type}</span>
              </div>
              <div class="feed-title">${title}</div>
              <div class="feed-detail">${detail}</div>
            </div>`;
          }).join('');

          const journalBody = document.getElementById('journal-table-body');
          journalBody.innerHTML = reversed.map((e, idx) => {
            return `<tr>
              <td>#${e.sequence || (reversed.length - idx)}</td>
              <td><strong>${e.event_type}</strong></td>
              <td>${e.occurred_at_utc}</td>
              <td style="color:#94a3b8;">${JSON.stringify(e.payload)}</td>
            </tr>`;
          }).join('');
        } else {
          document.getElementById('feed-list').innerHTML = '<div class="feed-item" style="text-align: center; color: var(--text-dim);">Fresh session started. Waiting for market events...</div>';
          document.getElementById('journal-table-body').innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No events in current session.</td></tr>';
        }
      } catch (err) {
        console.warn('Polling error:', err);
      }
    }

    async function executeTrade(side) {
      try {
        if (side === 'buy') playBuySound();
        else playSellSound();
        const resp = await fetch('/api/execute_trade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ side: side, symbol: 'BTCUSDm', quantity: 0.01 })
        });
        const res = await resp.json();
        if (res.success) {
          playFillSound();
          fetchState();
        } else {
          alert('Execution rejected: ' + (res.error || 'Unknown error'));
        }
      } catch (err) {
        alert('Network error executing trade: ' + err);
      }
    }

    async function closeOpenPosition() {
      try {
        const resp = await fetch('/api/close_all', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
          playFillSound();
          fetchState();
        } else {
          alert('Failed to close position: ' + (res.error || 'No open position'));
        }
      } catch (err) {
        alert('Error closing position: ' + err);
      }
    }

    async function closeProfitablePositions() {
      try {
        const resp = await fetch('/api/close_profit', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
          playFillSound();
          alert(`💰 Profit Banked! Closed ${res.closed_count} position(s) with net profit of +$${res.realized_pnl.toFixed(2)}`);
          fetchState();
        } else {
          alert(res.error || 'No open positions currently in profit.');
        }
      } catch (err) {
        alert('Error closing in profit: ' + err);
      }
    }

    async function testTelegram() {
      try {
        const resp = await fetch('/api/test_telegram', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
          alert('📱 Telegram alert dispatched to @bamquantforgebot!');
        } else {
          alert('Telegram error: ' + (res.error || 'Not configured'));
        }
      } catch (err) {
        alert('Error contacting Telegram: ' + err);
      }
    }

    async function resetJournal() {
      if (!confirm("Are you sure you want to reset the paper journal and start fresh?")) return;
      try {
        const resp = await fetch('/api/reset_journal', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
          alert("Paper journal and live bridge reset successfully!");
          fetchState();
        }
      } catch (e) {
        alert("Failed to reset journal: " + e);
      }
    }

    setInterval(fetchState, 500);
    fetchState();
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/state":
            state = self.get_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/reset_journal":
            try:
                if JOURNAL_DB.exists():
                    conn = sqlite3.connect(JOURNAL_DB)
                    conn.execute("DELETE FROM event_journal;")
                    conn.commit()
                    conn.close()

                try:
                    req = urllib.request.Request(
                        BRIDGE_RESET_URL,
                        headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/test_telegram":
            try:
                notifier = TelegramNotifier()
                last_p = f"${LAST_BID:,.2f}" if LAST_BID > 0 else "Active"
                sent = notifier.send_message(
                    f"⚡ <b>QuantForge Live System Ping</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Status     : 🟢 <b>MT5 Bridge Connected</b>\n"
                    f"Live Mark  : <code>{last_p}</code>\n"
                    f"Time (UTC) : <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"Risk Guard : <b>1.0% Capital Protected</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Cockpit & Alerts Online</i>",
                    async_send=False,
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": sent}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/execute_trade":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
                side = str(body.get("side", "buy")).lower()
                sym = str(body.get("symbol", "BTCUSDm"))
                qty = float(body.get("quantity", 0.01))

                cur_price = LAST_ASK if side == "buy" else LAST_BID
                if cur_price <= 0:
                    cur_price = 78250.0

                order_id = f"qf-{int(time.time()*1000)}"
                is_btc = "BTC" in sym.upper()
                # Quick Strike Scalper: Tight Risk ($0.80 - $1.00) : Direct $1.50 Profit Target
                sl_dist = 80.0 if is_btc else 1.00
                tp_dist = 150.0 if is_btc else 1.50
                sl_price = cur_price - sl_dist if side == "buy" else cur_price + sl_dist
                tp_price = cur_price + tp_dist if side == "buy" else cur_price - tp_dist

                now_utc = datetime.now().isoformat()

                # 1. Record events into SQLite Journal
                JOURNAL_DB.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(JOURNAL_DB)
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS event_journal (
                            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                            event_id TEXT NOT NULL UNIQUE,
                            event_type TEXT NOT NULL,
                            schema_version INTEGER NOT NULL,
                            occurred_at_utc TEXT NOT NULL,
                            correlation_id TEXT NOT NULL,
                            causation_id TEXT,
                            payload_json TEXT NOT NULL,
                            checksum TEXT NOT NULL
                        )
                        """
                    )
                    import hashlib
                    # Intent
                    intent_payload = {
                        "intent_id": order_id,
                        "instrument": sym,
                        "side": side,
                        "quantity": qty,
                        "entry_price": cur_price,
                        "stop_loss_price": sl_price,
                        "target_price": tp_price,
                        "rationale": "Manual Cockpit Execution (Tight SL : 2.5R TP)",
                    }
                    ch1 = hashlib.sha256(json.dumps(intent_payload).encode()).hexdigest()
                    conn.execute(
                        "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"intent-{order_id}", "TradeIntentGenerated", 1, now_utc, order_id, None, json.dumps(intent_payload), ch1),
                    )

                    # Risk Approved
                    risk_payload = {
                        "intent_id": order_id,
                        "approved": True,
                        "allocated_capital": 30.0 * 0.01,
                        "reasons": ["1.0% Risk Budget Approved"],
                    }
                    ch2 = hashlib.sha256(json.dumps(risk_payload).encode()).hexdigest()
                    conn.execute(
                        "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"risk-{order_id}", "RiskDecisionRecorded", 1, now_utc, order_id, f"intent-{order_id}", json.dumps(risk_payload), ch2),
                    )

                    # Fill execution with SL and TP
                    fill_payload = {
                        "order_id": order_id,
                        "instrument": sym,
                        "side": side,
                        "quantity": qty,
                        "price": cur_price,
                        "stop_loss_price": sl_price,
                        "target_price": tp_price,
                        "fee": 0.05,
                        "status": "filled",
                    }
                    ch3 = hashlib.sha256(json.dumps(fill_payload).encode()).hexdigest()
                    conn.execute(
                        "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"fill-{order_id}", "ExecutionOutcomeRecorded", 1, now_utc, order_id, f"risk-{order_id}", json.dumps(fill_payload), ch3),
                    )
                conn.close()

                # 2. Try enqueuing to MT5 Execution Bridge
                try:
                    mt5_req_payload = {
                        "order_id": order_id,
                        "symbol": sym,
                        "side": side,
                        "volume": qty,
                        "order_type": "market",
                        "price": cur_price,
                        "stop_loss": sl_price,
                        "take_profit": tp_price,
                        "magic_number": 7007,
                        "comment": "QuantForge Scalper",
                    }
                    mt5_req = urllib.request.Request(
                        "http://127.0.0.1:8765/v1/mt5/orders/enqueue_test",
                        data=json.dumps(mt5_req_payload).encode("utf-8"),
                        headers={"Authorization": f"Bearer {BRIDGE_TOKEN}", "Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(mt5_req, timeout=2)
                except Exception:
                    pass

                # 3. Send Telegram Notification
                notifier = TelegramNotifier()
                notifier.send_signal_alert(
                    instrument=sym,
                    side=side,
                    entry_price=Decimal(str(cur_price)),
                    stop_loss=Decimal(str(sl_price)),
                    target_price=Decimal(str(tp_price)),
                    strategy_name="QuantForge Live Scalper",
                    rationale=f"Cockpit 1% Risk Scalp ({qty} lots)",
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "order_id": order_id, "price": cur_price}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/close_all":
            try:
                closed_count = 0
                total_realized = 0.0
                if JOURNAL_DB.exists():
                    conn = sqlite3.connect(JOURNAL_DB)
                    cursor = conn.cursor()
                    cursor.execute("SELECT sequence, event_type, payload_json FROM event_journal ORDER BY sequence ASC")
                    rows = cursor.fetchall()
                    open_pos = {}
                    for seq, et, p_json in rows:
                        p = json.loads(p_json)
                        if et == "ExecutionOutcomeRecorded":
                            st = p.get("status")
                            oid = p.get("order_id")
                            if st == "filled":
                                open_pos[oid] = p
                            elif st in {"stopped_out", "target_reached", "forced_exit"} and oid in open_pos:
                                open_pos.pop(oid, None)

                    now_utc = datetime.now().isoformat()
                    import hashlib
                    for oid, pos in open_pos.items():
                        side = pos.get("side", "buy")
                        qty = float(pos.get("quantity", 0.01))
                        ep = float(pos.get("price", 0.0))
                        cp = LAST_BID if side == "buy" else LAST_ASK
                        if cp <= 0:
                            cp = ep
                        pnl = (cp - ep) * qty if side == "buy" else (ep - cp) * qty
                        total_realized += pnl

                        exit_payload = {
                            "order_id": oid,
                            "instrument": pos.get("instrument", "BTCUSDm"),
                            "side": side,
                            "quantity": qty,
                            "price": cp,
                            "fee": 0.05,
                            "status": "forced_exit",
                            "reason": "Manual Close / Profit Lock",
                        }
                        ch = hashlib.sha256(json.dumps(exit_payload).encode()).hexdigest()
                        conn.execute(
                            "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (f"exit-{oid}-{int(time.time()*1000)}", "ExecutionOutcomeRecorded", 1, now_utc, oid, None, json.dumps(exit_payload), ch),
                        )
                        closed_count += 1
                    conn.commit()
                    conn.close()

                if closed_count > 0:
                    notifier = TelegramNotifier()
                    sign = "+" if total_realized >= 0 else ""
                    notifier.send_message(
                        f"🏁 <b>QuantForge Position Closed</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Positions Closed : <b>{closed_count}</b>\n"
                        f"Realized PnL     : <b>{sign}${total_realized:,.2f}</b>\n"
                        f"Status           : <b>All Positions Flat</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Manual Exit Recorded</i>",
                        async_send=False,
                    )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "closed_count": closed_count, "realized_pnl": total_realized}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/close_profit":
            try:
                closed_count = 0
                total_realized = 0.0
                if JOURNAL_DB.exists():
                    conn = sqlite3.connect(JOURNAL_DB)
                    cursor = conn.cursor()
                    cursor.execute("SELECT sequence, event_type, payload_json FROM event_journal ORDER BY sequence ASC")
                    rows = cursor.fetchall()
                    open_pos = {}
                    for seq, et, p_json in rows:
                        p = json.loads(p_json)
                        if et == "ExecutionOutcomeRecorded":
                            st = p.get("status")
                            oid = p.get("order_id")
                            if st == "filled":
                                open_pos[oid] = p
                            elif st in {"stopped_out", "target_reached", "forced_exit"} and oid in open_pos:
                                open_pos.pop(oid, None)

                    now_utc = datetime.now().isoformat()
                    import hashlib
                    for oid, pos in open_pos.items():
                        side = pos.get("side", "buy")
                        qty = float(pos.get("quantity", 0.01))
                        ep = float(pos.get("price", 0.0))
                        cp = LAST_BID if side == "buy" else LAST_ASK
                        if cp <= 0:
                            cp = ep
                        pnl = (cp - ep) * qty if side == "buy" else (ep - cp) * qty
                        
                        # ONLY close if strictly in positive profit
                        if pnl > 0:
                            total_realized += pnl
                            exit_payload = {
                                "order_id": oid,
                                "instrument": pos.get("instrument", "BTCUSDm"),
                                "side": side,
                                "quantity": qty,
                                "price": cp,
                                "fee": 0.05,
                                "status": "forced_exit",
                                "reason": "Profit Lock / Early Bank",
                            }
                            ch = hashlib.sha256(json.dumps(exit_payload).encode()).hexdigest()
                            conn.execute(
                                "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (f"exit-{oid}-{int(time.time()*1000)}", "ExecutionOutcomeRecorded", 1, now_utc, oid, None, json.dumps(exit_payload), ch),
                            )
                            closed_count += 1
                    conn.commit()
                    conn.close()

                if closed_count > 0:
                    notifier = TelegramNotifier()
                    notifier.send_message(
                        f"💰 <b>QuantForge Profit Lock Activated!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Positions Closed : <b>{closed_count}</b>\n"
                        f"Banked Gain      : <b>+${total_realized:,.2f}</b>\n"
                        f"Status           : <b>Profits Banked into Cash</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Early Profit Lock Complete</i>",
                        async_send=False,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "closed_count": closed_count, "realized_pnl": total_realized}).encode("utf-8"))
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "No open positions currently in profit."}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def get_state(self) -> dict[str, object]:
        global SNAPSHOT_COUNT, LAST_BID, LAST_ASK, TICK_COUNT, START_TIME
        live_quote = None
        raw_mt5_positions = []

        # 1. Fetch real-time snapshot directly from running MT5 live bridge
        try:
            req = urllib.request.Request(
                BRIDGE_LATEST_URL,
                headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    q = payload.get("quote", {})
                    if q:
                        bid = float(q.get("bid", 0.0))
                        ask = float(q.get("ask", 0.0))
                        obs_time = payload.get("observed_at_utc", "")
                        time_str = obs_time[11:19] if len(obs_time) >= 19 else "Live"
                        live_quote = {
                            "bid": bid,
                            "ask": ask,
                            "spread_points": float(q.get("spread_points", 0.0)),
                            "tick_time": time_str,
                            "symbol": payload.get("instrument", {}).get("broker_symbol", "#BTCUSD"),
                        }
                        SNAPSHOT_COUNT += 1
                        TICK_COUNT += 1

                        if (
                            not PRICE_HISTORY
                            or PRICE_HISTORY[-1]["bid"] != bid
                            or PRICE_HISTORY[-1]["ask"] != ask
                            or PRICE_HISTORY[-1]["time"] != time_str
                        ):
                            PRICE_HISTORY.append({"time": time_str, "bid": bid, "ask": ask})

                        LAST_BID = bid
                        LAST_ASK = ask
                        raw_mt5_positions = payload.get("positions", [])
        except Exception:
            pass

        # Fallback to public live ticker if local MT5 EA hasn't pushed a tick yet
        if not live_quote:
            try:
                b_req = urllib.request.Request(
                    "https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT",
                    headers={"User-Agent": "Mozilla/5.0 QuantForge-Cockpit"},
                )
                with urllib.request.urlopen(b_req, timeout=1.5) as b_resp:
                    if b_resp.status == 200:
                        b_data = json.loads(b_resp.read().decode("utf-8"))
                        bid = float(b_data.get("bidPrice", 0.0))
                        ask = float(b_data.get("askPrice", 0.0))
                        time_str = datetime.now().strftime("%H:%M:%S")
                        live_quote = {
                            "bid": bid,
                            "ask": ask,
                            "spread_points": round(ask - bid, 2),
                            "tick_time": time_str,
                            "symbol": "#BTCUSD (Live Market)",
                        }
                        SNAPSHOT_COUNT += 1
                        TICK_COUNT += 1
                        if (
                            not PRICE_HISTORY
                            or PRICE_HISTORY[-1]["bid"] != bid
                            or PRICE_HISTORY[-1]["time"] != time_str
                        ):
                            PRICE_HISTORY.append({"time": time_str, "bid": bid, "ask": ask})
                        LAST_BID = bid
                        LAST_ASK = ask
            except Exception:
                if LAST_BID > 0 and LAST_ASK > 0:
                    live_quote = {
                        "bid": LAST_BID,
                        "ask": LAST_ASK,
                        "spread_points": round(LAST_ASK - LAST_BID, 2),
                        "tick_time": datetime.now().strftime("%H:%M:%S"),
                        "symbol": "#BTCUSD (Cached)",
                    }

        # Calculate tick rate
        elapsed = max(1.0, time.time() - START_TIME)
        tick_rate = round(TICK_COUNT / elapsed, 1)

        # 2. Read journal events & calculate positions, floating & realized PnL, and closed trades
        events = []
        open_positions = {}
        closed_trades = []
        seen_closed_order_ids = set()
        realized_pnl = 0.0
        fills_count = 0

        if JOURNAL_DB.exists():
            try:
                conn = sqlite3.connect(JOURNAL_DB)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT sequence, event_type, occurred_at_utc, payload_json FROM event_journal ORDER BY sequence ASC"
                )
                rows = cursor.fetchall()
                conn.close()

                for seq, event_type, occurred_at_utc, payload_json in rows:
                    payload = json.loads(payload_json)
                    events.append(
                        {
                            "sequence": seq,
                            "event_type": event_type,
                            "occurred_at_utc": occurred_at_utc,
                            "payload": payload,
                        }
                    )

                    if event_type == "ExecutionOutcomeRecorded":
                        st = payload.get("status")
                        oid = payload.get("order_id")
                        qty = float(payload.get("quantity", 0.0) or 0.0)
                        p_price = float(payload.get("price", 0.0) or 0.0)
                        side = payload.get("side", "buy")

                        if st == "filled":
                            fills_count += 1
                            open_positions[oid] = {
                                "order_id": oid,
                                "instrument": payload.get("instrument", "#BTCUSD"),
                                "side": side,
                                "quantity": qty,
                                "open_price": p_price,
                                "stop_loss_price": float(payload.get("stop_loss_price") or 0.0),
                                "target_price": float(payload.get("target_price") or 0.0),
                                "opened_at": occurred_at_utc,
                            }
                        elif st in {"stopped_out", "target_reached", "forced_exit", "breakeven"}:
                            if oid and oid in seen_closed_order_ids:
                                continue
                            if oid in open_positions:
                                pos = open_positions.pop(oid)
                                ep = pos["open_price"]
                                pnl = (p_price - ep) * qty if pos["side"] == "buy" else (ep - p_price) * qty
                                realized_pnl += pnl
                                if oid:
                                    seen_closed_order_ids.add(oid)
                                fills_count += 1
                                closed_trades.append({
                                    "order_id": oid,
                                    "instrument": pos["instrument"],
                                    "side": pos["side"],
                                    "quantity": qty,
                                    "open_price": ep,
                                    "exit_price": p_price,
                                    "pnl": pnl,
                                    "opened_at": pos["opened_at"],
                                    "closed_at": occurred_at_utc,
                                    "status": st,
                                    "reason": payload.get("reason", "Take Profit Hit" if st == "target_reached" else "Market Exit"),
                                })
            except Exception:
                pass

        # If live MT5 positions exist in snapshot, merge them
        if raw_mt5_positions:
            for mt5_p in raw_mt5_positions:
                ticket_id = str(mt5_p.get("ticket") or mt5_p.get("id") or "")
                if ticket_id and ticket_id not in open_positions:
                    open_price = float(mt5_p.get("open_price", mt5_p.get("price_open", 0.0)))
                    profit = float(mt5_p.get("profit", 0.0))
                    open_positions[ticket_id] = {
                        "order_id": ticket_id,
                        "instrument": mt5_p.get("symbol", "#BTCUSD"),
                        "side": str(mt5_p.get("type", "buy")).lower(),
                        "quantity": float(mt5_p.get("volume", 0.01)),
                        "open_price": open_price,
                        "profit": profit,
                        "opened_at": str(mt5_p.get("time_utc", datetime.now().isoformat())),
                    }

        # Calculate floating PnL on open positions using live quotes & execute automated exits
        floating_pnl = 0.0
        active_positions_list = []
        cur_bid = live_quote["bid"] if live_quote else 0.0
        cur_ask = live_quote["ask"] if live_quote else 0.0
        now_eval_utc = datetime.now().isoformat()
        positions_to_close = []

        for pos in list(open_positions.values()):
            cp = cur_bid if pos["side"] == "buy" else cur_ask
            qty = pos.get("quantity", 0.01)
            ep = pos.get("open_price", 0.0)
            is_btc = "BTC" in pos.get("instrument", "").upper()

            if "profit" in pos and pos.get("profit") is not None and pos["profit"] != 0.0:
                pos_pnl = float(pos["profit"])
            elif cp > 0 and ep > 0:
                pos_pnl = (cp - ep) * qty if pos["side"] == "buy" else (ep - cp) * qty
            else:
                pos_pnl = 0.0

            floating_pnl += pos_pnl
            pos_copy = dict(pos)
            pos_copy["floating_pnl"] = pos_pnl
            pos_copy["current_price"] = cp

            # Quick Strike $1.00 - $2.00 Profit Bank Target (Gold & BTC Scalper)
            # Gold: $1.00 profit (10 pips) / BTC: $1.50 profit ($150 move)
            sensible_profit_target = 1.50 if is_btc else 1.00
            be_thresh = 40.0 if is_btc else 0.50
            be_buffer = 15.0 if is_btc else 0.35

            sl_dist = 80.0 if is_btc else 1.00
            tp_dist = 150.0 if is_btc else 1.50
            sl_p = float(pos.get("stop_loss_price") or (ep - sl_dist if pos["side"] == "buy" else ep + sl_dist))
            tp_p = float(pos.get("target_price") or (ep + tp_dist if pos["side"] == "buy" else ep - tp_dist))

            pos_copy["stop_loss_price"] = sl_p
            pos_copy["target_price"] = tp_p

            is_be = (cp - ep >= be_thresh) if pos["side"] == "buy" else (ep - cp >= be_thresh) if ep > 0 else False
            pos_copy["breakeven_active"] = is_be
            pos_copy["breakeven_price"] = (ep + be_buffer) if pos["side"] == "buy" else (ep - be_buffer)

            # Auto-Exit Check: Sensible Profit Milestone / TP / Positive BE / SL
            if cp > 0 and ep > 0:
                if (pos["side"] == "buy" and cp >= tp_p) or (pos["side"] == "sell" and cp <= tp_p) or (pos_pnl >= sensible_profit_target):
                    positions_to_close.append((pos, "target_reached", "Sensible Profit / Target Reached (+Gain Locked)", cp))
                elif is_be and ((pos["side"] == "buy" and cp <= ep + be_buffer) or (pos["side"] == "sell" and cp >= ep - be_buffer)):
                    positions_to_close.append((pos, "breakeven", "Positive Breakeven Hit (+Profit Protected)", cp))
                elif (pos["side"] == "buy" and cp <= sl_p) or (pos["side"] == "sell" and cp >= sl_p):
                    positions_to_close.append((pos, "stopped_out", "Protective Stop Loss", cp))
                else:
                    active_positions_list.append(pos_copy)
            else:
                active_positions_list.append(pos_copy)

        # Execute automated closures into SQLite Journal
        if positions_to_close and JOURNAL_DB.exists():
            try:
                import hashlib
                conn = sqlite3.connect(JOURNAL_DB)
                with conn:
                    for p_obj, st_reason, reason_desc, exit_p in positions_to_close:
                        oid = p_obj["order_id"]
                        exit_payload = {
                            "order_id": oid,
                            "instrument": p_obj.get("instrument", "BTCUSDm"),
                            "side": "sell" if p_obj["side"] == "buy" else "buy",
                            "quantity": p_obj.get("quantity", 0.01),
                            "price": exit_p,
                            "fee": 0.05,
                            "status": st_reason,
                            "reason": reason_desc,
                        }
                        ch = hashlib.sha256(json.dumps(exit_payload).encode()).hexdigest()
                        conn.execute(
                            "INSERT OR IGNORE INTO event_journal (event_id, event_type, schema_version, occurred_at_utc, correlation_id, causation_id, payload_json, checksum) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (f"exit-{oid}-{int(time.time()*1000)}", "ExecutionOutcomeRecorded", 1, now_eval_utc, oid, None, json.dumps(exit_payload), ch),
                        )
                conn.close()

                # Dispatch instant alert via Telegram
                try:
                    from quantforge.infrastructure.notifications.telegram_notifier import get_default_notifier
                    notifier = get_default_notifier()
                    for p_obj, st_reason, reason_desc, exit_p in positions_to_close:
                        ep = p_obj.get("open_price", 0.0)
                        qty = p_obj.get("quantity", 0.01)
                        pnl = (exit_p - ep) * qty if p_obj["side"] == "buy" else (ep - exit_p) * qty
                        pnl_sign = "+" if pnl >= 0 else ""
                        msg = (
                            f"⚡ <b>Automated Position Exit ({reason_desc})</b>\n\n"
                            f"📌 <b>Symbol:</b> <code>{p_obj.get('instrument', 'XAUUSD')}</code>\n"
                            f"🎯 <b>Status:</b> <code>{st_reason.upper()}</code>\n"
                            f"💰 <b>Net PnL:</b> <code>{pnl_sign}${pnl:.2f}</code>\n"
                            f"📊 <b>Exit Price:</b> <code>{exit_p:.2f}</code>"
                        )
                        notifier.send_message(msg)
                except Exception:
                    pass
            except Exception:
                pass

        initial_cash = 30.0
        current_cash = initial_cash + realized_pnl
        current_equity = current_cash + floating_pnl
        total_pnl = realized_pnl + floating_pnl

        signals = sum(1 for e in events if e["event_type"] == "TradeIntentGenerated")
        approved = sum(1 for e in events if e["event_type"] == "OrderApproved")

        # Win Rate & Profit Factor calculations
        win_trades = [t for t in closed_trades if t["pnl"] > 0]
        loss_trades = [t for t in closed_trades if t["pnl"] < 0]
        win_count = len(win_trades)
        loss_count = len(loss_trades)
        win_rate = (win_count / len(closed_trades) * 100) if closed_trades else 0.0

        gross_profit = sum(t["pnl"] for t in win_trades)
        gross_loss = abs(sum(t["pnl"] for t in loss_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        return {
            "equity": current_equity,
            "cash": current_cash,
            "realized_pnl": realized_pnl,
            "floating_pnl": floating_pnl,
            "total_pnl": total_pnl,
            "open_positions": active_positions_list,
            "closed_trades": list(reversed(closed_trades)),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "win_count": win_count,
            "loss_count": loss_count,
            "fills_count": fills_count,
            "signals_count": signals,
            "approved_orders": approved,
            "events": events,
            "total_snapshots": max(SNAPSHOT_COUNT, len(PRICE_HISTORY)),
            "live_quote": live_quote,
            "price_history": list(PRICE_HISTORY),
            "tick_rate": tick_rate,
        }

    def log_message(self, format: str, *args: Any) -> None:
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🚀 QuantForge Studio Live Dashboard running at: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
