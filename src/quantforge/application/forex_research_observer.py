"""One-shot, research-only USDJPY M1 observation command.

It cannot submit, simulate, or modify an order.  It only consumes a fresh
closed-candle snapshot and appends a validated local-model decision to SQLite.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from quantforge.application.tradingagents_forex import TradingAgentsForexResearch
from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.daily_equity_baseline import (
    MT5DailyEquityBaselineResolver,
)
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.infrastructure.mt5.research_snapshot import (
    MT5ResearchSnapshotConsumer,
    policy_from_demo_settings,
)
from quantforge.infrastructure.ollama_research import OllamaResearchBackend
from quantforge.risk.forex_gate import ForexRiskContext, ForexRiskGate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only USDJPY decision observer"
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config/forex_mt5_demo_usdjpy.toml")
    )
    arguments = parser.parse_args()
    settings = load_forex_mt5_demo_settings(arguments.config)
    if (
        settings.execution.live_trading_enabled
        or settings.execution.order_submission_enabled
    ):
        raise RuntimeError("research observer refuses all order-capable configurations")
    log = SQLiteMarketObservationLog(settings.logging.journal_path)
    try:
        snapshot = MT5ResearchSnapshotConsumer(
            log, policy=policy_from_demo_settings(settings)
        ).consume_latest()
        if snapshot is None:
            print("no bridge observation is available")
            return
        if not snapshot.accepted:
            print("snapshot rejected: " + "; ".join(snapshot.issues))
            return
        backend = OllamaResearchBackend(
            base_url=settings.llm.backend_url or "http://127.0.0.1:11434",
            model=settings.llm.deep_think_model,
        )
        baseline_resolver = MT5DailyEquityBaselineResolver(log, settings)

        def risk_context(snapshot: dict[str, object]) -> ForexRiskContext | None:
            baseline = baseline_resolver.resolve(snapshot)
            return ForexRiskContext(baseline) if baseline is not None else None

        result = TradingAgentsForexResearch(
            log,
            backend,
            max_risk_percent=settings.risk.risk_per_trade,
            risk_gate=ForexRiskGate(settings.risk),
            risk_context_provider=risk_context,
        ).run_latest()
        assert result is not None
        if result.accepted:
            print("decision accepted")
        else:
            print("decision rejected: " + "; ".join(result.reasons))
        if result.trade_intent is not None:
            print(result.trade_intent)
    finally:
        log.close()


if __name__ == "__main__":
    main()
