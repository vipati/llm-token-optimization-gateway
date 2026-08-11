from token_gateway.compression import compress_prompt, remove_duplicate_lines


def test_remove_duplicate_lines() -> None:
    text = "Always be concise.\nAlways be concise.\nReset passwords from login."

    assert remove_duplicate_lines(text).splitlines() == [
        "Always be concise.",
        "Reset passwords from login.",
    ]


def test_compress_prompt_keeps_relevant_context() -> None:
    prompt = compress_prompt(
        "How do I reset my password?",
        "Billing happens monthly. Users reset passwords from the login page.",
    )

    assert "reset passwords" in prompt
    assert "Question:" in prompt

