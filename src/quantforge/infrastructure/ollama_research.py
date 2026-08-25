"""Local Ollama client for non-executable research agents.

The client has no MT5, order, position, or execution dependencies.  It only
turns a role and validated market context into local-model text.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TRADE_INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "symbol",
        "timestamp",
        "direction",
        "entry_type",
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_percent",
        "confidence",
        "reason",
        "expiry",
    ],
    "properties": {
        "symbol": {"type": "string", "enum": ["USDJPY"]},
        "timestamp": {"type": "string"},
        "direction": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD"],
            "description": (
                "BUY requires stop_loss < entry_price < take_profit; "
                "SELL requires take_profit < entry_price < stop_loss."
            ),
        },
        "entry_type": {"type": "string"},
        "entry_price": {"type": "number", "description": "Reference entry price."},
        "stop_loss": {
            "type": "number",
            "description": "BUY: below entry_price. SELL: above entry_price.",
        },
        "take_profit": {
            "type": "number",
            "description": "BUY: above entry_price. SELL: below entry_price.",
        },
        "risk_percent": {"type": "number"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "expiry": {"type": "string"},
    },
}


class OllamaResearchError(RuntimeError):
    """Raised when the local Ollama research endpoint cannot provide text."""


class OllamaResearchBackend:
    """Small, deterministic local API adapter for the research-role protocol."""

    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        if not base_url.startswith("http://127.0.0.1:") and not base_url.startswith(
            "http://localhost:"
        ):
            raise ValueError("Ollama research backend must be a local HTTP endpoint")
        if not model:
            raise ValueError("Ollama model must not be empty")
        normalized_url = base_url.rstrip("/")
        # The profile may use Ollama's OpenAI-compatible ``/v1`` URL.  This
        # adapter uses only Ollama's native, local ``/api/generate`` endpoint.
        self._base_url = (
            normalized_url.removesuffix("/v1")
            if normalized_url.endswith("/v1")
            else normalized_url
        )
        self._model = model
        self._timeout_seconds = timeout_seconds

    def complete(self, role: str, context: dict[str, Any]) -> str:
        prompt = self._prompt(role, context)
        final_role = role == "risk_portfolio"
        request_payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 224 if final_role else 32,
            },
        }
        if final_role:
            request_payload["format"] = self._final_intent_schema(context)
        body = json.dumps(request_payload).encode("utf-8")
        request = Request(
            f"{self._base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            message = f"local Ollama request failed: {error}"
            raise OllamaResearchError(message) from error
        text = payload.get("response")
        if not isinstance(text, str):
            raise OllamaResearchError("local Ollama response did not contain text")
        return text

    @staticmethod
    def _final_intent_schema(context: dict[str, Any]) -> dict[str, Any]:
        """Bind the model's structured timestamp to this snapshot exactly."""
        snapshot = context.get("snapshot")
        if not isinstance(snapshot, dict):
            raise ValueError("risk_portfolio context must include a snapshot")
        timestamp = snapshot.get("observed_at_utc")
        if not isinstance(timestamp, str) or not timestamp:
            raise ValueError("risk_portfolio snapshot must include observed_at_utc")

        schema = deepcopy(_TRADE_INTENT_SCHEMA)
        schema["properties"]["timestamp"]["const"] = timestamp
        return schema

    @staticmethod
    def _prompt(role: str, context: dict[str, Any]) -> str:
        payload = json.dumps(context, sort_keys=True, separators=(",", ":"))
        if role == "risk_portfolio":
            return (
                "You are the non-executable risk-and-portfolio research role. "
                "Return only one JSON object matching the supplied schema. No Markdown "
                "or explanatory prose. Use snapshot observed_at_utc exactly as "
                "timestamp. Choose BUY, SELL, or HOLD. For BUY or SELL, use valid "
                "protective levels and risk_percent no greater than 0.005. Expiry must "
                "be later than timestamp. reason must be a factual phrase of 12 words "
                "or fewer. BUY requires stop_loss < entry_price < take_profit. SELL "
                "requires take_profit < entry_price < stop_loss. This is research "
                "only: never issue an order or execution "
                "instruction. Context: "
                + payload
            )
        return (
            f"You are the {role} role in a non-executable USDJPY M1 research workflow. "
            "Analyze only the supplied market facts. Do not propose or place orders. "
            "Return at most 80 words of research notes. Context: " + payload
        )
