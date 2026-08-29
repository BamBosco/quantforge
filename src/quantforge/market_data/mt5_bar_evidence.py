"""Structural, timezone-neutral evidence checks for native MT5 bar exports."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

_REQUIRED_COLUMNS = frozenset(
    {
        "<DATE>",
        "<TIME>",
        "<OPEN>",
        "<HIGH>",
        "<LOW>",
        "<CLOSE>",
        "<TICKVOL>",
        "<SPREAD>",
    }
)


@dataclass(frozen=True)
class MT5BarEvidence:
    """Auditable facts derivable from a timezone-naive MT5 Bars CSV only."""

    sha256: str
    file_size_bytes: int
    row_count: int
    start_terminal_time: datetime
    end_terminal_time: datetime
    duplicate_timestamps: int
    malformed_rows: int
    invalid_ohlc_rows: int
    negative_tick_volume_rows: int
    negative_spread_rows: int
    spread_percentiles: tuple[tuple[int, int], ...]
    daily_row_counts: tuple[tuple[str, int], ...]

    @property
    def complete_session_row_count(self) -> int:
        """Return the modal daily row count; this is descriptive, not a rule."""
        counts = [count for _, count in self.daily_row_counts]
        return Counter(counts).most_common(1)[0][0]

    @property
    def incomplete_terminal_dates(self) -> tuple[str, ...]:
        expected = self.complete_session_row_count
        return tuple(date for date, count in self.daily_row_counts if count != expected)


def inspect_mt5_bar_evidence(path: Path) -> MT5BarEvidence:
    """Validate and summarize a native MT5 export without assigning a timezone."""
    digest = sha256(path.read_bytes()).hexdigest()
    timestamps: set[datetime] = set()
    daily_counts: Counter[str] = Counter()
    spreads: list[int] = []
    malformed = invalid_ohlc = negative_tick_volume = negative_spread = duplicates = 0
    start: datetime | None = None
    end: datetime | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
            reader.fieldnames
        ):
            raise ValueError("not a supported MT5 bar export")
        for row in reader:
            try:
                timestamp = datetime.strptime(
                    _required(row, "<DATE>") + " " + _required(row, "<TIME>"),
                    "%Y.%m.%d %H:%M:%S",
                )
                open_price, high, low, close = (
                    Decimal(_required(row, field))
                    for field in ("<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>")
                )
                tick_volume = int(_required(row, "<TICKVOL>"))
                spread = int(_required(row, "<SPREAD>"))
            except (InvalidOperation, ValueError):
                malformed += 1
                continue
            if (
                high < max(open_price, close)
                or low > min(open_price, close)
                or high < low
            ):
                invalid_ohlc += 1
            if tick_volume < 0:
                negative_tick_volume += 1
            if spread < 0:
                negative_spread += 1
            if timestamp in timestamps:
                duplicates += 1
            timestamps.add(timestamp)
            daily_counts[timestamp.date().isoformat()] += 1
            spreads.append(spread)
            start = timestamp if start is None or timestamp < start else start
            end = timestamp if end is None or timestamp > end else end

    if start is None or end is None:
        raise ValueError("MT5 bar export contains no valid data rows")
    if malformed:
        raise ValueError(f"MT5 bar export contains {malformed} malformed rows")
    if duplicates:
        raise ValueError(f"MT5 bar export contains {duplicates} duplicate timestamps")
    if invalid_ohlc or negative_tick_volume or negative_spread:
        raise ValueError("MT5 bar export contains invalid market values")

    sorted_spreads = sorted(spreads)
    return MT5BarEvidence(
        sha256=digest,
        file_size_bytes=path.stat().st_size,
        row_count=len(spreads),
        start_terminal_time=start,
        end_terminal_time=end,
        duplicate_timestamps=duplicates,
        malformed_rows=malformed,
        invalid_ohlc_rows=invalid_ohlc,
        negative_tick_volume_rows=negative_tick_volume,
        negative_spread_rows=negative_spread,
        spread_percentiles=tuple(
            (percentile, _percentile(sorted_spreads, percentile))
            for percentile in (1, 5, 50, 90, 95, 99, 100)
        ),
        daily_row_counts=tuple(sorted(daily_counts.items())),
    )


def _required(row: dict[str, str | None], field: str) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"missing {field}")
    return value.strip()


def _percentile(values: list[int], percentile: int) -> int:
    return values[round((len(values) - 1) * percentile / 100)]
