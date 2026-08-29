"""Unit tests for Candidate 007 Paper Trading Simulation Integration."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from quantforge.application.candidate_007_paper_demo import (
    build_candidate_007_paper_host,
    make_observation,
    run_candidate_007_paper_simulation,
)
from quantforge.backtest.models import MinuteBar

NEW_YORK = ZoneInfo("America/New_York")


def make_bar(
    timestamp: datetime,
    open_: str = "2400.00",
    close: str = "2400.00",
    high: str | None = None,
    low: str | None = None,
) -> MinuteBar:
    o = Decimal(open_)
    c = Decimal(close)
    h = Decimal(high) if high is not None else max(o, c) + Decimal("1.00")
    l = Decimal(low) if low is not None else min(o, c) - Decimal("1.00")
    return MinuteBar(
        timestamp=timestamp,
        open=o,
        high=h,
        low=l,
        close=c,
        tick_volume=10,
        spread_points=2,
    )


def test_build_candidate_007_paper_host(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite3"
    host, strategy, portfolio, journal = build_candidate_007_paper_host(db_path)
    assert portfolio.cash == Decimal("10000")
    assert strategy.strategy_id == "candidate_007_volatility_regime_trend"
    assert db_path.exists()


def test_candidate_007_paper_simulation_lifecycle(tmp_path: Path) -> None:
    db_path = tmp_path / "paper_lifecycle.sqlite3"
    start_ny = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)

    bars: list[MinuteBar] = []
    # 70 upward trending warmup bars
    for i in range(70):
        price = Decimal("2380.00") + (Decimal(str(i)) * Decimal("0.3"))
        bars.append(
            make_bar(
                start_ny + timedelta(minutes=i),
                open_=str(price),
                close=str(price),
                high=str(price + Decimal("2.0")),
                low=str(price - Decimal("2.0")),
            )
        )

    # At 09:15 NY (within active session), trigger breakout high
    bars.append(
        make_bar(
            datetime(2026, 8, 28, 9, 15, tzinfo=NEW_YORK),
            open_="2410.00",
            close="2412.00",
            high="2415.00",
            low="2409.00",
        )
    )

    results = run_candidate_007_paper_simulation(bars, db_path)

    assert results["total_bars_processed"] == 71
    assert results["signals_generated"] >= 1
    assert results["orders_approved"] >= 1
    assert results["fills_executed"] >= 1
    assert db_path.exists()
