"""Validated, vendor-neutral scheduled economic-calendar observations."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


def _require_utc(value: datetime, field_name: str) -> None:
    """Reject naive and non-UTC timestamps at the market-data boundary."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be UTC")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """One provider event mapped to QuantForge's canonical event type."""

    provider_event_id: str
    canonical_event_type: str
    scheduled_at: datetime
    importance: str
    country: str
    currency: str

    def __post_init__(self) -> None:
        if not self.provider_event_id:
            raise ValueError("provider event ID must not be empty")
        if not self.canonical_event_type:
            raise ValueError("canonical event type must not be empty")
        _require_utc(self.scheduled_at, "scheduled_at")


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
    """Immutable calendar response retained for policy decisions and replay."""

    provider_name: str
    snapshot_id: str
    retrieved_at: datetime
    events: tuple[CalendarEvent, ...]

    def __post_init__(self) -> None:
        if not self.provider_name or not self.snapshot_id:
            raise ValueError("calendar provider name and snapshot ID are required")
        _require_utc(self.retrieved_at, "retrieved_at")
        event_ids = [event.provider_event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("calendar snapshot contains duplicate provider event IDs")


class EconomicCalendarProvider(Protocol):
    """Port implemented by a future calendar-vendor adapter."""

    def fetch_snapshot(self, as_of: datetime) -> CalendarSnapshot:
        """Return a validated snapshot whose timestamps are all UTC."""
