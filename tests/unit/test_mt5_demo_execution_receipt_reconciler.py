from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.demo_execution_receipt_reconciler import (
    DemoExecutionReceiptReconciler,
)
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

NOW = datetime(2026, 8, 24, 22, tzinfo=UTC)
READINESS_SCOPE = "candidate_005_usdjpy_one_demo_order"


def _request() -> dict[str, object]:
    return {
        "stage": "A",
        "action": "BUY_MARKET",
        "broker_symbol": "USDJPY",
        "volume": "0.02",
        "price": 159.1,
        "stop_loss": 159.0,
        "take_profit": 159.3,
        "send_allowed": False,
        "submission_status": "prohibited_stage_a",
    }


def _response(**changes: object) -> dict[str, object]:
    response: dict[str, object] = {
        "broker_status": "accepted",
        "broker_symbol": "USDJPY",
        "return_code": 10009,
        "return_message": "Request completed",
        "submitted_at_utc": NOW.isoformat(),
        "responded_at_utc": NOW.isoformat(),
        "requested_volume": "0.02",
        "requested_price": 159.1,
        "filled_volume": "0.02",
        "filled_price": 159.102,
        "order_ticket": "7001",
        "deal_ticket": "8001",
        "position_ticket": "9001",
    }
    response.update(changes)
    return response


def _setup(
    tmp_path: Path,
) -> tuple[SQLiteMarketObservationLog, DemoExecutionReceiptReconciler]:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    request = _request()
    log.append_execution_request(
        observation_id="ready-observation",
        request_status="constructed",
        validation_issues=(),
        request=request,
    )
    log.append_one_time_demo_readiness(
        authorization_scope=READINESS_SCOPE,
        observation_id="ready-observation",
        nonce="unclaimed-test-nonce",
        checks=("all readiness checks passed",),
        request=request,
        account_state={"currency": "USD", "broker_symbol": "USDJPY"},
    )
    state = {
        "observation_timestamp_utc": NOW.isoformat(),
        "account": {
            "server": "Dukascopy-demo-mt5-1",
            "balance": 10_000,
            "equity": 10_000,
        },
        "broker_symbol": "USDJPY",
        "open_positions": [
            {"ticket": "9001", "symbol": "USDJPY", "volume": 0.02}
        ],
        "pending_orders": [],
    }
    log.append_demo_position_state_observation(
        observation_id="post-submit-observation",
        observation_timestamp_utc=NOW.isoformat(),
        account_id="123",
        broker_symbol="USDJPY",
        validation_status="accepted",
        validation_issues=(),
        state=state,
    )
    settings = load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))
    return log, DemoExecutionReceiptReconciler(log, settings)


def test_confirms_matching_response_and_position_ticket(tmp_path: Path) -> None:
    log, reconciler = _setup(tmp_path)
    try:
        result = reconciler.reconcile(
            broker_response=_response(),
            position_state_observation_id="post-submit-observation",
        )

        assert result.status == "confirmed"
        assert result.stored
        stored = log.demo_execution_receipt_reconciliations()[0]
        assert stored["readiness_observation_id"] == "ready-observation"
        assert stored["broker_response"]["return_code"] == "10009"
        assert stored["reconciliation"]["matched_position_ticket"] == "9001"
    finally:
        log.close()


def test_records_broker_rejection_without_a_position_match(tmp_path: Path) -> None:
    log, reconciler = _setup(tmp_path)
    try:
        result = reconciler.reconcile(
            broker_response=_response(
                broker_status="rejected",
                return_code=10021,
                return_message="Price changed",
                filled_volume=0,
                filled_price=None,
                position_ticket=None,
            ),
            position_state_observation_id="post-submit-observation",
        )

        assert result.status == "rejected_by_broker"
        stored = log.demo_execution_receipt_reconciliations()
        assert stored[0]["status"] == "rejected_by_broker"
    finally:
        log.close()


def test_records_unmatched_when_position_ticket_is_not_observed(tmp_path: Path) -> None:
    log, reconciler = _setup(tmp_path)
    try:
        result = reconciler.reconcile(
            broker_response=_response(position_ticket="not-observed"),
            position_state_observation_id="post-submit-observation",
        )

        assert result.status == "unmatched"
        assert log.demo_execution_receipt_reconciliations()[0]["status"] == "unmatched"
    finally:
        log.close()
