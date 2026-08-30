#!/usr/bin/env python3
"""Run Candidate 007 with Live MT5 Auto-Execution Bridge — Patient Trend Strategy.

Supports 24/7 Weekend Testing on BTCUSD and Native Production Trading on Gold (XAUUSD).
"""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from quantforge.application.paper_runtime import RuntimeCycleResult
from quantforge.infrastructure.mt5.candidate_007_live_service import (
    create_candidate_007_live_bridge,
)
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.strategies.candidate_007 import Candidate007Settings

NEW_YORK = ZoneInfo("America/New_York")


def on_cycle_callback(result: RuntimeCycleResult, observation: ObservationEnvelope) -> None:
    """Pretty-print live MT5 ticks, strategy signals, and executions."""
    ny_time = observation.observed_at_utc.astimezone(NEW_YORK).strftime("%Y-%m-%d %H:%M:%S NY")
    quote = observation.payload.get("quote", {})
    bid = float(quote.get("bid", 0.0))

    if result.signal_generated:
        print(f"\n[{ny_time}] 🎯 CANDIDATE 007 TREND SIGNAL | Symbol: {observation.broker_symbol} | Price: ${bid:,.2f}")

    if result.order_approved:
        print("  └─ 🛡️  RISK GATE: APPROVED | 1.0% Risk Sizing Compliant")

    for ex in result.executions:
        if ex.fill is not None:
            print(
                f"  └─ ⚡ EXECUTED FILL: {ex.fill.side.upper()} {ex.fill.quantity} lots "
                f"at ${ex.fill.price:,.2f} (Fee: ${ex.fill.fee:.2f})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Candidate 007 Live MT5 Auto-Execution Bridge")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback bind address")
    parser.add_argument("--port", type=int, default=8765, help="HTTP Bridge Port (Default: 8765)")
    parser.add_argument(
        "--symbol",
        default="BTCUSD",
        help="Target broker symbol (Default: BTCUSD for weekend forward-testing, or XAUUSD for Gold)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("QUANTFORGE_MT5_BRIDGE_TOKEN", "quantforge-live-token-2026"),
        help="Authentication Bearer token for MT5 EA (Default: quantforge-live-token-2026)",
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=Path("data/paper_mode/candidate_007_paper.sqlite3"),
        help="SQLite event journal path",
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=30.0,
        help="Initial account balance in USD",
    )
    parser.add_argument(
        "--auto-exec",
        action="store_true",
        default=True,
        help="Enable automated trade execution on MT5 (Default: True)",
    )
    args = parser.parse_args()

    token = args.token
    norm_sym = args.symbol.strip("#._/ ").replace("/", "").upper()
    is_crypto = "BTC" in norm_sym

    # Load Dynamic Micro-Scalper Settings (100–250 Daily Trades Capacity)
    if is_crypto:
        settings = Candidate007Settings.for_btcusd_scalper()
    else:
        settings = Candidate007Settings.for_gold_active_scalper()

    server, strategy, portfolio, journal, execution_queue = create_candidate_007_live_bridge(
        host=args.host,
        port=args.port,
        token=token,
        symbol=args.symbol,
        journal_path=args.journal,
        initial_balance=Decimal(str(args.balance)),
        settings=settings,
        enable_auto_execution=args.auto_exec,
        on_cycle=on_cycle_callback,
    )

    print("=" * 75, flush=True)
    print("🛰️  QUANTFORGE HIGH-VELOCITY SMC SCALPER ENGINE — CANDIDATE 007", flush=True)
    print("=" * 75, flush=True)
    print(f"Target Asset       : {args.symbol} {'(Weekend Forward-Testing Mode)' if is_crypto else '(Live Gold Strategy)'}", flush=True)
    print("Strategy Preset    : 🎯 High-Frequency SMC Scalper (Donchian, 20 EMA, 10 ATR, 1.5R Target)", flush=True)
    print("Daily Trade Cap    : Up to 250 High-Velocity Scalps / Day", flush=True)
    print(f"Auto-Execution     : {'🟢 ENABLED (Native MT5 OrderSend)' if args.auto_exec else '🟡 PAPER ONLY'}", flush=True)
    print(f"Bridge URL         : http://{args.host}:{args.port}/v1/mt5/snapshots", flush=True)
    print(f"Durable Journal    : {args.journal}", flush=True)
    print("=" * 75, flush=True)
    print(f"Scanning {args.symbol} for institutional SMC breakout setups...\n", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Live MT5 Bridge...")
    finally:
        server.close()
        print("Bridge safely shutdown.")


if __name__ == "__main__":
    main()
