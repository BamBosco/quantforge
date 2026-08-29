"""Batch orchestration and CLI runner for Candidate 007 backtest simulations."""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from quantforge.backtest.candidate_007 import (
    Candidate007SimulationSettings,
    simulate_candidate_007_session,
)
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import ReplaySessionResult, SessionOutcome
from quantforge.market_data.mt5_csv import load_mt5_minute_bars

NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class Candidate007Summary:
    """Statistical performance summary of a Candidate 007 backtest run."""

    total_sessions: int
    completed_trades: int
    wins: int
    losses: int
    win_rate_pct: Decimal
    total_r: Decimal
    mean_r: Decimal
    profit_factor: Decimal
    max_drawdown_r: Decimal
    ambiguous_sessions: int
    no_trade_sessions: int


@dataclass(frozen=True, slots=True)
class Candidate007BacktestRun:
    """All evaluated session results for one cost scenario."""

    results: tuple[ReplaySessionResult, ...]
    summary: Candidate007Summary


def summarize_candidate_007_run(
    results: Sequence[ReplaySessionResult],
) -> Candidate007Summary:
    """Compute standard quantitative performance metrics from session outcomes."""
    trades = [r for r in results if r.r_multiple is not None]
    wins = [r for r in trades if r.r_multiple > 0]
    losses = [r for r in trades if r.r_multiple <= 0]

    completed_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (
        (Decimal(win_count) / Decimal(completed_trades) * 100)
        if completed_trades > 0
        else Decimal("0")
    )

    total_r = sum((r.r_multiple for r in trades), Decimal("0"))
    mean_r = (
        (total_r / Decimal(completed_trades)) if completed_trades > 0 else Decimal("0")
    )

    gross_profit = sum((r.r_multiple for r in wins), Decimal("0"))
    gross_loss = abs(sum((r.r_multiple for r in losses), Decimal("0")))
    profit_factor = (
        (gross_profit / gross_loss)
        if gross_loss > 0
        else (Decimal("999.0") if gross_profit > 0 else Decimal("0"))
    )

    # Compute maximum drawdown in R-multiples
    running_r = Decimal("0")
    peak_r = Decimal("0")
    max_dd = Decimal("0")
    for r in trades:
        assert r.r_multiple is not None
        running_r += r.r_multiple
        if running_r > peak_r:
            peak_r = running_r
        dd = peak_r - running_r
        if dd > max_dd:
            max_dd = dd

    ambiguous = sum(1 for r in results if r.outcome == SessionOutcome.AMBIGUOUS)
    no_trades = sum(1 for r in results if r.outcome == SessionOutcome.NO_TRADE)

    return Candidate007Summary(
        total_sessions=len(results),
        completed_trades=completed_trades,
        wins=win_count,
        losses=loss_count,
        win_rate_pct=round(win_rate, 2),
        total_r=round(total_r, 4),
        mean_r=round(mean_r, 4),
        profit_factor=round(profit_factor, 4),
        max_drawdown_r=round(max_dd, 4),
        ambiguous_sessions=ambiguous,
        no_trade_sessions=no_trades,
    )


def run_candidate_007_backtest(
    bars: Iterable[MinuteBar],
    *,
    settings: Candidate007SimulationSettings | None = None,
    excluded_session_days: frozenset[date] = frozenset(),
) -> Candidate007BacktestRun:
    """Run chronological Candidate 007 simulation across a bar series."""
    cfg = settings or Candidate007SimulationSettings()
    bars_by_session: dict[date, list[MinuteBar]] = {}

    for bar in bars:
        session_day = bar.timestamp.astimezone(NEW_YORK).date()
        if session_day.weekday() < 5:
            bars_by_session.setdefault(session_day, []).append(bar)

    session_days = sorted(bars_by_session)
    results: list[ReplaySessionResult] = []
    prior_bars_buffer: deque[MinuteBar] = deque(maxlen=250)

    for day in session_days:
        if day in excluded_session_days:
            continue
        day_bars = bars_by_session[day]
        res = simulate_candidate_007_session(
            session_day=day,
            session_bars=day_bars,
            warmup_bars=tuple(prior_bars_buffer),
            settings=cfg,
        )
        results.append(res)
        prior_bars_buffer.extend(day_bars)

    summary = summarize_candidate_007_run(results)
    return Candidate007BacktestRun(results=tuple(results), summary=summary)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Candidate 007 historical backtest"
    )
    parser.add_argument("--data", type=Path, required=True, help="Path to M1 CSV file")
    parser.add_argument(
        "--timezone", type=str, default="America/New_York", help="Source timezone"
    )
    args = parser.parse_args()

    print(f"Loading M1 bars from: {args.data} ...")
    bars = load_mt5_minute_bars(args.data, source_timezone=args.timezone)
    print(
        f"Loaded {len(bars)} M1 bars. Running Candidate 007 simulation across cost scenarios..."
    )

    for slip in (Decimal("0"), Decimal("1"), Decimal("3")):
        cfg = Candidate007SimulationSettings(additional_slippage_points=slip)
        run = run_candidate_007_backtest(bars, settings=cfg)
        s = run.summary
        print(f"\n--- Cost Scenario: +{slip} pts Slippage ---")
        print(f"  Sessions Evaluated : {s.total_sessions}")
        print(
            f"  Completed Trades   : {s.completed_trades} (Wins: {s.wins}, Losses: {s.losses})"
        )
        print(f"  Win Rate           : {s.win_rate_pct}%")
        print(f"  Total Return       : {s.total_r} R")
        print(f"  Mean Return / Trade: {s.mean_r} R")
        print(f"  Profit Factor      : {s.profit_factor}")
        print(f"  Max Drawdown       : {s.max_drawdown_r} R")


if __name__ == "__main__":
    main()
