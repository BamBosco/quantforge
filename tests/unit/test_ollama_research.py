from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from quantforge.infrastructure.ollama_research import (
    _TRADE_INTENT_SCHEMA,
    OllamaResearchBackend,
)


class _Handler(BaseHTTPRequestHandler):
    request_body: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802
        size = int(self.headers["Content-Length"])
        type(self).request_body = json.loads(self.rfile.read(size))
        body = json.dumps({"response": "local result"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_local_ollama_backend_sends_non_streaming_research_request() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        backend = OllamaResearchBackend(
            base_url=f"http://127.0.0.1:{port}", model="qwen3:latest"
        )
        response = backend.complete("technical", {"snapshot": {"symbol": "USDJPY"}})
        assert response == "local result"
        assert _Handler.request_body["model"] == "qwen3:latest"
        assert _Handler.request_body["stream"] is False
        assert _Handler.request_body["think"] is False
        assert _Handler.request_body["options"] == {"temperature": 0, "num_predict": 32}
    finally:
        server.shutdown()
        server.server_close()


def test_openai_compatible_v1_base_url_uses_native_ollama_endpoint() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        backend = OllamaResearchBackend(
            base_url=f"http://127.0.0.1:{port}/v1", model="qwen3:latest"
        )
        assert backend.complete("technical", {}) == "local result"
    finally:
        server.shutdown()
        server.server_close()


def test_final_research_role_has_room_for_a_complete_structured_intent() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        backend = OllamaResearchBackend(
            base_url=f"http://127.0.0.1:{port}", model="qwen3:latest"
        )
        snapshot_timestamp = "2026-08-24T16:35:00+00:00"
        assert (
            backend.complete(
                "risk_portfolio", {"snapshot": {"observed_at_utc": snapshot_timestamp}}
            )
            == "local result"
        )
        assert _Handler.request_body["options"] == {
            "temperature": 0,
            "num_predict": 224,
        }
        schema = _Handler.request_body["format"]
        assert isinstance(schema, dict)
        properties = schema["properties"]
        assert isinstance(properties, dict)
        timestamp = properties["timestamp"]
        assert timestamp == {"type": "string", "const": snapshot_timestamp}
        assert _TRADE_INTENT_SCHEMA["properties"]["timestamp"] == {"type": "string"}
    finally:
        server.shutdown()
        server.server_close()


def test_final_prompt_requires_a_concise_factual_reason() -> None:
    prompt = OllamaResearchBackend._prompt("risk_portfolio", {})

    assert "reason must be a factual phrase of 12 words or fewer" in prompt
    assert "No Markdown or explanatory prose" in prompt
    assert "BUY requires stop_loss < entry_price < take_profit" in prompt
    assert "SELL requires take_profit < entry_price < stop_loss" in prompt


def test_final_schema_describes_directional_protective_levels() -> None:
    direction = _TRADE_INTENT_SCHEMA["properties"]["direction"]
    description = direction["description"]

    assert "BUY requires stop_loss < entry_price < take_profit" in description
    assert "SELL requires take_profit < entry_price < stop_loss" in description
