"""Append-only audit storage for observed Candidate 006 XAUUSD broker facts.

This module accepts only observations that already arrived through the read-only
MT5 bridge.  It has no broker transport and no order, position, or execution
operations.
"""

from __future__ import annotations

import json
import sqlite3
from math import isfinite
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class XAUUSDBrokerProfileAuditError(ValueError):
    """Raised when a source observation is outside the Candidate 006 scope."""


@dataclass(frozen=True, slots=True)
class XAUUSDBrokerMetadataObservation:
    """Observed XAUUSD broker facts with unsupported fields recorded as absent."""

    source_event_id: int
    observed_at_utc: str
    latest_closed_m1_at_utc: str
    bid: float
    ask: float
    spread_points: float
    point: float
    digits: int
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    filling_modes: tuple[str, ...]
    terminal_connected: bool
    trade_mode: int | None = None
    trade_permission: bool | None = None
    order_mode: int | None = None
    stop_level: int | None = None
    freeze_level: int | None = None
    trade_calculation_mode: int | None = None
    profit_currency: str | None = None
    margin_currency: str | None = None
    tick_size: float | None = None
    tick_value: float | None = None
    tick_value_loss: float | None = None
    tick_value_profit: float | None = None

    @classmethod
    def from_read_only_payload(
        cls, *, source_event_id: int, payload: Mapping[str, Any]
    ) -> XAUUSDBrokerMetadataObservation:
        """Extract only facts emitted by the existing read-only bridge."""
        instrument = _mapping(payload.get("instrument"), "instrument")
        if instrument.get("canonical_instrument") != "XAUUSD":
            raise XAUUSDBrokerProfileAuditError("only XAUUSD observations are accepted")
        if instrument.get("broker_symbol") != "XAUUSD":
            raise XAUUSDBrokerProfileAuditError("broker symbol must be XAUUSD")
        specification = _mapping(instrument.get("specification"), "specification")
        quote = _mapping(payload.get("quote"), "quote")
        candles = _mapping(payload.get("candles"), "candles")
        completed = candles.get("completed")
        if not isinstance(completed, list) or not completed:
            raise XAUUSDBrokerProfileAuditError(
                "latest closed M1 candle is unavailable"
            )
        latest_candle = _mapping(completed[0], "candles.completed[0]")
        terminal = _mapping(payload.get("terminal"), "terminal")
        modes = specification.get("supported_filling_modes")
        if not isinstance(modes, list) or not all(
            isinstance(item, str) for item in modes
        ):
            raise XAUUSDBrokerProfileAuditError(
                "supported filling modes are unavailable"
            )
        return cls(
            source_event_id=source_event_id,
            observed_at_utc=_timestamp(
                payload.get("observed_at_utc"), "observed_at_utc"
            ),
            latest_closed_m1_at_utc=_timestamp(
                latest_candle.get("open_time_utc"), "candles.completed[0].open_time_utc"
            ),
            bid=_number(quote.get("bid"), "quote.bid"),
            ask=_number(quote.get("ask"), "quote.ask"),
            spread_points=_number(quote.get("spread_points"), "quote.spread_points"),
            point=_number(specification.get("point"), "instrument.specification.point"),
            digits=_integer(
                specification.get("digits"), "instrument.specification.digits"
            ),
            contract_size=_number(
                specification.get("contract_size"),
                "instrument.specification.contract_size",
            ),
            volume_min=_number(
                specification.get("volume_min"), "instrument.specification.volume_min"
            ),
            volume_max=_number(
                specification.get("volume_max"), "instrument.specification.volume_max"
            ),
            volume_step=_number(
                specification.get("volume_step"), "instrument.specification.volume_step"
            ),
            filling_modes=tuple(modes),
            terminal_connected=_boolean(
                terminal.get("connected"), "terminal.connected"
            ),
            trade_mode=_optional_integer(specification.get("trade_mode"), "trade_mode"),
            trade_permission=_optional_boolean(
                terminal.get("trade_allowed"), "terminal.trade_allowed"
            ),
            order_mode=_optional_integer(specification.get("order_mode"), "order_mode"),
            stop_level=_optional_integer(specification.get("stop_level"), "stop_level"),
            freeze_level=_optional_integer(
                specification.get("freeze_level"), "freeze_level"
            ),
            trade_calculation_mode=_optional_integer(
                specification.get("trade_calculation_mode"), "trade_calculation_mode"
            ),
            profit_currency=_optional_string(
                specification.get("profit_currency"), "profit_currency"
            ),
            margin_currency=_optional_string(
                specification.get("margin_currency"), "margin_currency"
            ),
            tick_size=_optional_number(specification.get("tick_size"), "tick_size"),
            tick_value=_optional_number(specification.get("tick_value"), "tick_value"),
            tick_value_loss=_optional_number(
                specification.get("tick_value_loss"), "tick_value_loss"
            ),
            tick_value_profit=_optional_number(
                specification.get("tick_value_profit"), "tick_value_profit"
            ),
        )


