"""Stage-B demo submission boundary, intentionally disabled by default.

There is no MT5 terminal import, HTTP client, or broker transport in this
module.  The only exposed submission operation always raises before any
external action can occur.  A future enabled transport requires a separately
authorised implementation and configuration review.
"""

from __future__ import annotations

from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings


class DemoSubmissionDisabled(RuntimeError):
    """Raised whenever any caller attempts Stage-B submission while disabled."""


class MT5DemoSubmissionGateway:
    """Validate Stage-A provenance, then unconditionally refuse submission."""

    def __init__(self, settings: ForexMT5DemoSettings) -> None:
        self._settings = settings

    @property
    def submission_enabled(self) -> bool:
        """Stage B has no configuration path that enables submission."""
        return False

    def validate_disabled_request(self, request: dict[str, Any]) -> tuple[str, ...]:
        """Return deterministic reasons that the request cannot be submitted."""
        reasons: list[str] = []
        if self._settings.execution.account_mode != "demo":
            reasons.append("Stage B requires demo account mode")
        if self._settings.execution.live_trading_enabled:
            reasons.append("live trading must remain disabled")
        if self._settings.execution.order_submission_enabled:
            reasons.append("configuration must keep order submission disabled")
        if request.get("stage") != "A":
            reasons.append("request was not constructed by Stage A")
        if request.get("send_allowed") is not False:
            reasons.append("Stage A request must prohibit sending")
        if request.get("submission_status") != "prohibited_stage_a":
            reasons.append("Stage A request has invalid submission status")
        if request.get("broker_symbol") != self._settings.instrument.broker_symbol:
            reasons.append("request broker symbol does not match demo profile")
        # This reason is intentionally present even when every other check passes.
        reasons.append("Stage B submission is disabled pending separate authorisation")
        return tuple(reasons)

    def submit(self, request: dict[str, Any]) -> None:
        """Refuse before any transport, terminal, or broker API can be called."""
        reasons = self.validate_disabled_request(request)
        raise DemoSubmissionDisabled("; ".join(reasons))
