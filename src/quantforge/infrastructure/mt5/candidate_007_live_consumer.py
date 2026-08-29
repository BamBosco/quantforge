"""Candidate 007 Live MT5 Observation Consumer.

Connects live incoming MT5 ObservationEnvelopes directly into Candidate007Strategy
and the QuantForge Paper Trading Runtime, dispatching real-time audio and Telegram alerts.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from quantforge.application.paper_runtime import PaperRuntimeHost, RuntimeCycleResult
from quantforge.backtest.models import MinuteBar
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import StoredObservation
from quantforge.infrastructure.notifications.alert_manager import AlertManager
from quantforge.strategies.candidate_007 import Candidate007Strategy


class Candidate007LiveConsumer:
    """Consumes real-time MT5 observation envelopes and drives Candidate 007."""

    def __init__(
        self,
        host: PaperRuntimeHost,
        strategy: Candidate007Strategy,
        alert_manager: AlertManager | None = None,
        on_cycle: Callable[[RuntimeCycleResult, ObservationEnvelope], None]
        | None = None,
    ) -> None:
        self.host = host
        self.strategy = strategy
        self.alert_manager = alert_manager or AlertManager()
        self.on_cycle = on_cycle
        self._last_completed_bar_time: str | None = None
        self._processed_observations = 0

    def consume(
        self, observation: ObservationEnvelope, receipt: StoredObservation
    ) -> RuntimeCycleResult | None:
        """Process an incoming MT5 observation through strategy, risk runtime, and alerts."""
        self._processed_observations += 1

        # 1. Ingest newly completed M1 candle if present in observation payload
        candles = observation.payload.get("candles", {})
        completed_candles = (
            candles.get("completed", []) if isinstance(candles, dict) else []
        )
        if completed_candles:
            latest_candle = completed_candles[-1]
            candle_time = latest_candle.get("open_time_utc")
            if candle_time and candle_time != self._last_completed_bar_time:
                open_time = datetime.fromisoformat(candle_time)
                bar = MinuteBar(
                    timestamp=open_time,
                    open=Decimal(str(latest_candle["open"])),
                    high=Decimal(str(latest_candle["high"])),
                    low=Decimal(str(latest_candle["low"])),
                    close=Decimal(str(latest_candle["close"])),
                    tick_volume=int(latest_candle.get("tick_volume", 10)),
                    spread_points=20,
                )
                self.strategy.update_bar(bar)
                self._last_completed_bar_time = candle_time

        # 2. Evaluate real-time market quote through Strategy -> Risk Gate -> Paper Executor
        result = self.host.process(
            observation, evaluated_at=observation.observed_at_utc
        )

        # 3. Trigger Telegram & Sound Alerts on events
        self.alert_manager.process_cycle_result(result, observation)

        if self.on_cycle is not None:
            self.on_cycle(result, observation)

        return result

    def close(self) -> None:
        """Clean up resources if needed."""
        pass
