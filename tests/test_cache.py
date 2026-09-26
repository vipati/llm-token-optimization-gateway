from pathlib import Path

from token_gateway.cache import ExactPromptCache, SemanticCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_exact_cache_uses_normalized_prompt() -> None:
    cache = ExactPromptCache()
    cache.set("  Reset   Password ", "Use Forgot Password.")

    assert cache.get("reset password").response == "Use Forgot Password."


def test_exact_cache_separates_namespaces() -> None:
    cache = ExactPromptCache()
    cache.set("reset password", "from model a", namespace="model-a")

    assert cache.get("reset password", namespace="model-b") is None


def test_exact_cache_evicts_least_recently_used() -> None:
    cache = ExactPromptCache(max_entries=2)
    cache.set("one", "1")
    cache.set("two", "2")
    cache.get("one")
    cache.set("three", "3")

    assert cache.get("two") is None
    assert cache.get("one") is not None
    assert len(cache) == 2


def test_exact_cache_expires_entries() -> None:
    clock = FakeClock()
    cache = ExactPromptCache(ttl_seconds=60, clock=clock)
    cache.set("reset password", "answer")
    clock.now += 61

    assert cache.get("reset password") is None


def test_exact_cache_persists_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    ExactPromptCache(path=path).set("reset password", "answer")

    assert ExactPromptCache(path=path).get("reset password").response == "answer"


def test_semantic_cache_matches_paraphrase_in_same_scope() -> None:
    cache = SemanticCache(threshold=0.8)
    cache.store("How do I reset my password?", "Use Forgot Password.", scope="docs")

    match = cache.lookup("how can i reset my passwords", scope="docs")

    assert match is not None
    assert match.response == "Use Forgot Password."


def test_semantic_cache_is_scoped_to_context() -> None:
    cache = SemanticCache(threshold=0.8)
    cache.store("How do I reset my password?", "answer", scope="docs-a")

    assert cache.lookup("How do I reset my password?", scope="docs-b") is None


def test_semantic_cache_keeps_question_words_and_negations_distinct() -> None:
    cache = SemanticCache(threshold=0.8)
    cache.store("When are invoices generated?", "On the first of the month.", scope="docs")
    cache.store("Can enterprise customers pay by bank transfer?", "Yes.", scope="docs")

    assert cache.lookup("Where are invoices generated?", scope="docs") is None
    assert cache.lookup("Can enterprise customers pay by credit card?", scope="docs") is None


def test_semantic_cache_is_bounded_and_expires() -> None:
    clock = FakeClock()
    cache = SemanticCache(max_entries=2, ttl_seconds=60, clock=clock)
    cache.store("first question here", "1", scope="a")
    cache.store("second question here", "2", scope="b")
    cache.store("third question here", "3", scope="c")

    assert len(cache) == 2
    assert cache.lookup("first question here", scope="a") is None

    clock.now += 61
    assert cache.lookup("third question here", scope="c") is None
