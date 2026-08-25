"""PAPER-ONLY runner polling the durable read-only observation log."""

from __future__ import annotations

import argparse
import logging
import time
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

logger = logging.getLogger(__name__)


def build_host(
    *, observation_log_path: Path, journal_path: Path, kill_switch_path: Path
) -> tuple[PaperRuntimeHost, SQLiteMarketObservationLog, SQLiteEventJournal]:
    """Build only the paper path; no MT5 execution adapter exists here."""
    source_log = SQLiteMarketObservationLog(observation_log_path)
    journal = SQLiteEventJournal(journal_path)
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
        observation_log=source_log,
        instrument_metadata={"XAUUSD": InstrumentRiskMetadata(Decimal("100"))},
        correlated_open_risk=lambda _: Decimal("0"),
        pending_order_projection=lambda _: executor.pending_statuses(),
        max_observation_age=timedelta(seconds=30),
        kill_switch_active=kill_switch_path.exists,
    )
    return host, source_log, journal


def run_once(
    host: PaperRuntimeHost,
    source_log: SQLiteMarketObservationLog,
    seen_observation_ids: set[str],
    *,
    evaluated_at: datetime | None = None,
) -> int:
    """Process newly received read-only observations in durable-log order."""
    processed = 0
    now = evaluated_at or datetime.now(UTC)
    observations = reversed(source_log.recent_observations(limit=100))
    for stored in observations:
        observation_id = str(stored["observation_id"])
        if observation_id in seen_observation_ids:
            continue
        seen_observation_ids.add(observation_id)
        result = host.process(
            ObservationEnvelope.from_payload(stored["payload"]),
            evaluated_at=now,
        )
        logger.info(
            "PAPER MODE observation=%s accepted=%s signal=%s approved=%s reason=%s",
            observation_id,
            result.accepted,
            result.signal_generated,
            result.order_approved,
            result.reason or "-",
        )
        processed += 1
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QuantForge PAPER-ONLY Experimental Strategy 001 runner"
    )
    parser.add_argument("--observation-log", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--kill-switch-file", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be positive")
    if args.symbol != "XAUUSD":
        raise SystemExit("ExperimentalPaperStrategy001 supports only --symbol XAUUSD")
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    logger.warning("PAPER MODE ONLY: no MT5 order execution capability is present")
    host, source_log, journal = build_host(
        observation_log_path=args.observation_log,
        journal_path=args.journal,
        kill_switch_path=args.kill_switch_file,
    )
    seen: set[str] = set()
    try:
        while True:
            run_once(host, source_log, seen)
            if args.once:
                return
            time.sleep(args.poll_seconds)
    finally:
        source_log.close()
        journal.close()


if __name__ == "__main__":
    main()
