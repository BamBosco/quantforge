"""Local, authenticated receiver for a read-only MetaTrader 5 bridge.

This process is deliberately limited to receiving account and market snapshots
from an MT5 Expert Advisor.  It exposes no endpoint that can create, amend, or
close a broker order.  Binding to loopback keeps the bridge inaccessible from
other machines by default.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any, Final

from .observation_contracts import ObservationEnvelope
from .observation_log import SQLiteMarketObservationLog

_MAX_REQUEST_BYTES: Final = 32_768
_BRIDGE_TOKEN_ENV: Final = "QUANTFORGE_MT5_BRIDGE_TOKEN"
_OBSERVATION_LOG_PATH_ENV: Final = "QUANTFORGE_MT5_OBSERVATION_LOG_PATH"
_DEFAULT_OBSERVATION_LOG_PATH: Final = Path("data/mt5_observations.sqlite3")


class SnapshotValidationError(ValueError):
    """Raised when an MT5 snapshot cannot be trusted as a valid contract."""


@dataclass(frozen=True, slots=True)
class MT5Snapshot:
    """Validated, read-only facts supplied by the MT5 terminal."""

    schema_version: int
    observed_at_utc: datetime
    account_login: int
    account_server: str
    account_currency: str
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
    terminal_trade_allowed: bool

    @classmethod
    def from_payload(cls, payload: object) -> MT5Snapshot:
        """Validate the version-one EA payload before making it observable."""
        if not isinstance(payload, dict):
            raise SnapshotValidationError("snapshot must be a JSON object")
        account = _object(payload, "account")
        symbol = _object(payload, "symbol")
        terminal = _object(payload, "terminal")
        observed_at = _utc_timestamp(_string(payload, "observed_at_utc"))
        snapshot = cls(
            schema_version=_integer(payload, "schema_version"),
            observed_at_utc=observed_at,
            account_login=_integer(account, "login"),
            account_server=_string(account, "server"),
            account_currency=_string(account, "currency"),
            balance=_number(account, "balance"),
            equity=_number(account, "equity"),
            margin=_number(account, "margin"),
            free_margin=_number(account, "free_margin"),
            symbol=_string(symbol, "name"),
            bid=_number(symbol, "bid"),
            ask=_number(symbol, "ask"),
            point=_number(symbol, "point"),
            digits=_integer(symbol, "digits"),
            volume_min=_number(symbol, "volume_min"),
            volume_max=_number(symbol, "volume_max"),
            volume_step=_number(symbol, "volume_step"),
            position_count=_integer(payload, "position_count"),
            terminal_connected=_boolean(terminal, "connected"),
            terminal_trade_allowed=_boolean(terminal, "trade_allowed"),
        )
        if snapshot.schema_version != 1:
            raise SnapshotValidationError("unsupported snapshot schema version")
        if snapshot.bid <= 0 or snapshot.ask <= 0 or snapshot.ask < snapshot.bid:
            raise SnapshotValidationError("invalid bid/ask quote")
        if snapshot.point <= 0 or snapshot.digits < 0:
            raise SnapshotValidationError("invalid symbol precision")
        if (
            snapshot.volume_min <= 0
            or snapshot.volume_max < snapshot.volume_min
            or snapshot.volume_step <= 0
        ):
            raise SnapshotValidationError("invalid broker volume constraints")
        if snapshot.position_count < 0:
            raise SnapshotValidationError("position count cannot be negative")
        return snapshot

    def public_payload(self) -> dict[str, object]:
        """Return safe operational facts without exposing an authentication token."""
        return {
            "schema_version": self.schema_version,
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "account": {
                "login": self.account_login,
                "server": self.account_server,
                "currency": self.account_currency,
                "balance": self.balance,
                "equity": self.equity,
                "margin": self.margin,
                "free_margin": self.free_margin,
            },
            "symbol": {
                "name": self.symbol,
                "bid": self.bid,
                "ask": self.ask,
                "point": self.point,
                "digits": self.digits,
                "volume_min": self.volume_min,
                "volume_max": self.volume_max,
                "volume_step": self.volume_step,
            },
            "position_count": self.position_count,
            "terminal": {
                "connected": self.terminal_connected,
                "trade_allowed": self.terminal_trade_allowed,
            },
        }


class SnapshotStore:
    """Thread-safe latest snapshot cache with durable audit storage."""

    def __init__(self, observation_log: SQLiteMarketObservationLog) -> None:
        self._lock = Lock()
        self._latest: ObservationEnvelope | None = None
        self._observation_log = observation_log

    def record(self, observation: ObservationEnvelope) -> None:
        self._observation_log.append_observation(observation)
        with self._lock:
            self._latest = observation

    def latest(self) -> ObservationEnvelope | None:
        with self._lock:
            return self._latest

    def close(self) -> None:
        self._observation_log.close()


class ReadOnlyBridgeServer(ThreadingHTTPServer):
    """HTTP server that owns and closes its durable observation store."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        snapshot_store: SnapshotStore,
    ) -> None:
        self._snapshot_store = snapshot_store
        super().__init__(server_address, handler_class)

    def close(self) -> None:
        self.server_close()
        self._snapshot_store.close()


