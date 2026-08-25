from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from quantforge.backtest.candidate_003 import (
    COST_SCENARIOS,
    EVALUATION_FILENAME,
    EVALUATION_MANIFEST,
    MINIMUM_QUALIFYING_SESSIONS,
    PROVENANCE_ADDENDUM,
    load_frozen_evaluation,
    settings,
    simulate_session,
)
from quantforge.backtest.candidate_003_runner import _verify_authorization
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import SessionOutcome


def bar(
    moment: datetime, open_: str, close: str, low: str = "99", high: str = "102"
) -> MinuteBar:
    return MinuteBar(
        moment, Decimal(open_), Decimal(high), Decimal(low), Decimal(close), 1, 2
    )


def session(
    day: date, *, first_open: str = "100", last_close: str = "101"
) -> list[MinuteBar]:
    start = datetime(day.year, day.month, day.day, 13, 20, tzinfo=UTC)
    bars = [bar(start + timedelta(minutes=i), "100", "100") for i in range(311)]
    for index in range(5, len(bars)):
        bars[index] = bar(bars[index].timestamp, "100", "100", low="99.5")
    bars[0] = bar(start, first_open, "100")
    bars[4] = bar(start + timedelta(minutes=4), "100", last_close)
    # The ordinary 08:25 bar does not touch the long stop; explicit tests cover
    # the conservative entry-bar ambiguity separately.
    bars[5] = bar(start + timedelta(minutes=5), "100", "100", low="99.5")
    return bars


def test_fixed_cost_scenarios_and_direction() -> None:
    assert (Decimal("0"), Decimal("1"), Decimal("3")) == COST_SCENARIOS
    assert MINIMUM_QUALIFYING_SESSIONS == 709
    result = simulate_session(
        session(date(2024, 1, 2)),
        session_day=date(2024, 1, 2),
        slippage_points=Decimal("1"),
    )
    assert result.entry_side == "buy"
    assert result.entry_price == Decimal("100.003")


def test_stop_gap_can_produce_r_below_negative_one_and_exit_precedes_stop() -> None:
    bars = session(date(2024, 1, 2))
    bars[6] = bar(bars[6].timestamp, "98", "98", low="97", high="99")
    stopped = simulate_session(
        bars, session_day=date(2024, 1, 2), slippage_points=Decimal("0")
    )
    assert stopped.outcome is SessionOutcome.STOPPED_OUT
    assert stopped.r_multiple is not None and stopped.r_multiple < Decimal("-1")

    bars = session(date(2024, 1, 2))
    bars[-1] = bar(bars[-1].timestamp, "101", "101", low="90", high="102")
    forced = simulate_session(
        bars, session_day=date(2024, 1, 2), slippage_points=Decimal("0")
    )
    assert forced.outcome is SessionOutcome.FORCED_EXIT


def test_dst_duplicate_missing_and_idempotency() -> None:
    day = date(2024, 3, 11)  # First New York trading day after DST begins.
    start = datetime(2024, 3, 11, 12, 20, tzinfo=UTC)
    bars = [bar(start + timedelta(minutes=index), "100", "100") for index in range(311)]
    bars[4] = bar(bars[4].timestamp, "100", "101")
    bars[5] = bar(bars[5].timestamp, "100", "100", low="99.5")
    first = simulate_session(bars, session_day=day, slippage_points=Decimal("0"))
    second = simulate_session(bars, session_day=day, slippage_points=Decimal("0"))
    assert first == second

    duplicated = [*bars, bars[10]]
    assert (
        simulate_session(
            duplicated, session_day=day, slippage_points=Decimal("0")
        ).outcome
        is SessionOutcome.INVALID_DATA
    )
    assert (
        simulate_session(
            bars[:-1], session_day=day, slippage_points=Decimal("0")
        ).outcome
        is SessionOutcome.INVALID_DATA
    )


def test_neutral_is_no_trade_and_missing_session_is_invalid() -> None:
    neutral = simulate_session(
        session(date(2024, 1, 2), last_close="100"),
        session_day=date(2024, 1, 2),
        slippage_points=Decimal("0"),
    )
    assert neutral.outcome is SessionOutcome.NO_TRADE
    invalid = simulate_session(
        session(date(2024, 1, 2))[:-1],
        session_day=date(2024, 1, 2),
        slippage_points=Decimal("0"),
    )
    assert invalid.outcome is SessionOutcome.INVALID_DATA


def test_entry_bar_stop_is_ambiguous_and_invalid_cost_is_rejected() -> None:
    bars = session(date(2024, 1, 2))
    bars[5] = bar(bars[5].timestamp, "100", "100", low="99", high="102")
    result = simulate_session(
        bars, session_day=date(2024, 1, 2), slippage_points=Decimal("0")
    )
    assert result.outcome is SessionOutcome.AMBIGUOUS
    with pytest.raises(ValueError):
        settings(Decimal("2"))


def test_dataset_identity_rejects_checksum_mismatch_and_confirmation_path(
    tmp_path,
) -> None:
    evaluation = tmp_path / EVALUATION_FILENAME
    evaluation.write_text("synthetic-only")
    manifest = tmp_path / EVALUATION_MANIFEST
    manifest.write_text("")
    provenance = tmp_path / PROVENANCE_ADDENDUM
    provenance.write_text("")
    with pytest.raises(ValueError, match="SHA-256"):
        load_frozen_evaluation(evaluation, manifest=manifest, provenance=provenance)

    confirmation = tmp_path / "confirmation" / EVALUATION_FILENAME
    confirmation.parent.mkdir()
    confirmation.write_text("synthetic-only")
    with pytest.raises(ValueError, match="confirmation"):
        load_frozen_evaluation(confirmation, manifest=manifest, provenance=provenance)


def test_authorization_record_must_bind_the_exact_frozen_bundle(tmp_path) -> None:
    authorization = tmp_path / "authorization.toml"
    authorization.write_text("[authorization]\ncandidate_id = 'wrong'\n")
    with pytest.raises(SystemExit, match="does not exactly bind"):
        _verify_authorization(authorization)
