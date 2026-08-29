"""Unit tests for TelegramNotifier and AlertManager."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from quantforge.infrastructure.notifications.alert_manager import AlertManager
from quantforge.infrastructure.notifications.telegram_notifier import (
    TelegramConfig,
    TelegramNotifier,
)


def test_telegram_notifier_unconfigured_graceful_fallback() -> None:
    notifier = TelegramNotifier(TelegramConfig(bot_token="", chat_id=""))
    assert not notifier.is_configured
    assert not notifier.send_message("Test message")


def test_telegram_notifier_formatted_signal_alert() -> None:
    notifier = TelegramNotifier(TelegramConfig(bot_token="test_tok", chat_id="test_chat"))
    assert notifier.is_configured

    with patch.object(notifier, "_post_message_sync", return_value=True) as mock_post:
        success = notifier.send_signal_alert(
            instrument="#BTCUSD",
            side="buy",
            entry_price=Decimal("77650.00"),
            stop_loss=Decimal("77600.00"),
            target_price=Decimal("77750.00"),
            rationale="ATR expansion & 50 EMA trend",
        )
        assert success
        assert mock_post.called
        msg = mock_post.call_args[0][0]
        assert "BUY SIGNAL" in msg
        assert "#BTCUSD" in msg
        assert "$77,650.00" in msg
        assert "$77,750.00" in msg


def test_telegram_notifier_risk_and_fill_alerts() -> None:
    notifier = TelegramNotifier(TelegramConfig(bot_token="test_tok", chat_id="test_chat"))

    with patch.object(notifier, "_post_message_sync", return_value=True) as mock_post:
        # Risk Gate Alert
        notifier.send_risk_approval(
            instrument="BTCUSD",
            side="buy",
            lots=Decimal("0.15"),
            risk_dollars=Decimal("100.00"),
        )
        assert mock_post.called
        msg = mock_post.call_args[0][0]
        assert "Risk Gate" in msg
        assert "0.15 lots" in msg

        # Fill Alert
        notifier.send_fill_execution(
            instrument="BTCUSD",
            side="buy",
            lots=Decimal("0.15"),
            price=Decimal("77650.00"),
            fee=Decimal("1.50"),
        )
        msg2 = mock_post.call_args[0][0]
        assert "Paper Execution" in msg2
        assert "$77,650.00" in msg2


def test_alert_manager_cycle_result_dispatch() -> None:
    mock_telegram = MagicMock(spec=TelegramNotifier)
    manager = AlertManager(telegram=mock_telegram)

    mock_result = MagicMock()
    mock_result.signal_generated = True
    mock_result.order_approved = False
    mock_result.executions = []

    mock_intent = MagicMock()
    mock_intent.side = "buy"
    mock_intent.entry_price = Decimal("77650.00")
    mock_intent.stop_loss_price = Decimal("77600.00")
    mock_intent.target_price = Decimal("77750.00")
    mock_intent.rationale = "Bullish breakout"
    mock_result.intent = mock_intent

    mock_obs = MagicMock()
    mock_obs.broker_symbol = "#BTCUSD"

    res = manager.process_cycle_result(mock_result, mock_obs)
    assert len(res["dispatched_events"]) == 1
    assert res["dispatched_events"][0]["type"] == "SIGNAL"
    assert res["dispatched_events"][0]["sound"] == "signal_buy"
    assert mock_telegram.send_signal_alert.called
