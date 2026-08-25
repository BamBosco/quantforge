"""Paper-only engineering strategy used to exercise the runtime lifecycle."""

from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from quantforge.application.trading_pipeline import MarketFact, TradingSignal

NEW_YORK = ZoneInfo("America/New_York")


class ExperimentalPaperStrategy001:
    """A deterministic, non-research strategy with no profitability claim."""

    strategy_id = "experimental_paper_strategy_001"
    version = "0.1"
    paper_only = True
    _entry_time = time(9, 0)
    _stop_distance = Decimal("1")
    _target_distance = Decimal("1")

    def __init__(self) -> None:
        self._traded_dates: set[str] = set()

    def evaluate(
        self, market: MarketFact, *, evaluated_at: datetime
    ) -> TradingSignal | None:
        """Emit one synthetic paper probe signal during the 09:00 NY minute."""
        if not self._valid_market(market):
            return None
        # The strategy cycle belongs to the observed market event, not to the
        # wall-clock instant a local poller happens to dispatch it.
        session_time = market.observed_at.astimezone(NEW_YORK)
        date_key = session_time.date().isoformat()
        if (
            session_time.weekday() > 4
            or session_time.hour != self._entry_time.hour
            or session_time.minute != self._entry_time.minute
        ):
            return None
        if date_key in self._traded_dates:
            return None
        self._traded_dates.add(date_key)
        entry_price = market.ask
        return TradingSignal(
            strategy_id=self.strategy_id,
            instrument="XAUUSD",
            side="buy",
            entry_price=entry_price,
            stop_loss_price=entry_price - self._stop_distance,
            target_price=entry_price + self._target_distance,
            scheduled_exit_at=datetime.combine(
                session_time.date(), time(13, 30), tzinfo=NEW_YORK
            ).astimezone(UTC),
            rationale="PAPER-ONLY engineering lifecycle probe; not a trading edge",
            signal_id=uuid5(
                NAMESPACE_URL,
                f"{self.strategy_id}:{self.version}:{date_key}:buy",
            ),
        )

    @staticmethod
    def _valid_market(market: MarketFact) -> bool:
        return bool(
            market.instrument == "XAUUSD"
            and market.observed_at.tzinfo is not None
            and market.observed_at.utcoffset() is not None
            and market.bid > 0
            and market.ask >= market.bid
        )
