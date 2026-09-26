import os
import re
from collections.abc import Callable
from functools import cache

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


def _regex_count(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))


@cache
def _counter() -> tuple[str, Callable[[str], int]]:
    """Pick the token counter once per process.

    The regex counter is the deterministic default. Setting TOKEN_GATEWAY_TOKENIZER=tiktoken
    (with the `tiktoken` extra installed) switches to the cl100k_base BPE encoding, which matches
    what OpenAI-style models bill for. Any failure to load it falls back to the regex counter.
    """
    if os.environ.get("TOKEN_GATEWAY_TOKENIZER", "regex").lower() == "tiktoken":
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return "tiktoken/cl100k_base", lambda text: len(encoding.encode(text))
        except Exception:  # noqa: BLE001 - optional dependency, fall back quietly
            pass
    return "regex", _regex_count


def count_tokens(text: str) -> int:
    return _counter()[1](text)


def tokenizer_name() -> str:
    return _counter()[0]
