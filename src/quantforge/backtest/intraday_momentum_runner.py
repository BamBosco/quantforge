"""Chronological batch runner for Intraday Momentum Experiment 001."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from quantforge.backtest.intraday_momentum import (
    IntradayMomentumSettings,
    simulate_intraday_momentum_session,
)
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import ReplaySessionResult, SkippedSession


@dataclass(frozen=True, slots=True)
class IntradayMomentumBacktestRun:
    """All chronology-preserving outcomes for one cost scenario."""

    results: tuple[ReplaySessionResult, ...]
    skipped_sessions: tuple[SkippedSession, ...]


def run_intraday_momentum_backtest(
    bars: Iterable[MinuteBar],
    *,
    settings: IntradayMomentumSettings,
    excluded_session_days: frozenset[date],
) -> IntradayMomentumBacktestRun:
    """Replay each New York weekday once, retaining invalid outcomes visibly."""
    timezone = ZoneInfo(settings.timezone)
    bars_by_session: dict[date, list[MinuteBar]] = {}
    for bar in bars:
        session_day = bar.timestamp.astimezone(timezone).date()
        if session_day.weekday() < 5:
            bars_by_session.setdefault(session_day, []).append(bar)

    results: list[ReplaySessionResult] = []
    skipped: list[SkippedSession] = []
    for session_day in sorted(bars_by_session):
        if session_day in excluded_session_days:
            skipped.append(SkippedSession(session_day, "dataset quality exclusion"))
            continue
        results.append(
            simulate_intraday_momentum_session(
                bars_by_session[session_day],
                session_day=session_day,
                settings=settings,
            )
        )
    return IntradayMomentumBacktestRun(tuple(results), tuple(skipped))
