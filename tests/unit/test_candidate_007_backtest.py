"""Unit tests for Candidate 007 backtest and historical simulation engine."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.backtest.candidate_007 import (
    Candidate007SimulationSettings,
    simulate_candidate_007_session,
)
from quantforge.backtest.candidate_007_runner import (
    run_candidate_007_backtest,
    summarize_candidate_007_run,
)
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import SessionOutcome

NEW_YORK = ZoneInfo("America/New_York")


def make_bar(
    timestamp: datetime,
    open_: str = "2400.00",
    close: str = "2400.00",
    high: str | None = None,
    low: str | None = None,
    spread_points: int = 2,
) -> MinuteBar:
    o = Decimal(open_)
    c = Decimal(close)
    h = Decimal(high) if high is not None else max(o, c) + Decimal("1.00")
    l = Decimal(low) if low is not None else min(o, c) - Decimal("1.00")
    return MinuteBar(
        timestamp=timestamp,
        open=o,
        high=h,
        low=l,
        close=c,
        tick_volume=10,
        spread_points=spread_points,
    )


def test_simulate_candidate_007_buy_hits_2r_target() -> None:
    session_day = date(2026, 8, 28)
    start_ny = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)
    warmup_bars = [
        make_bar(start_ny + timedelta(minutes=i), open_="2390.00", high="2392.00", low="2388.00", close="2390.00")
        for i in range(80)
    ]

    # At 08:35 NY, price breaks out upward
    session_bars = [
        make_bar(datetime(2026, 8, 28, 8, 30, tzinfo=NEW_YORK) + timedelta(minutes=i), open_="2390.00", close="2390.00")
        for i in range(5)
    ]
    # Breakout bar at 08:35: High surges to 2405 (channel high was 2392)
    session_bars.append(
        make_bar(
            datetime(2026, 8, 28, 8, 35, tzinfo=NEW_YORK),
            open_="2390.00",
            high="2405.00",
            low="2389.00",
            close="2404.00",
        )
    )
    # Subsequent bar hits 2R target
    session_bars.append(
        make_bar(
            datetime(2026, 8, 28, 8, 36, tzinfo=NEW_YORK),
            open_="2404.00",
            high="2425.00",
            low="2403.00",
            close="2420.00",
        )
    )

    settings = Candidate007SimulationSettings(risk_reward_ratio=Decimal("2.0"))
    result = simulate_candidate_007_session(session_day, session_bars, warmup_bars, settings)

    assert result.outcome == SessionOutcome.FORCED_EXIT
    assert result.entry_side == "buy"
    assert result.r_multiple is not None
    assert result.r_multiple >= Decimal("1.95")  # Verified ~2R target return


def test_simulate_candidate_007_stop_loss_hit() -> None:
    session_day = date(2026, 8, 28)
    start_ny = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)
    warmup_bars = [
        make_bar(start_ny + timedelta(minutes=i), open_="2390.00", high="2392.00", low="2388.00", close="2390.00")
        for i in range(80)
    ]

    session_bars = [
        make_bar(datetime(2026, 8, 28, 8, 30, tzinfo=NEW_YORK) + timedelta(minutes=i), open_="2390.00", close="2390.00")
        for i in range(5)
    ]
    # Breakout bar triggers BUY
    session_bars.append(
        make_bar(
            datetime(2026, 8, 28, 8, 35, tzinfo=NEW_YORK),
            open_="2390.00",
            high="2400.00",
            low="2389.00",
            close="2398.00",
        )
    )
    # Reversal bar collapses and hits protective stop
    session_bars.append(
        make_bar(
            datetime(2026, 8, 28, 8, 36, tzinfo=NEW_YORK),
            open_="2398.00",
            high="2398.00",
            low="2370.00",
            close="2372.00",
        )
    )

    settings = Candidate007SimulationSettings()
    result = simulate_candidate_007_session(session_day, session_bars, warmup_bars, settings)

    assert result.outcome == SessionOutcome.STOPPED_OUT
    assert result.entry_side == "buy"
    assert result.r_multiple is not None
    assert result.r_multiple <= Decimal("-0.95")  # Verified ~ -1.0R loss


def test_candidate_007_backtest_runner_summary() -> None:
    session_day = date(2026, 8, 28)
    bars = [
        make_bar(datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK) + timedelta(minutes=i))
        for i in range(120)
    ]
    run = run_candidate_007_backtest(bars)
    assert run.summary.total_sessions == 1
    assert run.summary.win_rate_pct is not None
