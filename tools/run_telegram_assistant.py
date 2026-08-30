#!/usr/bin/env python3
"""Runner daemon for QuantForge Telegram Two-Way Interactive AI Assistant & Brain.

Listens for incoming messages from @bamquantforgebot, provides live MT5 context,
executes trades, manages breakeven stops, and maintains long-term SQLite memory.
"""

import sys
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from quantforge.infrastructure.notifications.telegram_assistant import (  # noqa: E402
    TelegramAIAssistant,
)


def main() -> None:
    print("🤖 QuantForge Telegram Two-Way Interactive AI Quant Brain Starting...")
    print("📱 Authorized Bot: @bamquantforgebot")
    print("🧠 Memory Database: data/telegram_ai_brain.sqlite3")
    print("⚡ Real-Time Connection: http://127.0.0.1:8080/api/state")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    assistant = TelegramAIAssistant()
    assistant.run_loop()


if __name__ == "__main__":
    main()
