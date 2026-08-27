from pathlib import Path

from tools.analyze_xauusd_historical_boundaries import analyze


def test_analyze_daily_boundaries_and_long_gaps(tmp_path: Path) -> None:
    dataset = tmp_path / "xauusd.tsv"
    dataset.write_text(
        "<DATE>\t<TIME>\t<SPREAD>\n"
        "2025.01.06\t01:00:00\t8\n"
        "2025.01.06\t23:58:00\t20\n"
        "2025.01.07\t02:00:00\t30\n"
        "2025.01.07\t02:01:00\t12\n"
    )

    result = analyze(dataset)

    assert result["observed_dates"] == 2
    assert result["first_bar_hours"] == {1: 1, 2: 1}
    assert result["delayed_or_shifted_opens"][0]["first"] == "02:00"
    assert result["long_gap_count"] == 2
    assert result["gaps_over_30_minutes"][0]["before_spread"] == 8.0
    assert result["gaps_over_30_minutes"][0]["after_spread"] == 20.0
