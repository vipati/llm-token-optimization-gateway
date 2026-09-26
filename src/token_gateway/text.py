import math
import re
from collections import Counter

WORD_PATTERN = re.compile(r"[a-z0-9]+")
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")

# Question words and negations are deliberately kept: "when" vs "where" or "can" vs "cannot"
# change the answer, so the semantic cache must see them.
STOP_WORDS = frozenset(
    """
    a about after all also an and any are as at be been but by could did do does for from
    had has have i if in into is it its just me my of on or our so than that the their them
    then there these they this to up was we were will with would you your
    """.split()
)


def terms(text: str) -> list[str]:
    """Lowercased content words with stop words removed."""
    return [word for word in WORD_PATTERN.findall(text.lower()) if word not in STOP_WORDS]


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_BOUNDARY.split(text) if part.strip()]


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right[term] for term, count in left.items())
    norm = math.sqrt(sum(v * v for v in left.values())) * math.sqrt(
        sum(v * v for v in right.values())
    )
    return dot / norm if norm else 0.0


def term_vector(text: str) -> Counter[str]:
    return Counter(_stem(term) for term in terms(text))


def _stem(word: str) -> str:
    # Light suffix stripping so "passwords"/"password" and "resetting"/"reset" match.
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word
