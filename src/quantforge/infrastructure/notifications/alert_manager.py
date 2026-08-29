"""Central Alert and Notification Manager for QuantForge.

Coordinates audio sound triggers, Telegram notifications, and logging
whenever trade events, risk approvals, or executions occur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from quantforge.application.paper_runtime import RuntimeCycleResult
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.notifications.telegram_notifier import (
    TelegramNotifier,
)


@dataclass
class AlertManager:
    """Manages audio alerts, notifications, and event broadcasting."""

    telegram: TelegramNotifier = field(default_factory=TelegramNotifier)
    sound_enabled: bool = True

    def process_cycle_result(
        self, result: RuntimeCycleResult, observation: ObservationEnvelope
    ) -> dict[str, Any]:
        """Dispatch notifications and generate UI audio triggers based on cycle events."""
        events: list[dict[str, Any]] = []

        # Handle direct signal intent dispatch
        if (
            getattr(result, "signal_generated", False)
            and getattr(result, "intent", None) is not None
        ):
            intent = result.intent
            self.telegram.send_signal_alert(
                instrument=observation.broker_symbol,
                side=intent.side,
                entry_price=intent.entry_price,
                stop_loss=intent.stop_loss_price,
                target_price=intent.target_price,
                strategy_name="Candidate 007 Scalper",
            )
            events.append(
                {
                    "type": "SIGNAL",
                    "sound": "signal_buy" if intent.side == "buy" else "signal_sell",
                    "title": f"🎯 Signal: {intent.side.upper()} {observation.broker_symbol}",
                    "details": f"Price: ${float(intent.entry_price):,.2f}",
                }
            )

        # Handle executions
        for ex in getattr(result, "executions", ()):
            if ex.fill is not None and ex.outcome is not None:
                if ex.outcome.status == "filled":
                    side = ex.outcome.side
                    p = float(ex.fill.price)
                    dist = 15.0 if "BTC" in observation.broker_symbol.upper() else 1.5
                    sl = Decimal(str(p - dist if side == "buy" else p + dist))
                    tp = Decimal(
                        str(p + (dist * 1.5) if side == "buy" else p - (dist * 1.5))
                    )

                    self.telegram.send_signal_alert(
                        instrument=observation.broker_symbol,
                        side=side,
                        entry_price=ex.fill.price,
                        stop_loss=sl,
                        target_price=tp,
                        strategy_name="Candidate 007 Scalper",
                    )
                    events.append(
                        {
                            "type": "FILL",
                            "sound": "fill_success",
                            "title": f"⚡ Filled: {side.upper()} {ex.outcome.quantity} lots",
                            "details": f"Price: ${p:,.2f}",
                        }
                    )
                elif ex.outcome.status in {
                    "stopped_out",
                    "target_reached",
                    "forced_exit",
                }:
                    self.telegram.send_fill_execution(
                        instrument=observation.broker_symbol,
                        side=ex.outcome.side,
                        lots=ex.outcome.quantity,
                        price=ex.fill.price,
                        fee=ex.fill.fee,
                    )
                    events.append(
                        {
                            "type": "EXIT",
                            "sound": "fill_success",
                            "title": f"🏁 Exit ({ex.outcome.status}): {ex.outcome.side.upper()} @ ${float(ex.fill.price):,.2f}",
                            "details": f"Lots: {ex.outcome.quantity}",
                        }
                    )

        return {"dispatched_events": events}
