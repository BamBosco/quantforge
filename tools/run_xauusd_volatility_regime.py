#!/usr/bin/env python3
"""Run the offline XAUUSD volatility study against a verified frozen export."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantforge.backtest.volatility_regime_runner import run_volatility_regime_study


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    run = run_volatility_regime_study(
        data_path=args.data,
        manifest_path=args.manifest,
        configuration_path=args.config,
    )
    report = run.report
    print(f"dataset_id={run.manifest.dataset_id}")
    print(f"dataset_sha256={run.manifest.sha256}")
    print(f"study_id={run.configuration.study_id}")
    print(f"study_version={run.configuration.version}")
    print(f"valid_observations={report.valid_observations}")
    print(f"excluded_sessions={report.excluded_sessions}")
    for name, metrics in (
        ("development", report.development_metrics),
        ("holdout", report.holdout_metrics),
    ):
        print(f"{name}_scored_sessions={metrics.scored_sessions}")
        print(f"{name}_baseline_mae={metrics.baseline_mae}")
        print(f"{name}_model_mae={metrics.model_mae}")
        print(f"{name}_improvement={metrics.improvement}")
    print(f"passed={report.gate_decision.passed}")
    print(f"reasons={' | '.join(report.gate_decision.reasons)}")


if __name__ == "__main__":
    main()
