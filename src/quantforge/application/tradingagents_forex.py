"""Non-executable USD/JPY research adapter using the TradingAgents role sequence."""
# ruff: noqa: E501

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.risk.forex_gate import ForexRiskContext, ForexRiskGate


class ForexResearchBackend(Protocol):
    """A local LLM backend; it returns text and has no broker access."""

    def complete(self, role: str, context: dict[str, Any]) -> str: ...


@dataclass(frozen=True, slots=True)
class AgentDecisionResult:
    accepted: bool
    reasons: tuple[str, ...]
    trade_intent: dict[str, Any] | None


class TradingAgentsForexResearch:
    """Forex adaptation: technical → bull/bear → trader → risk/portfolio.

    It produces an unsized trade intent only. It has no MT5 or execution import.
    """

    def __init__(
        self,
        audit_log: SQLiteMarketObservationLog,
        backend: ForexResearchBackend,
        *,
        max_risk_percent: float = 0.005,
        risk_gate: ForexRiskGate | None = None,
        risk_context_provider: Callable[[dict[str, Any]], ForexRiskContext | None]
        | None = None,
    ) -> None:
        if not 0 < max_risk_percent <= 1:
            raise ValueError(
                "max_risk_percent must be greater than zero and at most one"
            )
        self._audit_log = audit_log
        self._backend = backend
        self._max_risk_percent = max_risk_percent
        self._risk_gate = risk_gate
        self._risk_context_provider = risk_context_provider

    def run_latest(
        self,
        *,
        evaluated_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> AgentDecisionResult | None:
        accepted = self._audit_log.latest_accepted_research_snapshot()
        if accepted is None:
            return None
        existing = self._audit_log.agent_decision_for_observation(
            str(accepted["observation_id"])
        )
        if existing is not None:
            return AgentDecisionResult(
                existing["status"] == "accepted",
                tuple(str(reason) for reason in existing["reasons"]),
                existing["trade_intent"],
            )
        snapshot = accepted["snapshot"]
        assert isinstance(snapshot, dict)
        now = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
        reasons = self._snapshot_issues(snapshot, now)
        raw: dict[str, Any] = {}
        intent: dict[str, Any] | None = None
        if not reasons:
            reports: dict[str, str] = {}
            for role in ("technical", "bull", "bear", "trader", "risk_portfolio"):
                reports[role] = self._backend.complete(
                    role, {"snapshot": snapshot, "reports": reports}
                )
            raw = {"reports": reports, "final": reports["risk_portfolio"]}
            intent, reasons = self._parse_intent(
                reports["risk_portfolio"], snapshot, self._max_risk_percent
            )
            finished = (completed_at or evaluated_at or datetime.now(UTC)).astimezone(
                UTC
            )
            if not reasons:
                reasons = self._snapshot_issues(snapshot, finished)
                if reasons:
                    intent = None
        result = AgentDecisionResult(not reasons, tuple(reasons), intent)
        self._audit_log.append_agent_decision(
            observation_id=str(accepted["observation_id"]),
            status="accepted" if result.accepted else "rejected",
            reasons=result.reasons,
            agent_decision=raw,
            trade_intent=intent,
        )
        if result.accepted and intent is not None and self._risk_gate is not None:
            context = (
                self._risk_context_provider(snapshot)
                if self._risk_context_provider is not None
                else None
            )
            risk_result = self._risk_gate.evaluate(
                trade_intent=intent,
                market_snapshot=snapshot,
                context=context,
            )
            self._audit_log.append_risk_decision(
                observation_id=str(accepted["observation_id"]),
                risk_status=risk_result.status,
                risk_decision=risk_result.audit_payload(),
            )
        return result

    @staticmethod
    def _snapshot_issues(snapshot: dict[str, Any], now: datetime) -> list[str]:
        candle = snapshot.get("candle", {})
        instrument = snapshot.get("instrument", {})
        observed = snapshot.get("observed_at_utc")
        if instrument.get("canonical_symbol") != "USDJPY":
            return ["unsupported symbol"]
        if candle.get("timeframe") != "M1":
            return ["unsupported timeframe"]
        try:
            timestamp = datetime.fromisoformat(str(observed)).astimezone(UTC)
        except ValueError:
            return ["invalid snapshot timestamp"]
        if now - timestamp > timedelta(seconds=90):
            return ["snapshot is stale"]
        return []

    @staticmethod
    def _parse_intent(
        text: str, snapshot: dict[str, Any], max_risk_percent: float
    ) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None, ["malformed agent output"]
        if not isinstance(value, dict):
            return None, ["malformed agent output"]
        required = {
            "symbol",
            "timestamp",
            "direction",
            "entry_type",
            "entry_price",
            "stop_loss",
            "take_profit",
            "risk_percent",
            "confidence",
            "reason",
            "expiry",
        }
        missing = required.difference(value)
        if missing:
            return None, ["missing trade intent fields: " + ", ".join(sorted(missing))]
        if value["symbol"] != "USDJPY":
            return None, ["unsupported trade intent symbol"]
        decision_time = TradingAgentsForexResearch._utc_timestamp(
            value["timestamp"], "invalid decision timestamp"
        )
        if decision_time is None:
            return None, ["invalid decision timestamp"]
        snapshot_time = TradingAgentsForexResearch._utc_timestamp(
            snapshot.get("observed_at_utc"), "invalid snapshot timestamp"
        )
        if snapshot_time is None or decision_time != snapshot_time:
            return None, ["decision timestamp does not match snapshot"]
        expiry = TradingAgentsForexResearch._utc_timestamp(
            value["expiry"], "invalid expiry"
        )
        if expiry is None:
            return None, ["invalid expiry"]
        if expiry <= decision_time:
            return None, ["expiry must be later than decision timestamp"]
        if value["direction"] == "HOLD":
            return value, []
        if value["direction"] not in {"BUY", "SELL"}:
            return None, ["invalid direction"]
        for field in (
            "entry_price",
            "stop_loss",
            "take_profit",
            "risk_percent",
            "confidence",
        ):
            if (
                not isinstance(value[field], (int, float))
                or isinstance(value[field], bool)
                or not math.isfinite(float(value[field]))
            ):
                return None, [f"invalid {field}"]
        if not 0 < float(value["risk_percent"]) <= max_risk_percent:
            return None, ["invalid risk_percent"]
        if value["stop_loss"] <= 0 or value["take_profit"] <= 0:
            return None, ["missing protective levels"]
        if (
            value["direction"] == "BUY"
            and not value["stop_loss"] < value["entry_price"] < value["take_profit"]
        ):
            return None, ["invalid BUY protective levels"]
        if (
            value["direction"] == "SELL"
            and not value["take_profit"] < value["entry_price"] < value["stop_loss"]
        ):
            return None, ["invalid SELL protective levels"]
        return value, []

    @staticmethod
    def _utc_timestamp(value: Any, _error: str) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError:
            return None
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return None
        return timestamp.astimezone(UTC)
