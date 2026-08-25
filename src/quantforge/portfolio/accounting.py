"""Deterministic, decimal-safe portfolio accounting.

This module deliberately contains no broker or persistence dependency.  An
adapter supplies normalized fills and marks; the resulting state can then be
persisted or replayed from the durable journal.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from quantforge.risk.limits import AccountRiskSnapshot


@dataclass(frozen=True, slots=True)
class Fill:
    """A normalized execution fill used to update portfolio state."""

    instrument: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.instrument:
            raise ValueError("instrument must not be empty")
        if self.side not in {"buy", "sell"}:
            raise ValueError("side must be either 'buy' or 'sell'")
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill quantity and price must be positive")
        if self.fee < 0:
            raise ValueError("fill fee must not be negative")


@dataclass(frozen=True, slots=True)
class Position:
    """Net position and its weighted average open price."""

    quantity: Decimal
    average_open_price: Decimal
    realized_pnl: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.quantity == 0:
            raise ValueError("zero-quantity positions must not be stored")
        if self.average_open_price <= 0:
            raise ValueError("average open price must be positive")


@dataclass(slots=True)
class Portfolio:
    """In-memory projection of fills and marks for one account.

    Positive quantities represent long positions; negative quantities represent
    shorts.  ``cash`` includes realized P&L and fees, while open positions are
    valued from the most recent mark (or their cost when no mark exists).
    """

    initial_cash: Decimal
    start_of_day_equity: Decimal | None = None
    cash: Decimal = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict, init=False)
    marks: dict[str, Decimal] = field(default_factory=dict, init=False)
    peak_equity: Decimal = field(init=False)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial cash must be positive")
        if self.start_of_day_equity is None:
            self.start_of_day_equity = self.initial_cash
        elif self.start_of_day_equity <= 0:
            raise ValueError("start-of-day equity must be positive")
        self.cash = self.initial_cash
        self.peak_equity = self.initial_cash

    def apply_fill(self, fill: Fill) -> None:
        """Apply a fill, realizing P&L only for the closed portion."""
        signed_quantity = fill.quantity if fill.side == "buy" else -fill.quantity
        current = self.positions.get(fill.instrument)
        current_quantity = current.quantity if current else Decimal("0")
        current_price = current.average_open_price if current else fill.price
        realized = current.realized_pnl if current else Decimal("0")

        closing_quantity = min(abs(current_quantity), abs(signed_quantity)) if (
            current_quantity and current_quantity * signed_quantity < 0
        ) else Decimal("0")
        if closing_quantity:
            direction = Decimal("1") if current_quantity > 0 else Decimal("-1")
            realized += closing_quantity * (fill.price - current_price) * direction

        new_quantity = current_quantity + signed_quantity
        self.cash -= fill.fee
        if new_quantity == 0:
            self.cash += realized
            del self.positions[fill.instrument]
        else:
            if current_quantity == 0 or current_quantity * signed_quantity > 0:
                average_price = (
                    fill.price
                    if current_quantity == 0
                    else (
                        abs(current_quantity) * current_price
                        + abs(signed_quantity) * fill.price
                    )
                    / abs(new_quantity)
                )
            elif current_quantity * new_quantity < 0:
                # A reversal: the residual quantity opened at this fill price.
                self.cash += realized
                realized = Decimal("0")
                average_price = fill.price
            else:
                average_price = current_price
            self.positions[fill.instrument] = Position(
                new_quantity, average_price, realized
            )
        self._update_peak_equity()

    def mark(self, instrument: str, price: Decimal) -> None:
        """Record a current, normalized instrument mark."""
        if not instrument or price <= 0:
            raise ValueError("instrument and positive mark price are required")
        self.marks[instrument] = price
        self._update_peak_equity()

    @property
    def equity(self) -> Decimal:
        """Current marked-to-market account equity."""
        return self.cash + sum(
            position.quantity
            * (
                self.marks.get(instrument, position.average_open_price)
                - position.average_open_price
            )
            for instrument, position in self.positions.items()
        ) + sum(position.realized_pnl for position in self.positions.values())

    def risk_snapshot(self, *, correlated_open_risk: Decimal) -> AccountRiskSnapshot:
        """Return the account facts required by the independent risk gate."""
        if correlated_open_risk < 0:
            raise ValueError("correlated open risk must not be negative")
        assert self.start_of_day_equity is not None
        return AccountRiskSnapshot(
            current_equity=self.equity,
            start_of_day_equity=self.start_of_day_equity,
            peak_equity=self.peak_equity,
            correlated_open_risk=correlated_open_risk,
        )

    def _update_peak_equity(self) -> None:
        self.peak_equity = max(self.peak_equity, self.equity)
