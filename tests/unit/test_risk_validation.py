from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from quantforge.config.event_risk import load_event_risk_policy
from quantforge.market_data.economic_calendar import CalendarEvent, CalendarSnapshot
from quantforge.risk.event_policy import EventRiskPolicy
from quantforge.risk.validation import validate_event_risk, validate_protective_stop


def test_accepts_valid_buy_protective_stop() -> None:
    decision = validate_protective_stop("buy", Decimal("100"), Decimal("99"))

    assert decision.approved is True


def test_rejects_buy_stop_above_entry() -> None:
    decision = validate_protective_stop("buy", Decimal("100"), Decimal("101"))

    assert decision.approved is False


def test_rejects_new_intent_during_event_blackout() -> None:
    timestamp = datetime(2026, 8, 14, 9, tzinfo=UTC)
    event = CalendarEvent(
        provider_event_id="cpi-20260814",
        canonical_event_type="US_CPI",
        scheduled_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
        importance="high",
        country="US",
        currency="USD",
    )
    event_decision = EventRiskPolicy(
        load_event_risk_policy(Path("config/risk/xauusd_scheduled_event_policy.toml"))
    ).evaluate(
        instrument="XAUUSD",
        evaluated_at=timestamp,
        calendar=CalendarSnapshot(
            provider_name="example",
            snapshot_id="snapshot-1",
            retrieved_at=timestamp,
            events=(event,),
        ),
    )

    validation = validate_event_risk(event_decision)

    assert validation.approved is False
    assert validation.reasons == (
        "event-risk policy: scheduled-event blackout is active",
    )
