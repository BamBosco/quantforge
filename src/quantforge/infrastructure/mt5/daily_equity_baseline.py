"""Read-only daily equity baseline resolution for the USDJPY demo risk gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from quantforge.config.settings import ForexMT5DemoSettings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


class MT5DailyEquityBaselineResolver:
    """Persist and resolve the earliest valid same-day read-only account equity."""

    def __init__(
        self, audit_log: SQLiteMarketObservationLog, settings: ForexMT5DemoSettings
    ) -> None:
        self._audit_log = audit_log
        self._settings = settings

    def resolve(self, snapshot: dict[str, Any]) -> Decimal | None:
        """Return the immutable baseline for this snapshot's account UTC day.

        No baseline is inferred: the value must come from the earliest valid raw
        MT5 observation for the identical account, server, and USDJPY symbol.
        """
        identity = self._identity(snapshot)
        if identity is None:
            return None
        account_id, account_server, broker_symbol, day = identity
        existing = self._audit_log.daily_account_equity_baseline(
            account_id=account_id,
            account_server=account_server,
            broker_symbol=broker_symbol,
            baseline_date_utc=day.isoformat(),
        )
        if existing is not None:
            return Decimal(existing["equity"])
        source = self._earliest_valid_source(
            account_id=account_id,
            account_server=account_server,
            broker_symbol=broker_symbol,
            day=day,
        )
        if source is None:
            return None
        equity = Decimal(str(source["payload"]["account"]["equity"]))
        self._audit_log.append_daily_account_equity_baseline(
            account_id=account_id,
            account_server=account_server,
            broker_symbol=broker_symbol,
            baseline_date_utc=day.isoformat(),
            source_observation_id=str(source["observation_id"]),
            source_observation_timestamp_utc=str(source["event_time_utc"]),
            equity=str(equity),
        )
        return equity

    def _identity(
        self, snapshot: dict[str, Any]
    ) -> tuple[str, str, str, datetime] | None:
        execution = self._settings.execution
        if (
            execution.account_mode != "demo"
            or execution.live_trading_enabled
            or execution.order_submission_enabled
        ):
            return None
        try:
            instrument = snapshot["instrument"]
            account = snapshot["account"]
            observed = _utc(snapshot["observed_at_utc"])
            account_id = str(account["account_id"])
            account_server = str(account["server"])
            broker_symbol = str(instrument["broker_symbol"])
        except (KeyError, TypeError, ValueError):
            return None
        if (
            instrument.get("canonical_symbol") != "USDJPY"
            or broker_symbol != self._settings.instrument.broker_symbol
            or "demo" not in account_server.lower()
        ):
            return None
        return (
            account_id,
            account_server,
            broker_symbol,
            observed.replace(hour=0, minute=0, second=0, microsecond=0),
        )

    def _earliest_valid_source(
        self,
        *,
        account_id: str,
        account_server: str,
        broker_symbol: str,
        day: datetime,
    ) -> dict[str, Any] | None:
        candidates = self._audit_log.observations_for_account_day(
            account_id=account_id,
            broker_symbol=broker_symbol,
            day_start_utc=day,
            day_end_utc=day + timedelta(days=1),
        )
        for candidate in candidates:
            payload = candidate["payload"]
            account = payload.get("account", {})
            if (
                account.get("server") != account_server
                or payload.get("terminal", {}).get("connected") is not True
                or payload.get("data_quality", {}).get("adapter_status") != "ok"
                or payload.get("data_quality", {}).get("missing_data")
            ):
                continue
            try:
                equity = Decimal(str(account["equity"]))
            except (InvalidOperation, KeyError, TypeError, ValueError):
                continue
            if equity > 0:
                return candidate
        return None


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return timestamp.astimezone(UTC)
