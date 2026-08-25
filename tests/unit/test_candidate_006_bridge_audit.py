from datetime import UTC, datetime
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

def receipt() -> StoredObservation:
    return StoredObservation(42, "observation", 2, datetime(2026, 8, 25, tzinfo=UTC), "accepted", ())

def observation():
    result = demo_observation(observed_at=datetime(2026, 8, 25, tzinfo=UTC))
    result.payload["account"]["server"] = "Dukascopy-demo-mt5-1"
    spec = result.payload["instrument"]["specification"]
    spec.update({"trade_mode": 4, "order_mode": 127, "stop_level": 0, "freeze_level": 0, "trade_calculation_mode": 1, "profit_currency": "USD", "margin_currency": "XAU", "tick_size": 0.001, "tick_value": 0.1, "tick_value_loss": 0.1, "tick_value_profit": 0.1})
    result.payload["terminal"]["trade_allowed"] = True
    return result

def test_persists_only_a_complete_dukascopy_bridge_receipt(tmp_path: Path) -> None:
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "candidate_006.sqlite3")
    try:
        result = Candidate006BridgeAuditConsumer(audit).consume(observation(), receipt())
        assert result.accepted and audit.count() == 1
    finally:
        audit.close()

def test_rejects_missing_native_metadata(tmp_path: Path) -> None:
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "candidate_006.sqlite3")
    try:
        item = observation()
        item.payload["instrument"]["specification"].pop("tick_value_loss")
        with pytest.raises(Candidate006BridgeAuditError, match="complete native"):
            Candidate006BridgeAuditConsumer(audit).consume(item, receipt())
    finally:
        audit.close()
