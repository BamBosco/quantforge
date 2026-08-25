"""Paper-only checks for the enforceable signal-to-fill path."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from quantforge.application.trading_pipeline import (
    MarketFact,
    PaperTradingPipeline,
    TradingSignal,
)
from quantforge.execution import PaperExecutor, Quote
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Fill, Portfolio
from quantforge.risk.limits import AccountRiskSnapshot, RiskLimits

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _pipeline() -> PaperTradingPipeline:
    return PaperTradingPipeline(
        limits=RiskLimits(
            Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
        ),
        policy_version="paper-0.1",
        max_market_age=timedelta(seconds=30),
        approval_ttl=timedelta(seconds=10),
    )


def _signal(*, target_price: Decimal | None = None) -> TradingSignal:
    return TradingSignal(
        "test_strategy",
        "XAUUSD",
        "buy",
        Decimal("100"),
        Decimal("99"),
        "test",
        target_price=target_price,
    )


def _market(observed_at: datetime = NOW) -> MarketFact:
    return MarketFact(
        "XAUUSD",
        Decimal("99.9"),
        Decimal("100"),
        observed_at,
        Decimal("100"),
        Decimal("0.01"),
        Decimal("100"),
        Decimal("0.01"),
    )


def _account() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        Decimal("10000"), Decimal("10000"), Decimal("10000"), Decimal("0")
    )


def test_valid_signal_approves_and_paper_fills_once() -> None:
    pipeline = _pipeline()
    result = pipeline.evaluate(
        _signal(), market=_market(), account=_account(), evaluated_at=NOW
    )

    assert result.decision.approved
    assert result.order is not None
    executor = PaperExecutor(Portfolio(Decimal("10000")))
    execution = executor.submit(
        result.order,
        result.intent,
        quote=Quote("XAUUSD", Decimal("99.9"), Decimal("100"), NOW),
        submitted_at=NOW,
    )

    assert execution.outcome.status == "filled"
    assert execution.fill is not None
    assert (
        executor.submit(
            result.order,
            result.intent,
            quote=Quote("XAUUSD", Decimal("99.9"), Decimal("100"), NOW),
            submitted_at=NOW,
        ).outcome.status
        == "rejected"
    )


def test_stale_data_and_kill_switch_create_no_order() -> None:
    stale = _pipeline().evaluate(
        _signal(),
        market=_market(NOW - timedelta(seconds=31)),
        account=_account(),
        evaluated_at=NOW,
    )
    halted = _pipeline().evaluate(
        _signal(),
        market=_market(),
        account=_account(),
        evaluated_at=NOW,
        kill_switch_active=True,
    )

    assert stale.order is None and stale.decision.reasons == ("market data is stale",)
    assert halted.order is None and halted.decision.reasons == (
        "kill switch is active",
    )


def test_pipeline_journals_intent_decision_and_approved_order(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "paper.sqlite3")
    pipeline = PaperTradingPipeline(
        limits=RiskLimits(
            Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
        ),
        policy_version="paper-0.1",
        max_market_age=timedelta(seconds=30),
        approval_ttl=timedelta(seconds=10),
        journal=journal,
    )

    pipeline.evaluate(_signal(), market=_market(), account=_account(), evaluated_at=NOW)

    assert [event["event_type"] for event in journal.events()] == [
        "TradeIntentGenerated",
        "RiskDecisionRecorded",
        "OrderApproved",
    ]
    journal.close()


def test_paper_target_exit_updates_position_and_reconciles() -> None:
    pipeline = _pipeline()
    result = pipeline.evaluate(
        _signal(target_price=Decimal("101")),
        market=_market(),
        account=_account(),
        evaluated_at=NOW,
    )
    assert result.order is not None
    portfolio = Portfolio(Decimal("10000"))
    executor = PaperExecutor(portfolio)
    executor.submit(
        result.order,
        result.intent,
        quote=Quote("XAUUSD", Decimal("99.9"), Decimal("100"), NOW),
        submitted_at=NOW,
    )

    exits = executor.process_quote(
        Quote("XAUUSD", Decimal("101"), Decimal("101.1"), NOW)
    )

    assert exits[0].outcome.status == "target_reached"
    assert portfolio.positions == {}
    assert executor.reconcile().matched


def test_reconciliation_detects_portfolio_drift() -> None:
    pipeline = _pipeline()
    result = pipeline.evaluate(
        _signal(), market=_market(), account=_account(), evaluated_at=NOW
    )
    assert result.order is not None
    portfolio = Portfolio(Decimal("10000"))
    executor = PaperExecutor(portfolio)
    executor.submit(
        result.order,
        result.intent,
        quote=Quote("XAUUSD", Decimal("99.9"), Decimal("100"), NOW),
        submitted_at=NOW,
    )
    portfolio.apply_fill(Fill("XAUUSD", "buy", Decimal("1"), Decimal("100")))

    reconciliation = executor.reconcile()

    assert not reconciliation.matched
    assert "position mismatch for XAUUSD" in reconciliation.reasons[0]


def test_oco_reserves_only_maximum_side_and_blocks_double_risk() -> None:
    pipeline = PaperTradingPipeline(
        limits=RiskLimits(
            Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.01")
        ),
        policy_version="paper-0.1",
        max_market_age=timedelta(seconds=30),
        approval_ttl=timedelta(seconds=10),
    )
    buy = _signal()
    sell = TradingSignal(
        "test_strategy", "XAUUSD", "sell", Decimal("100"), Decimal("101"), "test"
    )

    result = pipeline.evaluate_oco(
        (buy, sell),
        market=_market(),
        account=_account(),
        evaluated_at=NOW,
        reservation_id=uuid4(),
    )

    assert result.reservation is not None
    assert result.reservation.reserved_risk == Decimal("100")
    assert pipeline.total_conditional_reserved_risk == Decimal("100")
    blocked = pipeline.evaluate(
        _signal(), market=_market(), account=_account(), evaluated_at=NOW
    )
    assert not blocked.decision.approved
    assert blocked.decision.reasons == ("correlated open-risk limit would be exceeded",)
