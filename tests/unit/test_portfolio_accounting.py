"""Tests for deterministic fill accounting and risk-gate facts."""

from decimal import Decimal

from quantforge.portfolio import Fill, Portfolio


def test_long_position_mark_and_close_realizes_pnl_once() -> None:
    portfolio = Portfolio(Decimal("10000"))
    portfolio.apply_fill(Fill("XAUUSD", "buy", Decimal("2"), Decimal("100")))
    portfolio.mark("XAUUSD", Decimal("105"))

    assert portfolio.equity == Decimal("10010")

    portfolio.apply_fill(Fill("XAUUSD", "sell", Decimal("2"), Decimal("105")))

    assert portfolio.equity == Decimal("10010")
    assert portfolio.positions == {}


def test_partial_close_preserves_open_cost_and_realized_pnl() -> None:
    portfolio = Portfolio(Decimal("10000"))
    portfolio.apply_fill(Fill("XAUUSD", "buy", Decimal("3"), Decimal("100")))
    portfolio.apply_fill(Fill("XAUUSD", "sell", Decimal("1"), Decimal("110")))

    position = portfolio.positions["XAUUSD"]

    assert position.quantity == Decimal("2")
    assert position.average_open_price == Decimal("100")
    assert position.realized_pnl == Decimal("10")
    assert portfolio.equity == Decimal("10010")


def test_short_position_marks_and_risk_snapshot_tracks_peak_equity() -> None:
    portfolio = Portfolio(Decimal("10000"))
    portfolio.apply_fill(Fill("XAUUSD", "sell", Decimal("2"), Decimal("100")))
    portfolio.mark("XAUUSD", Decimal("95"))

    snapshot = portfolio.risk_snapshot(correlated_open_risk=Decimal("80"))

    assert snapshot.current_equity == Decimal("10010")
    assert snapshot.peak_equity == Decimal("10010")
    assert snapshot.start_of_day_equity == Decimal("10000")
    assert snapshot.correlated_open_risk == Decimal("80")
