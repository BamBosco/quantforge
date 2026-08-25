"""Tests for the explicitly non-profitable paper engineering experiment."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.application.experimental_paper_demo import demo_observation, run_demo
from quantforge.application.paper_runtime import (
    InstrumentRiskMetadata,
    PaperRuntimeHost,
)
from quantforge.application.trading_pipeline import MarketFact, PaperTradingPipeline
from quantforge.execution import PaperExecutor, Quote
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Portfolio
from quantforge.risk.limits import RiskLimits
from quantforge.strategies import ExperimentalPaperStrategy001

ENTRY_TIME = datetime(2026, 8, 21, 13, 0, tzinfo=UTC)


def _market(*, observed_at: datetime = ENTRY_TIME) -> MarketFact:
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


def _host(
    tmp_path: Path,
    *,
    limits: RiskLimits | None = None,
    kill_switch: bool = False,
) -> tuple[PaperRuntimeHost, PaperExecutor, Portfolio, SQLiteEventJournal]:
    journal = SQLiteEventJournal(tmp_path / "paper.sqlite3")
    portfolio = Portfolio(Decimal("10000"))
    executor = PaperExecutor(portfolio, journal=journal)
    host = PaperRuntimeHost(
        strategy=ExperimentalPaperStrategy001(),
        pipeline=PaperTradingPipeline(
            limits=limits
            or RiskLimits(
                Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
            ),
            policy_version="paper-engineering-0.1",
            max_market_age=timedelta(seconds=30),
            approval_ttl=timedelta(seconds=10),
            journal=journal,
        ),
        executor=executor,
        portfolio=portfolio,
        observation_log=SQLiteMarketObservationLog(tmp_path / "observations.sqlite3"),
        instrument_metadata={"XAUUSD": InstrumentRiskMetadata(Decimal("100"))},
        correlated_open_risk=lambda _: Decimal("0"),
        pending_order_projection=lambda _: executor.pending_statuses(),
        max_observation_age=timedelta(seconds=30),
        kill_switch_active=lambda: kill_switch,
    )
    return host, executor, portfolio, journal


def test_strategy_signal_is_deterministic_and_session_bound() -> None:
    first = ExperimentalPaperStrategy001().evaluate(_market(), evaluated_at=ENTRY_TIME)
    second = ExperimentalPaperStrategy001().evaluate(_market(), evaluated_at=ENTRY_TIME)

    assert first is not None and second is not None
    assert first.signal_id == second.signal_id
    assert first.side == "buy" and first.target_price == Decimal("101")
    assert (
        ExperimentalPaperStrategy001().evaluate(
            _market(observed_at=ENTRY_TIME - timedelta(minutes=1)),
            evaluated_at=ENTRY_TIME - timedelta(minutes=1),
        )
        is None
    )


def test_strategy_uses_market_event_time_when_dispatch_is_delayed() -> None:
    observed_at = datetime(2026, 8, 21, 13, 0, 45, tzinfo=UTC)
    dispatched_at = datetime(2026, 8, 21, 13, 1, 5, tzinfo=UTC)

    signal = ExperimentalPaperStrategy001().evaluate(
        _market(observed_at=observed_at), evaluated_at=dispatched_at
    )

    assert signal is not None


def test_strategy_new_york_dst_conversion_is_event_time_correct() -> None:
    summer = datetime(2026, 8, 21, 13, 0, tzinfo=UTC)
    winter = datetime(2026, 1, 21, 14, 0, tzinfo=UTC)

    assert (
        ExperimentalPaperStrategy001().evaluate(
            _market(observed_at=summer), evaluated_at=summer
        )
        is not None
    )
    assert (
        ExperimentalPaperStrategy001().evaluate(
            _market(observed_at=winter), evaluated_at=winter
        )
        is not None
    )


def test_strategy_rejects_invalid_data_and_second_signal() -> None:
    strategy = ExperimentalPaperStrategy001()
    invalid = MarketFact(
        "XAUUSD",
        Decimal("0"),
        Decimal("0"),
        ENTRY_TIME,
        Decimal("100"),
        Decimal("0.01"),
        Decimal("100"),
        Decimal("0.01"),
    )

    assert strategy.evaluate(invalid, evaluated_at=ENTRY_TIME) is None
    assert strategy.evaluate(_market(), evaluated_at=ENTRY_TIME) is not None
    assert strategy.evaluate(_market(), evaluated_at=ENTRY_TIME) is None


def test_risk_rejection_does_not_open_paper_position(tmp_path: Path) -> None:
    host, _, portfolio, _ = _host(
        tmp_path,
        limits=RiskLimits(
            Decimal("0.000001"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
        ),
    )

    result = host.process(
        demo_observation(
            observed_at=ENTRY_TIME, bid=Decimal("99.9"), ask=Decimal("100")
        ),
        evaluated_at=ENTRY_TIME,
    )

    assert result.accepted and result.signal_generated and not result.order_approved
    assert portfolio.positions == {}


def test_approved_signal_reaches_paper_target_and_journal(tmp_path: Path) -> None:
    host, executor, portfolio, journal = _host(tmp_path)
    host.process(
        demo_observation(
            observed_at=ENTRY_TIME, bid=Decimal("99.9"), ask=Decimal("100")
        ),
        evaluated_at=ENTRY_TIME,
    )
    result = host.process(
        demo_observation(
            observed_at=ENTRY_TIME + timedelta(minutes=1),
            bid=Decimal("101"),
            ask=Decimal("101.1"),
        ),
        evaluated_at=ENTRY_TIME + timedelta(minutes=1),
    )

    assert result.executions[0].outcome.status == "target_reached"
    assert portfolio.positions == {} and executor.reconcile().matched
    assert [event["event_type"] for event in journal.events()] == [
        "TradeIntentGenerated",
        "RiskDecisionRecorded",
        "OrderApproved",
        "ExecutionOutcomeRecorded",
        "ExecutionOutcomeRecorded",
    ]


def test_protective_stop_and_scheduled_exit_are_paper_enforced(tmp_path: Path) -> None:
    host, executor, portfolio, _ = _host(tmp_path)
    host.process(
        demo_observation(
            observed_at=ENTRY_TIME, bid=Decimal("99.9"), ask=Decimal("100")
        ),
        evaluated_at=ENTRY_TIME,
    )
    stopped = host.process(
        demo_observation(
            observed_at=ENTRY_TIME + timedelta(minutes=1),
            bid=Decimal("98.9"),
            ask=Decimal("99"),
        ),
        evaluated_at=ENTRY_TIME + timedelta(minutes=1),
    )
    assert stopped.executions[0].outcome.status == "stopped_out"

    host, executor, portfolio, _ = _host(tmp_path / "forced")
    host.process(
        demo_observation(
            observed_at=ENTRY_TIME, bid=Decimal("99.9"), ask=Decimal("100")
        ),
        evaluated_at=ENTRY_TIME,
    )
    exit_time = datetime(2026, 8, 21, 17, 30, tzinfo=UTC)
    forced = host.heartbeat(
        evaluated_at=exit_time,
        quotes={"XAUUSD": Quote("XAUUSD", Decimal("99.5"), Decimal("99.6"), exit_time)},
        pending_projection=executor.pending_statuses(),
    )
    assert forced.executions[0].outcome.status == "forced_exit"
    assert portfolio.positions == {} and executor.reconcile().matched


def test_duplicate_observation_kill_switch_and_event_time_replay(
    tmp_path: Path,
) -> None:
    host, _, portfolio, _ = _host(tmp_path, kill_switch=True)
    observation = demo_observation(
        observed_at=ENTRY_TIME, bid=Decimal("99.9"), ask=Decimal("100")
    )
    killed = host.process(observation, evaluated_at=ENTRY_TIME)
    duplicate = host.process(observation, evaluated_at=ENTRY_TIME)
    assert killed.reason == "kill switch is active; entries are blocked"
    assert not duplicate.accepted and portfolio.positions == {}

    replay_host, _, _, _ = _host(tmp_path / "replay")
    historic = demo_observation(
        observed_at=ENTRY_TIME - timedelta(days=365),
        bid=Decimal("99.9"),
        ask=Decimal("100"),
    )
    replay = replay_host.replay([historic])
    assert replay[0].accepted and replay[0].order_approved


def test_deterministic_demo_completes_paper_lifecycle(tmp_path: Path) -> None:
    result = run_demo(tmp_path)

    assert result["mode"] == "PAPER-ONLY ENGINEERING DEMONSTRATION"
    assert result["entry_status"] == "filled"
    assert result["exit_status"] == "target_reached"
    assert result["positions"] == 0 and result["reconciled"] is True
