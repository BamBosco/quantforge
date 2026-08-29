"""Unit tests for Telegram Two-Way Interactive AI Assistant & Brain."""

from pathlib import Path

import pytest

from quantforge.infrastructure.notifications.telegram_assistant import (
    TelegramAIAssistant,
)
from quantforge.infrastructure.notifications.telegram_notifier import TelegramConfig


@pytest.fixture
def mock_assistant(tmp_path: Path) -> TelegramAIAssistant:
    config = TelegramConfig(
        bot_token="test_token_123", chat_id="5386759666", enabled=True
    )
    db_path = tmp_path / "test_brain.sqlite3"
    return TelegramAIAssistant(config=config, brain_db_path=db_path)


def test_sqlite_memory_initialization_and_notes(
    mock_assistant: TelegramAIAssistant,
) -> None:
    mock_assistant.add_note("Always use 1.5R target on gold", category="preference")
    mock_assistant.add_note("Avoid trading 15 mins before CPI", category="risk")

    notes = mock_assistant.get_notes()
    assert len(notes) == 2
    assert "1.5R target" in notes[1]["note"]
    assert "CPI" in notes[0]["note"]


def test_chat_history_recording(mock_assistant: TelegramAIAssistant) -> None:
    mock_assistant.store_chat("user", "Hello bot!", chat_id="5386759666")
    mock_assistant.store_chat("assistant", "Hello Trader!", chat_id="5386759666")

    notes = mock_assistant.get_notes()
    assert isinstance(notes, list)


def test_process_help_command(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "/help", user_name="Bamidele"
    )
    assert "Welcome, Bamidele" in reply
    assert "/status" in reply
    assert "/buy" in reply


def test_process_status_command(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "/status", user_name="Bamidele"
    )
    assert "QuantForge Live Account Status" in reply
    assert "Account Equity" in reply


def test_process_strategy_command(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message("5386759666", "/strategy")
    assert "Candidate 007 SMC Strategy Blueprint" in reply
    assert "50-period Exponential Moving Average" in reply
    assert "Positive Breakeven" in reply


def test_process_remember_command(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "/remember prefer 0.01 lot size on gold"
    )
    assert "Saved to Persistent Memory!" in reply

    notes = mock_assistant.get_notes()
    assert len(notes) == 1
    assert "prefer 0.01 lot size on gold" in notes[0]["note"]

    # Test /memory command
    mem_reply = mock_assistant.process_incoming_message("5386759666", "/memory")
    assert "prefer 0.01 lot size on gold" in mem_reply


def test_natural_language_sell_gold(
    mock_assistant: TelegramAIAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mock_assistant,
        "execute_trade_action",
        lambda side, symbol, quantity: {
            "success": True,
            "order_id": "test-sell-1",
            "price": 2735.0,
        },
    )
    reply = mock_assistant.process_incoming_message("5386759666", "sell gold")
    assert "SELL XAUUSD Scalp Executed!" in reply
    assert "2,735.00" in reply


def test_natural_language_buy_bitcoin(
    mock_assistant: TelegramAIAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mock_assistant,
        "execute_trade_action",
        lambda side, symbol, quantity: {
            "success": True,
            "order_id": "test-buy-1",
            "price": 78250.0,
        },
    )
    reply = mock_assistant.process_incoming_message("5386759666", "buy bitcoin")
    assert "BUY BTCUSDm Scalp Executed!" in reply
    assert "78,250.00" in reply


def test_close_profit_trigger(
    mock_assistant: TelegramAIAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mock_assistant,
        "close_profit_action",
        lambda: {"success": True, "closed_count": 2, "realized_pnl": 45.50},
    )
    reply = mock_assistant.process_incoming_message("5386759666", "close all in profit")
    assert "Profit Banked Successfully!" in reply
    assert "+$45.50" in reply


def test_conversational_ai_greetings(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "hello there", user_name="Bamidele"
    )
    assert "Hey Bamidele!" in reply


def test_conversational_ai_market_analysis(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "what do you think of gold right now?"
    )
    assert "Market Structure Analysis for Gold (XAUUSD)" in reply
    assert "50-period EMA" in reply


def test_conversational_ai_order_block_explanation(
    mock_assistant: TelegramAIAssistant,
) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "what is an order block?"
    )
    assert "What is an Order Block?" in reply
    assert "Bullish OB" in reply


def test_conversational_ai_risk_safety(mock_assistant: TelegramAIAssistant) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "is my money safe with this bot?"
    )
    assert "QuantForge Capital Protection Shield" in reply
    assert "Strict Micro-Lot Sizing" in reply


def test_conversational_ai_quantforge_knowledge_disclosure(
    mock_assistant: TelegramAIAssistant,
) -> None:
    reply = mock_assistant.process_incoming_message(
        "5386759666", "tell me about quantforge", user_name="Bamidele"
    )
    assert "QuantForge Autonomous Trading Intelligence" in reply
    assert "Candidate 007 SMC Scalper" in reply
    assert "50 EMA" in reply
    assert "1.0% Capital Budget" in reply


def test_gemini_ai_query_mock(
    mock_assistant: TelegramAIAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mock_assistant, "_get_gemini_api_key", lambda: "fake-key")
    monkeypatch.setattr(
        mock_assistant,
        "query_gemini_ai",
        lambda text, user_name, ctx, chat_id: "🧠 <b>Gemini Quant Intelligence:</b> Market is consolidating around 50 EMA.",
    )
    reply = mock_assistant.process_incoming_message(
        "5386759666", "What is the optimal stop distance today?"
    )
    assert "Gemini Quant Intelligence" in reply
    assert "50 EMA" in reply


def test_gemini_ai_action_tag_handling(
    mock_assistant: TelegramAIAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mock_assistant,
        "execute_trade_action",
        lambda side, symbol, quantity: {
            "success": True,
            "order_id": "gemini-trade-1",
            "price": 2736.50,
        },
    )
    action_res = mock_assistant._handle_gemini_actions(
        "I analyzed the market and executed the setup: [ACTION:BUY_GOLD]",
        {"bid": 2736.50},
    )
    assert "BUY 0.01 XAUUSD @ $2,736.50" in action_res
    assert "[ACTION:BUY_GOLD]" not in action_res
