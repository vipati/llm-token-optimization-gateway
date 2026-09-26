import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from token_gateway.backends import (
    BackendError,
    MockBackend,
    OpenAICompatibleBackend,
    backend_from_settings,
)
from token_gateway.config import Settings


class _Handler(BaseHTTPRequestHandler):
    received: list[dict] = []
    reply: dict = {}

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers["Content-Length"])
        _Handler.received.append(
            {
                "path": self.path,
                "auth": self.headers.get("Authorization"),
                "body": json.loads(self.rfile.read(length)),
            }
        )
        payload = json.dumps(_Handler.reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def fake_openai_server() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Handler.received = []
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_openai_backend_sends_chat_request(fake_openai_server: str) -> None:
    _Handler.reply = {
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 1},
    }
    backend = OpenAICompatibleBackend(fake_openai_server, api_key="test-key")

    result = backend.complete("prompt text", "some-model")

    assert result.text == "hello"
    assert result.prompt_tokens == 12
    request = _Handler.received[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["auth"] == "Bearer test-key"
    assert request["body"]["model"] == "some-model"
    assert request["body"]["messages"][0]["content"] == "prompt text"


def test_openai_backend_rejects_malformed_response(fake_openai_server: str) -> None:
    _Handler.reply = {"unexpected": True}

    with pytest.raises(BackendError):
        OpenAICompatibleBackend(fake_openai_server).complete("prompt", "model")


def test_openai_backend_wraps_connection_errors() -> None:
    backend = OpenAICompatibleBackend("http://127.0.0.1:9/v1", timeout_seconds=1)

    with pytest.raises(BackendError):
        backend.complete("prompt", "model")


def test_backend_from_settings() -> None:
    assert isinstance(backend_from_settings(Settings()), MockBackend)
    assert isinstance(backend_from_settings(Settings(backend="openai")), OpenAICompatibleBackend)
    with pytest.raises(ValueError):
        backend_from_settings(Settings(backend="nope"))
