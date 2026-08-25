"""Timezone-aware session windows and minute-sequence validation."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """A half-open wall-clock session whose UTC bounds follow DST correctly."""

    timezone_name: str
    starts_at: time
    ends_at: time

    def __post_init__(self) -> None:
        if not self.timezone_name or self.starts_at >= self.ends_at:
            raise ValueError("session window requires an ordered timezone and times")

    def bounds_utc(self, session_day: date) -> tuple[datetime, datetime]:
        timezone = ZoneInfo(self.timezone_name)
        start = datetime.combine(session_day, self.starts_at, tzinfo=timezone)
        end = datetime.combine(session_day, self.ends_at, tzinfo=timezone)
        return start.astimezone(UTC), end.astimezone(UTC)

    def expected_minutes_utc(self, session_day: date) -> tuple[datetime, ...]:
        start, end = self.bounds_utc(session_day)
        minutes: list[datetime] = []
        current = start
        while current < end:
            minutes.append(current)
            current += timedelta(minutes=1)
        return tuple(minutes)


@dataclass(frozen=True, slots=True)
class MinuteWindowAssessment:
    complete: bool
    missing: tuple[datetime, ...]
    duplicates: tuple[datetime, ...]
    outside_window: tuple[datetime, ...]


def assess_minute_window(
    timestamps: Iterable[datetime], *, window: SessionWindow, session_day: date
) -> MinuteWindowAssessment:
    """Assess a minute sequence without guessing missing or duplicate observations."""
    expected = frozenset(window.expected_minutes_utc(session_day))
    observed: list[datetime] = []
    for timestamp in timestamps:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("market timestamp must be timezone-aware")
        observed.append(timestamp.astimezone(UTC))
    observed_set = frozenset(observed)
    duplicates = tuple(
        sorted({value for value in observed if observed.count(value) > 1})
    )
    outside = tuple(sorted(observed_set - expected))
    missing = tuple(sorted(expected - observed_set))
    return MinuteWindowAssessment(
        complete=not missing and not duplicates and not outside,
        missing=missing,
        duplicates=duplicates,
        outside_window=outside,
    )
