# ruff: noqa: E501
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    SQLiteXAUUSDBrokerProfileAudit,
    XAUUSDBrokerMetadataObservation,
)
from quantforge.infrastructure.mt5.xauusd_evidence_package import (
    Candidate006EvidencePackageError,
    export_candidate_006_evidence_package,
    verify_candidate_006_evidence_package,
)


def payload() -> dict[str, object]:
    observed = datetime.now(UTC).replace(microsecond=0)
    candle = observed - timedelta(minutes=2)
    observed_text = observed.isoformat()
    candle_text = candle.replace(second=0).isoformat()
    return {
        "schema_version": 2,
        "observed_at_utc": observed_text,
        "source": {"adapter": "mt5_read_only_ea", "broker_profile_id": "mt5_runtime_observed"},
        "account": {"account_id": "1", "server": "Dukascopy-demo-mt5-1", "currency": "USD", "balance": 10000.0, "equity": 10000.0, "margin": 0.0, "free_margin": 10000.0},
        "instrument": {"canonical_instrument": "XAUUSD", "broker_symbol": "XAUUSD", "specification": {"point": 0.001, "digits": 3, "contract_size": 100.0, "volume_min": 0.01, "volume_max": 10000.0, "volume_step": 0.01, "supported_filling_modes": ["immediate_or_cancel"], "trade_mode": 4, "order_mode": 127, "stop_level": 0, "freeze_level": 0, "trade_calculation_mode": 0, "profit_currency": "USD", "margin_currency": "XAU", "tick_size": 0.001, "tick_value": 0.1, "tick_value_loss": 0.1, "tick_value_profit": 0.1}},
        "quote": {"bid": 4666.425, "ask": 4667.185, "spread_points": 760.0, "tick_time_utc": observed_text},
        "candles": {"timeframe": "M1", "forming": None, "completed": [{"open_time_utc": candle_text, "open": 4666.0, "high": 4667.0, "low": 4665.0, "close": 4666.5, "tick_volume": 10.0}]},
        "terminal": {"connected": True, "trade_allowed": True},
        "data_quality": {"adapter_status": "ok", "missing_data": []},
        "positions": [], "active_orders": [],
        "deals": {"history_from_utc": observed_text, "history_to_utc": observed_text, "items": []},
    }


def test_freezes_and_verifies_receipt_linked_evidence(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "observations.sqlite3")
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "audit.sqlite3")
    try:
        observation = ObservationEnvelope.from_payload(payload())
        receipt = log.append_observation(observation)
        audit.append(XAUUSDBrokerMetadataObservation.from_read_only_payload(source_event_id=receipt.id, payload=observation.payload))
    finally:
        log.close()
        audit.close()
    package = export_candidate_006_evidence_package(observation_database=tmp_path / "observations.sqlite3", audit_database=tmp_path / "audit.sqlite3", destination=tmp_path / "evidence")
    assert package.record_count == verify_candidate_006_evidence_package(tmp_path / "evidence") == 1
    assert package.records_path.stat().st_mode & 0o777 == 0o400


def test_refuses_mismatched_audit_payload(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "observations.sqlite3")
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "audit.sqlite3")
    try:
        observation = ObservationEnvelope.from_payload(payload())
        receipt = log.append_observation(observation)
        audit.append(XAUUSDBrokerMetadataObservation.from_read_only_payload(source_event_id=receipt.id, payload=observation.payload))
    finally:
        log.close()
        audit.close()
    connection = __import__("sqlite3").connect(tmp_path / "audit.sqlite3")
    try:
        value = json.loads(connection.execute("select payload_json from xauusd_broker_metadata_observation").fetchone()[0])
        value["spread_points"] = 1.0
        connection.execute("update xauusd_broker_metadata_observation set payload_json = ?", (json.dumps(value),))
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(Candidate006EvidencePackageError, match="does not match"):
        export_candidate_006_evidence_package(observation_database=tmp_path / "observations.sqlite3", audit_database=tmp_path / "audit.sqlite3", destination=tmp_path / "evidence")
