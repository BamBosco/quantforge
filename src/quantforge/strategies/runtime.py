"""Runtime strategy boundary for candidates approved for paper operation."""

from datetime import datetime
from typing import Protocol

from quantforge.application.trading_pipeline import MarketFact, TradingSignal


class RuntimeStrategy(Protocol):
    """A strategy may create a signal; it cannot size or execute an order."""

    strategy_id: str

    def evaluate(
        self, market: MarketFact, *, evaluated_at: datetime
    ) -> TradingSignal | None:
        """Return one valid signal or no signal for this observation."""
