"""Candidate 006 readiness for the paper and simulated-fill boundary only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from quantforge.config.xauusd_research_stage_a import XAUUSDResearchStageASettings
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


@dataclass(frozen=True, slots=True)
class Candidate006NonLiveReadiness:
    """Receipt-linked state that never authorizes broker submission."""

    observation_id: str
    status: str
    checks: tuple[str, ...]
    artifact: dict[str, Any]


def assess_candidate_006_non_live_readiness(
    *,
    observation: ObservationEnvelope,
    settings: XAUUSDResearchStageASettings,
    evaluated_at: datetime,
    maximum_age: timedelta = timedelta(seconds=30),
) -> Candidate006NonLiveReadiness:
    """Assess one accepted, fresh Dukascopy XAUUSD receipt for non-live use."""
    now = evaluated_at.astimezone(UTC)
    payload = observation.to_public_payload()
    checks: list[str] = []
    reasons: list[str] = []
    terminal = payload["terminal"]
    instrument = payload["instrument"]
    quote = payload["quote"]
    quality = payload["data_quality"]
    account = payload["account"]
    assert isinstance(terminal, dict)
    assert isinstance(instrument, dict)
    assert isinstance(quote, dict)
    assert isinstance(quality, dict)
    assert isinstance(account, dict)
    if (
        observation.broker_symbol != "XAUUSD"
        or instrument.get("canonical_instrument") != "XAUUSD"
    ):
        reasons.append("receipt is not canonical XAUUSD")
    else:
        checks.append("canonical XAUUSD receipt")
    server = account.get("server")
    if (
        not isinstance(server, str)
        or "dukascopy" not in server.lower()
        or "demo" not in server.lower()
    ):
        reasons.append("receipt is not from a Dukascopy demo server")
    else:
        checks.append("Dukascopy demo source")
    if terminal.get("connected") is not True:
        reasons.append("terminal is disconnected")
    else:
        checks.append("terminal connected")
    if quality.get("adapter_status") != "ok" or quality.get("missing_data"):
        reasons.append("receipt data quality is degraded")
    else:
        checks.append("complete read-only bridge metadata")
    age = now - observation.observed_at_utc
    if age < timedelta() or age > maximum_age:
        reasons.append("receipt is not fresh")
    else:
        checks.append("fresh observation")
    try:
        spread = Decimal(str(quote["spread_points"]))
    except (KeyError, ValueError):
        reasons.append("receipt spread is invalid")
    else:
        if Decimal("0") < spread <= settings.maximum_spread_points:
            checks.append("within provisional research spread cap")
        else:
            reasons.append("spread exceeds provisional research cap")
    if now >= settings.review_by_utc:
        reasons.append("provisional research parameters have expired for review")
    else:
        checks.append("provisional profile remains within review window")
    artifact = {
        "candidate_id": "candidate_006_xauusd",
        "classification": "provisional_research_only",
        "path": "non_live_paper_and_simulated_fills_only",
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "send_allowed": False,
        "submission_status": "prohibited_stage_a",
        "provisional_parameters": {
            "maximum_spread_points": settings.maximum_spread_points,
            "risk_per_trade": str(settings.risk_per_trade),
            "maximum_position_size": str(settings.maximum_position_size),
            "review_by_utc": settings.review_by_utc.isoformat(),
        },
    }
    return Candidate006NonLiveReadiness(
        observation.observation_id,
        "ready_non_live" if not reasons else "not_ready",
        tuple([*checks, *reasons]),
        artifact,
    )


def persist_candidate_006_non_live_readiness(
    log: SQLiteMarketObservationLog, readiness: Candidate006NonLiveReadiness
) -> bool:
    """Persist the result exactly once, without creating an executable request."""
    return log.append_candidate_006_non_live_readiness(
        observation_id=readiness.observation_id,
        readiness_status=readiness.status,
        checks=readiness.checks,
        artifact=readiness.artifact,
    )
