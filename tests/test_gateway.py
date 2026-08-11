from token_gateway.gateway import GatewayRequest, TokenOptimizationGateway


def test_gateway_reduces_tokens_and_calls_local_llm() -> None:
    gateway = TokenOptimizationGateway()
    response = gateway.complete(
        GatewayRequest(
            question="How do I reset my password?",
            context=(
                "Company boilerplate. Company boilerplate.\n"
                "Users can reset a password from the login page by clicking Forgot Password. "
                "The reset link expires after 30 minutes. "
                "The dashboard color palette changed last quarter."
            ),
        )
    )

    assert "reset their password" in response.answer
    assert response.metrics.tokens_after < response.metrics.tokens_before
    assert response.metrics.cache_hit is False


def test_gateway_hits_cache_on_repeated_optimized_prompt() -> None:
    gateway = TokenOptimizationGateway()
    request = GatewayRequest(
        question="How do I reset my password?",
        context="Users can reset a password from the login page by clicking Forgot Password.",
    )

    first = gateway.complete(request)
    second = gateway.complete(request)

    assert first.metrics.cache_hit is False
    assert second.metrics.cache_hit is True
    assert second.answer == first.answer

