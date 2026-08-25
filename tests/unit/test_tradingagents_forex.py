from __future__ import annotations

# ruff: noqa: E501, E701
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quantforge.application.tradingagents_forex import TradingAgentsForexResearch
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

NOW = datetime(2026, 8, 24, 16, 35, tzinfo=UTC)


class Backend:
    def __init__(self, final: str) -> None:
        self.final = final
        self.calls = 0

    def complete(self, role: str, context: dict[str, object]) -> str:
        self.calls += 1
        return self.final if role == "risk_portfolio" else role + " report"


def snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {"instrument": {"canonical_symbol": "USDJPY"}, "candle": {"timeframe": "M1"}, "observed_at_utc": NOW.isoformat()}
    for key, item in changes.items(): value[key] = item
    return value


def intent(direction: str = "BUY", **changes: object) -> str:
    value: dict[str, object] = {"symbol": "USDJPY", "timestamp": NOW.isoformat(), "direction": direction, "entry_type": "market", "entry_price": 159.1, "stop_loss": 159.0, "take_profit": 159.3, "risk_percent": 0.005, "confidence": 0.7, "reason": "test", "expiry": (NOW + timedelta(minutes=2)).isoformat()}
    if direction == "SELL": value.update({"stop_loss": 159.2, "take_profit": 158.9})
    value.update(changes)
    return json.dumps(value)


def run(
    tmp_path: Path,
    final: str,
    market: dict[str, object] | None = None,
    *,
    backend: Backend | None = None,
):
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    log.append_research_snapshot(
        observation_id="obs",
        candle_open_time_utc=NOW,
        validation_status="accepted",
        validation_issues=(),
        snapshot=market or snapshot(),
    )
    used_backend = backend or Backend(final)
    result = TradingAgentsForexResearch(log, used_backend).run_latest(evaluated_at=NOW)
    assert result is not None
    return result, log, used_backend


@pytest.mark.parametrize("direction", ["BUY", "SELL", "HOLD"])
def test_valid_intents_are_audited(tmp_path: Path, direction: str) -> None:
    result, log, _ = run(tmp_path, intent(direction))
    try: assert result.accepted and log.agent_decisions()[0]["status"] == "accepted"
    finally: log.close()


@pytest.mark.parametrize("final,reason", [("no", "malformed agent output"), (intent(stop_loss=0), "missing protective levels"), (intent(risk_percent=2), "invalid risk_percent")])
def test_invalid_agent_output_is_rejected(tmp_path: Path, final: str, reason: str) -> None:
    result, log, _ = run(tmp_path, final)
    try: assert not result.accepted and reason in result.reasons and log.agent_decisions()[0]["status"] == "rejected"
    finally: log.close()


@pytest.mark.parametrize("market,reason", [(snapshot(observed_at_utc=(NOW-timedelta(seconds=91)).isoformat()), "snapshot is stale"), (snapshot(instrument={"canonical_symbol": "EURUSD"}), "unsupported symbol")])
def test_stale_or_unsupported_snapshot_is_rejected(tmp_path: Path, market: dict[str, object], reason: str) -> None:
    result, log, _ = run(tmp_path, intent(), market)
    try: assert not result.accepted and reason in result.reasons
    finally: log.close()


@pytest.mark.parametrize(
    ("final", "reason"),
    [
        (intent(timestamp="2026-08-24T16:35:00"), "invalid decision timestamp"),
        (intent(timestamp=(NOW + timedelta(seconds=1)).isoformat()), "decision timestamp does not match snapshot"),
        (intent(expiry=NOW.isoformat()), "expiry must be later than decision timestamp"),
        (intent(expiry="not-a-timestamp"), "invalid expiry"),
        (intent(risk_percent=0.006), "invalid risk_percent"),
    ],
)
def test_timestamp_expiry_and_configured_risk_are_validated(
    tmp_path: Path, final: str, reason: str
) -> None:
    result, log, _ = run(tmp_path, final)
    try:
        assert not result.accepted
        assert reason in result.reasons
    finally:
        log.close()


def test_different_decision_timestamp_is_rejected(tmp_path: Path) -> None:
    result, log, _ = run(
        tmp_path, intent(timestamp=(NOW + timedelta(seconds=1)).isoformat())
    )
    try:
        assert not result.accepted
        assert result.reasons == ("decision timestamp does not match snapshot",)
    finally:
        log.close()


def test_snapshot_timestamp_remains_valid_for_a_matching_intent(tmp_path: Path) -> None:
    result, log, _ = run(tmp_path, intent(timestamp=NOW.isoformat()))
    try:
        assert result.accepted
        assert log.agent_decisions()[0]["status"] == "accepted"
    finally:
        log.close()


def test_existing_observation_decision_is_not_sent_to_model_twice(tmp_path: Path) -> None:
    backend = Backend(intent())
    result, log, _ = run(tmp_path, intent(), backend=backend)
    try:
        assert result.accepted
        assert backend.calls == 5
        repeat = TradingAgentsForexResearch(log, backend).run_latest(evaluated_at=NOW)
        assert repeat is not None and repeat.accepted
        assert backend.calls == 5
        assert len(log.agent_decisions()) == 1
    finally:
        log.close()


def test_response_becomes_rejected_if_snapshot_stales_during_model_work(
    tmp_path: Path,
) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    log.append_research_snapshot(
        observation_id="obs",
        candle_open_time_utc=NOW,
        validation_status="accepted",
        validation_issues=(),
        snapshot=snapshot(),
    )
    try:
        result = TradingAgentsForexResearch(log, Backend(intent())).run_latest(
            evaluated_at=NOW,
            completed_at=NOW + timedelta(seconds=91),
        )
        assert result is not None
        assert not result.accepted
        assert result.reasons == ("snapshot is stale",)
        assert log.agent_decisions()[0]["status"] == "rejected"
    finally:
        log.close()
