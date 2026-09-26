import hashlib
import re


def normalize_request(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def fingerprint(*parts: str) -> str:
    """Stable hash of normalized parts, used as a cache key."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(normalize_request(part).encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()
