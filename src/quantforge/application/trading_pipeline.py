"""Paper-only orchestration from a validated signal to an approved order."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID, uuid4

from quantforge.domain.events import (
    OrderApproved,
    RiskDecisionRecorded,
    TradeIntentGenerated,
)
from quantforge.journal.sqlite import SQLiteEventJournal
from quantforge.risk.limits import (
    AccountRiskSnapshot,
    RiskDecision,
    RiskLimits,
    SizingRequest,
    assess_pre_trade_risk,
)
from quantforge.risk.reservations import ConditionalRiskReservations, RiskReservation


@dataclass(frozen=True, slots=True)
class TradingSignal:
    """Strategy output before it becomes a risk-owned trade intent."""

    strategy_id: str
    instrument: str
    side: str
    entry_price: Decimal
    stop_loss_price: Decimal
    rationale: str
    target_price: Decimal | None = None
    scheduled_exit_at: datetime | None = None
    signal_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class MarketFact:
    """Validated point-in-time facts necessary for a paper risk decision."""

    instrument: str
    bid: Decimal
    ask: Decimal
    observed_at: datetime
    value_per_price_unit_per_lot: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal


@dataclass(frozen=True, slots=True)
class PipelineResult:
    intent: TradeIntentGenerated
    decision: RiskDecisionRecorded
    order: OrderApproved | None


@dataclass(frozen=True, slots=True)
class ConditionalPipelineResult:
    """Two independently approved orders bound by one OCO risk reservation."""

    results: tuple[PipelineResult, ...]
    reservation: RiskReservation | None


class PaperTradingPipeline:
    """Fail-closed application service. It has no broker dependency."""

    def __init__(
        self,
        *,
        limits: RiskLimits,
        policy_version: str,
        max_market_age: timedelta,
        approval_ttl: timedelta,
        journal: SQLiteEventJournal | None = None,
        reservations: ConditionalRiskReservations | None = None,
    ) -> None:
        if max_market_age <= timedelta() or approval_ttl <= timedelta():
            raise ValueError("market age and approval TTL must be positive")
        self._limits = limits
        self._policy_version = policy_version
        self._max_market_age = max_market_age
        self._approval_ttl = approval_ttl
        self._journal = journal
        self._reservations = reservations or ConditionalRiskReservations()
        self._seen_signal_ids: set[UUID] = set()

    def evaluate(
        self,
        signal: TradingSignal,
        *,
        market: MarketFact,
        account: AccountRiskSnapshot,
        evaluated_at: datetime,
        kill_switch_active: bool = False,
        event_risk_allows_entries: bool = True,
    ) -> PipelineResult:
        """Return a decision and, only if safe, a short-lived approved order."""
        now = evaluated_at.astimezone(UTC)
        intent = TradeIntentGenerated(
            correlation_id=signal.signal_id,
            occurred_at=now,
            strategy_id=signal.strategy_id,
            instrument=signal.instrument,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss_price,
            target_price=signal.target_price,
            scheduled_exit_at=signal.scheduled_exit_at,
            rationale=signal.rationale,
        )
        reasons: list[str] = []
        if signal.signal_id in self._seen_signal_ids:
            reasons.append("duplicate signal has already been evaluated")
        else:
            self._seen_signal_ids.add(signal.signal_id)
        if kill_switch_active:
            reasons.append("kill switch is active")
        if not event_risk_allows_entries:
            reasons.append("scheduled-event risk blocks new entries")
        if market.instrument != signal.instrument:
            reasons.append("market fact instrument does not match signal")
        if market.observed_at.tzinfo is None:
            reasons.append("market fact timestamp must be timezone-aware")
        elif now - market.observed_at.astimezone(UTC) > self._max_market_age:
            reasons.append("market data is stale")
        if market.bid <= 0 or market.ask < market.bid:
            reasons.append("market quote is invalid")
        if signal.side not in {"buy", "sell"}:
            reasons.append("unsupported signal side")

        risk = (
            RiskDecision(False, tuple(reasons))
            if reasons
            else assess_pre_trade_risk(
                SizingRequest(
                    side=cast(Literal["buy", "sell"], signal.side),
                    entry_price=signal.entry_price,
                    stop_loss_price=signal.stop_loss_price,
                    value_per_price_unit_per_lot=market.value_per_price_unit_per_lot,
                    minimum_volume=market.minimum_volume,
                    maximum_volume=market.maximum_volume,
                    volume_step=market.volume_step,
                ),
                AccountRiskSnapshot(
                    current_equity=account.current_equity,
                    start_of_day_equity=account.start_of_day_equity,
                    peak_equity=account.peak_equity,
                    correlated_open_risk=(
                        account.correlated_open_risk
                        + self._reservations.total_reserved_risk
                    ),
                ),
                self._limits,
            )
        )
        decision = RiskDecisionRecorded(
            correlation_id=signal.signal_id,
            causation_id=intent.event_id,
            intent_id=intent.event_id,
            approved=risk.approved,
            policy_version=self._policy_version,
            reasons=risk.reasons,
            quantity=risk.quantity,
            proposed_risk=risk.proposed_risk,
            kill_switch_required=risk.kill_switch_required,
        )
        order = None
        if risk.approved and risk.quantity is not None:
            order = OrderApproved(
                correlation_id=signal.signal_id,
                causation_id=decision.event_id,
                intent_id=intent.event_id,
                decision_id=decision.event_id,
                policy_version=self._policy_version,
                instrument=signal.instrument,
                side=signal.side,
                quantity=risk.quantity,
                expires_at=now + self._approval_ttl,
            )
        if self._journal is not None:
            self._journal.append(intent)
            self._journal.append(decision)
            if order is not None:
                self._journal.append(order)
        return PipelineResult(intent, decision, order)

    def evaluate_oco(
        self,
        signals: tuple[TradingSignal, TradingSignal],
        *,
        market: MarketFact,
        account: AccountRiskSnapshot,
        evaluated_at: datetime,
        reservation_id: UUID,
        kill_switch_active: bool = False,
        event_risk_allows_entries: bool = True,
    ) -> ConditionalPipelineResult:
        """Approve an OCO pair and reserve its maximum possible loss once."""
        if signals[0].instrument != signals[1].instrument:
            raise ValueError("OCO signals must use the same instrument")
        if signals[0].side == signals[1].side:
            raise ValueError("OCO signals must have opposing sides")
        results = (
            self.evaluate(
                signals[0],
                market=market,
                account=account,
                evaluated_at=evaluated_at,
                kill_switch_active=kill_switch_active,
                event_risk_allows_entries=event_risk_allows_entries,
            ),
            self.evaluate(
                signals[1],
                market=market,
                account=account,
                evaluated_at=evaluated_at,
                kill_switch_active=kill_switch_active,
                event_risk_allows_entries=event_risk_allows_entries,
            ),
        )
        if any(
            result.order is None or result.decision.proposed_risk is None
            for result in results
        ):
            return ConditionalPipelineResult(results, None)
        reservation = self._reservations.reserve_oco(
            reservation_id,
            {
                result.order.event_id: result.decision.proposed_risk
                for result in results
                if result.order is not None
                and result.decision.proposed_risk is not None
            },
        )
        return ConditionalPipelineResult(results, reservation)

    @property
    def total_conditional_reserved_risk(self) -> Decimal:
        """Expose risk-owned outstanding conditional exposure for observability."""
        return self._reservations.total_reserved_risk
