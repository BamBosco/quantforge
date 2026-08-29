from pathlib import Path

import pytest

from quantforge.backtest.volatility_regime_runner import run_volatility_regime_study


def test_rejects_a_non_xauusd_manifest_before_accessing_data(tmp_path: Path) -> None:
    manifest = tmp_path / "dataset.toml"
    manifest.write_text(
        """
[identity]
dataset_id = "usdjpy"
instrument = "USDJPY"
sha256 = "0000000000000000000000000000000000000000000000000000000000000000"

[time]
source_timezone = "UTC"
start_utc = "2026-01-01T00:00:00+00:00"
end_utc = "2026-01-02T00:00:00+00:00"

[quality]
excluded_session_days = []
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires an XAUUSD"):
        run_volatility_regime_study(
            data_path=tmp_path / "not-read.csv",
            manifest_path=manifest,
            configuration_path=tmp_path / "not-read.toml",
        )
