from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from quantforge.config.settings import ForexRiskSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.risk.forex_gate import ForexRiskContext, ForexRiskGate


def settings() -> ForexRiskSettings:
    return ForexRiskSettings(
        risk_per_trade=0.005,
        max_daily_loss=0.02,
        max_open_positions=1,
        max_spread_points=20,
        max_position_size=0.10,
        require_stop_loss=True,
        require_take_profit=True,
        broker_lot_constraints_source="mt5_symbol_info",
    )


def snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "instrument": {
            "canonical_symbol": "USDJPY",
            "specification": {
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "contract_size": 100000.0,
            },
        },
        "account": {"currency": "USD", "equity": 10000.0},
        "quote": {"spread_points": 3.0},
        "position_state": {"positions": []},
    }
    value.update(changes)
    return value


def intent(direction: str = "BUY", **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "direction": direction,
        "entry_price": 160.0,
        "stop_loss": 159.8,
        "take_profit": 160.4,
        "risk_percent": 0.005,
    }
    if direction == "SELL":
        value.update({"stop_loss": 160.2, "take_profit": 159.6})
    value.update(changes)
    return value


def evaluate(
    trade_intent: dict[str, object] | None = None,
    market_snapshot: dict[str, object] | None = None,
    *,
    start_of_day_equity: str = "10000",
):
    return ForexRiskGate(settings()).evaluate(
        trade_intent=trade_intent or intent(),
        market_snapshot=market_snapshot or snapshot(),
        context=ForexRiskContext(Decimal(start_of_day_equity)),
    )


def test_valid_intent_has_non_executable_lot_proposal() -> None:
    decision = evaluate()

    assert decision.approved
    assert decision.proposed_volume == Decimal("0.10")
    assert decision.proposed_risk_usd is not None
    assert decision.audit_payload()["non_executable"] is True


def test_hold_is_not_a_trade_proposal() -> None:
    decision = evaluate(intent("HOLD"))

    assert decision.status == "not_applicable"
    assert decision.proposed_volume is None


def test_rejects_excessive_spread_and_open_position() -> None:
    market = snapshot(
        quote={"spread_points": 21.0},
        position_state={"positions": [{"ticket": "existing"}]},
    )
    decision = evaluate(market_snapshot=market)

    assert not decision.approved
    assert decision.reasons == (
        "spread exceeds configured maximum",
        "maximum open positions reached",
    )


def test_rejects_daily_loss_and_risk_above_configured_limit() -> None:
    market = snapshot(account={"currency": "USD", "equity": 9799.0})
    decision = evaluate(intent(risk_percent=0.006), market, start_of_day_equity="10000")

    assert not decision.approved
    assert decision.reasons == (
        "requested risk exceeds configured risk per trade",
        "maximum daily loss reached",
    )


def test_rejects_invalid_protective_levels_and_account_currency() -> None:
    market = snapshot(account={"currency": "JPY", "equity": 10000.0})
    decision = evaluate(intent(stop_loss=160.1), market)

    assert not decision.approved
    assert decision.reasons == (
        "USD account currency is required for USDJPY sizing",
        "invalid BUY protective levels",
    )


def test_risk_result_is_persisted_as_non_executable_audit_data(tmp_path: Path) -> None:
    decision = evaluate()
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    try:
        assert log.append_risk_decision(
            observation_id="snapshot-1",
            risk_status=decision.status,
            risk_decision=decision.audit_payload(),
        )
        stored = log.risk_decisions()[0]
        assert stored["status"] == "approved"
        assert stored["risk_decision"]["non_executable"] is True
    finally:
        log.close()
