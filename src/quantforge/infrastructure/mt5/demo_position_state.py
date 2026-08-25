"""Read-only USDJPY demo position-state observer.

This module only projects facts already received from the MT5 read-only bridge.
It has no MT5 client import and no operation capable of changing an order or
position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


@dataclass(frozen=True, slots=True)
class DemoPositionStateResult:
    """Persisted state or deterministic scope/data rejection."""

    accepted: bool
    issues: tuple[str, ...]
    state: dict[str, Any] | None


class MT5DemoPositionStateObserver:
    """Persist USDJPY position and pending-order facts from one bridge snapshot."""

    def __init__(
        self, audit_log: SQLiteMarketObservationLog, settings: ForexMT5DemoSettings
    ) -> None:
        self._audit_log = audit_log
        self._settings = settings

    def observe(self, observation: ObservationEnvelope) -> DemoPositionStateResult:
        """Validate scope and persist a non-executable account-state projection."""
        payload = observation.payload
        issues = self._issues(payload)
        state = self._state(payload) if not issues else None
        result = DemoPositionStateResult(not issues, tuple(issues), state)
        self._audit_log.append_demo_position_state_observation(
            observation_id=observation.observation_id,
            observation_timestamp_utc=observation.observed_at_utc.isoformat(),
            account_id=observation.account_id,
            broker_symbol=observation.broker_symbol,
            validation_status="accepted" if result.accepted else "rejected",
            validation_issues=result.issues,
            state=result.state,
        )
        return result

    def observe_latest(self) -> DemoPositionStateResult | None:
        """Observe the newest raw MT5 bridge observation, if one exists."""
        observations = self._audit_log.recent_observations(limit=1)
        if not observations:
            return None
        observation = ObservationEnvelope.from_payload(observations[0]["payload"])
        return self.observe(observation)

    def _issues(self, payload: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if self._settings.execution.account_mode != "demo":
            issues.append("demo account mode is required")
        if self._settings.execution.live_trading_enabled:
            issues.append("live trading must remain disabled")
        if self._settings.execution.order_submission_enabled:
            issues.append("order submission must remain disabled")
        instrument = payload["instrument"]
        if instrument["canonical_instrument"] != "USDJPY":
            issues.append("unexpected canonical instrument")
        if instrument["broker_symbol"] != self._settings.instrument.broker_symbol:
            issues.append("unexpected broker symbol")
        if not payload["terminal"]["connected"]:
            issues.append("MT5 terminal is disconnected")
        if "demo" not in str(payload["account"]["server"]).lower():
            issues.append("MT5 account server is not identified as demo")
        for index, position in enumerate(payload["positions"]):
            if position.get("symbol") == self._settings.instrument.broker_symbol and (
                position.get("opened_at_utc") is None
            ):
                issues.append(f"positions[{index}] is missing opened_at_utc")
        return issues

    def _state(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = self._settings.instrument.broker_symbol
        return {
            "observation_timestamp_utc": payload["observed_at_utc"],
            "account": {
                "account_id": payload["account"]["account_id"],
                "server": payload["account"]["server"],
                "currency": payload["account"]["currency"],
                "balance": payload["account"]["balance"],
                "equity": payload["account"]["equity"],
            },
            "broker_symbol": symbol,
            "open_positions": [
                self._position(position)
                for position in payload["positions"]
                if position.get("symbol") == symbol
            ],
            "pending_orders": [
                self._pending_order(order)
                for order in payload["active_orders"]
                if order.get("symbol") == symbol
            ],
        }

    @staticmethod
    def _position(position: dict[str, Any]) -> dict[str, Any]:
        return {
            "ticket": position["ticket"],
            "symbol": position["symbol"],
            "direction": position.get("side"),
            "volume": position.get("volume"),
            "entry_price": position.get("price_open"),
            "current_price": position.get("price_current"),
            "stop_loss": position.get("sl"),
            "take_profit": position.get("tp"),
            "profit": position.get("profit"),
            "opened_at_utc": position.get("opened_at_utc"),
        }

    @staticmethod
    def _pending_order(order: dict[str, Any]) -> dict[str, Any]:
        return {
            "ticket": order["ticket"],
            "symbol": order["symbol"],
            "direction": order.get("side"),
            "order_type": order.get("type"),
            "volume": order.get("volume"),
            "entry_price": order.get("price"),
            "stop_loss": order.get("sl"),
            "take_profit": order.get("tp"),
        }
