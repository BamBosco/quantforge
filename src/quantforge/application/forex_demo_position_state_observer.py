"""Run one read-only USDJPY demo position-state observation."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.demo_position_state import (
    MT5DemoPositionStateObserver,
)
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only USDJPY demo position observer"
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config/forex_mt5_demo_usdjpy.toml")
    )
    arguments = parser.parse_args()
    settings = load_forex_mt5_demo_settings(arguments.config)
    log = SQLiteMarketObservationLog(settings.logging.journal_path)
    try:
        result = MT5DemoPositionStateObserver(log, settings).observe_latest()
        if result is None:
            print("no bridge observation is available")
        elif result.accepted:
            print("position state observed")
        else:
            print("position state rejected: " + "; ".join(result.issues))
    finally:
        log.close()


if __name__ == "__main__":
    main()
