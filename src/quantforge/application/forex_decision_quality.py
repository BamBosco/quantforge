"""Run the non-executable USDJPY decision-quality evaluator once."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantforge.application.decision_quality_evaluator import DecisionQualityEvaluator
from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only decision-quality evaluator"
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
        raise RuntimeError(
            "decision-quality evaluation refuses order-capable configuration"
        )
    log = SQLiteMarketObservationLog(settings.logging.journal_path)
    try:
        results = DecisionQualityEvaluator(log).evaluate_available()
        print(f"evaluations_persisted={len(results)}")
        for result in results:
            print(result.evaluation["outcome_classification"])
    finally:
        log.close()


if __name__ == "__main__":
    main()
