from token_gateway.tokenizer import count_tokens


def test_count_tokens_handles_words_and_punctuation() -> None:
    assert count_tokens("Reset password, please!") == 5
