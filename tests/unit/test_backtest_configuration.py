from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from quantforge.backtest.configuration import (
    load_cost_scenarios,
    load_directional_bias_settings,
    load_instrument_point_size,
)
from quantforge.backtest.dataset import (
    DatasetManifest,
    load_dataset_manifest,
    verify_dataset_checksum,
)

ROOT = Path(__file__).parents[2]


def test_loads_versioned_orb_cost_scenarios_and_broker_point_size() -> None:
    scenarios = load_cost_scenarios(
        ROOT / "config/strategies/orb_xauusd_headway_demo_baseline.toml"
    )
    point_size = load_instrument_point_size(
        ROOT / "config/brokers/headway_demo.toml",
        "XAUUSD",
    )

    assert [item.name for item in scenarios] == [
        "recorded_spread_only",
        "plus_1_point",
        "plus_3_points",
    ]
    assert point_size.as_tuple().digits == (1,)


def test_loads_experiment_directional_bias_without_changing_baseline() -> None:
    experiment = load_directional_bias_settings(
        ROOT / "config/strategies/orb_xauusd_headway_demo_overnight_bias.toml"
    )
    baseline = load_directional_bias_settings(
        ROOT / "config/strategies/orb_xauusd_headway_demo_baseline.toml"
    )

    assert experiment is not None
    assert experiment.start_time.isoformat() == "00:00:00"
    assert experiment.end_time.isoformat() == "08:19:00"
    assert baseline is None


def test_loads_dataset_manifest() -> None:
    manifest = load_dataset_manifest(
        ROOT / "config/datasets/headway_demo_xauusd_m1_20260505_20260814.toml"
    )

    assert manifest.instrument == "XAUUSD"
    assert len(manifest.excluded_session_days) == 10


def test_rejects_checksum_mismatch(tmp_path: Path) -> None:
    dataset = tmp_path / "bars.csv"
    dataset.write_text("different data", encoding="utf-8")
    manifest = DatasetManifest(
        dataset_id="test",
        instrument="XAUUSD",
        sha256=sha256(b"expected data").hexdigest(),
        source_timezone="America/Chicago",
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_utc=datetime(2026, 1, 2, tzinfo=UTC),
        excluded_session_days=frozenset(),
    )

    with pytest.raises(ValueError, match="checksum"):
        verify_dataset_checksum(dataset, manifest)
