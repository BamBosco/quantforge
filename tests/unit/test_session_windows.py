"""Tests for generic session handling across America/New_York DST changes."""

from datetime import UTC, date, time

from quantforge.application.session_windows import SessionWindow, assess_minute_window


def test_new_york_window_uses_the_correct_dst_offset() -> None:
    window = SessionWindow("America/New_York", time(8, 20), time(8, 35))

    winter_start, _ = window.bounds_utc(date(2026, 1, 5))
    summer_start, _ = window.bounds_utc(date(2026, 6, 1))

    assert winter_start.hour == 13
    assert summer_start.hour == 12
    assert winter_start.tzinfo is UTC and summer_start.tzinfo is UTC


def test_window_rejects_missing_and_duplicate_minutes() -> None:
    window = SessionWindow("America/New_York", time(8, 20), time(8, 23))
    expected = list(window.expected_minutes_utc(date(2026, 6, 1)))

    assessment = assess_minute_window(
        [expected[0], expected[1], expected[1]],
        window=window,
        session_day=date(2026, 6, 1),
    )

    assert not assessment.complete
    assert assessment.missing == (expected[2],)
    assert assessment.duplicates == (expected[1],)
