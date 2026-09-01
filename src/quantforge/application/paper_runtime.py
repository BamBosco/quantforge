"""Strategy-neutral host for the read-only-observation to paper-execution path."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from quantforge.application.trading_pipeline import MarketFact, PaperTradingPipeline
from quantforge.execution import (
    PaperExecutionResult,
    PaperExecutor,
    PendingOrderStatus,
    Quote,
)
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.portfolio import Portfolio
from quantforge.risk.event_policy import EventRiskAction, EventRiskDecision
from quantforge.risk.limits import AccountRiskSnapshot
from quantforge.strategies import RuntimeStrategy

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InstrumentRiskMetadata:
    """Non-strategy market metadata required to construct a risk-owned fact."""

    value_per_price_unit_per_lot: Decimal

    def __post_init__(self) -> None:
        if self.value_per_price_unit_per_lot <= 0:
            raise ValueError("value per price unit must be positive")


@dataclass(frozen=True, slots=True)
class RuntimeCycleResult:
    """Observable, fail-closed result of processing one market observation."""

    observation_id: str
    accepted: bool
    reason: str = ""
    signal_generated: bool = False
    order_approved: bool = False
    executions: tuple[PaperExecutionResult, ...] = ()


class PaperRuntimeHost:
    """Continuously operate an approved strategy against read-only observations.

    This host has no broker adapter. It only supplies a paper executor with
    validated observations and calls an injected ``RuntimeStrategy``.
    """

    def __init__(
        self,
        *,
        strategy: RuntimeStrategy,
        pipeline: PaperTradingPipeline,
        executor: PaperExecutor,
        portfolio: Portfolio,
        observation_log: SQLiteMarketObservationLog,
        instrument_metadata: dict[str, InstrumentRiskMetadata],
        correlated_open_risk: Callable[[Portfolio], Decimal],
        pending_order_projection: Callable[
            [ObservationEnvelope], dict[UUID, PendingOrderStatus]
        ],
        max_observation_age: timedelta,
        kill_switch_active: Callable[[], bool] | None = None,
        event_risk: Callable[[ObservationEnvelope], EventRiskDecision | None]
        | None = None,
    ) -> None:
        if max_observation_age <= timedelta():
            raise ValueError("maximum observation age must be positive")
        self._strategy = strategy
        self._pipeline = pipeline
        self._executor = executor
        self._portfolio = portfolio
        self._observation_log = observation_log
        self._instrument_metadata = dict(instrument_metadata)
        self._correlated_open_risk = correlated_open_risk
        self._pending_order_projection = pending_order_projection
        self._max_observation_age = max_observation_age
        self._kill_switch_active = kill_switch_active or (lambda: False)
        self._event_risk = event_risk
        self._processed_observations: set[str] = set()
        self._last_observed_at: datetime | None = None
        self._blocked = False

    def process(
        self, observation: ObservationEnvelope, *, evaluated_at: datetime
    ) -> RuntimeCycleResult:
        """Process one observation; reject unsafe input before strategy evaluation."""
        now = evaluated_at.astimezone(UTC)
        observation_id = observation.observation_id
        if self._blocked:
            return self._reject(observation_id, "runtime is blocked pending recovery")
        if observation_id in self._processed_observations:
            return self._reject(observation_id, "duplicate observation")
        if not observation.payload["terminal"]["connected"]:
            return self._reject(
                observation_id, "read-only market source is disconnected"
            )
        observed_at = observation.observed_at_utc
        if now - observed_at > self._max_observation_age:
            return self._reject(observation_id, "market observation is stale")
        if observed_at > now:
            return self._reject(observation_id, "market observation is from the future")
        if self._last_observed_at is not None and observed_at < self._last_observed_at:
            return self._reject(observation_id, "market observation clock regression")
        if observation.payload["data_quality"]["adapter_status"] != "ok":
            return self._reject(
                observation_id, "market source reported degraded quality"
            )
        if observation.payload["data_quality"]["missing_data"]:
            return self._reject(
                observation_id, "market source reports required data missing"
            )

        # Persist every receipt for audit, but do not use the log's wall-clock
        # quality assessment as a runtime gate: replay supplies its own
        # deterministic clock through ``evaluated_at`` above.
        self._observation_log.append_observation(observation)
        self._processed_observations.add(observation_id)
        self._last_observed_at = observed_at

        market = self._market_fact(observation)
        if market is None:
            return self._reject(
                observation_id, "instrument risk metadata is unavailable"
            )
        quote = Quote(market.instrument, market.bid, market.ask, market.observed_at)
        event_decision = self._event_risk(observation) if self._event_risk else None
        executions: list[PaperExecutionResult] = []
        if event_decision is not None:
            executions.extend(
                self._executor.apply_event_risk(
                    event_decision, quotes={quote.instrument: quote}
                )
            )
        executions.extend(self._executor.process_pending_quote(quote))
        executions.extend(self._executor.process_quote(quote))
        executions.extend(
            self._executor.process_scheduled_exits(
                evaluated_at=now, quotes={quote.instrument: quote}
            )
        )
        reconciliation = self._executor.reconcile()
        if not reconciliation.matched:
            self._blocked = True
            return self._reject(observation_id, "; ".join(reconciliation.reasons))
        pending_reconciliation = self._executor.reconcile_pending(
            self._pending_order_projection(observation)
        )
        if not pending_reconciliation.matched:
            self._blocked = True
            return self._reject(
                observation_id, "; ".join(pending_reconciliation.reasons)
            )

        try:
            account = self._account_snapshot()
        except (ValueError, TypeError) as error:
            return self._reject(
                observation_id, f"account snapshot is unavailable: {error}"
            )
        if self._kill_switch_active():
            return RuntimeCycleResult(
                observation_id,
                True,
                reason="kill switch is active; entries are blocked",
                executions=tuple(executions),
            )
        signal = self._strategy.evaluate(market, evaluated_at=now)
        if signal is None:
            return RuntimeCycleResult(
                observation_id, True, executions=tuple(executions)
            )
        if not self._valid_signal(signal, market):
            return self._reject(observation_id, "strategy returned an invalid signal")
        allows_entries = event_decision is None or (
            EventRiskAction.CANCEL_PENDING_ENTRIES not in event_decision.actions
        )
        result = self._pipeline.evaluate(
            signal,
            market=market,
            account=account,
            evaluated_at=now,
            kill_switch_active=self._blocked,
            event_risk_allows_entries=allows_entries,
        )
        if result.order is not None:
            execution = self._executor.submit(
                result.order, result.intent, quote=quote, submitted_at=now
            )
            executions.append(execution)
            if execution.fill is not None and signal.scheduled_exit_at is not None:
                self._executor.schedule_exit(
                    result.order.event_id, exit_at=signal.scheduled_exit_at
                )
        return RuntimeCycleResult(
            observation_id,
            True,
            signal_generated=True,
            order_approved=result.order is not None,
            executions=tuple(executions),
        )

    def replay(
        self, observations: Iterable[ObservationEnvelope]
    ) -> tuple[RuntimeCycleResult, ...]:
        """Replay a supplied sequence at each observation's original event time."""
        return tuple(
            self.process(observation, evaluated_at=observation.observed_at_utc)
            for observation in sorted(
                observations, key=lambda item: item.observed_at_utc
            )
        )

    def heartbeat(
        self,
        *,
        evaluated_at: datetime,
        quotes: dict[str, Quote],
        pending_projection: dict[UUID, PendingOrderStatus],
    ) -> RuntimeCycleResult:
        """Run time-based exits and reconciliation when no strategy input is due."""
        now = evaluated_at.astimezone(UTC)
        heartbeat_id = f"heartbeat:{now.isoformat()}"
        if self._blocked:
            return self._reject(heartbeat_id, "runtime is blocked pending recovery")
        if any(
            quote.observed_at.tzinfo is None
            or now - quote.observed_at.astimezone(UTC) > self._max_observation_age
            or quote.observed_at.astimezone(UTC) > now
            for quote in quotes.values()
        ):
            return self._reject(heartbeat_id, "heartbeat quote is stale or invalid")
        executions: list[PaperExecutionResult] = []
        for quote in quotes.values():
            executions.extend(self._executor.process_quote(quote))
        executions.extend(
            self._executor.process_scheduled_exits(evaluated_at=now, quotes=quotes)
        )
        reconciliation = self._executor.reconcile()
        pending_reconciliation = self._executor.reconcile_pending(pending_projection)
        if not reconciliation.matched or not pending_reconciliation.matched:
            self._blocked = True
            reasons = reconciliation.reasons + pending_reconciliation.reasons
            return self._reject(heartbeat_id, "; ".join(reasons))
        return RuntimeCycleResult(heartbeat_id, True, executions=tuple(executions))

    def recover(self) -> bool:
        """Unblock only after state reconciliation proves the projection safe."""
        reconciliation = self._executor.reconcile()
        self._blocked = not reconciliation.matched
        return reconciliation.matched

    def _market_fact(self, observation: ObservationEnvelope) -> MarketFact | None:
        payload = observation.payload
        instrument = str(payload["instrument"]["canonical_instrument"])
        metadata = self._instrument_metadata.get(instrument)
        if metadata is None:
            norm = instrument.strip("#._/ ").replace("/", "").upper()
            metadata = self._instrument_metadata.get(norm)
            if metadata is None:
                if "XAU" in norm or "GOLD" in norm:
                    metadata = InstrumentRiskMetadata(Decimal("100"))
                elif "BTC" in norm:
                    metadata = InstrumentRiskMetadata(Decimal("1"))
                elif any(cur in norm for cur in ("EUR", "GBP", "USD", "JPY", "AUD", "NZD", "CAD", "CHF")):
                    metadata = InstrumentRiskMetadata(Decimal("100000"))
                else:
                    metadata = InstrumentRiskMetadata(Decimal("100"))
        specification = payload["instrument"]["specification"]
        if metadata is None or not all(
            specification.get(field) is not None
            for field in ("volume_min", "volume_max", "volume_step")
        ):
            return None
        quote = payload["quote"]
        return MarketFact(
            instrument=instrument,
            bid=Decimal(str(quote["bid"])),
            ask=Decimal(str(quote["ask"])),
            observed_at=observation.observed_at_utc,
            value_per_price_unit_per_lot=metadata.value_per_price_unit_per_lot,
            minimum_volume=Decimal(str(specification["volume_min"])),
            maximum_volume=Decimal(str(specification["volume_max"])),
            volume_step=Decimal(str(specification["volume_step"])),
        )

    def _account_snapshot(self) -> AccountRiskSnapshot:
        return self._portfolio.risk_snapshot(
            correlated_open_risk=self._correlated_open_risk(self._portfolio)
        )

    @staticmethod
    def _valid_signal(signal: object, market: MarketFact) -> bool:
        scheduled_exit_at = getattr(signal, "scheduled_exit_at", None)
        return bool(
            getattr(signal, "strategy_id", "")
            and getattr(signal, "instrument", None) == market.instrument
            and getattr(signal, "side", None) in {"buy", "sell"}
            and getattr(signal, "entry_price", Decimal("0")) > 0
            and getattr(signal, "stop_loss_price", Decimal("0")) > 0
            and (scheduled_exit_at is None or scheduled_exit_at.tzinfo is not None)
            and (scheduled_exit_at is None or scheduled_exit_at.utcoffset() is not None)
        )

    @staticmethod
    def _reject(observation_id: str, reason: str) -> RuntimeCycleResult:
        logger.warning(
            "paper runtime rejected observation %s: %s", observation_id, reason
        )
        return RuntimeCycleResult(observation_id, False, reason=reason)
