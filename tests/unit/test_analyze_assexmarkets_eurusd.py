from datetime import UTC, datetime

from tools.analyze_assexmarkets_eurusd import detect_boundary_gaps


def test_detect_boundary_gaps_reports_only_long_intervals() -> None:
    times = [
        datetime(2026, 8, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 8, 27, 9, 1, tzinfo=UTC),
        datetime(2026, 8, 27, 9, 4, tzinfo=UTC),
    ]

    assert detect_boundary_gaps(times) == [
        {
            "before_utc": "2026-08-27T09:01:00+00:00",
            "after_utc": "2026-08-27T09:04:00+00:00",
            "gap_seconds": 180.0,
            "before_weekday": "Thursday",
            "after_weekday": "Thursday",
        }
    ]
