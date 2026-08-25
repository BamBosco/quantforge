from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.infrastructure.mt5.one_time_demo_readiness import (
    OneTimeDemoReadinessGuard,
)

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


def test_arms_one_fresh_approved_stage_a_request_only(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    settings = load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))
    snapshot = {"observed_at_utc": NOW.isoformat()}
    request = {
        "stage": "A",
        "action": "SELL_MARKET",
        "broker_symbol": "USDJPY",
        "send_allowed": False,
        "submission_status": "prohibited_stage_a",
    }
    try:
        log.append_research_snapshot(
            observation_id="obs",
            candle_open_time_utc=NOW,
            validation_status="accepted",
            validation_issues=(),
            snapshot=snapshot,
        )
        log.append_risk_decision(
            observation_id="obs",
            risk_status="approved",
            risk_decision={"non_executable": True},
        )
        log.append_execution_request(
            observation_id="obs",
            request_status="constructed",
            validation_issues=(),
            request=request,
        )
        state = {
            "currency": "USD",
            "broker_symbol": "USDJPY",
            "positions": [],
            "active_orders": [],
        }
        result = OneTimeDemoReadinessGuard(settings).arm(
            log, observation_id="obs", current_account_state=state, evaluated_at=NOW
        )
        assert result.status == "ready_unclaimed"
        assert result.nonce is not None
        assert (
            log.one_time_demo_readiness("candidate_005_usdjpy_one_demo_order")["status"]
            == "ready_unclaimed"
        )
        again = OneTimeDemoReadinessGuard(settings).arm(
            log, observation_id="obs", current_account_state=state, evaluated_at=NOW
        )
        assert again.status == "rejected"
        assert "already reserved" in again.reasons[0]
    finally:
        log.close()


def test_rejects_stale_or_positioned_request(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    settings = load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))
    try:
        log.append_research_snapshot(
            observation_id="obs",
            candle_open_time_utc=NOW,
            validation_status="accepted",
            validation_issues=(),
            snapshot={"observed_at_utc": NOW.isoformat()},
        )
        log.append_risk_decision(
            observation_id="obs", risk_status="approved", risk_decision={}
        )
        log.append_execution_request(
            observation_id="obs",
            request_status="constructed",
            validation_issues=(),
            request={
                "stage": "A",
                "action": "BUY_MARKET",
                "broker_symbol": "USDJPY",
                "send_allowed": False,
                "submission_status": "prohibited_stage_a",
            },
        )
        state = {
            "currency": "USD",
            "broker_symbol": "USDJPY",
            "positions": [{"ticket": "1"}],
            "active_orders": [],
        }
        result = OneTimeDemoReadinessGuard(settings).arm(
            log, observation_id="obs", current_account_state=state, evaluated_at=NOW
        )
        assert "one-position rule prevents readiness" in result.reasons
    finally:
        log.close()
