"""Deterministic, non-executable USDJPY MT5 demo risk gate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any

from quantforge.config.settings import ForexRiskSettings


@dataclass(frozen=True, slots=True)
class ForexRiskContext:
    """Account facts that cannot be inferred safely from one market snapshot."""

    start_of_day_equity: Decimal

    def __post_init__(self) -> None:
        if self.start_of_day_equity <= 0:
            raise ValueError("start_of_day_equity must be positive")


@dataclass(frozen=True, slots=True)
class ForexRiskDecision:
    """A position-size proposal only; it is explicitly not an order."""

    status: str
    reasons: tuple[str, ...]
    proposed_volume: Decimal | None = None
    proposed_risk_usd: Decimal | None = None

    @property
    def approved(self) -> bool:
        return self.status == "approved"

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


class ForexRiskGate:
    """Validate USDJPY intent shape, runtime broker facts, and account limits."""

    def __init__(self, settings: ForexRiskSettings) -> None:
        self._settings = settings

    def evaluate(
        self,
        *,
        trade_intent: dict[str, Any],
        market_snapshot: dict[str, Any],
        context: ForexRiskContext | None,
    ) -> ForexRiskDecision:
        if trade_intent.get("direction") == "HOLD":
            return ForexRiskDecision("not_applicable", ("HOLD has no trade risk",))
        if context is None:
            return ForexRiskDecision(
                "rejected", ("daily start-of-day equity baseline is unavailable",)
            )
        reasons = self._validate(trade_intent, market_snapshot, context)
        if reasons:
            return ForexRiskDecision("rejected", tuple(reasons))
        entry = _decimal(trade_intent["entry_price"])
        stop = _decimal(trade_intent["stop_loss"])
        requested_risk = _decimal(trade_intent["risk_percent"])
        specification = market_snapshot["instrument"]["specification"]
        contract_size = _decimal(specification["contract_size"])
        # USDJPY has JPY P/L per lot. Convert deterministically to the USD
        # account currency at the proposed entry price; no broker API is called.
        risk_per_lot_usd = abs(entry - stop) * contract_size / entry
        budget_usd = _decimal(market_snapshot["account"]["equity"]) * requested_risk
        step = _decimal(specification["volume_step"])
        volume = _snap_down(budget_usd / risk_per_lot_usd, step)
        broker_max = _decimal(specification["volume_max"])
        effective_max = min(broker_max, Decimal(str(self._settings.max_position_size)))
        volume = min(volume, effective_max)
        minimum = _decimal(specification["volume_min"])
        if volume < minimum:
            return ForexRiskDecision(
                "rejected", ("risk budget is smaller than broker minimum volume",)
            )
        proposed_risk = volume * risk_per_lot_usd
        return ForexRiskDecision("approved", (), volume, proposed_risk)

    def _validate(
        self,
        intent: dict[str, Any],
        snapshot: dict[str, Any],
        context: ForexRiskContext,
    ) -> list[str]:
        reasons: list[str] = []
        instrument = snapshot.get("instrument", {})
        account = snapshot.get("account", {})
        quote = snapshot.get("quote", {})
        specification = instrument.get("specification", {})
        if instrument.get("canonical_symbol") != "USDJPY":
            reasons.append("unsupported instrument")
        if account.get("currency") != "USD":
            reasons.append("USD account currency is required for USDJPY sizing")
        direction = intent.get("direction")
        if direction not in {"BUY", "SELL"}:
            reasons.append("direction must be BUY or SELL")
            return reasons
        try:
            entry = _decimal(intent["entry_price"])
            stop = _decimal(intent["stop_loss"])
            target = _decimal(intent["take_profit"])
            requested_risk = _decimal(intent["risk_percent"])
            equity = _decimal(account["equity"])
            spread = _decimal(quote["spread_points"])
            minimum = _decimal(specification["volume_min"])
            maximum = _decimal(specification["volume_max"])
            step = _decimal(specification["volume_step"])
            contract_size = _decimal(specification["contract_size"])
        except (KeyError, ValueError, ArithmeticError):
            return [*reasons, "invalid numeric risk input"]
        if entry <= 0 or stop <= 0 or target <= 0:
            reasons.append("entry, stop loss, and take profit must be positive")
        if direction == "BUY" and not stop < entry < target:
            reasons.append("invalid BUY protective levels")
        if direction == "SELL" and not target < entry < stop:
            reasons.append("invalid SELL protective levels")
        configured_risk = Decimal(str(self._settings.risk_per_trade))
        if not Decimal("0") < requested_risk <= configured_risk:
            reasons.append("requested risk exceeds configured risk per trade")
        if spread < 0 or spread > Decimal(str(self._settings.max_spread_points)):
            reasons.append("spread exceeds configured maximum")
        if minimum <= 0 or maximum < minimum or step <= 0 or contract_size <= 0:
            reasons.append("invalid broker lot specification")
        positions = snapshot.get("position_state", {}).get("positions", [])
        if len(positions) >= self._settings.max_open_positions:
            reasons.append("maximum open positions reached")
        daily_loss = (
            context.start_of_day_equity - equity
        ) / context.start_of_day_equity
        if daily_loss >= Decimal(str(self._settings.max_daily_loss)):
            reasons.append("maximum daily loss reached")
        return reasons


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a decimal")
    return Decimal(str(value))


def _snap_down(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step
