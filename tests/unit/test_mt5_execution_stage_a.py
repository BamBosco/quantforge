from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.execution_stage_a import MT5StageAExecutionGateway
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


def snapshot() -> dict[str, object]:
    return {
        "instrument": {
            "canonical_symbol": "USDJPY",
            "broker_symbol": "USDJPY",
            "specification": {
                "point": 0.001,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "supported_filling_modes": ["immediate_or_cancel"],
            },
        },
        "quote": {"bid": 159.1, "ask": 159.101},
        "observed_at_utc": NOW.isoformat(),
    }


def intent(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "symbol": "USDJPY",
        "direction": "BUY",
        "entry_type": "market",
        "entry_price": 159.1,
        "stop_loss": 159.0,
        "take_profit": 159.3,
    }
    value.update(changes)
    return value


def risk() -> dict[str, object]:
    return {
        "status": "approved",
        "risk_decision": {"proposed_volume": "0.10", "non_executable": True},
    }


def gateway() -> MT5StageAExecutionGateway:
    return MT5StageAExecutionGateway(
        load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))
    )


def test_constructs_unsendable_market_request_from_approved_risk() -> None:
    result = gateway().construct(
        trade_intent=intent(),
        risk_decision=risk(),
        market_snapshot=snapshot(),
        evaluated_at=NOW,
    )

    assert result.status == "constructed"
    assert result.request is not None
    assert result.request["action"] == "BUY_MARKET"
    assert result.request["volume"] == "0.10"
    assert result.request["send_allowed"] is False
    assert result.request["submission_status"] == "prohibited_stage_a"


def test_rejects_unapproved_risk_and_stale_snapshot() -> None:
    rejected_risk = {"status": "rejected", "risk_decision": {}}
    result = gateway().construct(
        trade_intent=intent(),
        risk_decision=rejected_risk,
        market_snapshot=snapshot(),
        evaluated_at=NOW,
    )
    assert result.reasons == ("risk decision is not approved",)

    stale = snapshot()
    stale["observed_at_utc"] = "2026-08-24T11:58:29+00:00"
    result = gateway().construct(
        trade_intent=intent(),
        risk_decision=risk(),
        market_snapshot=stale,
        evaluated_at=NOW,
    )
    assert "market snapshot is stale" in result.reasons


def test_rejects_limit_price_and_unsupported_filling_mode() -> None:
    result = gateway().construct(
        trade_intent=intent(entry_type="limit", entry_price=159.2),
        risk_decision=risk(),
        market_snapshot=snapshot(),
        evaluated_at=NOW,
    )
    assert "BUY limit price must be below ask" in result.reasons

    unsupported = snapshot()
    specification = unsupported["instrument"]["specification"]
    assert isinstance(specification, dict)
    specification["supported_filling_modes"] = ["fill_or_kill"]
    result = gateway().construct(
        trade_intent=intent(),
        risk_decision=risk(),
        market_snapshot=unsupported,
        evaluated_at=NOW,
    )
    assert "configured filling mode is unsupported by broker" in result.reasons


def test_construct_from_audit_persists_stage_a_request(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    try:
        log.append_research_snapshot(
            observation_id="obs",
            candle_open_time_utc=NOW,
            validation_status="accepted",
            validation_issues=(),
            snapshot=snapshot(),
        )
        log.append_agent_decision(
            observation_id="obs",
            status="accepted",
            reasons=(),
            agent_decision={"final": "test"},
            trade_intent=intent(),
        )
        log.append_risk_decision(
            observation_id="obs",
            risk_status="approved",
            risk_decision=risk()["risk_decision"],
        )
        result = gateway().construct_from_audit(
            log, observation_id="obs", evaluated_at=NOW
        )
        assert result.status == "constructed"
        stored = log.execution_requests()[0]
        assert stored["status"] == "constructed"
        assert stored["request"]["send_allowed"] is False
    finally:
        log.close()
