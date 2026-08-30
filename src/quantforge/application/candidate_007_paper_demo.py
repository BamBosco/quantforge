"""Candidate 007 Paper Trading Simulation Host & Runner for XAUUSD & BTCUSD."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from quantforge.application.paper_runtime import (
    InstrumentRiskMetadata,
    PaperRuntimeHost,
    RuntimeCycleResult,
)
from quantforge.application.trading_pipeline import PaperTradingPipeline
from quantforge.backtest.models import MinuteBar
from quantforge.execution import PaperExecutor
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Portfolio
from quantforge.risk.limits import RiskLimits
from quantforge.strategies.candidate_007 import (
    Candidate007Settings,
    Candidate007Strategy,
)

NEW_YORK = ZoneInfo("America/New_York")


def make_observation(
    *,
    observed_at: datetime,
    bid: Decimal,
    ask: Decimal,
    instrument: str = "BTCUSD",
    balance: Decimal = Decimal("10000"),
) -> ObservationEnvelope:
    """Build an ObservationEnvelope matching QuantForge's MT5 schema."""
    timestamp = observed_at.astimezone(UTC).isoformat()
    norm = instrument.strip("#._/ ").replace("/", "").upper()
    contract_size = 1.0 if "BTC" in norm else 100.0
    point = 0.01 if "BTC" in norm or "XAU" in norm else 0.0001
    return ObservationEnvelope.from_payload(
        {
            "schema_version": 2,
            "observed_at_utc": timestamp,
            "source": {
                "adapter": "candidate_007_paper_stream",
                "broker_profile_id": f"paper_{norm.lower()}",
            },
            "account": {
                "account_id": "paper-candidate-007",
                "server": "PAPER-DEMO",
                "currency": "USD",
                "balance": float(balance),
                "equity": float(balance),
                "margin": 0,
                "free_margin": float(balance),
            },
            "instrument": {
                "canonical_instrument": instrument,
                "broker_symbol": instrument,
                "specification": {
                    "point": point,
                    "digits": 2,
                    "volume_min": 0.01,
                    "volume_max": 5.0,
                    "volume_step": 0.01,
                    "contract_size": contract_size,
                },
            },
            "quote": {
                "bid": float(bid),
                "ask": float(ask),
                "tick_time_utc": timestamp,
                "spread_points": float((ask - bid) / Decimal(str(point))),
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


class FlexInstrumentRiskMetadata(dict[str, InstrumentRiskMetadata]):
    """Dynamic risk metadata dictionary supporting broker prefix/suffix variations."""

    def __getitem__(self, key: str) -> InstrumentRiskMetadata:
        if key in self:
            val: InstrumentRiskMetadata = super().__getitem__(key)
            return val
        norm = key.strip("#._/ ").replace("/", "").upper()
        if "BTC" in norm or "ETH" in norm or "SOL" in norm:
            return InstrumentRiskMetadata(Decimal("1"))
        if "XAU" in norm or "GOLD" in norm:
            return InstrumentRiskMetadata(Decimal("100"))
        return InstrumentRiskMetadata(Decimal("100000"))

    def get(self, key: str, default: InstrumentRiskMetadata | None = None) -> InstrumentRiskMetadata:  # type: ignore[override]
        try:
            return self[key]
        except KeyError:
            if default is not None:
                return default
            return InstrumentRiskMetadata(Decimal("1"))


def build_candidate_007_paper_host(
    journal_path: Path,
    *,
    initial_balance: Decimal = Decimal("10000"),
    risk_limits: RiskLimits | None = None,
    settings: Candidate007Settings | None = None,
) -> tuple[PaperRuntimeHost, Candidate007Strategy, Portfolio, SQLiteEventJournal]:
    """Assemble all QuantForge paper runtime components for Candidate 007."""
    journal = SQLiteEventJournal(journal_path)
    portfolio = Portfolio(initial_balance)
    executor = PaperExecutor(portfolio, journal=journal)
    strategy = Candidate007Strategy(settings=settings)

    limits = risk_limits or RiskLimits(
        Decimal("0.01"),
        Decimal("0.03"),
        Decimal("0.06"),
        Decimal("0.03"),
        allow_micro_lot_clamp=True,
    )
    pipeline = PaperTradingPipeline(
        limits=limits,
        policy_version="candidate_007_paper_0.1",
        max_market_age=timedelta(seconds=60),
        approval_ttl=timedelta(seconds=30),
        journal=journal,
    )
    obs_log_path = journal_path.parent / "observations.sqlite3"

    instrument_metadata = FlexInstrumentRiskMetadata(
        {
            "XAUUSD": InstrumentRiskMetadata(Decimal("100")),
            "BTCUSD": InstrumentRiskMetadata(Decimal("1")),
            "#BTCUSD": InstrumentRiskMetadata(Decimal("1")),
            "BTCUSDm": InstrumentRiskMetadata(Decimal("1")),
            "BTCUSD.s": InstrumentRiskMetadata(Decimal("1")),
            "BTCUSD.p": InstrumentRiskMetadata(Decimal("1")),
        }
    )

    host = PaperRuntimeHost(
        strategy=strategy,
        pipeline=pipeline,
        executor=executor,
        portfolio=portfolio,
        observation_log=SQLiteMarketObservationLog(obs_log_path),
        instrument_metadata=instrument_metadata,
        correlated_open_risk=lambda _: Decimal("0"),
        pending_order_projection=lambda _: executor.pending_statuses(),
        max_observation_age=timedelta(seconds=60),
    )
    return host, strategy, portfolio, journal


def run_candidate_007_paper_simulation(
    bars: Sequence[MinuteBar],
    journal_path: Path,
    *,
    instrument: str = "BTCUSD",
    initial_balance: Decimal = Decimal("10000"),
) -> dict[str, object]:
    """Feed bar stream through Candidate 007 Strategy -> Risk Gate -> Paper Executor."""
    settings = (
        Candidate007Settings.for_btcusd()
        if "BTC" in instrument.upper()
        else Candidate007Settings(instrument=instrument)
    )
    host, strategy, portfolio, journal = build_candidate_007_paper_host(
        journal_path, initial_balance=initial_balance, settings=settings
    )

    signals_count = 0
    orders_approved = 0
    fills_count = 0
    cycle_results: list[RuntimeCycleResult] = []

    for bar in bars:
        strategy.update_bar(bar)

        spread = Decimal(bar.spread_points or 20) * Decimal("0.01")
        bid = bar.close
        ask = bar.close + spread
        obs = make_observation(
            observed_at=bar.timestamp,
            bid=bid,
            ask=ask,
            instrument=instrument,
            balance=portfolio.cash,
        )

        res = host.process(obs, evaluated_at=bar.timestamp)
        cycle_results.append(res)
        if res.signal_generated:
            signals_count += 1
        if res.order_approved:
            orders_approved += 1
        for ex in res.executions:
            if ex.fill is not None:
                fills_count += 1

    return {
        "total_bars_processed": len(bars),
        "signals_generated": signals_count,
        "orders_approved": orders_approved,
        "fills_executed": fills_count,
        "final_cash": portfolio.cash,
        "final_equity": portfolio.equity,
        "open_positions": len(portfolio.positions),
    }
