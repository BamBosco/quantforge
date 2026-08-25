"""Read-only MT5 observation consumer for TradingAgents-compatible snapshots.

This module never imports an execution adapter and never produces an order. It
turns a bridge observation into a validated market fact that a research layer
may read after deterministic validation has succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


@dataclass(frozen=True, slots=True)
class ResearchSnapshotPolicy:
    """Validation policy for a single closed USD/JPY M1 candle."""

    canonical_instrument: str = "USDJPY"
    broker_symbol: str = "USDJPY"
    max_observation_age: timedelta = timedelta(seconds=90)
    max_spread_points: float = 20.0
    required_filling_mode: str = "fill_or_kill"
    timeframe: str = "M1"


@dataclass(frozen=True, slots=True)
class ResearchSnapshotResult:
    """Accepted snapshot or an auditable deterministic rejection."""

    accepted: bool
    issues: tuple[str, ...]
    snapshot: dict[str, Any] | None


def policy_from_demo_settings(settings: ForexMT5DemoSettings) -> ResearchSnapshotPolicy:
    """Derive broker-specific validation policy from the non-secret demo profile."""
    return ResearchSnapshotPolicy(
        canonical_instrument=settings.instrument.internal_symbol,
        broker_symbol=settings.instrument.broker_symbol,
        max_observation_age=timedelta(seconds=settings.mt5.data_freshness_seconds),
        max_spread_points=float(settings.risk.max_spread_points),
        required_filling_mode=settings.execution.filling_mode,
        timeframe=settings.instrument.timeframe,
    )


class MT5ResearchSnapshotConsumer:
    """Consume bridge data into research facts; it has no execution authority."""

    def __init__(
        self,
        audit_log: SQLiteMarketObservationLog,
        *,
        policy: ResearchSnapshotPolicy | None = None,
    ) -> None:
        self._audit_log = audit_log
        self._policy = policy or ResearchSnapshotPolicy()

    def consume(
        self,
        observation: ObservationEnvelope,
        *,
        evaluated_at: datetime | None = None,
    ) -> ResearchSnapshotResult:
        """Validate and persist a closed-candle research snapshot.

        ``evaluated_at`` is injectable for deterministic tests. Production uses
        UTC now. Both the candle and observation timestamps remain UTC-aware.
        """
        now = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
        snapshot, candle_time, issues = self._normalize(observation, now)
        result = ResearchSnapshotResult(not issues, tuple(issues), snapshot)
        self._audit_log.append_research_snapshot(
            observation_id=observation.observation_id,
            candle_open_time_utc=candle_time,
            validation_status="accepted" if result.accepted else "rejected",
            validation_issues=result.issues,
            snapshot=result.snapshot,
        )
        return result

    def consume_latest(
        self, *, evaluated_at: datetime | None = None
    ) -> ResearchSnapshotResult | None:
        """Consume the newest bridge observation, if one has been recorded."""
        observations = self._audit_log.recent_observations(limit=1)
        if not observations:
            return None
        return self.consume(
            ObservationEnvelope.from_payload(observations[0]["payload"]),
            evaluated_at=evaluated_at,
        )

    def _normalize(
        self, observation: ObservationEnvelope, now: datetime
    ) -> tuple[dict[str, Any] | None, datetime | None, list[str]]:
        payload = observation.payload
        issues: list[str] = []
        observed_at = observation.observed_at_utc
        if now < observed_at or now - observed_at > self._policy.max_observation_age:
            issues.append("observation is stale")
        if not payload["terminal"]["connected"]:
            issues.append("MT5 terminal is disconnected")
        if payload["data_quality"]["adapter_status"] != "ok":
            issues.append("adapter status is not ok")
        if payload["data_quality"]["missing_data"]:
            issues.append("observation reports missing data")

        instrument = payload["instrument"]
        if instrument["canonical_instrument"] != self._policy.canonical_instrument:
            issues.append("unexpected canonical instrument")
        if instrument["broker_symbol"] != self._policy.broker_symbol:
            issues.append("unexpected broker symbol")
        self._validate_specification(instrument["specification"], issues)
        spread = payload["quote"].get("spread_points")
        if spread is None or spread < 0 or spread > self._policy.max_spread_points:
            issues.append("invalid or excessive spread")
        filling_modes = instrument["specification"]["supported_filling_modes"]
        if self._policy.required_filling_mode not in filling_modes:
            issues.append("required filling mode is not supported")

        candles = payload["candles"]
        candle_time: datetime | None = None
        if candles["timeframe"] != self._policy.timeframe:
            issues.append("unexpected candle timeframe")
        if candles["forming"] is not None:
            issues.append("forming candle must not be consumed")
        if not candles["completed"]:
            issues.append("completed M1 candle is missing")
            return None, candle_time, issues

        candle = candles["completed"][-1]
        candle_time = datetime.fromisoformat(candle["open_time_utc"]).astimezone(UTC)
        if candle_time + timedelta(minutes=1) > observed_at:
            issues.append("reported completed candle has not closed")
        if candle_time + timedelta(minutes=1) > now:
            issues.append("candle close is in the future")

        if issues:
            return None, candle_time, issues
        return (
            {
                "schema_version": 1,
                "instrument": {
                    "canonical_symbol": instrument["canonical_instrument"],
                    "broker_symbol": instrument["broker_symbol"],
                    "specification": instrument["specification"],
                },
                "candle": {
                    "timeframe": self._policy.timeframe,
                    "open_time_utc": candle["open_time_utc"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "tick_volume": candle.get("tick_volume"),
                },
                "quote": payload["quote"],
                "account": payload["account"],
                "source": payload["source"],
                "observed_at_utc": observed_at.isoformat(),
                "position_state": {
                    "positions": payload["positions"],
                    "active_orders": payload["active_orders"],
                },
            },
            candle_time,
            issues,
        )

    @staticmethod
    def _validate_specification(
        specification: dict[str, Any], issues: list[str]
    ) -> None:
        point = specification["point"]
        volume_min = specification.get("volume_min")
        volume_max = specification.get("volume_max")
        volume_step = specification.get("volume_step")
        contract_size = specification.get("contract_size")
        if point <= 0 or specification["digits"] < 1:
            issues.append("invalid broker point or digits")
        if (
            volume_min is None
            or volume_max is None
            or volume_step is None
            or volume_min <= 0
            or volume_max < volume_min
            or volume_step <= 0
        ):
            issues.append("invalid broker lot specification")
        if contract_size is None or contract_size <= 0:
            issues.append("invalid broker contract size")
        if not specification["supported_filling_modes"]:
            issues.append("broker filling modes are missing")
