"""Execution contracts and schemas for automated MT5 trade execution.

Defines the bidirectional protocol between Python Strategy/Risk Engine
and the MetaTrader 5 Expert Advisor execution bridge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal


class ExecutionContractError(ValueError):
    """Raised when an execution payload violates contract constraints."""


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """An approved order intent dispatched to MT5 for native broker execution."""

    order_id: str
    symbol: str
    side: Literal["buy", "sell"]
    volume: float
    order_type: Literal["market", "limit", "stop"]
    price: float
    stop_loss: float
    take_profit: float
    magic_number: int = 7007
    comment: str = "QuantForge C007"
    created_at_utc: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize into JSON-compatible dictionary."""
        data = asdict(self)
        if not data["created_at_utc"]:
            data["created_at_utc"] = datetime.now(UTC).isoformat()
        return data

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> OrderRequest:
        """Validate and construct OrderRequest from payload."""
        if not isinstance(payload, dict):
            raise ExecutionContractError("payload must be a dictionary")
        order_id = str(payload.get("order_id", "")).strip()
        symbol = str(payload.get("symbol", "")).strip()
        side = str(payload.get("side", "")).lower()
        if not order_id:
            raise ExecutionContractError("order_id is required")
        if not symbol:
            raise ExecutionContractError("symbol is required")
        if side not in {"buy", "sell"}:
            raise ExecutionContractError(f"invalid side: {side}")

        return cls(
            order_id=order_id,
            symbol=symbol,
            side=side,  # type: ignore[arg-type]
            volume=float(payload.get("volume", 0.01)),
            order_type=payload.get("order_type", "market"),
            price=float(payload.get("price", 0.0)),
            stop_loss=float(payload.get("stop_loss", 0.0)),
            take_profit=float(payload.get("take_profit", 0.0)),
            magic_number=int(payload.get("magic_number", 7007)),
            comment=str(payload.get("comment", "QuantForge C007")),
            created_at_utc=str(payload.get("created_at_utc", "")),
        )


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Confirmation receipt returned by MT5 after executing an OrderRequest."""

    order_id: str
    broker_ticket: int
    executed_price: float
    executed_volume: float
    status: Literal["FILLED", "REJECTED", "EXPIRED", "ERROR"]
    error_code: int = 0
    error_message: str = ""
    executed_at_utc: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize into JSON-compatible dictionary."""
        data = asdict(self)
        if not data["executed_at_utc"]:
            data["executed_at_utc"] = datetime.now(UTC).isoformat()
        return data

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExecutionReceipt:
        """Validate and construct ExecutionReceipt from payload."""
        if not isinstance(payload, dict):
            raise ExecutionContractError("payload must be a dictionary")
        order_id = str(payload.get("order_id", "")).strip()
        if not order_id:
            raise ExecutionContractError("order_id is required")

        status = str(payload.get("status", "ERROR")).upper()
        if status not in {"FILLED", "REJECTED", "EXPIRED", "ERROR"}:
            status = "ERROR"

        return cls(
            order_id=order_id,
            broker_ticket=int(payload.get("broker_ticket", 0)),
            executed_price=float(payload.get("executed_price", 0.0)),
            executed_volume=float(payload.get("executed_volume", 0.0)),
            status=status,  # type: ignore[arg-type]
            error_code=int(payload.get("error_code", 0)),
            error_message=str(payload.get("error_message", "")),
            executed_at_utc=str(payload.get("executed_at_utc", "")),
        )
