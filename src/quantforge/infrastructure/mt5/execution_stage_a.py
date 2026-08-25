"""Stage-A MT5 request construction with an unconditional no-submit boundary.

This module is deliberately data-only.  It has no MetaTrader package import,
network client, terminal call, or method capable of transmitting a request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from quantforge.config.settings import DemoExecutionSettings, ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


@dataclass(frozen=True, slots=True)
class StageAExecutionResult:
    """Constructed broker request or deterministic rejection; never an order."""

    status: str
    reasons: tuple[str, ...]
    request: dict[str, Any] | None


class MT5StageAExecutionGateway:
    """Build and validate an unsendable MT5-shaped demo request."""

    def __init__(self, settings: ForexMT5DemoSettings) -> None:
        self._settings = settings

    def construct(
        self,
        *,
        trade_intent: dict[str, Any],
        risk_decision: dict[str, Any],
        market_snapshot: dict[str, Any],
        evaluated_at: datetime | None = None,
    ) -> StageAExecutionResult:
        now = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
        reasons = self._validate_configuration(self._settings.execution)
        reasons.extend(
            self._validate_inputs(trade_intent, risk_decision, market_snapshot, now)
        )
        if reasons:
            return StageAExecutionResult("rejected", tuple(reasons), None)
        request = self._request(trade_intent, risk_decision, market_snapshot)
        return StageAExecutionResult("constructed", (), request)

    def construct_from_audit(
        self,
        audit_log: SQLiteMarketObservationLog,
        *,
        observation_id: str,
        evaluated_at: datetime | None = None,
    ) -> StageAExecutionResult:
        """Build and persist one Stage-A request from existing research audit facts."""
        agent = audit_log.agent_decision_for_observation(observation_id)
        risk = audit_log.risk_decision_for_observation(observation_id)
        market = audit_log.research_snapshot_for_observation(observation_id)
        if (
            agent is None
            or risk is None
            or market is None
            or not isinstance(agent["trade_intent"], dict)
            or not isinstance(market["snapshot"], dict)
        ):
            result = StageAExecutionResult(
                "rejected",
                ("required audited intent, risk, or snapshot is missing",),
                None,
            )
        else:
            result = self.construct(
                trade_intent=agent["trade_intent"],
                risk_decision=risk,
                market_snapshot=market["snapshot"],
                evaluated_at=evaluated_at,
            )
        audit_log.append_execution_request(
            observation_id=observation_id,
            request_status=result.status,
            validation_issues=result.reasons,
            request=result.request,
        )
        return result

    @staticmethod
    def _validate_configuration(settings: DemoExecutionSettings) -> list[str]:
        reasons: list[str] = []
        if settings.account_mode != "demo":
            reasons.append("Stage A requires demo account mode")
        if settings.live_trading_enabled:
            reasons.append("live trading must remain disabled")
        if settings.order_submission_enabled:
            reasons.append("order submission must remain disabled in Stage A")
        return reasons

    def _validate_inputs(
        self,
        intent: dict[str, Any],
        risk: dict[str, Any],
        snapshot: dict[str, Any],
        now: datetime,
    ) -> list[str]:
        reasons: list[str] = []
        if risk.get("status") != "approved":
            reasons.append("risk decision is not approved")
            return reasons
        risk_payload = risk.get("risk_decision", {})
        if (
            not isinstance(risk_payload, dict)
            or risk_payload.get("non_executable") is not True
        ):
            reasons.append("risk decision is not a non-executable audit result")
        if intent.get("symbol") != self._settings.instrument.internal_symbol:
            reasons.append("unexpected intent symbol")
        instrument = snapshot.get("instrument", {})
        if instrument.get("broker_symbol") != self._settings.instrument.broker_symbol:
            reasons.append("unexpected broker symbol")
        if (
            instrument.get("canonical_symbol")
            != self._settings.instrument.internal_symbol
        ):
            reasons.append("unexpected canonical instrument")
        observed_at = _utc(snapshot.get("observed_at_utc"))
        if observed_at is None or now - observed_at > timedelta(
            seconds=self._settings.mt5.data_freshness_seconds
        ):
            reasons.append("market snapshot is stale")
        direction = intent.get("direction")
        entry_type = str(intent.get("entry_type", "")).lower()
        if direction not in {"BUY", "SELL"}:
            reasons.append("Stage A constructs BUY or SELL only")
        if entry_type not in {"market", "limit"}:
            reasons.append("unsupported entry type")
        try:
            volume = Decimal(str(risk_payload["proposed_volume"]))
            entry = Decimal(str(intent["entry_price"]))
            stop = Decimal(str(intent["stop_loss"]))
            target = Decimal(str(intent["take_profit"]))
            quote = snapshot["quote"]
            bid = Decimal(str(quote["bid"]))
            ask = Decimal(str(quote["ask"]))
            point = Decimal(str(instrument["specification"]["point"]))
            minimum = Decimal(str(instrument["specification"]["volume_min"]))
            maximum = Decimal(str(instrument["specification"]["volume_max"]))
            step = Decimal(str(instrument["specification"]["volume_step"]))
            supported_modes = instrument["specification"]["supported_filling_modes"]
        except (KeyError, ValueError, ArithmeticError, TypeError):
            return [*reasons, "invalid request construction input"]
        if volume < minimum or volume > maximum or volume % step != 0:
            reasons.append("proposed volume violates broker constraints")
        if point <= 0:
            reasons.append("invalid broker point")
        if self._settings.execution.filling_mode not in supported_modes:
            reasons.append("configured filling mode is unsupported by broker")
        if direction == "BUY" and not stop < entry < target:
            reasons.append("invalid BUY protective levels")
        if direction == "SELL" and not target < entry < stop:
            reasons.append("invalid SELL protective levels")
        request_price = ask if direction == "BUY" else bid
        if entry_type == "limit":
            request_price = entry
            if direction == "BUY" and request_price >= ask:
                reasons.append("BUY limit price must be below ask")
            if direction == "SELL" and request_price <= bid:
                reasons.append("SELL limit price must be above bid")
        else:
            price_delta_points = abs(request_price - entry) / point
            if price_delta_points > self._settings.execution.deviation_points:
                reasons.append(
                    "market price exceeds allowed deviation from risk reference"
                )
        return reasons

    def _request(
        self,
        intent: dict[str, Any],
        risk: dict[str, Any],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        direction = str(intent["direction"])
        entry_type = str(intent["entry_type"]).lower()
        quote = snapshot["quote"]
        price = intent["entry_price"]
        if entry_type == "market":
            price = quote["ask"] if direction == "BUY" else quote["bid"]
        action = f"{direction}_{entry_type.upper()}"
        return {
            "stage": "A",
            "action": action,
            "broker_symbol": self._settings.instrument.broker_symbol,
            "volume": risk["risk_decision"]["proposed_volume"],
            "price": price,
            "stop_loss": intent["stop_loss"],
            "take_profit": intent["take_profit"],
            "deviation_points": self._settings.execution.deviation_points,
            "filling_mode": self._settings.execution.filling_mode,
            "magic_number": self._settings.execution.magic_number,
            "send_allowed": False,
            "submission_status": "prohibited_stage_a",
            "risk_reference_price": intent["entry_price"],
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
