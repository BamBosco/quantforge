from pathlib import Path

import pytest

from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    SQLiteXAUUSDBrokerProfileAudit,
    XAUUSDBrokerMetadataObservation,
    XAUUSDBrokerProfileAuditError,
)


def payload() -> dict[str, object]:
    return {
        "observed_at_utc": "2026-08-25T07:54:45+00:00",
        "instrument": {
            "canonical_instrument": "XAUUSD",
            "broker_symbol": "XAUUSD",
            "specification": {
                "point": 0.001,
                "digits": 3,
                "volume_min": 0.01,
                "volume_max": 10000.0,
                "volume_step": 0.01,
                "contract_size": 100.0,
                "supported_filling_modes": ["immediate_or_cancel"],
                "trade_mode": 4,
                "order_mode": 127,
                "stop_level": 0,
                "freeze_level": 0,
                "trade_calculation_mode": 1,
                "profit_currency": "USD",
                "margin_currency": "USD",
                "tick_size": 0.001,
                "tick_value": 0.1,
                "tick_value_loss": 0.1,
                "tick_value_profit": 0.1,
            },
        },
        "quote": {"bid": 4631.245, "ask": 4631.705, "spread_points": 460.0},
        "candles": {"completed": [{"open_time_utc": "2026-08-25T07:53:00+00:00"}]},
        "terminal": {"connected": True, "trade_allowed": True},
    }


def test_persists_xauusd_facts_in_its_own_append_only_audit(tmp_path: Path) -> None:
    observation = XAUUSDBrokerMetadataObservation.from_read_only_payload(
        source_event_id=1042, payload=payload()
    )
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "xauusd.sqlite3")
    try:
        audit.append(observation)
        assert audit.count() == 1
        assert observation.trade_mode == 4
        assert observation.trade_permission is True
        assert observation.order_mode == 127
        assert observation.stop_level == 0
        assert observation.freeze_level == 0
        assert observation.trade_calculation_mode == 1
        assert observation.profit_currency == observation.margin_currency == "USD"
        assert observation.tick_size == 0.001
        assert observation.tick_value_loss == observation.tick_value_profit == 0.1
        assert observation.filling_modes == ("immediate_or_cancel",)
    finally:
        audit.close()


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_rejects_non_finite_broker_facts(value: float) -> None:
    source = payload()
    quote = source["quote"]
    assert isinstance(quote, dict)
    quote["bid"] = value
    with pytest.raises(XAUUSDBrokerProfileAuditError, match="must be finite"):
        XAUUSDBrokerMetadataObservation.from_read_only_payload(
            source_event_id=1042, payload=source
        )


def test_rejects_non_xauusd_source_observations() -> None:
    source = payload()
    instrument = source["instrument"]
    assert isinstance(instrument, dict)
    instrument["canonical_instrument"] = "USDJPY"
    with pytest.raises(XAUUSDBrokerProfileAuditError, match="only XAUUSD"):
        XAUUSDBrokerMetadataObservation.from_read_only_payload(
            source_event_id=1042, payload=source
        )


def test_missing_read_only_metadata_is_persisted_as_unavailable() -> None:
    source = payload()
    instrument = source["instrument"]
    assert isinstance(instrument, dict)
    specification = instrument["specification"]
    assert isinstance(specification, dict)
    for key in (
        "trade_mode",
        "order_mode",
        "stop_level",
        "freeze_level",
        "trade_calculation_mode",
        "profit_currency",
        "margin_currency",
        "tick_size",
        "tick_value",
        "tick_value_loss",
        "tick_value_profit",
    ):
        specification.pop(key)
    terminal = source["terminal"]
    assert isinstance(terminal, dict)
    terminal.pop("trade_allowed")

    observation = XAUUSDBrokerMetadataObservation.from_read_only_payload(
        source_event_id=1042, payload=source
    )

    assert observation.trade_mode is None
    assert observation.trade_permission is None
    assert observation.tick_value_loss is None


def test_append_only_audit_refuses_to_replace_a_source_receipt(tmp_path: Path) -> None:
    observation = XAUUSDBrokerMetadataObservation.from_read_only_payload(
        source_event_id=1042, payload=payload()
    )
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "xauusd.sqlite3")
    try:
        audit.append(observation)
        with pytest.raises(XAUUSDBrokerProfileAuditError, match="already persisted"):
            audit.append(observation)
        assert audit.count() == 1
    finally:
        audit.close()


def test_xauusd_risk_audit_requires_a_matching_source_and_status(
    tmp_path: Path,
) -> None:
    observation = XAUUSDBrokerMetadataObservation.from_read_only_payload(
        source_event_id=1104, payload=payload()
    )
    audit = SQLiteXAUUSDBrokerProfileAudit(tmp_path / "xauusd.sqlite3")
    try:
        with pytest.raises(XAUUSDBrokerProfileAuditError, match="non-executable"):
            audit.append_risk_decision(
                source_event_id=1104,
                risk_status="approved",
                risk_decision={"non_executable": False, "status": "approved"},
            )
        with pytest.raises(XAUUSDBrokerProfileAuditError, match="persisted source"):
            audit.append_risk_decision(
                source_event_id=1104,
                risk_status="rejected",
                risk_decision={"non_executable": True, "status": "rejected"},
            )
        audit.append(observation)
        with pytest.raises(XAUUSDBrokerProfileAuditError, match="must match"):
            audit.append_risk_decision(
                source_event_id=1104,
                risk_status="approved",
                risk_decision={"non_executable": True, "status": "rejected"},
            )
        audit.append_risk_decision(
            source_event_id=1104,
            risk_status="rejected",
            risk_decision={"non_executable": True, "status": "rejected"},
        )
        with pytest.raises(XAUUSDBrokerProfileAuditError, match="already has"):
            audit.append_risk_decision(
                source_event_id=1104,
                risk_status="rejected",
                risk_decision={"non_executable": True, "status": "rejected"},
            )
    finally:
        audit.close()
