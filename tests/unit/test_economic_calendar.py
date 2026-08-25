from datetime import UTC, datetime

import pytest

from quantforge.market_data.economic_calendar import CalendarEvent, CalendarSnapshot


def utc(hour: int) -> datetime:
    return datetime(2026, 8, 14, hour, tzinfo=UTC)


def test_calendar_event_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="scheduled_at must be UTC"):
        CalendarEvent(
            provider_event_id="provider-1",
            canonical_event_type="US_CPI",
            scheduled_at=datetime(2026, 8, 14, 12),
            importance="high",
            country="US",
            currency="USD",
        )


def test_snapshot_rejects_duplicate_provider_event_ids() -> None:
    event = CalendarEvent(
        provider_event_id="provider-1",
        canonical_event_type="US_CPI",
        scheduled_at=utc(12),
        importance="high",
        country="US",
        currency="USD",
    )

    with pytest.raises(ValueError, match="duplicate"):
        CalendarSnapshot(
            provider_name="example",
            snapshot_id="snapshot-1",
            retrieved_at=utc(9),
            events=(event, event),
        )
