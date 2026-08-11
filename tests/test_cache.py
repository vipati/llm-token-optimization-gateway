from token_gateway.cache import ExactPromptCache


def test_exact_cache_uses_normalized_prompt() -> None:
    cache = ExactPromptCache()
    cache.set("  Reset   Password ", "Use Forgot Password.")

    assert cache.get("reset password").response == "Use Forgot Password."

