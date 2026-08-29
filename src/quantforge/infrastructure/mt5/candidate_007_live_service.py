"""Candidate 007 Live MT5 Bridge Service.

Binds loopback HTTP server to receive authenticated MT5 EA observations
and pipe approved trade orders into the Auto Execution Queue (BTCUSD & XAUUSD).
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from quantforge.application.candidate_007_paper_demo import build_candidate_007_paper_host
from quantforge.application.paper_runtime import RuntimeCycleResult
from quantforge.infrastructure.mt5.auto_execution_service import AutoExecutionQueue
from quantforge.infrastructure.mt5.candidate_007_live_consumer import Candidate007LiveConsumer
from quantforge.infrastructure.mt5.execution_contracts import OrderRequest
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog, StoredObservation
from quantforge.infrastructure.mt5.read_only_bridge import (
    ReadOnlyBridgeServer,
    SnapshotStore,
    _handler_for,
)
from quantforge.infrastructure.notifications.alert_manager import AlertManager
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Portfolio
from quantforge.risk.limits import RiskLimits
from quantforge.strategies.candidate_007 import Candidate007Settings, Candidate007Strategy


class Candidate007SnapshotStore(SnapshotStore):
    """Snapshot store that dispatches observations to Candidate007LiveConsumer."""

    def __init__(
        self,
        observation_log: SQLiteMarketObservationLog,
        consumer: Candidate007LiveConsumer,
        on_reset: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(observation_log, on_reset=on_reset)
        self._consumer = consumer

    def record(self, observation: ObservationEnvelope) -> StoredObservation:
        receipt = self._observation_log.append_observation(observation)
        self._consumer.consume(observation, receipt)
        with self._lock:
            self._latest = observation
        return receipt

    def close(self) -> None:
        self._consumer.close()
        super().close()


def create_candidate_007_live_bridge(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str,
    symbol: str | None = None,
    journal_path: Path | str = Path("data/paper_mode/candidate_007_paper.sqlite3"),
    obs_log_path: Path | str = Path("data/mt5_observations.sqlite3"),
    initial_balance: Decimal = Decimal("10000"),
    settings: Candidate007Settings | None = None,
    risk_limits: RiskLimits | None = None,
    enable_auto_execution: bool = True,
    on_cycle: Callable[[RuntimeCycleResult, ObservationEnvelope], None] | None = None,
) -> tuple[ReadOnlyBridgeServer, Candidate007Strategy, Portfolio, SQLiteEventJournal, AutoExecutionQueue]:
    """Create an authenticated live MT5 bridge server with Auto-Execution queue."""
    journal_path = Path(journal_path)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    obs_log_path = Path(obs_log_path)
    obs_log_path.parent.mkdir(parents=True, exist_ok=True)

    if settings is None:
        if symbol and "BTC" in symbol.upper():
            settings = Candidate007Settings.for_btcusd_scalper()
        else:
            settings = Candidate007Settings(instrument=symbol or "XAUUSD")

    paper_host, strategy, portfolio, journal = build_candidate_007_paper_host(
        journal_path,
        initial_balance=initial_balance,
        risk_limits=risk_limits,
        settings=settings,
    )

    execution_queue = AutoExecutionQueue()
    execution_queue.auto_trading_enabled = enable_auto_execution

    def wrapped_on_cycle(result: RuntimeCycleResult, observation: ObservationEnvelope) -> None:
        for ex in result.executions:
            if ex.outcome is not None and ex.outcome.status == "filled" and ex.fill is not None:
                side = ex.outcome.side
                entry_p = float(ex.fill.price)
                dist = 85.0 if "BTC" in observation.broker_symbol.upper() else 1.5
                sl = entry_p - dist if side == "buy" else entry_p + dist
                tp = entry_p + (dist * 1.5) if side == "buy" else entry_p - (dist * 1.5)
                req = OrderRequest(
                    order_id=str(ex.outcome.order_id),
                    symbol=observation.broker_symbol,
                    side=side,
                    volume=float(ex.outcome.quantity),
                    order_type="market",
                    price=entry_p,
                    stop_loss=sl,
                    take_profit=tp,
                    magic_number=7007,
                    comment="QuantForge C007",
                )
                execution_queue.enqueue_order(req)

        if on_cycle is not None:
            on_cycle(result, observation)

    alert_mgr = AlertManager()
    consumer = Candidate007LiveConsumer(
        host=paper_host,
        strategy=strategy,
        alert_manager=alert_mgr,
        on_cycle=wrapped_on_cycle,
    )

    def on_reset() -> None:
        portfolio.cash = initial_balance
        portfolio.start_of_day_equity = initial_balance
        portfolio.peak_equity = initial_balance
        portfolio.positions.clear()
        strategy._daily_trade_counts.clear()
        strategy._bars_since_last_trade = 999

    obs_log = SQLiteMarketObservationLog(obs_log_path)
    store = Candidate007SnapshotStore(obs_log, consumer, on_reset=on_reset)
    handler = _handler_for(store, token, expected_symbol=symbol, execution_queue=execution_queue)

    server = ReadOnlyBridgeServer((host, port), handler, store)
    return server, strategy, portfolio, journal, execution_queue
