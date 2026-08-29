#!/usr/bin/env python3
"""Run Candidate 007 through the full QuantForge Paper Trading Lifecycle."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from quantforge.application.candidate_007_paper_demo import (
    build_candidate_007_paper_host,
    make_observation,
)
from quantforge.market_data.mt5_csv import load_mt5_minute_bars

NEW_YORK = ZoneInfo("America/New_York")


def main() -> None:
    parser = argparse.ArgumentParser(description="Candidate 007 Paper Trading Simulation")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/candidate_006_second_broker/raw/XAUUSD_M1_202601020100_202608141159.csv"),
        help="Path to M1 CSV file",
    )
    parser.add_argument("--limit-bars", type=int, default=5000, help="Number of M1 bars to simulate")
    parser.add_argument("--journal", type=Path, default=Path("data/paper_mode/candidate_007_paper.sqlite3"))
    parser.add_argument("--balance", type=float, default=10000.0, help="Initial paper capital in USD")
    args = parser.parse_args()

    args.journal.parent.mkdir(parents=True, exist_ok=True)
    if args.journal.exists():
        args.journal.unlink()

    print("=" * 70)
    print("🚀 QUANTFORGE PAPER TRADING SIMULATION — CANDIDATE 007")
    print("=" * 70)
    print(f"Data Source       : {args.data}")
    print(f"Initial Balance   : ${args.balance:,.2f}")
    print(f"Event Journal DB  : {args.journal}")
    print("Risk Gate Policy  : 1.0% Max Risk per Trade | Max 3.0% Correlated Risk")
    print("-" * 70)

    print(f"Loading market bars from {args.data}...")
    bars = load_mt5_minute_bars(args.data, source_timezone="Etc/UTC")
    sim_bars = bars[: args.limit_bars]
    print(f"Loaded {len(bars)} total bars. Simulating stream of {len(sim_bars)} M1 bars...\n")

    host, strategy, portfolio, journal = build_candidate_007_paper_host(
        args.journal, initial_balance=Decimal(str(args.balance))
    )

    signals_count = 0
    approved_orders = 0
    filled_orders = 0

    for idx, bar in enumerate(sim_bars, 1):
        strategy.update_bar(bar)

        spread = Decimal(bar.spread_points or 20) * Decimal("0.01")
        bid = bar.close
        ask = bar.close + spread
        obs = make_observation(
            observed_at=bar.timestamp,
            bid=bid,
            ask=ask,
            balance=portfolio.cash,
        )

        res = host.process(obs, evaluated_at=bar.timestamp)

        if res.signal_generated:
            signals_count += 1
            ny_str = bar.timestamp.astimezone(NEW_YORK).strftime("%Y-%m-%d %H:%M NY")
            print(f"[{ny_str}] 🎯 SIGNAL GENERATED at Price={ask:.2f}")

        if res.order_approved:
            approved_orders += 1
            print(f"  └─ 🛡️  RISK GATE: APPROVED | Sizing compliant with Account Risk Rules")

        for ex in res.executions:
            if ex.fill is not None:
                filled_orders += 1
                print(
                    f"  └─ ⚡ PAPER FILL: {ex.fill.side.upper()} {ex.fill.quantity} lots "
                    f"at ${ex.fill.price:.2f} (Fee: ${ex.fill.fee:.2f})"
                )

        if idx % 1000 == 0:
            current_eq = portfolio.equity
            print(f"  ... Processed {idx:,} bars | Equity: ${current_eq:,.2f} | Open Positions: {len(portfolio.positions)}")

    # Final summary report
    final_equity = portfolio.equity
    pnl = final_equity - Decimal(str(args.balance))
    pnl_pct = (pnl / Decimal(str(args.balance))) * 100

    print("\n" + "=" * 70)
    print("🏁 SIMULATION LIFECYCLE COMPLETE — AUDIT SUMMARY")
    print("=" * 70)
    print(f"M1 Bars Processed     : {len(sim_bars):,}")
    print(f"Trading Signals Emitted: {signals_count}")
    print(f"Orders Risk-Approved   : {approved_orders}")
    print(f"Executions Filled      : {filled_orders}")
    print(f"Final Cash Balance     : ${portfolio.cash:,.2f}")
    print(f"Final Equity           : ${final_equity:,.2f} ({pnl:+,.2f} USD / {pnl_pct:+.2f}%)")
    print(f"Open Positions         : {len(portfolio.positions)}")
    print(f"SQLite Audit Journal   : {args.journal} (Durable & Replayable)")
    print("=" * 70)


if __name__ == "__main__":
    main()
