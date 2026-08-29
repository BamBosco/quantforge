"""Telegram Notification and Alert Dispatcher for QuantForge.

Sends real-time trading signals, risk gate decisions, and paper fills
to a configured Telegram bot/channel.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final

logger = logging.getLogger("quantforge.notifications.telegram")

TELEGRAM_API_BASE: Final = "https://api.telegram.org"
DEFAULT_CONFIG_PATH: Final = Path("config/telegram_config.json")


def _get_ssl_context() -> ssl.SSLContext:
    """Create an SSL context, configuring certifi or unverified fallback on macOS."""
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()


@dataclass
class TelegramConfig:
    """Configuration for Telegram Bot alerts."""

    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True

    @classmethod
    def from_env(cls) -> TelegramConfig:
        """Load Telegram config from environment variables or persistent config file."""
        token = os.environ.get(
            "QUANTFORGE_TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", "")
        )
        chat = os.environ.get(
            "QUANTFORGE_TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")
        )

        if (not token or not chat) and DEFAULT_CONFIG_PATH.exists():
            try:
                with open(DEFAULT_CONFIG_PATH) as f:
                    data = json.load(f)
                    token = token or data.get("bot_token", "")
                    chat = chat or data.get("chat_id", "")
            except Exception:
                pass

        return cls(bot_token=token, chat_id=chat, enabled=bool(token and chat))


class TelegramNotifier:
    """Thread-safe, non-blocking Telegram notification dispatcher."""

    def __init__(self, config: TelegramConfig | None = None) -> None:
        self.config = config or TelegramConfig.from_env()

    @property
    def is_configured(self) -> bool:
        """Check if bot token and chat ID are valid and set."""
        return bool(self.config.bot_token and self.config.chat_id)

    def send_message(
        self, text: str, *, parse_mode: str = "HTML", async_send: bool = True
    ) -> bool:
        """Send a raw text or HTML formatted message to Telegram."""
        if not self.is_configured:
            logger.debug(
                "Telegram notification skipped: Bot token or Chat ID not configured."
            )
            return False

        if async_send:
            thread = threading.Thread(
                target=self._post_message_sync,
                args=(text, parse_mode),
                daemon=True,
            )
            thread.start()
            return True
        return self._post_message_sync(text, parse_mode)

    def send_signal_alert(
        self,
        *,
        instrument: str,
        side: str,
        entry_price: Decimal | float,
        stop_loss: Decimal | float,
        target_price: Decimal | float,
        strategy_name: str = "Candidate 007",
        rationale: str = "",
    ) -> bool:
        """Send a formatted Trade Signal notification."""
        side_upper = str(side).upper()
        icon = (
            "🟢 🚀 <b>BUY SIGNAL</b>"
            if side_upper == "BUY"
            else "🔴 🔻 <b>SELL SIGNAL</b>"
        )

        msg = (
            f"🎯 <b>QuantForge Alert — {strategy_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Action     : {icon}\n"
            f"Asset      : <code>{instrument}</code>\n"
            f"Entry      : <b>${float(entry_price):,.2f}</b>\n"
            f"Stop Loss  : <b>${float(stop_loss):,.2f}</b>\n"
            f"2R Target  : <b>${float(target_price):,.2f}</b>\n"
        )
        if rationale:
            msg += f"Rationale  : <i>{rationale}</i>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Automated Real-Time Strategy Signal</i>"
        return self.send_message(msg)

    def send_risk_approval(
        self,
        *,
        instrument: str,
        side: str,
        lots: Decimal | float,
        risk_dollars: Decimal | float,
        risk_pct: Decimal | float = Decimal("1.0"),
    ) -> bool:
        """Send a Risk Gate Approval notification."""
        msg = (
            f"🛡️ <b>Risk Gate — Approved Trade</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Asset      : <code>{instrument}</code>\n"
            f"Order Side : <b>{str(side).upper()}</b>\n"
            f"Position   : <b>{float(lots):.2f} lots</b>\n"
            f"Max Risk   : <b>${float(risk_dollars):,.2f}</b> ({float(risk_pct):.1f}% equity)\n"
            f"Status     : ✅ <i>Passed Drawdown & Risk Policy</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(msg)

    def send_fill_execution(
        self,
        *,
        instrument: str,
        side: str,
        lots: Decimal | float,
        price: Decimal | float,
        fee: Decimal | float = Decimal("0"),
    ) -> bool:
        """Send a Paper Trade Fill notification."""
        msg = (
            f"⚡ <b>Paper Execution — Order Filled</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Asset      : <code>{instrument}</code>\n"
            f"Filled Side: <b>{str(side).upper()}</b>\n"
            f"Volume     : <b>{float(lots):.2f} lots</b>\n"
            f"Fill Price : <b>${float(price):,.2f}</b>\n"
            f"Comm/Fee   : <b>${float(fee):.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Paper Portfolio Updated</i>"
        )
        return self.send_message(msg)

    def send_test_message(self) -> tuple[bool, str]:
        """Send a synchronous test message to verify Telegram credentials."""
        if not self.config.bot_token:
            return False, "Telegram Bot Token is missing."
        if not self.config.chat_id:
            return False, "Telegram Chat ID is missing."

        msg = (
            "🎉 <b>QuantForge Telegram Alerts Connected!</b>\n\n"
            "Your trading engine is successfully linked to this chat.\n\n"
            "You will receive instant alerts for:\n"
            "• 🎯 Candidate 007 Signals (#BTCUSD & XAUUSD)\n"
            "• 🛡️ Risk Management Gate Approvals\n"
            "• ⚡ Paper Order Fills & Performance"
        )
        url = f"{TELEGRAM_API_BASE}/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        for use_unverified in (False, True):
            try:
                ctx = (
                    ssl._create_unverified_context()
                    if use_unverified
                    else ssl.create_default_context()
                )
                with urllib.request.urlopen(req, context=ctx, timeout=8) as response:
                    if response.status == 200:
                        return True, "Test message delivered successfully to Telegram!"
            except urllib.error.HTTPError as err:
                body = err.read().decode("utf-8")
                if "chat not found" in body.lower():
                    return False, (
                        "Chat not found! Please open your bot in Telegram (@bamquantforgebot) "
                        "and tap 'START' first so the bot is allowed to message you."
                    )
                return False, f"Telegram API error {err.code}: {body}"
            except Exception as err:
                if not use_unverified:
                    continue
                return False, f"Connection error: {err}"

        return False, "Unable to send Telegram message."

    def _post_message_sync(self, text: str, parse_mode: str = "HTML") -> bool:
        url = f"{TELEGRAM_API_BASE}/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for use_unverified in (False, True):
            try:
                ctx = (
                    ssl._create_unverified_context()
                    if use_unverified
                    else ssl.create_default_context()
                )
                with urllib.request.urlopen(req, context=ctx, timeout=8) as response:
                    return bool(response.status == 200)
            except Exception as err:
                if not use_unverified:
                    continue
                logger.warning(f"Telegram API request failed: {err}")
                return False
        return False
