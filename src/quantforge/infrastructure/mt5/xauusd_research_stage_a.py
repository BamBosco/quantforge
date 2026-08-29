"""Candidate 006's unsendable, provisional XAUUSD Stage A constructor."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from quantforge.config.xauusd_research_stage_a import XAUUSDResearchStageASettings
from quantforge.infrastructure.mt5.execution_stage_a import StageAExecutionResult


class XAUUSDResearchStageAGateway:
    """Construct a research artefact only; this type cannot submit an order."""

    def __init__(self, settings: XAUUSDResearchStageASettings) -> None:
        self._settings = settings

    def construct(
        self,
        *,
        trade_intent: dict[str, Any],
        risk_decision: dict[str, Any],
        market_snapshot: dict[str, Any],
        evaluated_at: datetime,
    ) -> StageAExecutionResult:
        now = evaluated_at.astimezone(UTC)
        reasons = self._validate(trade_intent, risk_decision, market_snapshot, now)
        if reasons:
            return StageAExecutionResult("rejected", tuple(reasons), None)
        return StageAExecutionResult(
            "constructed",
            (),
            {
                "stage": "A",
                "classification": "provisional_research_only",
                "broker_symbol": "XAUUSD",
                "action": "RESEARCH_ONLY",
                "send_allowed": False,
                "submission_status": "prohibited_stage_a",
                "execution_deviation_points": 0,
                "volume": risk_decision["risk_decision"]["proposed_volume"],
                "reference_price": trade_intent["entry_price"],
                "review_by_utc": self._settings.review_by_utc.isoformat(),
            },
        )

    def _validate(
        self,
        intent: dict[str, Any],
        risk: dict[str, Any],
        snapshot: dict[str, Any],
        now: datetime,
    ) -> list[str]:
        reasons: list[str] = []
        if now >= self._settings.review_by_utc:
            reasons.append("provisional research parameters have expired for review")
        local_now = now.astimezone(ZoneInfo(self._settings.timezone))
        if local_now.weekday() >= 5 or not (
            self._settings.session_start
            <= local_now.timetz().replace(tzinfo=None)
            < self._settings.session_end
        ):
            reasons.append("outside provisional XAUUSD research session")
        if intent.get("symbol") != "XAUUSD":
            reasons.append("unexpected intent symbol")
        if risk.get("status") != "approved":
            reasons.append("risk decision is not approved")
            return reasons
        payload = risk.get("risk_decision")
        if not isinstance(payload, dict) or payload.get("non_executable") is not True:
            reasons.append("risk decision is not a non-executable audit result")
            return reasons
        quote, specification = _quote_and_specification(snapshot, reasons)
        if quote is None or specification is None:
            return reasons
        try:
            spread = Decimal(str(quote["spread_points"]))
            bid = Decimal(str(quote["bid"]))
            ask = Decimal(str(quote["ask"]))
            entry = Decimal(str(intent["entry_price"]))
            volume = Decimal(str(payload["proposed_volume"]))
        except (KeyError, InvalidOperation, ValueError):
            return [*reasons, "invalid provisional research input"]
        if not Decimal("0") < spread <= self._settings.maximum_spread_points:
            reasons.append("spread exceeds provisional research cap")
        if volume <= 0 or volume > self._settings.maximum_position_size:
            reasons.append("proposed volume exceeds provisional research cap")
        direction = intent.get("direction")
        reference = ask if direction == "BUY" else bid if direction == "SELL" else None
        if reference is None:
            reasons.append("direction must be BUY or SELL")
        elif entry != reference:
            reasons.append("zero-deviation research request requires exact quote")
        return reasons


def _quote_and_specification(
    snapshot: dict[str, Any], reasons: list[str]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    instrument = snapshot.get("instrument")
    quote = snapshot.get("quote")
    if (
        not isinstance(instrument, dict)
        or instrument.get("canonical_instrument") != "XAUUSD"
    ):
        reasons.append("unexpected snapshot instrument")
    if not isinstance(quote, dict):
        reasons.append("snapshot quote is unavailable")
    specification = (
        instrument.get("specification") if isinstance(instrument, dict) else None
    )
    if not isinstance(specification, dict):
        reasons.append("snapshot specification is unavailable")
    return (
        quote if isinstance(quote, dict) else None,
        specification if isinstance(specification, dict) else None,
    )
