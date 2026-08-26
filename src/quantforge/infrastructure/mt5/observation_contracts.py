"""Versioned, read-only observation contracts for infrastructure adapters.

These contracts are deliberately independent from any broker, account type, or
instrument.  An adapter may supply broker-specific identifiers, but consumers
should work with the normalised payload rather than with an MT5-specific model.
"""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

LEGACY_SCHEMA_VERSION = 1
CURRENT_SCHEMA_VERSION = 2


class ObservationValidationError(ValueError):
    """Raised when an adapter payload does not satisfy its declared contract."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON suitable for audit and duplicate detection."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ObservationValidationError(f"{path} must be an object")
    return dict(value)


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ObservationValidationError(f"{path} must be a list")
    return value


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ObservationValidationError(f"{path} must be a non-empty string")
    return value


def _terminal_clock(value: Any, path: str) -> str:
    """Validate a terminal clock without assigning it a timezone or offset."""
    text = _string(value, path)
    try:
        datetime.strptime(text, "%Y.%m.%d %H:%M:%S")
    except ValueError as error:
        raise ObservationValidationError(
            f"{path} must be an MT5 terminal timestamp"
        ) from error
    return text


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ObservationValidationError(f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise ObservationValidationError(f"{path} must be at least {minimum}")
    return value


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ObservationValidationError(f"{path} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ObservationValidationError(f"{path} must be finite")
    if minimum is not None and number < minimum:
        raise ObservationValidationError(f"{path} must be at least {minimum}")
    return number


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ObservationValidationError(f"{path} must be a boolean")
    return value


def _utc_timestamp(value: Any, path: str) -> str:
    text = _string(value, path)
    # MT5's standard time rendering uses dots while ISO 8601 uses hyphens.
    if len(text) >= 19 and text[4:5] == "." and text[7:8] == ".":
        text = text.replace(".", "-", 2).replace(" ", "T", 1)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ObservationValidationError(
            f"{path} must be an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise ObservationValidationError(f"{path} must include a UTC offset")
    return parsed.astimezone(UTC).isoformat()


def _identifier(value: Any, path: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ObservationValidationError(
            f"{path} must be a string or integer identifier"
        )
    result = str(value)
    if not result:
        raise ObservationValidationError(f"{path} must not be empty")
    return result


@dataclass(frozen=True)
class MT5Snapshot:
    """The original v1 bridge payload, retained for migration compatibility."""

    account_login: str
    account_server: str
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    symbol: str
    bid: float
    ask: float
    point: float
    digits: int
    volume_min: float
    volume_max: float
    volume_step: float
    position_count: int
    terminal_connected: bool
    observed_at_utc: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> MT5Snapshot:
        data = _object(payload, "payload")
        schema_version = _integer(
            data.get("schema_version"), "schema_version", minimum=1
        )
        if schema_version != LEGACY_SCHEMA_VERSION:
            raise ObservationValidationError("v1 snapshot requires schema_version 1")
        return cls(
            account_login=_identifier(data.get("account_login"), "account_login"),
            account_server=_string(data.get("account_server"), "account_server"),
            currency=_string(data.get("currency"), "currency"),
            balance=_number(data.get("balance"), "balance"),
            equity=_number(data.get("equity"), "equity"),
            margin=_number(data.get("margin"), "margin"),
            free_margin=_number(data.get("free_margin"), "free_margin"),
            symbol=_string(data.get("symbol"), "symbol"),
            bid=_number(data.get("bid"), "bid"),
            ask=_number(data.get("ask"), "ask"),
            point=_number(data.get("point"), "point", minimum=0.0),
            digits=_integer(data.get("digits"), "digits", minimum=0),
            volume_min=_number(data.get("volume_min"), "volume_min", minimum=0.0),
            volume_max=_number(data.get("volume_max"), "volume_max", minimum=0.0),
            volume_step=_number(data.get("volume_step"), "volume_step", minimum=0.0),
            position_count=_integer(
                data.get("position_count"), "position_count", minimum=0
            ),
            terminal_connected=_boolean(
                data.get("terminal_connected"), "terminal_connected"
            ),
            observed_at_utc=_utc_timestamp(
                data.get("observed_at_utc"), "observed_at_utc"
            ),
        )

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "schema_version": LEGACY_SCHEMA_VERSION,
            "account_login": self.account_login,
            "account_server": self.account_server,
            "currency": self.currency,
            "balance": self.balance,
            "equity": self.equity,
            "margin": self.margin,
            "free_margin": self.free_margin,
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "point": self.point,
            "digits": self.digits,
            "volume_min": self.volume_min,
            "volume_max": self.volume_max,
            "volume_step": self.volume_step,
            "position_count": self.position_count,
            "terminal_connected": self.terminal_connected,
            "observed_at_utc": self.observed_at_utc,
        }


def _validate_candle(value: Any, path: str) -> dict[str, Any]:
    candle = _object(value, path)
    candle["open_time_utc"] = _utc_timestamp(
        candle.get("open_time_utc"), f"{path}.open_time_utc"
    )
    for field in ("open", "high", "low", "close"):
        candle[field] = _number(candle.get(field), f"{path}.{field}")
    if candle["high"] < max(candle["open"], candle["low"], candle["close"]):
        raise ObservationValidationError(f"{path}.high is inconsistent")
    if candle["low"] > min(candle["open"], candle["high"], candle["close"]):
        raise ObservationValidationError(f"{path}.low is inconsistent")
    if "tick_volume" in candle:
        candle["tick_volume"] = _number(
            candle["tick_volume"], f"{path}.tick_volume", minimum=0.0
        )
    return candle


def _validate_trade_record(value: Any, path: str) -> dict[str, Any]:
    record = _object(value, path)
    record["ticket"] = _identifier(record.get("ticket"), f"{path}.ticket")
    for key in ("symbol", "side", "state", "type"):
        if key in record:
            record[key] = _string(record[key], f"{path}.{key}")
    for key in ("volume", "price_open", "price_current", "price", "sl", "tp", "profit"):
        if key in record and record[key] is not None:
            record[key] = _number(record[key], f"{path}.{key}")
    for key in ("opened_at_utc", "updated_at_utc", "time_utc", "expires_at_utc"):
        if key in record and record[key] is not None:
            record[key] = _utc_timestamp(record[key], f"{path}.{key}")
    return record


@dataclass(frozen=True)
class ObservationEnvelope:
    """Normalised v2 market/account observation, independent of a broker brand."""

    payload: dict[str, Any]

    @property
    def schema_version(self) -> int:
        return CURRENT_SCHEMA_VERSION

    @property
    def observed_at_utc(self) -> datetime:
        """Return the validated event time as a timezone-aware UTC datetime."""
        return datetime.fromisoformat(self.payload["observed_at_utc"]).astimezone(UTC)

    @property
    def observation_id(self) -> str:
        """Stable content identifier used for the append-only audit record."""
        return payload_sha256(self.payload)

    @property
    def source_adapter(self) -> str:
        return str(self.payload["source"]["adapter"])

    @property
    def broker_profile_id(self) -> str:
        return str(self.payload["source"]["broker_profile_id"])

    @property
    def account_id(self) -> str:
        return str(self.payload["account"]["account_id"])

    @property
    def broker_symbol(self) -> str:
        return str(self.payload["instrument"]["broker_symbol"])

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ObservationEnvelope:
        data = _object(payload, "payload")
        schema_version = _integer(
            data.get("schema_version"), "schema_version", minimum=1
        )
        if schema_version == LEGACY_SCHEMA_VERSION:
            if "account" in data:
                return cls(cls._from_read_only_bridge(data))
            return cls(cls._from_legacy(MT5Snapshot.from_payload(data)))
        if schema_version != CURRENT_SCHEMA_VERSION:
            raise ObservationValidationError(
                f"unsupported schema_version {schema_version}"
            )
        return cls(cls._validate_v2(data))

    @staticmethod
    def _from_read_only_bridge(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize the nested v1 payload emitted by the read-only MT5 EA.

        The original bridge contract predates the generic observation envelope.
        Keeping this conversion here gives the bridge one canonical durable
        representation without adding an execution capability to it.
        """
        observed_at_utc = _utc_timestamp(data.get("observed_at_utc"), "observed_at_utc")
        account = _object(data.get("account"), "account")
        symbol = _object(data.get("symbol"), "symbol")
        terminal = _object(data.get("terminal"), "terminal")
        point = _number(symbol.get("point"), "symbol.point", minimum=0.0)
        bid = _number(symbol.get("bid"), "symbol.bid")
        ask = _number(symbol.get("ask"), "symbol.ask")
        if ask < bid:
            raise ObservationValidationError(
                "symbol.ask must not be less than symbol.bid"
            )
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "observed_at_utc": observed_at_utc,
            "source": {"adapter": "mt5", "broker_profile_id": "legacy_unprofiled_mt5"},
            "account": {
                "account_id": _identifier(account.get("login"), "account.login"),
                "server": _string(account.get("server"), "account.server"),
                "currency": _string(account.get("currency"), "account.currency"),
                "balance": _number(account.get("balance"), "account.balance"),
                "equity": _number(account.get("equity"), "account.equity"),
                "margin": _number(account.get("margin"), "account.margin"),
                "free_margin": _number(
                    account.get("free_margin"), "account.free_margin"
                ),
            },
            "instrument": {
                "canonical_instrument": _string(symbol.get("name"), "symbol.name"),
                "broker_symbol": _string(symbol.get("name"), "symbol.name"),
                "specification": {
                    "point": point,
                    "digits": _integer(
                        symbol.get("digits"), "symbol.digits", minimum=0
                    ),
                    "volume_min": _number(
                        symbol.get("volume_min"), "symbol.volume_min", minimum=0.0
                    ),
                    "volume_max": _number(
                        symbol.get("volume_max"), "symbol.volume_max", minimum=0.0
                    ),
                    "volume_step": _number(
                        symbol.get("volume_step"), "symbol.volume_step", minimum=0.0
                    ),
                    "contract_size": None,
                },
            },
            "quote": {
                "bid": bid,
                "ask": ask,
                "tick_time_utc": observed_at_utc,
                "spread_points": (ask - bid) / point if point else None,
            },
            "candles": {"timeframe": "UNKNOWN", "forming": None, "completed": []},
            "positions": [],
            "active_orders": [],
            "deals": {
                "history_from_utc": observed_at_utc,
                "history_to_utc": observed_at_utc,
                "items": [],
            },
            "terminal": {
                "connected": _boolean(terminal.get("connected"), "terminal.connected")
            },
            "data_quality": {
                "adapter_status": "legacy_v1",
                "missing_data": ["account_trade_mode", "positions_detail", "candles"],
            },
        }

    @staticmethod
    def _from_legacy(snapshot: MT5Snapshot) -> dict[str, Any]:
        spread_points = None
        if snapshot.point > 0:
            spread_points = (snapshot.ask - snapshot.bid) / snapshot.point
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "observed_at_utc": snapshot.observed_at_utc,
            "source": {"adapter": "mt5", "broker_profile_id": "legacy_unprofiled_mt5"},
            "account": {
                "account_id": snapshot.account_login,
                "server": snapshot.account_server,
                "currency": snapshot.currency,
                "balance": snapshot.balance,
                "equity": snapshot.equity,
                "margin": snapshot.margin,
                "free_margin": snapshot.free_margin,
            },
            "instrument": {
                "canonical_instrument": snapshot.symbol,
                "broker_symbol": snapshot.symbol,
                "specification": {
                    "point": snapshot.point,
                    "digits": snapshot.digits,
                    "volume_min": snapshot.volume_min,
                    "volume_max": snapshot.volume_max,
                    "volume_step": snapshot.volume_step,
                    "contract_size": None,
                },
            },
            "quote": {
                "bid": snapshot.bid,
                "ask": snapshot.ask,
                "tick_time_utc": snapshot.observed_at_utc,
                "spread_points": spread_points,
            },
            "candles": {"timeframe": "UNKNOWN", "forming": None, "completed": []},
            "positions": [],
            "active_orders": [],
            "deals": {
                "history_from_utc": snapshot.observed_at_utc,
                "history_to_utc": snapshot.observed_at_utc,
                "items": [],
            },
            "terminal": {"connected": snapshot.terminal_connected},
            "data_quality": {
                "adapter_status": "legacy_v1",
                "missing_data": [
                    "positions_detail",
                    "active_orders",
                    "deal_history",
                    "candles",
                    "contract_size",
                ],
            },
        }

    @staticmethod
    def _validate_v2(data: dict[str, Any]) -> dict[str, Any]:
        result = dict(data)
        result["schema_version"] = CURRENT_SCHEMA_VERSION
        result["observed_at_utc"] = _utc_timestamp(
            data.get("observed_at_utc"), "observed_at_utc"
        )

        time_provenance = data.get("time_provenance")
        if time_provenance is not None:
            clocks = _object(time_provenance, "time_provenance")
            for field in ("terminal_server_time", "terminal_local_time"):
                clocks[field] = _terminal_clock(
                    clocks.get(field), f"time_provenance.{field}"
                )
            clocks["terminal_utc_time"] = _utc_timestamp(
                clocks.get("terminal_utc_time"), "time_provenance.terminal_utc_time"
            )
            result["time_provenance"] = clocks

        source = _object(data.get("source"), "source")
        source["adapter"] = _string(source.get("adapter"), "source.adapter")
        source["broker_profile_id"] = _string(
            source.get("broker_profile_id"), "source.broker_profile_id"
        )
        result["source"] = source

        account = _object(data.get("account"), "account")
        account["account_id"] = _identifier(
            account.get("account_id"), "account.account_id"
        )
        for field in ("currency", "server"):
            account[field] = _string(account.get(field), f"account.{field}")
        for field in ("balance", "equity", "margin", "free_margin"):
            account[field] = _number(account.get(field), f"account.{field}")
        result["account"] = account

        instrument = _object(data.get("instrument"), "instrument")
        instrument["canonical_instrument"] = _string(
            instrument.get("canonical_instrument"), "instrument.canonical_instrument"
        )
        instrument["broker_symbol"] = _string(
            instrument.get("broker_symbol"), "instrument.broker_symbol"
        )
        specification = _object(
            instrument.get("specification"), "instrument.specification"
        )
        specification["point"] = _number(
            specification.get("point"), "instrument.specification.point", minimum=0.0
        )
        specification["digits"] = _integer(
            specification.get("digits"), "instrument.specification.digits", minimum=0
        )
        for field in (
            "volume_min",
            "volume_max",
            "volume_step",
            "contract_size",
            "tick_size",
            "tick_value",
            "tick_value_loss",
            "tick_value_profit",
        ):
            if specification.get(field) is not None:
                specification[field] = _number(
                    specification[field],
                    f"instrument.specification.{field}",
                    minimum=0.0,
                )
        for field in (
            "trade_mode",
            "order_mode",
            "stop_level",
            "freeze_level",
            "trade_calculation_mode",
        ):
            if specification.get(field) is not None:
                specification[field] = _integer(
                    specification[field],
                    f"instrument.specification.{field}",
                    minimum=0,
                )
        for field in ("profit_currency", "margin_currency"):
            if specification.get(field) is not None:
                specification[field] = _string(
                    specification[field], f"instrument.specification.{field}"
                )
        filling_modes = _list(
            specification.get("supported_filling_modes", []),
            "instrument.specification.supported_filling_modes",
        )
        specification["supported_filling_modes"] = [
            _string(item, f"instrument.specification.supported_filling_modes[{index}]")
            for index, item in enumerate(filling_modes)
        ]
        instrument["specification"] = specification
        result["instrument"] = instrument

        quote = _object(data.get("quote"), "quote")
        quote["bid"] = _number(quote.get("bid"), "quote.bid")
        quote["ask"] = _number(quote.get("ask"), "quote.ask")
        quote["tick_time_utc"] = _utc_timestamp(
            quote.get("tick_time_utc"), "quote.tick_time_utc"
        )
        if quote["ask"] < quote["bid"]:
            raise ObservationValidationError(
                "quote.ask must not be less than quote.bid"
            )
        if quote.get("spread_points") is None:
            point = specification["point"]
            quote["spread_points"] = (
                (quote["ask"] - quote["bid"]) / point if point else None
            )
        elif quote["spread_points"] is not None:
            quote["spread_points"] = _number(
                quote["spread_points"], "quote.spread_points", minimum=0.0
            )
        result["quote"] = quote

        candles = _object(data.get("candles"), "candles")
        candles["timeframe"] = _string(candles.get("timeframe"), "candles.timeframe")
        forming = candles.get("forming")
        candles["forming"] = (
            None if forming is None else _validate_candle(forming, "candles.forming")
        )
        completed = _list(candles.get("completed"), "candles.completed")
        candles["completed"] = [
            _validate_candle(item, f"candles.completed[{index}]")
            for index, item in enumerate(completed)
        ]
        result["candles"] = candles

        for field in ("positions", "active_orders"):
            records = _list(data.get(field), field)
            result[field] = [
                _validate_trade_record(item, f"{field}[{index}]")
                for index, item in enumerate(records)
            ]

        deals = _object(data.get("deals"), "deals")
        deals["history_from_utc"] = _utc_timestamp(
            deals.get("history_from_utc"), "deals.history_from_utc"
        )
        deals["history_to_utc"] = _utc_timestamp(
            deals.get("history_to_utc"), "deals.history_to_utc"
        )
        deals["items"] = [
            _validate_trade_record(item, f"deals.items[{index}]")
            for index, item in enumerate(_list(deals.get("items"), "deals.items"))
        ]
        result["deals"] = deals

        terminal = _object(data.get("terminal"), "terminal")
        terminal["connected"] = _boolean(
            terminal.get("connected"), "terminal.connected"
        )
        if terminal.get("trade_allowed") is not None:
            terminal["trade_allowed"] = _boolean(
                terminal["trade_allowed"], "terminal.trade_allowed"
            )
        result["terminal"] = terminal

        data_quality = _object(data.get("data_quality"), "data_quality")
        data_quality["adapter_status"] = _string(
            data_quality.get("adapter_status"), "data_quality.adapter_status"
        )
        missing = _list(data_quality.get("missing_data"), "data_quality.missing_data")
        data_quality["missing_data"] = [
            _string(item, f"data_quality.missing_data[{index}]")
            for index, item in enumerate(missing)
        ]
        result["data_quality"] = data_quality
        return result

    def to_public_payload(self) -> dict[str, Any]:
        # JSON roundtrip prevents external callers mutating the immutable envelope's data.
        result = json.loads(canonical_json(self.payload))
        assert isinstance(result, dict)
        return result