class SQLiteXAUUSDBrokerProfileAudit:
    """A minimal append-only Candidate 006 audit scope for raw broker facts."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._bootstrap()

    def _bootstrap(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS xauusd_broker_metadata_observation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_event_id INTEGER NOT NULL UNIQUE,
                    observed_at_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS xauusd_risk_decision (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_event_id INTEGER NOT NULL UNIQUE,
                    risk_status TEXT NOT NULL,
                    risk_decision_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    FOREIGN KEY (source_event_id)
                        REFERENCES xauusd_broker_metadata_observation(source_event_id)
                )
                """
            )

    def append(self, observation: XAUUSDBrokerMetadataObservation) -> None:
        """Append once without modifying or replacing duplicate source receipts."""
        with self._connection:
            try:
                self._connection.execute(
                    """
                    INSERT INTO xauusd_broker_metadata_observation (
                        source_event_id, observed_at_utc, payload_json, created_at_utc
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        observation.source_event_id,
                        observation.observed_at_utc,
                        json.dumps(
                            asdict(observation), sort_keys=True, separators=(",", ":")
                        ),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise XAUUSDBrokerProfileAuditError(
                    "source observation was already persisted"
                ) from error

    def count(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM xauusd_broker_metadata_observation"
        ).fetchone()
        assert row is not None
        return int(row[0])

    def append_risk_decision(
        self,
        *,
        source_event_id: int,
        risk_status: str,
        risk_decision: Mapping[str, Any],
    ) -> None:
        """Append a non-executable Candidate 006 sizing outcome to its own audit."""
        if risk_decision.get("non_executable") is not True:
            raise XAUUSDBrokerProfileAuditError(
                "XAUUSD risk audit must be non-executable"
            )
        if risk_status not in {"approved", "rejected"}:
            raise XAUUSDBrokerProfileAuditError(
                "XAUUSD risk audit status must be approved or rejected"
            )
        if risk_decision.get("status") != risk_status:
            raise XAUUSDBrokerProfileAuditError(
                "XAUUSD risk audit status must match the decision"
            )
        source_exists = self._connection.execute(
            """
            SELECT 1 FROM xauusd_broker_metadata_observation
            WHERE source_event_id = ?
            """,
            (source_event_id,),
        ).fetchone()
        if source_exists is None:
            raise XAUUSDBrokerProfileAuditError(
                "XAUUSD risk decision requires a persisted source observation"
            )
        with self._connection:
            try:
                self._connection.execute(
                    """
                    INSERT INTO xauusd_risk_decision (
                        source_event_id, risk_status, risk_decision_json, created_at_utc
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        source_event_id,
                        risk_status,
                        json.dumps(risk_decision, sort_keys=True, separators=(",", ":")),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise XAUUSDBrokerProfileAuditError(
                    "source observation already has a risk decision"
                ) from error

    def close(self) -> None:
        self._connection.close()


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be an object")
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be numeric")
    number = float(value)
    if not isfinite(number):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be finite")
    return number


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be an integer")
    return value


def _optional_integer(value: Any, path: str) -> int | None:
    return None if value is None else _integer(value, path)


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be boolean")
    return value


def _optional_boolean(value: Any, path: str) -> bool | None:
    return None if value is None else _boolean(value, path)


def _optional_number(value: Any, path: str) -> float | None:
    return None if value is None else _number(value, path)


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise XAUUSDBrokerProfileAuditError(f"{path} must be a non-empty string")
    return value


def _timestamp(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise XAUUSDBrokerProfileAuditError(f"{path} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise XAUUSDBrokerProfileAuditError(
            f"{path} must be an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise XAUUSDBrokerProfileAuditError(f"{path} must include an offset")
    return parsed.astimezone(UTC).isoformat()
