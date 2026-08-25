"""Batch orchestration for deterministic, non-sized ORB research replays."""

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from quantforge.backtest.orb_bias import determine_entry_eligibility
from quantforge.backtest.models import MinuteBar, OpeningRange
from quantforge.backtest.orb import build_opening_range, to_new_york
from quantforge.backtest.orb_simulation import (
    OrbSessionResult,
    OrbSimulationSettings,
    SessionOutcome,
    complete_session_bars,
    simulate_orb_session,
)


@dataclass(frozen=True, slots=True)
class SkippedSession:
    """A session deliberately omitted from a research run, with its reason."""

    session_day: date
    reason: str


@dataclass(frozen=True, slots=True)
class OrbBacktestRun:
    """All evaluated and deliberately skipped sessions for one cost scenario."""

    results: tuple[OrbSessionResult, ...]
    skipped_sessions: tuple[SkippedSession, ...]


def run_orb_backtest(
    bars: Iterable[MinuteBar],
    *,
    settings: OrbSimulationSettings,
    excluded_session_days: frozenset[date],
) -> OrbBacktestRun:
    """Run chronological ORB sessions without using excluded data for Stretch.

    A session enters the ten-range Stretch history only after its entire
    08:20-to-13:30 New York M1 window is complete and it is not in the immutable
    dataset exclusion list. The current session is appended only after it has
    been evaluated, preventing look-ahead bias.
    """
    bars_by_session: dict[date, list[MinuteBar]] = {}
    for bar in bars:
        session_day = to_new_york(bar.timestamp).date()
        if session_day.weekday() < 5:
            bars_by_session.setdefault(session_day, []).append(bar)
    session_days = sorted(bars_by_session)
    prior_ranges: deque[OpeningRange] = deque(maxlen=10)
    results: list[OrbSessionResult] = []
    skipped: list[SkippedSession] = []

    for session_day in session_days:
        if session_day in excluded_session_days:
            skipped.append(SkippedSession(session_day, "dataset quality exclusion"))
            continue
        session_bars = complete_session_bars(
            bars_by_session[session_day],
            session_day,
            settings.exit_time,
        )
        if session_bars is None:
            skipped.append(
                SkippedSession(session_day, "incomplete required M1 session window")
            )
            continue
        try:
            opening_range = build_opening_range(session_bars, session_day)
        except ValueError:
            skipped.append(SkippedSession(session_day, "invalid opening-range M1 data"))
            continue
        if len(prior_ranges) < 10:
            skipped.append(
                SkippedSession(
                    session_day, "insufficient prior valid sessions for Stretch"
                )
            )
            prior_ranges.append(opening_range)
            continue
        entry_eligibility = determine_entry_eligibility(
            tuple(bars_by_session[session_day]),
            session_day=session_day,
            settings=settings.directional_bias,
        )
        result = simulate_orb_session(
            session_bars,
            session_day=session_day,
            prior_ranges=tuple(prior_ranges),
            settings=settings,
            entry_eligibility=entry_eligibility,
        )
        results.append(result)
        if result.outcome is SessionOutcome.INVALID_DATA:
            raise RuntimeError(
                "session passed runner validation but failed simulation validation"
            )
        prior_ranges.append(opening_range)

    return OrbBacktestRun(tuple(results), tuple(skipped))
