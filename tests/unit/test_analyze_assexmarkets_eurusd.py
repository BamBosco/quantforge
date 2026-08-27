from datetime import UTC, datetime

from tools.analyze_assexmarkets_eurusd import detect_boundary_gaps


def test_detect_boundary_gaps_reports_only_long_intervals() -> None:
    observations = [
        {
            "event_time": datetime(2026, 8, 27, 9, 0, tzinfo=UTC),
            "spread_points": 15.0,
            "server_offset": 180,
        },
        {
            "event_time": datetime(2026, 8, 27, 9, 1, tzinfo=UTC),
            "spread_points": 16.0,
            "server_offset": 180,
        },
        {
            "event_time": datetime(2026, 8, 27, 9, 4, tzinfo=UTC),
            "spread_points": 17.0,
            "server_offset": 180,
        },
    ]

    assert detect_boundary_gaps(observations) == [
        {
            "before_utc": "2026-08-27T09:01:00+00:00",
            "after_utc": "2026-08-27T09:04:00+00:00",
            "gap_seconds": 180.0,
            "classification": "ordinary_collection_gap",
            "boundary_type": "unclassified_long_gap",
            "before_weekday": "Thursday",
            "after_weekday": "Thursday",
            "before_spread_points": 16.0,
            "after_spread_points": 17.0,
            "before_server_minus_utc_minutes": 180,
            "after_server_minus_utc_minutes": 180,
        }
    ]
