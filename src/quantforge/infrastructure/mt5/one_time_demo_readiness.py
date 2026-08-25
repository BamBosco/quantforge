"""Non-executable readiness guard for one manually confirmed demo order.

It only creates an auditable *unclaimed* marker for an already constructed
Stage-A request.  It deliberately contains neither broker imports nor a send
method, so it cannot submit an order.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

_SCOPE = "candidate_005_usdjpy_one_demo_order"


@dataclass(frozen=True, slots=True)
class DemoReadinessResult:
    status: str
    reasons: tuple[str, ...]
    nonce: str | None


class OneTimeDemoReadinessGuard:
    """Gate one fresh Stage-A request; it cannot perform a broker action."""

    def __init__(self, settings: ForexMT5DemoSettings) -> None:
        self._settings = settings

    def arm(
        self,
        audit_log: SQLiteMarketObservationLog,
        *,
        observation_id: str,
        current_account_state: dict[str, Any],
        evaluated_at: datetime | None = None,
    ) -> DemoReadinessResult:
        now = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
        existing = audit_log.one_time_demo_readiness(_SCOPE)
        if existing is not None:
            return DemoReadinessResult(
                "rejected", ("one-time demo authorization is already reserved",), None
            )
        request_row = next(
            (
                row
                for row in audit_log.execution_requests()
                if row["observation_id"] == observation_id
            ),
            None,
        )
        snapshot = audit_log.research_snapshot_for_observation(observation_id)
        risk = audit_log.risk_decision_for_observation(observation_id)
        reasons = self._checks(request_row, snapshot, risk, current_account_state, now)
        if reasons:
            return DemoReadinessResult("rejected", tuple(reasons), None)
        assert request_row is not None and isinstance(request_row["request"], dict)
        nonce = secrets.token_urlsafe(24)
        stored = audit_log.append_one_time_demo_readiness(
            authorization_scope=_SCOPE,
            observation_id=observation_id,
            nonce=nonce,
            checks=("all readiness checks passed",),
            request=request_row["request"],
            account_state=current_account_state,
        )
        if not stored:
            return DemoReadinessResult(
                "rejected", ("one-time demo authorization is already reserved",), None
            )
        return DemoReadinessResult("ready_unclaimed", (), nonce)

    def _checks(
        self,
        request_row: dict[str, Any] | None,
        snapshot: dict[str, Any] | None,
        risk: dict[str, Any] | None,
        account: dict[str, Any],
        now: datetime,
    ) -> list[str]:
        reasons: list[str] = []
        execution = self._settings.execution
        if execution.account_mode != "demo" or execution.live_trading_enabled:
            reasons.append("demo-only configuration check failed")
        if execution.order_submission_enabled:
            reasons.append("base profile must keep order submission disabled")
        request = request_row.get("request") if request_row else None
        if (
            request_row is None
            or request_row.get("status") != "constructed"
            or not isinstance(request, dict)
        ):
            reasons.append("constructed Stage A request is missing")
        elif (
            request.get("stage") != "A"
            or request.get("send_allowed") is not False
            or request.get("submission_status") != "prohibited_stage_a"
            or request.get("broker_symbol") != self._settings.instrument.broker_symbol
            or request.get("action")
            not in {"BUY_MARKET", "SELL_MARKET", "BUY_LIMIT", "SELL_LIMIT"}
        ):
            reasons.append("Stage A request provenance or symbol is invalid")
        if risk is None or risk.get("status") != "approved":
            reasons.append("deterministic risk decision is not approved")
        market = snapshot.get("snapshot") if snapshot else None
        if not isinstance(market, dict):
            reasons.append("accepted market snapshot is missing")
        else:
            observed = _utc(market.get("observed_at_utc"))
            if observed is None or now - observed > timedelta(
                seconds=self._settings.mt5.data_freshness_seconds
            ):
                reasons.append("market snapshot is stale")
        if account.get("currency") != "USD":
            reasons.append("current account is not USD")
        if account.get("broker_symbol") != self._settings.instrument.broker_symbol:
            reasons.append("current account observation has an unexpected symbol")
        if account.get("positions") or account.get("active_orders"):
            reasons.append("one-position rule prevents readiness")
        return reasons


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)
