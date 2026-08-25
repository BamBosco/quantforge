from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from quantforge.config.event_risk import load_event_risk_policy
from quantforge.market_data.economic_calendar import CalendarEvent, CalendarSnapshot
from quantforge.risk.event_policy import EventRiskAction, EventRiskPolicy


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 14, hour, minute, tzinfo=timezone.utc)


def policy() -> EventRiskPolicy:
    return EventRiskPolicy(
        load_event_risk_policy(Path("config/risk/xauusd_scheduled_event_policy.toml"))
    )


def snapshot(
    *events: CalendarEvent, retrieved_at: datetime = utc(9)
) -> CalendarSnapshot:
    return CalendarSnapshot(
        provider_name="example-calendar",
        snapshot_id="snapshot-20260814",
        retrieved_at=retrieved_at,
        events=events,
    )


def cpi_event() -> CalendarEvent:
    return CalendarEvent(
        provider_event_id="cpi-20260814",
        canonical_event_type="US_CPI",
        scheduled_at=utc(12),
        importance="high",
        country="US",
        currency="USD",
    )


def test_blackout_flattens_and_blocks_at_exact_three_hour_cutoff() -> None:
    decision = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(9),
        calendar=snapshot(cpi_event()),
    )

    assert decision.allows_new_intents is False
    assert decision.actions == frozenset(
        {
            EventRiskAction.REJECT_NEW_INTENTS,
            EventRiskAction.CANCEL_PENDING_ENTRIES,
            EventRiskAction.FLATTEN_OPEN_POSITION,
        }
    )
    assert decision.blackout_starts_at == utc(9)


def test_allows_before_blackout() -> None:
    decision = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(8, 59),
        calendar=snapshot(cpi_event()),
    )

    assert decision.actions == frozenset({EventRiskAction.ALLOW})


def test_stale_calendar_blocks_entries_and_cancels_pending_orders() -> None:
    decision = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(11),
        calendar=snapshot(cpi_event(), retrieved_at=utc(9)),
    )

    assert decision.actions == frozenset(
        {
            EventRiskAction.REJECT_NEW_INTENTS,
            EventRiskAction.CANCEL_PENDING_ENTRIES,
        }
    )
    assert decision.event is None


def test_post_event_requires_manual_release_but_does_not_repeat_flatten() -> None:
    decision = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(12, 1),
        calendar=snapshot(cpi_event(), retrieved_at=utc(12)),
    )

    assert decision.allows_new_intents is False
    assert EventRiskAction.FLATTEN_OPEN_POSITION not in decision.actions


def test_manual_release_allows_after_event_but_not_before_a_future_event() -> None:
    event = cpi_event()
    released = frozenset({event.provider_event_id})
    after_event = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(12, 1),
        calendar=snapshot(event, retrieved_at=utc(12)),
        manually_released_event_ids=released,
    )
    before_future_event = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(9),
        calendar=snapshot(event),
        manually_released_event_ids=released,
    )

    assert after_event.allows_new_intents is True
    assert before_future_event.allows_new_intents is False


def test_audit_event_records_policy_snapshot_and_actions() -> None:
    decision = policy().evaluate(
        instrument="XAUUSD",
        evaluated_at=utc(9),
        calendar=snapshot(cpi_event()),
    )

    audit_event = decision.to_audit_event(
        correlation_id=uuid4(), occurred_at=utc(9)
    )

    assert audit_event.calendar_snapshot_id == "snapshot-20260814"
    assert audit_event.provider_event_id == "cpi-20260814"
    assert "flatten_open_position" in audit_event.actions
