"""Receipt-bound, non-executable Candidate 006 MT5 observation audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import StoredObservation
from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    SQLiteXAUUSDBrokerProfileAudit,
    XAUUSDBrokerMetadataObservation,
)


class Candidate006BridgeAuditError(ValueError):
    """Raised when a bridge receipt is outside Candidate 006's read-only scope."""


@dataclass(frozen=True, slots=True)
class Candidate006BridgeAuditResult:
    source_event_id: int
    accepted: bool


class Candidate006BridgeAuditConsumer:
    """Persist only complete Dukascopy demo XAUUSD M1 bridge receipts."""

    def __init__(self, audit: SQLiteXAUUSDBrokerProfileAudit) -> None:
        self._audit = audit

    def consume(
        self, observation: ObservationEnvelope, receipt: StoredObservation
    ) -> Candidate006BridgeAuditResult:
        payload = observation.to_public_payload()
        self._validate(observation, receipt, payload)
        metadata = XAUUSDBrokerMetadataObservation.from_read_only_payload(
            source_event_id=receipt.id, payload=payload
        )
        self._audit.append(metadata)
        return Candidate006BridgeAuditResult(receipt.id, True)

    @staticmethod
    def _validate(
        observation: ObservationEnvelope,
        receipt: StoredObservation,
        payload: dict[str, Any],
    ) -> None:
        if observation.schema_version != 2:
            raise Candidate006BridgeAuditError("Candidate 006 requires schema version 2")
        if receipt.quality_status != "accepted":
            raise Candidate006BridgeAuditError("Candidate 006 requires an accepted receipt")
        if observation.broker_symbol != "XAUUSD":
            raise Candidate006BridgeAuditError("Candidate 006 requires XAUUSD")
        account = payload["account"]
        assert isinstance(account, dict)
        server = account["server"]
        assert isinstance(server, str)
        if "dukascopy" not in server.lower() or "demo" not in server.lower():
            raise Candidate006BridgeAuditError(
                "Candidate 006 requires a Dukascopy demo server receipt"
            )
        candles = payload["candles"]
        assert isinstance(candles, dict)
        if candles["timeframe"] != "M1" or not candles["completed"]:
            raise Candidate006BridgeAuditError(
                "Candidate 006 requires a completed XAUUSD M1 candle"
            )
        quality = payload["data_quality"]
        assert isinstance(quality, dict)
        if quality["adapter_status"] != "ok" or quality["missing_data"]:
            raise Candidate006BridgeAuditError(
                "Candidate 006 requires complete bridge metadata"
            )
        terminal = payload["terminal"]
        assert isinstance(terminal, dict)
        if terminal["connected"] is not True or "trade_allowed" not in terminal:
            raise Candidate006BridgeAuditError(
                "Candidate 006 requires terminal connection and trade permission facts"
            )
        specification = payload["instrument"]["specification"]
        assert isinstance(specification, dict)
        required = (
            "trade_mode", "order_mode", "stop_level", "freeze_level",
            "trade_calculation_mode", "profit_currency", "margin_currency",
            "tick_size", "tick_value", "tick_value_loss", "tick_value_profit",
        )
        if any(specification.get(name) is None for name in required):
            raise Candidate006BridgeAuditError(
                "Candidate 006 requires complete native broker metadata"
            )
