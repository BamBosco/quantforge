"""Strict importer for MetaTrader 5 bar exports used by offline research."""

import csv
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quantforge.backtest.models import MinuteBar

_REQUIRED_COLUMNS = frozenset({
    "<DATE>",
    "<TIME>",
    "<OPEN>",
    "<HIGH>",
    "<LOW>",
    "<CLOSE>",
    "<TICKVOL>",
    "<SPREAD>",
})
_TIMESTAMP_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M")


def load_mt5_minute_bars(path: Path, *, source_timezone: str) -> tuple[MinuteBar, ...]:
    """Load a tab-delimited MT5 M1 export and normalize timestamps to UTC.

    The export contains timezone-naive wall-clock times. The caller must record
    the timezone used by the terminal at export time in a dataset manifest; this
    function never guesses it from the computer's current clock.
    """
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"unknown source timezone: {source_timezone}") from error

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file, delimiter="\t")
        if rows.fieldnames is None or not _REQUIRED_COLUMNS.issubset(rows.fieldnames):
            raise ValueError("not a supported MT5 bar export")
        bars = tuple(
            _parse_row(row, line_number, timezone)
            for line_number, row in enumerate(rows, 2)
        )

    if not bars:
        raise ValueError("MT5 bar export contains no data")
    chronological = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    timestamps = [bar.timestamp for bar in chronological]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("MT5 bar export contains duplicate timestamps")
    return chronological


def _parse_row(
    row: dict[str, str | None], line_number: int, timezone: ZoneInfo
) -> MinuteBar:
    """Parse one MT5 row and add useful import context to malformed-row errors."""
    try:
        timestamp = _parse_timestamp(
            _required(row, "<DATE>") + " " + _required(row, "<TIME>")
        ).replace(tzinfo=timezone)
        return MinuteBar(
            timestamp=timestamp.astimezone(UTC),
            open=Decimal(_required(row, "<OPEN>")),
            high=Decimal(_required(row, "<HIGH>")),
            low=Decimal(_required(row, "<LOW>")),
            close=Decimal(_required(row, "<CLOSE>")),
            tick_volume=int(_required(row, "<TICKVOL>")),
            spread_points=int(_required(row, "<SPREAD>")),
        )
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"invalid MT5 bar at line {line_number}") from error


def _required(row: dict[str, str | None], field: str) -> str:
    """Return a non-empty field from a CSV row."""
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"missing {field}")
    return value.strip()


def _parse_timestamp(value: str) -> datetime:
    """Parse the timestamp forms emitted by MT5's bar exporter."""
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, timestamp_format)
        except ValueError:
            continue
    raise ValueError("unsupported MT5 timestamp format")
