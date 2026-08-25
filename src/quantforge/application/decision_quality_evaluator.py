"""Research-only observation of later market levels after audited decisions.

This evaluator records subsequent accepted USDJPY M1 candle facts.  It neither
models a fill nor makes a profitability claim; TP/SL results are strictly
price-level observations and same-candle ordering remains explicitly unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


@dataclass(frozen=True, slots=True)
class DecisionQualityResult:
    """One durable, non-executable outcome observation."""

    decision_observation_id: str
    status: str
    evaluation: dict[str, Any]


class DecisionQualityEvaluator:
    """Evaluate audited intents only against later accepted MT5 snapshots."""

    def __init__(
        self,
        audit_log: SQLiteMarketObservationLog,
        *,
        freshness_limit: timedelta = timedelta(seconds=90),
        max_candles: int = 60,
    ) -> None:
        if max_candles < 1:
            raise ValueError("max_candles must be positive")
        self._audit_log = audit_log
        self._freshness_limit = freshness_limit
        self._max_candles = max_candles

    def evaluate_available(self) -> list[DecisionQualityResult]:
        """Evaluate eligible, not-yet-audited accepted decisions exactly once."""
        evaluated_ids = {
            item["decision_observation_id"]
            for item in self._audit_log.decision_quality_evaluations(limit=10_000)
        }
        snapshots = self._accepted_snapshots()
        snapshot_by_id = {item["observation_id"]: item for item in snapshots}
        results: list[DecisionQualityResult] = []
        for decision in self._audit_log.agent_decisions(limit=10_000):
            observation_id = decision["observation_id"]
            if observation_id in evaluated_ids or decision["status"] != "accepted":
                continue
            intent = decision["trade_intent"]
            source = snapshot_by_id.get(observation_id)
            if not isinstance(intent, dict) or source is None:
                continue
            result = self._evaluate(decision, source, snapshots)
            self._audit_log.append_decision_quality_evaluation(
                decision_observation_id=observation_id,
                evaluation_status=result.status,
                evaluation=result.evaluation,
            )
            results.append(result)
        return results

    def _evaluate(
        self,
        decision: dict[str, Any],
        source: dict[str, Any],
        snapshots: list[dict[str, Any]],
    ) -> DecisionQualityResult:
        intent = decision["trade_intent"]
        assert isinstance(intent, dict)
        snapshot = source["snapshot"]
        assert isinstance(snapshot, dict)
        decision_time = _utc(intent["timestamp"])
        source_time = _utc(snapshot["observed_at_utc"])
        persisted_at = _utc(decision["created_at_utc"])
        if (
            decision_time is None
            or source_time is None
            or persisted_at is None
            or decision_time != source_time
            or persisted_at - source_time > self._freshness_limit
        ):
            return DecisionQualityResult(
                str(decision["observation_id"]),
                "skipped",
                {
                    "outcome_classification": "SKIPPED_NOT_TIMELY",
                    "decision_timestamp": intent.get("timestamp"),
                    "reason": "decision was not accepted within the freshness limit",
                },
            )
        expiry = _utc(intent["expiry"])
        if expiry is None or expiry <= decision_time:
            return DecisionQualityResult(
                str(decision["observation_id"]),
                "skipped",
                {
                    "outcome_classification": "SKIPPED_INVALID_EXPIRY",
                    "decision_timestamp": intent.get("timestamp"),
                },
            )
        candles = self._subsequent_candles(snapshots, decision_time, expiry)
        base = {
            "decision_timestamp": decision_time.isoformat(),
            "direction": intent["direction"],
            "entry_price": intent["entry_price"],
            "stop_loss": intent["stop_loss"],
            "take_profit": intent["take_profit"],
            "subsequent_market_observations": candles,
            "observation_only": True,
            "no_fill_or_profitability_inference": True,
        }
        if intent["direction"] == "HOLD":
            latest = candles[-1]["close_time_utc"] if candles else None
            return DecisionQualityResult(
                str(decision["observation_id"]),
                "evaluated",
                {
                    **base,
                    "outcome_classification": "HOLD_OBSERVATION",
                    "maximum_favorable_excursion": None,
                    "maximum_adverse_excursion": None,
                    "elapsed_seconds_to_outcome": _elapsed(decision_time, latest),
                    "tp_or_sl_reached_first": None,
                },
            )
        return DecisionQualityResult(
            str(decision["observation_id"]),
            "evaluated",
            self._directional_outcome(base, intent, candles, decision_time),
        )

    def _accepted_snapshots(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self._audit_log.research_snapshots(limit=10_000)
            if item["validation_status"] == "accepted"
            and isinstance(item["snapshot"], dict)
        ]

    def _subsequent_candles(
        self,
        snapshots: list[dict[str, Any]],
        decision_time: datetime,
        expiry: datetime,
    ) -> list[dict[str, Any]]:
        unique: dict[datetime, dict[str, Any]] = {}
        for item in snapshots:
            snapshot = item["snapshot"]
            assert isinstance(snapshot, dict)
            candle = snapshot["candle"]
            open_time = _utc(candle["open_time_utc"])
            if open_time is None:
                continue
            close_time = open_time + timedelta(minutes=1)
            if close_time <= decision_time or close_time > expiry:
                continue
            unique[open_time] = {
                "open_time_utc": open_time.isoformat(),
                "close_time_utc": close_time.isoformat(),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
            }
        return [unique[key] for key in sorted(unique)][: self._max_candles]

    @staticmethod
    def _directional_outcome(
        base: dict[str, Any],
        intent: dict[str, Any],
        candles: list[dict[str, Any]],
        decision_time: datetime,
    ) -> dict[str, Any]:
        direction = str(intent["direction"])
        entry = float(intent["entry_price"])
        stop = float(intent["stop_loss"])
        target = float(intent["take_profit"])
        mfe = 0.0
        mae = 0.0
        outcome = "NO_EXIT_LEVEL_REACHED"
        elapsed: float | None = _elapsed(
            decision_time, candles[-1]["close_time_utc"] if candles else None
        )
        for candle in candles:
            high = float(candle["high"])
            low = float(candle["low"])
            if direction == "BUY":
                mfe = max(mfe, high - entry)
                mae = max(mae, entry - low)
                target_hit, stop_hit = high >= target, low <= stop
            else:
                mfe = max(mfe, entry - low)
                mae = max(mae, high - entry)
                target_hit, stop_hit = low <= target, high >= stop
            if target_hit and stop_hit:
                outcome = "TP_AND_SL_SAME_CANDLE_AMBIGUOUS"
            elif target_hit:
                outcome = "TP_LEVEL_REACHED_FIRST"
            elif stop_hit:
                outcome = "SL_LEVEL_REACHED_FIRST"
            else:
                continue
            elapsed = _elapsed(decision_time, candle["close_time_utc"])
            break
        return {
            **base,
            "outcome_classification": outcome,
            "tp_or_sl_reached_first": outcome,
            "maximum_favorable_excursion": mfe,
            "maximum_adverse_excursion": mae,
            "elapsed_seconds_to_outcome": elapsed,
        }


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return None
    return timestamp.astimezone(UTC)


def _elapsed(start: datetime, end: str | None) -> float | None:
    timestamp = _utc(end)
    return None if timestamp is None else (timestamp - start).total_seconds()
