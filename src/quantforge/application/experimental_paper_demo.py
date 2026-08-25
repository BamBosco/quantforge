"""Deterministic PAPER MODE lifecycle demonstration; not a trading simulation."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.application.paper_runtime import (
    InstrumentRiskMetadata,
    PaperRuntimeHost,
)
from quantforge.application.trading_pipeline import PaperTradingPipeline
from quantforge.execution import PaperExecutor
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Portfolio
from quantforge.risk.limits import RiskLimits
from quantforge.strategies import ExperimentalPaperStrategy001


def demo_observation(
    *, observed_at: datetime, bid: Decimal, ask: Decimal
) -> ObservationEnvelope:
    """Build a deterministic test observation for the engineering demonstration."""
    timestamp = observed_at.astimezone(UTC).isoformat()
    return ObservationEnvelope.from_payload(
        {
            "schema_version": 2,
            "observed_at_utc": timestamp,
            "source": {"adapter": "demo_fixture", "broker_profile_id": "paper"},
            "account": {
                "account_id": "paper-demo",
                "server": "PAPER-ONLY",
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
                "bid": float(bid),
                "ask": float(ask),
                "tick_time_utc": timestamp,
                "spread_points": float((ask - bid) / Decimal("0.01")),
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


def run_demo(base_path: Path) -> dict[str, object]:
    """Run one deterministic fill-and-target lifecycle against paper components."""
    journal = SQLiteEventJournal(base_path / "paper.sqlite3")
    portfolio = Portfolio(Decimal("10000"))
    executor = PaperExecutor(portfolio, journal=journal)
    host = PaperRuntimeHost(
        strategy=ExperimentalPaperStrategy001(),
        pipeline=PaperTradingPipeline(
            limits=RiskLimits(
                Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
            ),
            policy_version="paper-engineering-0.1",
            max_market_age=timedelta(seconds=30),
            approval_ttl=timedelta(seconds=10),
            journal=journal,
        ),
        executor=executor,
        portfolio=portfolio,
        observation_log=SQLiteMarketObservationLog(base_path / "observations.sqlite3"),
        instrument_metadata={"XAUUSD": InstrumentRiskMetadata(Decimal("100"))},
        correlated_open_risk=lambda _: Decimal("0"),
        pending_order_projection=lambda _: executor.pending_statuses(),
        max_observation_age=timedelta(seconds=30),
    )
    entry_time = datetime(2026, 8, 21, 13, 0, tzinfo=UTC)
    entry = host.process(
        demo_observation(
            observed_at=entry_time, bid=Decimal("99.9"), ask=Decimal("100")
        ),
        evaluated_at=entry_time,
    )
    exit_time = datetime(2026, 8, 21, 13, 1, tzinfo=UTC)
    exit_result = host.process(
        demo_observation(
            observed_at=exit_time, bid=Decimal("101"), ask=Decimal("101.1")
        ),
        evaluated_at=exit_time,
    )
    output = {
        "mode": "PAPER-ONLY ENGINEERING DEMONSTRATION",
        "entry_status": entry.executions[-1].outcome.status,
        "exit_status": exit_result.executions[0].outcome.status,
        "positions": len(portfolio.positions),
        "reconciled": executor.reconcile().matched,
        "journal_events": [event["event_type"] for event in journal.events()],
    }
    journal.close()
    return output


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="quantforge-paper-demo-") as directory:
        print(json.dumps(run_demo(Path(directory)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