def create_server(
    host: str,
    port: int,
    token: str,
    observation_log_path: Path | str = _DEFAULT_OBSERVATION_LOG_PATH,
) -> ReadOnlyBridgeServer:
    """Create a loopback-only bridge server with its token held in memory."""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("the read-only bridge may bind only to loopback")
    if not token:
        raise ValueError("bridge token must not be empty")
    store = SnapshotStore(SQLiteMarketObservationLog(observation_log_path))
    handler = _handler_for(store, token)
    try:
        return ReadOnlyBridgeServer((host, port), handler, store)
    except OSError:
        store.close()
        raise


def main() -> None:
    """Run the read-only receiver from the command line."""
    parser = argparse.ArgumentParser(description="QuantForge read-only MT5 bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--observation-log",
        type=Path,
        default=Path(
            os.environ.get(_OBSERVATION_LOG_PATH_ENV, _DEFAULT_OBSERVATION_LOG_PATH)
        ),
    )
    arguments = parser.parse_args()
    if arguments.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("the read-only bridge may bind only to loopback")
    token = os.environ.get(_BRIDGE_TOKEN_ENV)
    if not token:
        parser.error(f"set {_BRIDGE_TOKEN_ENV} outside the repository before starting")
    server = create_server(
        arguments.host, arguments.port, token, arguments.observation_log
    )
    print(
        f"QuantForge read-only MT5 bridge listening on http://{arguments.host}:{arguments.port}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


def _handler_for(store: SnapshotStore, token: str) -> type[BaseHTTPRequestHandler]:
    class BridgeHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            if self.path == "/healthz":
                self._reply(HTTPStatus.OK, {"status": "ok", "mode": "read_only"})
                return
            if self.path == "/v1/mt5/latest":
                if not self._authorized():
                    self._reply(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                observation = store.latest()
                if observation is None:
                    self._reply(HTTPStatus.NOT_FOUND, {"error": "no snapshot received"})
                    return
                self._reply(HTTPStatus.OK, observation.to_public_payload())
                return
            self._reply(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
            if self.path != "/v1/mt5/snapshots":
                self._reply(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._authorized():
                self._reply(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
                if content_length <= 0 or content_length > _MAX_REQUEST_BYTES:
                    raise SnapshotValidationError("invalid request size")
                payload = json.loads(self.rfile.read(content_length))
                observation = ObservationEnvelope.from_payload(payload)
                store.record(observation)
                # This intentionally reports no account data, prices, or credentials.
                # It gives the operator one unambiguous, safe confirmation that the
                # read-only MT5 connection is delivering observations.
                print(
                    "QuantForge accepted read-only snapshot: "
                    f"symbol={observation.broker_symbol} "
                    f"observed_at_utc={observation.observed_at_utc.isoformat()}",
                    flush=True,
                )
            except (ValueError, json.JSONDecodeError, SnapshotValidationError) as error:
                self._reply(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            self._reply(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "mode": "read_only",
                    "execution_authorized": False,
                },
            )

        def _authorized(self) -> bool:
            expected = f"Bearer {token}"
            received = self.headers.get("Authorization", "")
            return hmac.compare_digest(received, expected)

        def _reply(self, status: HTTPStatus, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format: str, *_args: object) -> None:
            """Avoid recording account facts or request metadata in terminal logs."""

    return BridgeHandler


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SnapshotValidationError(f"{key} must be an object")
    return value


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SnapshotValidationError(f"{key} must be a non-empty string")
    return value


def _integer(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotValidationError(f"{key} must be an integer")
    return value


def _number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotValidationError(f"{key} must be a number")
    return float(value)


def _boolean(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SnapshotValidationError(f"{key} must be a boolean")
    return value


def _utc_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        # MQL5's TimeToString emits ``YYYY.MM.DD HH:MM:SS``. Accept its
        # explicit UTC form at this adapter boundary as well as ISO-8601.
        try:
            parsed = datetime.strptime(value, "%Y.%m.%d %H:%M:%SZ").replace(
                tzinfo=UTC
            )
        except ValueError:
            raise SnapshotValidationError("observed_at_utc must be ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotValidationError("observed_at_utc must include a UTC offset")
    offset = parsed.utcoffset()
    assert offset is not None
    if offset.total_seconds() != 0:
        raise SnapshotValidationError("observed_at_utc must use the UTC offset")
    return parsed


if __name__ == "__main__":
    main()
