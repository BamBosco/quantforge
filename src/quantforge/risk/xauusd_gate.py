"""Candidate 006 XAUUSD-only, non-executable deterministic sizing foundation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class XAUUSDRiskPolicy:
    """Policies must be explicitly supplied; this type has no defaults."""

    risk_per_trade: Decimal | None = None
    maximum_position_size: Decimal | None = None


@dataclass(frozen=True, slots=True)
class XAUUSDRiskDecision:
    status: str
    reasons: tuple[str, ...]
    proposed_volume: Decimal | None = None
    proposed_risk_usd: Decimal | None = None

    def audit_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "proposed_volume": str(self.proposed_volume)
            if self.proposed_volume is not None
            else None,
            "proposed_risk_usd": str(self.proposed_risk_usd)
            if self.proposed_risk_usd is not None
            else None,
            "non_executable": True,
        }


class XAUUSDRiskGate:
    """Size XAUUSD only from observed USD tick-loss metadata and explicit policy."""

    def evaluate(
        self,
        *,
        trade_intent: dict[str, Any],
        broker_metadata: dict[str, Any],
        account_equity: Decimal,
        policy: XAUUSDRiskPolicy,
    ) -> XAUUSDRiskDecision:
        reasons = _validate(trade_intent, broker_metadata, account_equity, policy)
        if reasons:
            return XAUUSDRiskDecision("rejected", tuple(reasons))
        assert policy.risk_per_trade is not None
        assert policy.maximum_position_size is not None
        entry = _decimal(trade_intent["entry_price"])
        stop = _decimal(trade_intent["stop_loss"])
        tick_size = _decimal(broker_metadata["tick_size"])
        tick_value_loss = _decimal(broker_metadata["tick_value_loss"])
        risk_per_lot = abs(entry - stop) / tick_size * tick_value_loss
        budget = account_equity * policy.risk_per_trade
        step = _decimal(broker_metadata["volume_step"])
        volume = _snap_down(budget / risk_per_lot, step)
        maximum = min(
            _decimal(broker_metadata["volume_max"]), policy.maximum_position_size
        )
        volume = min(volume, maximum)
        minimum = _decimal(broker_metadata["volume_min"])
        if volume < minimum:
            return XAUUSDRiskDecision(
                "rejected", ("risk budget is smaller than broker minimum volume",)
            )
        return XAUUSDRiskDecision("approved", (), volume, volume * risk_per_lot)


def _validate(
    intent: dict[str, Any],
    metadata: dict[str, Any],
    equity: Decimal,
    policy: XAUUSDRiskPolicy,
) -> list[str]:
    reasons: list[str] = []
    if policy.risk_per_trade is None:
        reasons.append("Candidate 006 risk-per-trade policy is unresolved")
    if policy.maximum_position_size is None:
        reasons.append("Candidate 006 maximum-position policy is unresolved")
    if metadata.get("symbol") != "XAUUSD":
        reasons.append("unsupported instrument")
    if metadata.get("account_currency") != "USD":
        reasons.append("USD account currency is required for XAUUSD sizing")
    if metadata.get("profit_currency") != "USD":
        reasons.append("USD profit currency is required for XAUUSD sizing")
    if metadata.get("trade_calculation_mode") != 0:
        reasons.append("unsupported XAUUSD trade calculation mode")
    try:
        entry = _decimal(intent["entry_price"])
        stop = _decimal(intent["stop_loss"])
        target = _decimal(intent["take_profit"])
        tick_size = _decimal(metadata["tick_size"])
        tick_value_loss = _decimal(metadata["tick_value_loss"])
        minimum = _decimal(metadata["volume_min"])
        maximum = _decimal(metadata["volume_max"])
        step = _decimal(metadata["volume_step"])
    except (KeyError, ValueError):
        return [*reasons, "invalid XAUUSD broker risk metadata"]
    direction = intent.get("direction")
    if direction == "BUY" and not stop < entry < target:
        reasons.append("invalid BUY protective levels")
    elif direction == "SELL" and not target < entry < stop:
        reasons.append("invalid SELL protective levels")
    elif direction not in {"BUY", "SELL"}:
        reasons.append("direction must be BUY or SELL")
    if tick_size <= 0 or tick_value_loss <= 0:
        reasons.append("invalid XAUUSD tick risk metadata")
    if minimum <= 0 or maximum < minimum or step <= 0:
        reasons.append("invalid XAUUSD broker volume metadata")
    if equity <= 0:
        reasons.append("account equity must be positive")
    if policy.risk_per_trade is not None and policy.risk_per_trade <= 0:
        reasons.append("risk-per-trade policy must be positive")
    if policy.maximum_position_size is not None and policy.maximum_position_size <= 0:
        reasons.append("maximum-position policy must be positive")
    return reasons


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    return Decimal(str(value))


def _snap_down(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step
