import json
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel

from llmapi.model import LocalLLM, LocalLLMRequest
from token_gateway.config import Settings


class BackendResponse(BaseModel):
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class BackendError(RuntimeError):
    """The model backend failed or returned something the gateway cannot use."""


class LLMBackend(Protocol):
    name: str

    def complete(self, prompt: str, model: str) -> BackendResponse: ...


class MockBackend:
    """In-process deterministic model; the default, so the project runs with no setup."""

    name = "mock"

    def __init__(self, llm: LocalLLM | None = None) -> None:
        self.llm = llm or LocalLLM()

    def complete(self, prompt: str, model: str) -> BackendResponse:
        result = self.llm.complete(LocalLLMRequest(prompt=prompt, model=model))
        return BackendResponse(
            text=result.text,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )


class OpenAICompatibleBackend:
    """Calls any `/chat/completions` API: OpenAI, Ollama, vLLM, LM Studio, or the bundled llmapi."""

    name = "openai"

    def __init__(self, base_url: str, api_key: str = "", timeout_seconds: float = 30.0) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str, model: str) -> BackendResponse:
        body = json.dumps(
            {"model": model, "messages": [{"role": "user", "content": prompt}]}
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise BackendError(f"LLM backend request to {self.url} failed: {error}") from error

        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise BackendError(f"Unexpected LLM backend response: {payload!r:.200}") from error
        usage = payload.get("usage") or {}
        return BackendResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


def backend_from_settings(settings: Settings) -> LLMBackend:
    if settings.backend == "mock":
        return MockBackend()
    if settings.backend == "openai":
        return OpenAICompatibleBackend(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout_seconds=settings.request_timeout_seconds,
        )
    raise ValueError(f"Unknown TOKEN_GATEWAY_BACKEND {settings.backend!r}; use 'mock' or 'openai'")
