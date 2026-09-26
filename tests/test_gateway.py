from pathlib import Path

import pytest

from token_gateway.backends import BackendError, BackendResponse
from token_gateway.config import Settings
from token_gateway.gateway import GatewayRequest, TokenOptimizationGateway

CONTEXT = (
    "Company boilerplate. Company boilerplate.\n"
    "Users can reset a password from the login page by clicking Forgot Password. "
    "The reset link expires after 30 minutes. "
    "The dashboard color palette changed last quarter."
)


class CountingBackend:
    name = "counting"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, model: str) -> BackendResponse:
        self.calls.append((prompt, model))
        return BackendResponse(text=f"answer from {model}")


class FailingBackend:
    name = "failing"

    def complete(self, prompt: str, model: str) -> BackendResponse:
        raise BackendError("boom")


def test_gateway_reduces_tokens_and_answers() -> None:
    gateway = TokenOptimizationGateway()
    response = gateway.complete(
        GatewayRequest(question="How do I reset my password?", context=CONTEXT)
    )

    assert "Forgot Password" in response.answer
    assert "palette" not in response.optimized_prompt
    assert response.metrics.tokens_after < response.metrics.tokens_before
    assert response.metrics.cache == "miss"


def test_gateway_hits_exact_cache_on_repeated_request() -> None:
    backend = CountingBackend()
    gateway = TokenOptimizationGateway(backend=backend)
    request = GatewayRequest(question="How do I reset my password?", context=CONTEXT)

    first = gateway.complete(request)
    second = gateway.complete(request)

    assert first.metrics.cache == "miss"
    assert second.metrics.cache == "exact"
    assert second.metrics.tokens_after == 0
    assert second.answer == first.answer
    assert len(backend.calls) == 1


def test_gateway_serves_paraphrase_from_semantic_cache() -> None:
    backend = CountingBackend()
    gateway = TokenOptimizationGateway(backend=backend)

    gateway.complete(GatewayRequest(question="How do I reset my password?", context=CONTEXT))
    response = gateway.complete(
        GatewayRequest(question="How can I reset my password?", context=CONTEXT)
    )

    assert response.metrics.cache == "semantic"
    assert response.metrics.semantic_match == "How do I reset my password?"
    assert len(backend.calls) == 1


def test_semantic_cache_can_be_disabled() -> None:
    backend = CountingBackend()
    gateway = TokenOptimizationGateway(
        backend=backend, settings=Settings(semantic_cache_enabled=False)
    )

    gateway.complete(GatewayRequest(question="How do I reset my password?", context=CONTEXT))
    gateway.complete(GatewayRequest(question="How can I reset my password?", context=CONTEXT))

    assert len(backend.calls) == 2


def test_cache_is_not_shared_between_models() -> None:
    backend = CountingBackend()
    gateway = TokenOptimizationGateway(backend=backend)

    first = gateway.complete(GatewayRequest(question="reset?", context=CONTEXT, model="a"))
    second = gateway.complete(GatewayRequest(question="reset?", context=CONTEXT, model="b"))

    assert first.answer == "answer from a"
    assert second.answer == "answer from b"


def test_backend_errors_are_counted_and_raised() -> None:
    gateway = TokenOptimizationGateway(backend=FailingBackend())

    with pytest.raises(BackendError):
        gateway.complete(GatewayRequest(question="reset?", context=CONTEXT))

    assert gateway.recorder.snapshot()["backend_errors"] == 1


def test_file_cache_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    request = GatewayRequest(question="How do I reset my password?", context=CONTEXT)

    TokenOptimizationGateway.with_file_cache(path).complete(request)
    response = TokenOptimizationGateway.with_file_cache(path).complete(request)

    assert response.metrics.cache == "exact"


def test_short_prompts_are_not_made_longer() -> None:
    gateway = TokenOptimizationGateway()
    prompts = gateway.optimize("Hi?", "Hello.")

    assert prompts.optimized_prompt == prompts.original_prompt
