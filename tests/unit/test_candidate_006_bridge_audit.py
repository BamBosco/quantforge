from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from quantforge.application.experimental_paper_demo import demo_observation
from quantforge.infrastructure.mt5.candidate_006_bridge_audit import (
    Candidate006BridgeAuditConsumer,
    Candidate006BridgeAuditError,
)
from quantforge.infrastructure.mt5.observation_log import StoredObservation
from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    SQLiteXAUUSDBrokerProfileAudit,
)


def receipt(observation_id: str | None = None) -> StoredObservation:
    return StoredObservation(
        42,
        observation_id or observation().observation_id,
        2,
        datetime(2026, 8, 25, tzinfo=UTC),
        "accepted",
        (),
    )


def observation():
    result = demo_observation(
        observed_at=datetime(2026, 8, 25, tzinfo=UTC),
        bid=Decimal("4645.335"),
        ask=Decimal("4645.835"),
    )
    result.payload["account"]["server"] = "Dukascopy-demo-mt5-1"
    result.payload["candles"]["completed"] = [
        {
            "open_time_utc": "2026-08-25T00:00:00+00:00",
            "open": 4633.205,
            "high": 4635.245,
            "low": 4633.205,
            "close": 4634.195,
            "tick_volume": 225,
        }
    ]
    spec = result.payload["instrument"]["specification"]
    spec.update(
        {
            "trade_mode": 4,
            "order_mode": 127,
            "stop_level": 0,
            "freeze_level": 0,
            "trade_calculation_mode": 1,
            "profit_currency": "USD",
            "margin_currency": "XAU",
            "tick_size": 0.001,
            "tick_value": 0.1,
            "tick_value_loss": 0.1,
            "tick_value_profit": 0.1,
        }
    )
    result.payload["terminal"]["trade_allowed"] = True
    return result


def test_persists_only_a_complete_dukascopy_bridge_receipt(tmp_path: Path) -> None:
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "candidate_006.sqlite3")
    try:
        result = Candidate006BridgeAuditConsumer(audit).consume(
            observation(), receipt()
        )
        assert result.accepted and audit.count() == 1
    finally:
        audit.close()


def test_rejects_mismatched_receipt(tmp_path: Path) -> None:
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "candidate_006.sqlite3")
    try:
        with pytest.raises(Candidate006BridgeAuditError, match="receipt to match"):
            Candidate006BridgeAuditConsumer(audit).consume(
                observation(), receipt("wrong-observation-id")
            )
        assert audit.count() == 0
    finally:
        audit.close()


def test_rejects_missing_native_metadata(tmp_path: Path) -> None:
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "candidate_006.sqlite3")
    try:
        item = observation()
        item.payload["instrument"]["specification"].pop("tick_value_loss")
        with pytest.raises(Candidate006BridgeAuditError, match="complete native"):
            Candidate006BridgeAuditConsumer(audit).consume(item, receipt(item.observation_id))
    finally:
        audit.close()
