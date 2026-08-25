"""Shared, broker-neutral execution value objects."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    instrument: str
    bid: Decimal
    ask: Decimal
    observed_at: datetime
