from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

import pytest

from quantforge.market_data import load_mt5_minute_bars


def write_export(path: Path, rows: str) -> None:
    path.write_text(
        dedent(
            """\
            <DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>
            """
        )
        + rows,
        encoding="utf-8",
    )


def test_normalizes_descending_mt5_export_to_utc(tmp_path: Path) -> None:
    export = tmp_path / "xauusd.csv"
    write_export(
        export,
        "2026.08.14\t07:21:00\t4340.00\t4341.00\t4339.00\t4340.50\t52\t0\t34\n"
        "2026.08.14\t07:20\t4339.00\t4340.00\t4338.00\t4340.00\t51\t0\t33\n",
    )

    bars = load_mt5_minute_bars(export, source_timezone="America/Chicago")

    assert [bar.timestamp for bar in bars] == [
        datetime(2026, 8, 14, 12, 20, tzinfo=UTC),
        datetime(2026, 8, 14, 12, 21, tzinfo=UTC),
    ]
    assert bars[0].tick_volume == 51
    assert bars[0].spread_points == 33


def test_rejects_export_without_required_mt5_columns(tmp_path: Path) -> None:
    export = tmp_path / "invalid.csv"
    export.write_text("timestamp,open\n2026-08-14,4340\n", encoding="utf-8")

    with pytest.raises(ValueError, match="supported MT5"):
        load_mt5_minute_bars(export, source_timezone="America/Chicago")


def test_rejects_unknown_source_timezone(tmp_path: Path) -> None:
    export = tmp_path / "xauusd.csv"
    write_export(export, "2026.08.14\t07:20\t4339\t4340\t4338\t4340\t51\t0\t33\n")

    with pytest.raises(ValueError, match="unknown source timezone"):
        load_mt5_minute_bars(export, source_timezone="not-a-timezone")
