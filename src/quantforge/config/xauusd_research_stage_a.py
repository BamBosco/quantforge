"""Candidate 006's provisional, data-only Stage A research configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class XAUUSDResearchStageAConfigurationError(ValueError):
    """Raised when a provisional research profile weakens a hard safety rule."""


@dataclass(frozen=True, slots=True)
class XAUUSDResearchStageASettings:
    """Explicit research caps; none grant broker or live-order authority."""

    maximum_spread_points: int
    risk_per_trade: Decimal
    maximum_position_size: Decimal
    timezone: str
    session_start: time
    session_end: time
    review_by_utc: datetime
    execution_deviation_points: int


def load_xauusd_research_stage_a_settings(path: Path) -> XAUUSDResearchStageASettings:
    """Load only a bounded, expiring, non-executable XAUUSD research profile."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    _required_flags(raw)
    spread = _table(raw, "spread")
    risk = _table(raw, "risk")
    session = _table(raw, "session")
    review = _table(raw, "review")
    execution = _table(raw, "execution")
    timezone = _string(session, "timezone")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise XAUUSDResearchStageAConfigurationError(
            "session timezone must be an explicit IANA timezone"
        ) from error
    settings = XAUUSDResearchStageASettings(
        maximum_spread_points=_integer(spread, "maximum_spread_points", minimum=1),
        risk_per_trade=_decimal(risk, "risk_per_trade"),
        maximum_position_size=_decimal(risk, "maximum_position_size"),
        timezone=timezone,
        session_start=_time(session, "start"),
        session_end=_time(session, "end"),
        review_by_utc=_timestamp(review, "review_by_utc"),
        execution_deviation_points=_integer(execution, "deviation_points", minimum=0),
    )
    if settings.maximum_spread_points != 760:
        raise XAUUSDResearchStageAConfigurationError(
            "maximum spread must retain the documented provisional cap"
        )
    if settings.risk_per_trade != Decimal("0.001"):
        raise XAUUSDResearchStageAConfigurationError(
            "risk per trade must retain the documented provisional cap"
        )
    if settings.maximum_position_size != Decimal("0.01"):
        raise XAUUSDResearchStageAConfigurationError(
            "maximum position must retain the observed minimum-volume cap"
        )
    if not settings.session_start < settings.session_end:
        raise XAUUSDResearchStageAConfigurationError("research session must be ordered")
    if settings.execution_deviation_points != 0:
        raise XAUUSDResearchStageAConfigurationError(
            "unmeasured execution deviation must remain zero"
        )
    return settings


def _required_flags(raw: dict[str, Any]) -> None:
    identity = _table(raw, "identity")
    execution = _table(raw, "execution")
    if identity.get("candidate_id") != "candidate_006_xauusd":
        raise XAUUSDResearchStageAConfigurationError("unexpected research candidate")
    if identity.get("classification") != "provisional_research_only":
        raise XAUUSDResearchStageAConfigurationError(
            "research classification must remain provisional"
        )
    for field in (
        "live_trading_enabled",
        "order_submission_enabled",
        "stage_a_send_allowed",
    ):
        if execution.get(field) is not False:
            raise XAUUSDResearchStageAConfigurationError(f"{field} must remain false")


def _table(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise XAUUSDResearchStageAConfigurationError(f"{name} must be a TOML table")
    return value


def _string(table: dict[str, Any], name: str) -> str:
    value = table.get(name)
    if not isinstance(value, str) or not value:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must be a non-empty string"
        )
    return value


def _integer(table: dict[str, Any], name: str, *, minimum: int) -> int:
    value = table.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise XAUUSDResearchStageAConfigurationError(f"{name} must be an integer")
    return value


def _decimal(table: dict[str, Any], name: str) -> Decimal:
    try:
        value = Decimal(str(table[name]))
    except (KeyError, InvalidOperation, ValueError) as error:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must be a finite decimal"
        ) from error
    if not value.is_finite() or value <= 0:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must be a positive finite decimal"
        )
    return value


def _time(table: dict[str, Any], name: str) -> time:
    try:
        return time.fromisoformat(_string(table, name))
    except ValueError as error:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must be an ISO time"
        ) from error


def _timestamp(table: dict[str, Any], name: str) -> datetime:
    try:
        result = datetime.fromisoformat(_string(table, name))
    except ValueError as error:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must be an ISO timestamp"
        ) from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise XAUUSDResearchStageAConfigurationError(
            f"{name} must include a UTC offset"
        )
    return result.astimezone(UTC)
