"""Append-only reconciliation of one manually submitted USDJPY demo order.

The reconciler accepts a normalized broker response as audit input only.  It
does not import MT5, call a broker transport, or expose any trading operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

_SCOPE = "candidate_005_usdjpy_one_demo_order"
_STATUSES = {"accepted", "rejected"}


@dataclass(frozen=True, slots=True)
class DemoExecutionReceiptReconciliation:
    """The immutable result of correlating a broker receipt to observed state."""

    status: str
    readiness_observation_id: str
    position_state_observation_id: str
    stored: bool


class DemoExecutionReceiptReconciler:
    """Reconcile one normalized manual-demo response against audited facts."""

    def __init__(
        self, audit_log: SQLiteMarketObservationLog, settings: ForexMT5DemoSettings
    ) -> None:
        self._audit_log = audit_log
        self._settings = settings

    def reconcile(
        self,
        *,
        broker_response: dict[str, Any],
        position_state_observation_id: str,
    ) -> DemoExecutionReceiptReconciliation:
        """Append a receipt reconciliation; it never performs a broker action."""
        response = self._normalized_response(broker_response)
        readiness = self._audit_log.one_time_demo_readiness(_SCOPE)
        if readiness is None or readiness["status"] != "ready_unclaimed":
            raise ValueError(
                "ready_unclaimed Candidate 005 readiness record is required"
            )
        readiness_observation_id = str(readiness["observation_id"])
        request_row = self._execution_request(readiness_observation_id)
        position_state = (
            self._audit_log.demo_position_state_observation_for_observation(
                position_state_observation_id
            )
        )
        self._validate_provenance(request_row, readiness, response, position_state)
        assert position_state is not None
        status, reconciliation = self._reconcile(request_row, response, position_state)
        stored = self._audit_log.append_demo_execution_receipt_reconciliation(
            readiness_observation_id=readiness_observation_id,
            position_state_observation_id=position_state_observation_id,
            reconciliation_status=status,
            broker_response=response,
            reconciliation=reconciliation,
        )
        return DemoExecutionReceiptReconciliation(
            status, readiness_observation_id, position_state_observation_id, stored
        )

    def _execution_request(self, observation_id: str) -> dict[str, Any]:
        for row in self._audit_log.execution_requests():
            if row["observation_id"] == observation_id:
                return row
        raise ValueError("authorized Stage A request is missing")

    def _validate_provenance(
        self,
        request_row: dict[str, Any],
        readiness: dict[str, Any],
        response: dict[str, Any],
        position_state: dict[str, Any] | None,
    ) -> None:
        execution = self._settings.execution
        if (
            execution.account_mode != "demo"
            or execution.live_trading_enabled
            or execution.order_submission_enabled
        ):
            raise ValueError("demo-only non-submitting profile is required")
        request = request_row.get("request")
        if (
            request_row.get("status") != "constructed"
            or not isinstance(request, dict)
            or request != readiness.get("request")
            or request.get("stage") != "A"
            or request.get("send_allowed") is not False
            or request.get("submission_status") != "prohibited_stage_a"
            or request.get("broker_symbol") != "USDJPY"
        ):
            raise ValueError("authorized Stage A request provenance is invalid")
        if response["broker_symbol"] != self._settings.instrument.broker_symbol:
            raise ValueError("broker response has an unexpected symbol")
        if position_state is None:
            raise ValueError("subsequent position-state observation is missing")
        if (
            position_state["validation_status"] != "accepted"
            or position_state["broker_symbol"]
            != self._settings.instrument.broker_symbol
            or not isinstance(position_state["state"], dict)
        ):
            raise ValueError("subsequent position-state observation is invalid")
        account = position_state["state"].get("account", {})
        if "demo" not in str(account.get("server", "")).lower():
            raise ValueError("subsequent position-state account is not demo")

    @staticmethod
    def _reconcile(
        request_row: dict[str, Any],
        response: dict[str, Any],
        position_state: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        request = request_row["request"]
        assert isinstance(request, dict)
        requested_volume_matches = _decimal(request["volume"]) == _decimal(
            response["requested_volume"]
        )
        requested_price_matches = _decimal(request["price"]) == _decimal(
            response["requested_price"]
        )
        base = {
            "stage_a_request": {
                "volume": request["volume"],
                "price": request["price"],
            },
            "requested_volume_matches": requested_volume_matches,
            "requested_price_matches": requested_price_matches,
            "broker_tickets": {
                "order_ticket": response.get("order_ticket"),
                "deal_ticket": response.get("deal_ticket"),
                "position_ticket": response.get("position_ticket"),
            },
            "matched_position_ticket": None,
        }
        if response["broker_status"] == "rejected":
            return "rejected_by_broker", base
        if not requested_volume_matches or not requested_price_matches:
            return "unmatched", base
        state = position_state["state"]
        assert isinstance(state, dict)
        positions = state.get("open_positions", [])
        expected_ticket = response.get("position_ticket")
        matching = next(
            (
                position
                for position in positions
                if isinstance(position, dict)
                and expected_ticket is not None
                and position.get("ticket") == expected_ticket
            ),
            None,
        )
        if matching is None:
            return "unmatched", base
        base["matched_position_ticket"] = matching["ticket"]
        if _decimal(matching["volume"]) != _decimal(response["filled_volume"]):
            return "unmatched", base
        return "confirmed", base

    @staticmethod
    def _normalized_response(response: dict[str, Any]) -> dict[str, Any]:
        required = {
            "broker_status",
            "broker_symbol",
            "return_code",
            "return_message",
            "submitted_at_utc",
            "responded_at_utc",
            "requested_volume",
            "requested_price",
            "filled_volume",
            "filled_price",
        }
        missing = sorted(required.difference(response))
        if missing:
            raise ValueError("broker response is missing: " + ", ".join(missing))
        result = dict(response)
        if result["broker_status"] not in _STATUSES:
            raise ValueError("broker response has an invalid broker_status")
        for key in ("broker_symbol", "return_message"):
            if not isinstance(result[key], str) or not result[key]:
                raise ValueError(f"broker response {key} must be a non-empty string")
        if isinstance(result["return_code"], bool) or not isinstance(
            result["return_code"], (str, int)
        ):
            raise ValueError("broker response return_code must be a string or integer")
        result["return_code"] = str(result["return_code"])
        for key in ("submitted_at_utc", "responded_at_utc"):
            result[key] = _utc(result[key], f"broker response {key}")
        for key in ("requested_volume", "requested_price"):
            result[key] = str(_positive_decimal(result[key], f"broker response {key}"))
        filled_volume = _decimal(result["filled_volume"])
        if filled_volume < 0:
            raise ValueError("broker response filled_volume must not be negative")
        result["filled_volume"] = str(filled_volume)
        if result["filled_price"] is not None:
            result["filled_price"] = str(
                _positive_decimal(
                    result["filled_price"], "broker response filled_price"
                )
            )
        for key in ("order_ticket", "deal_ticket", "position_ticket"):
            if key in result and result[key] is not None:
                result[key] = str(result[key])
        if (
            result["broker_status"] == "accepted"
            and result.get("position_ticket") is None
        ):
            raise ValueError("accepted broker response requires a position_ticket")
        if result["broker_status"] == "accepted" and result["filled_price"] is None:
            raise ValueError("accepted broker response requires a filled_price")
        return result


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("invalid decimal") from error


def _positive_decimal(value: Any, field: str) -> Decimal:
    result = _decimal(value)
    if result <= 0:
        raise ValueError(f"{field} must be positive")
    return result


def _utc(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    return parsed.astimezone(UTC).isoformat()
