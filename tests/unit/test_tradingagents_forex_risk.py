from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.application.tradingagents_forex import TradingAgentsForexResearch
from quantforge.config.settings import ForexRiskSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.risk.forex_gate import ForexRiskContext, ForexRiskGate

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


class Backend:
    def __init__(self, final: str) -> None:
        self._final = final

    def complete(self, role: str, context: dict[str, object]) -> str:
        return self._final if role == "risk_portfolio" else "research note"


def risk_settings() -> ForexRiskSettings:
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


def snapshot() -> dict[str, object]:
    return {
        "instrument": {
            "canonical_symbol": "USDJPY",
            "specification": {
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "contract_size": 100000.0,
            },
        },
        "candle": {"timeframe": "M1"},
        "quote": {"spread_points": 3.0},
        "account": {"currency": "USD", "equity": 10000.0},
        "position_state": {"positions": []},
        "observed_at_utc": NOW.isoformat(),
    }


def intent(direction: str = "BUY") -> str:
    value = {
        "symbol": "USDJPY",
        "timestamp": NOW.isoformat(),
        "direction": direction,
        "entry_type": "market",
        "entry_price": 160.0,
        "stop_loss": 159.8,
        "take_profit": 160.4,
        "risk_percent": 0.005 if direction != "HOLD" else 0,
        "confidence": 0.7,
        "reason": "test",
        "expiry": (NOW + timedelta(minutes=5)).isoformat(),
    }
    return json.dumps(value)


def run(tmp_path: Path, final: str, *, baseline: Decimal | None):
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    log.append_research_snapshot(
        observation_id="obs",
        candle_open_time_utc=NOW,
        validation_status="accepted",
        validation_issues=(),
        snapshot=snapshot(),
    )
    result = TradingAgentsForexResearch(
        log,
        Backend(final),
        risk_gate=ForexRiskGate(risk_settings()),
        risk_context_provider=lambda _: ForexRiskContext(baseline)
        if baseline is not None
        else None,
    ).run_latest(evaluated_at=NOW, completed_at=NOW)
    assert result is not None
    return result, log


def test_valid_buy_intent_flows_to_an_approved_non_executable_risk_decision(
    tmp_path: Path,
) -> None:
    result, log = run(tmp_path, intent(), baseline=Decimal("10000"))
    try:
        assert result.accepted
        risk = log.risk_decisions()[0]
        assert risk["status"] == "approved"
        assert Decimal(risk["risk_decision"]["proposed_volume"]) == Decimal("0.10")
        assert risk["risk_decision"]["non_executable"] is True
    finally:
        log.close()


def test_missing_daily_baseline_persists_a_risk_rejection(tmp_path: Path) -> None:
    result, log = run(tmp_path, intent(), baseline=None)
    try:
        assert result.accepted
        risk = log.risk_decisions()[0]
        assert risk["status"] == "rejected"
        assert risk["risk_decision"]["reasons"] == [
            "daily start-of-day equity baseline is unavailable"
        ]
    finally:
        log.close()


def test_hold_remains_not_applicable_to_trade_risk(tmp_path: Path) -> None:
    result, log = run(tmp_path, intent("HOLD"), baseline=None)
    try:
        assert result.accepted
        assert log.risk_decisions()[0]["status"] == "not_applicable"
    finally:
        log.close()
