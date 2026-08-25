from datetime import date, datetime, timedelta
from decimal import Decimal

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.orb import NEW_YORK, OPENING_TIME
from quantforge.backtest.orb_runner import run_orb_backtest
from quantforge.backtest.orb_simulation import OrbSimulationSettings, SessionOutcome
from quantforge.backtest.reporting import summarize_orb_backtest


def test_runner_skips_warmup_without_lookahead_and_reports_no_trade_sessions() -> None:
    bars = []
    session_day = date(2026, 7, 27)
    for _ in range(12):
        bars.extend(make_complete_session(session_day))
        session_day += timedelta(days=1)
        if session_day.weekday() == 5:
            session_day += timedelta(days=2)

    run = run_orb_backtest(
        bars,
        settings=OrbSimulationSettings(Decimal("0.01"), Decimal("0")),
        excluded_session_days=frozenset(),
    )
    summary = summarize_orb_backtest(run)

    assert len(run.skipped_sessions) == 10
    assert all("insufficient prior" in item.reason for item in run.skipped_sessions)
    assert len(run.results) == 2
    assert all(item.outcome is SessionOutcome.NO_TRADE for item in run.results)
    assert summary.completed_trades == 0
    assert summary.total_r is None


def test_runner_does_not_use_a_quality_exclusion_for_stretch_history() -> None:
    bars = []
    session_day = date(2026, 7, 27)
    excluded_day = session_day + timedelta(days=3)
    for _ in range(13):
        bars.extend(make_complete_session(session_day))
        session_day += timedelta(days=1)
        if session_day.weekday() == 5:
            session_day += timedelta(days=2)

    run = run_orb_backtest(
        bars,
        settings=OrbSimulationSettings(Decimal("0.01"), Decimal("0")),
        excluded_session_days=frozenset({excluded_day}),
    )

    assert any(item.session_day == excluded_day for item in run.skipped_sessions)
    assert len(run.results) == 2


def make_complete_session(session_day: date) -> list[MinuteBar]:
    start = datetime.combine(session_day, OPENING_TIME, tzinfo=NEW_YORK)
    bars = []
    for offset in range(311):
        high = Decimal("100")
        low = Decimal("100")
        if offset == 0:
            high = Decimal("101")
            low = Decimal("99")
        bars.append(
            MinuteBar(
                timestamp=start + timedelta(minutes=offset),
                open=Decimal("100"),
                high=high,
                low=low,
                close=Decimal("100"),
                tick_volume=1,
                spread_points=0,
            )
        )
    return bars
