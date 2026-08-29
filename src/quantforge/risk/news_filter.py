"""QuantForge Institutional News & Economic Calendar Risk Shield.

Protects Gold (XAUUSD) and Forex pairs from violent slippage and spread spikes
during high-impact macroeconomic releases (CPI, NFP, FOMC, Fed Rate Decisions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Sequence
import json
import urllib.request


@dataclass(frozen=True, slots=True)
class MacroEvent:
    title: str
    country: str
    currency: str
    impact: str  # "HIGH", "MEDIUM", "LOW"
    scheduled_at_utc: datetime


class NewsRiskShield:
    """Manages pre-news and post-news trading blackouts for high-impact releases."""

    def __init__(
        self,
        *,
        pre_event_blackout_minutes: int = 15,
        post_event_blackout_minutes: int = 15,
        max_allowed_spread_dollars: float = 0.50,
    ) -> None:
        self.pre_event_blackout = timedelta(minutes=pre_event_blackout_minutes)
        self.post_event_blackout = timedelta(minutes=post_event_blackout_minutes)
        self.max_allowed_spread_dollars = max_allowed_spread_dollars
        self._cached_events: list[MacroEvent] = []
        self._last_fetch_utc: datetime | None = None

    def is_news_blackout(
        self,
        current_time_utc: datetime,
        currency: str = "USD",
    ) -> tuple[bool, str]:
        """Check if current time is within a High-Impact news blackout window."""
        for event in self._cached_events:
            if event.impact == "HIGH" and event.currency.upper() == currency.upper():
                window_start = event.scheduled_at_utc - self.pre_event_blackout
                window_end = event.scheduled_at_utc + self.post_event_blackout
                if window_start <= current_time_utc <= window_end:
                    mins_to_event = int((event.scheduled_at_utc - current_time_utc).total_seconds() / 60)
                    if mins_to_event > 0:
                        reason = f"🛑 High-Impact News Blackout: '{event.title}' in {mins_to_event} min ({event.scheduled_at_utc.strftime('%H:%M')} UTC)"
                    else:
                        reason = f"🛑 High-Impact News Blackout: Post-event volatility settling for '{event.title}'"
                    return True, reason

        return False, "Clear (No High-Impact News Nearby)"

    def is_spread_safe(self, current_spread_dollars: float) -> tuple[bool, str]:
        """Protect against broker spread widening during volatility spikes."""
        if current_spread_dollars > self.max_allowed_spread_dollars:
            return False, f"🛑 Spread Spike Protection: Spread (${current_spread_dollars:.2f}) exceeds max allowed (${self.max_allowed_spread_dollars:.2f})"
        return True, "Spread Normal"

    def update_calendar_events(self, events: Sequence[MacroEvent]) -> None:
        """Inject upcoming calendar events."""
        self._cached_events = list(events)
        self._last_fetch_utc = datetime.now(timezone.utc)
