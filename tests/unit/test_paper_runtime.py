"""End-to-end checks for the strategy-neutral paper runtime host."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from quantforge.application.paper_runtime import (
    InstrumentRiskMetadata,
    PaperRuntimeHost,
)
from quantforge.application.trading_pipeline import (
    MarketFact,
    PaperTradingPipeline,
    TradingSignal,
)
from quantforge.execution import PaperExecutor, PendingOrderStatus
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Fill, Portfolio
from quantforge.risk.limits import RiskLimits

NOW = datetime(2026, 8, 21, 12, tzinfo=UTC)


class ApprovedStrategyStub:
    """A test-only stand-in for a future formally approved strategy."""

    strategy_id = "approved_test_candidate"

    def __init__(self, *, returns_signal: bool = True) -> None:
        self.returns_signal = returns_signal
        self.calls = 0

    def evaluate(
        self, market: MarketFact, *, evaluated_at: datetime
    ) -> TradingSignal | None:
        self.calls += 1
        if not self.returns_signal:
            return None
        return TradingSignal(
            self.strategy_id,
            market.instrument,
            "buy",
            Decimal("100"),
            Decimal("99"),
            "runtime-host test signal",
        )


def _observation(*, observed_at: datetime = NOW) -> ObservationEnvelope:
    timestamp = observed_at.astimezone(UTC).isoformat()
    return ObservationEnvelope.from_payload(
        {
            "schema_version": 2,
            "observed_at_utc": timestamp,
            "source": {"adapter": "mt5", "broker_profile_id": "paper-test"},
            "account": {
                "account_id": "1",
                "server": "Headway-Demo",
                "currency": "USD",
                "balance": 10000,
                "equity": 10000,
                "margin": 0,
                "free_margin": 10000,
            },
            "instrument": {
                "canonical_instrument": "XAUUSD",
                "broker_symbol": "XAUUSD",
                "specification": {
                    "point": 0.01,
                    "digits": 2,
                    "volume_min": 0.01,
                    "volume_max": 100,
                    "volume_step": 0.01,
                    "contract_size": 100,
                },
            },
            "quote": {
                "bid": 99.9,
                "ask": 100,
                "tick_time_utc": timestamp,
                "spread_points": 10,
            },
            "candles": {"timeframe": "M1", "forming": None, "completed": []},
            "positions": [],
            "active_orders": [],
            "deals": {
                "history_from_utc": timestamp,
                "history_to_utc": timestamp,
                "items": [],
            },
            "terminal": {"connected": True},
            "data_quality": {"adapter_status": "ok", "missing_data": []},
        }
    )


def _host(
    tmp_path: Path,
    strategy: ApprovedStrategyStub,
    pending_projection: Callable[[ObservationEnvelope], dict[UUID, PendingOrderStatus]]
    | None = None,
    kill_switch_active: Callable[[], bool] | None = None,
) -> tuple[PaperRuntimeHost, Portfolio, SQLiteEventJournal]:
    journal = SQLiteEventJournal(tmp_path / "paper.sqlite3")
    portfolio = Portfolio(Decimal("10000"))
    pipeline = PaperTradingPipeline(
        limits=RiskLimits(
            Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
        ),
        policy_version="paper-0.1",
        max_market_age=timedelta(seconds=30),
        approval_ttl=timedelta(seconds=10),
        journal=journal,
    )
    return (
        PaperRuntimeHost(
            strategy=strategy,
            pipeline=pipeline,
            executor=PaperExecutor(portfolio, journal=journal),
            portfolio=portfolio,
            observation_log=SQLiteMarketObservationLog(
                tmp_path / "observations.sqlite3"
            ),
            instrument_metadata={"XAUUSD": InstrumentRiskMetadata(Decimal("100"))},
            correlated_open_risk=lambda _: Decimal("0"),
            pending_order_projection=pending_projection or (lambda _: {}),
            max_observation_age=timedelta(seconds=30),
            kill_switch_active=kill_switch_active,
        ),
        portfolio,
        journal,
    )


def test_runtime_host_connects_read_only_observation_to_paper_fill(
    tmp_path: Path,
) -> None:
    strategy = ApprovedStrategyStub()
    host, portfolio, journal = _host(tmp_path, strategy)

    result = host.process(_observation(), evaluated_at=NOW)

    assert result.accepted and result.signal_generated and result.order_approved
    assert result.executions[-1].outcome.status == "filled"
    assert strategy.calls == 1
    assert portfolio.positions["XAUUSD"].quantity == Decimal("1")
    assert [event["event_type"] for event in journal.events()] == [
        "TradeIntentGenerated",
        "RiskDecisionRecorded",
        "OrderApproved",
        "ExecutionOutcomeRecorded",
    ]


def test_runtime_host_rejects_stale_and_duplicate_observations(tmp_path: Path) -> None:
    strategy = ApprovedStrategyStub()
    host, _, _ = _host(tmp_path, strategy)
    stale = host.process(
        _observation(observed_at=NOW - timedelta(seconds=31)), evaluated_at=NOW
    )
    current = _observation()
    accepted = host.process(current, evaluated_at=NOW)
    duplicate = host.process(current, evaluated_at=NOW)

    assert not stale.accepted and stale.reason == "market observation is stale"
    assert accepted.accepted
    assert not duplicate.accepted and duplicate.reason == "duplicate observation"
    assert strategy.calls == 1


def test_runtime_recovery_refuses_unreconciled_portfolio_state(tmp_path: Path) -> None:
    host, portfolio, _ = _host(tmp_path, ApprovedStrategyStub())
    host.process(_observation(), evaluated_at=NOW)
    portfolio.apply_fill(Fill("XAUUSD", "buy", Decimal("1"), Decimal("100")))

    assert not host.recover()


def test_runtime_blocks_on_pending_order_projection_drift(tmp_path: Path) -> None:
    host, _, _ = _host(
        tmp_path,
        ApprovedStrategyStub(returns_signal=False),
        pending_projection=lambda _: {uuid4(): PendingOrderStatus.PENDING},
    )

    result = host.process(_observation(), evaluated_at=NOW)

    assert not result.accepted
    assert "pending order mismatch" in result.reason


def test_runtime_kill_switch_blocks_entries_but_keeps_cycle_safe(
    tmp_path: Path,
) -> None:
    strategy = ApprovedStrategyStub()
    host, portfolio, _ = _host(tmp_path, strategy, kill_switch_active=lambda: True)

    result = host.process(_observation(), evaluated_at=NOW)

    assert result.accepted
    assert result.reason == "kill switch is active; entries are blocked"
    assert strategy.calls == 0
    assert portfolio.positions == {}


def test_replay_uses_observation_event_time_not_wall_clock(tmp_path: Path) -> None:
    host, _, _ = _host(tmp_path, ApprovedStrategyStub(returns_signal=False))
    historical = _observation(observed_at=NOW - timedelta(days=1))

    result = host.replay([historical])

    assert result[0].accepted
