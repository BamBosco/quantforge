from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from quantforge.application.decision_quality_evaluator import DecisionQualityEvaluator
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

NOW = datetime.now(UTC).replace(microsecond=0)


def market_snapshot(
    open_time: datetime, *, observed_at: datetime, high: float, low: float
) -> dict[str, object]:
    return {
        "instrument": {"canonical_symbol": "USDJPY"},
        "candle": {
            "open_time_utc": open_time.isoformat(),
            "open": 159.0,
            "high": high,
            "low": low,
            "close": 159.0,
            "timeframe": "M1",
        },
        "observed_at_utc": observed_at.isoformat(),
    }


def intent(direction: str = "BUY", *, timestamp: datetime = NOW) -> dict[str, object]:
    return {
        "symbol": "USDJPY",
        "timestamp": timestamp.isoformat(),
        "direction": direction,
        "entry_type": "market",
        "entry_price": 159.0,
        "stop_loss": 158.9 if direction == "BUY" else 159.1,
        "take_profit": 159.1 if direction == "BUY" else 158.9,
        "risk_percent": 0.005 if direction != "HOLD" else 0,
        "confidence": 0.5,
        "reason": "test",
        "expiry": (timestamp + timedelta(minutes=10)).isoformat(),
    }


def add_snapshot(
    log: SQLiteMarketObservationLog,
    observation_id: str,
    open_time: datetime,
    *,
    observed_at: datetime,
    high: float,
    low: float,
) -> None:
    log.append_research_snapshot(
        observation_id=observation_id,
        candle_open_time_utc=open_time,
        validation_status="accepted",
        validation_issues=(),
        snapshot=market_snapshot(
            open_time, observed_at=observed_at, high=high, low=low
        ),
    )


def build_log(tmp_path: Path, direction: str = "BUY") -> SQLiteMarketObservationLog:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    add_snapshot(
        log,
        "decision",
        NOW - timedelta(minutes=1),
        observed_at=NOW,
        high=159.01,
        low=158.99,
    )
    log.append_agent_decision(
        observation_id="decision",
        status="accepted",
        reasons=(),
        agent_decision={"final": "test"},
        trade_intent=intent(direction),
    )
    return log


def test_buy_tp_level_is_observed_first_and_persisted(tmp_path: Path) -> None:
    log = build_log(tmp_path)
    add_snapshot(
        log,
        "later",
        NOW,
        observed_at=NOW + timedelta(minutes=1),
        high=159.11,
        low=158.98,
    )
    try:
        results = DecisionQualityEvaluator(log).evaluate_available()
        assert results[0].status == "evaluated"
        evaluation = results[0].evaluation
        assert evaluation["outcome_classification"] == "TP_LEVEL_REACHED_FIRST"
        assert evaluation["maximum_favorable_excursion"] == 0.11000000000001364
        assert evaluation["elapsed_seconds_to_outcome"] == 60.0
        assert evaluation["no_fill_or_profitability_inference"] is True
        assert log.decision_quality_evaluations()[0]["status"] == "evaluated"
    finally:
        log.close()


def test_same_candle_tp_and_sl_is_explicitly_ambiguous(tmp_path: Path) -> None:
    log = build_log(tmp_path)
    add_snapshot(
        log,
        "later",
        NOW,
        observed_at=NOW + timedelta(minutes=1),
        high=159.2,
        low=158.8,
    )
    try:
        evaluation = DecisionQualityEvaluator(log).evaluate_available()[0].evaluation
        assert evaluation["outcome_classification"] == "TP_AND_SL_SAME_CANDLE_AMBIGUOUS"
    finally:
        log.close()


def test_hold_records_market_observation_without_trade_inference(
    tmp_path: Path,
) -> None:
    log = build_log(tmp_path, "HOLD")
    add_snapshot(
        log,
        "later",
        NOW,
        observed_at=NOW + timedelta(minutes=1),
        high=159.2,
        low=158.8,
    )
    try:
        evaluation = DecisionQualityEvaluator(log).evaluate_available()[0].evaluation
        assert evaluation["outcome_classification"] == "HOLD_OBSERVATION"
        assert evaluation["tp_or_sl_reached_first"] is None
        assert evaluation["maximum_favorable_excursion"] is None
    finally:
        log.close()


def test_late_decision_is_skipped_under_existing_freshness_rule(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    old = NOW - timedelta(seconds=91)
    add_snapshot(
        log,
        "decision",
        old - timedelta(minutes=1),
        observed_at=old,
        high=159.01,
        low=158.99,
    )
    log.append_agent_decision(
        observation_id="decision",
        status="accepted",
        reasons=(),
        agent_decision={"final": "test"},
        trade_intent=intent(timestamp=old),
    )
    try:
        result = DecisionQualityEvaluator(log).evaluate_available()[0]
        assert result.status == "skipped"
        assert result.evaluation["outcome_classification"] == "SKIPPED_NOT_TIMELY"
    finally:
        log.close()
