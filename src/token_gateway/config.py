import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.environ.get(f"TOKEN_GATEWAY_{name}", default)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration, read from TOKEN_GATEWAY_* environment variables."""

    backend: str = "mock"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "tiny-local-model"
    request_timeout_seconds: float = 30.0
    max_context_tokens: int = 120
    cache_max_entries: int = 10_000
    cache_ttl_seconds: float = 3600.0
    semantic_cache_enabled: bool = True
    semantic_threshold: float = 0.8
    price_per_1k_tokens: float = 0.002

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            backend=_env("BACKEND", cls.backend),
            base_url=_env("BASE_URL", cls.base_url),
            api_key=_env("API_KEY", cls.api_key),
            model=_env("MODEL", cls.model),
            request_timeout_seconds=float(
                _env("REQUEST_TIMEOUT_SECONDS", str(cls.request_timeout_seconds))
            ),
            max_context_tokens=int(_env("MAX_CONTEXT_TOKENS", str(cls.max_context_tokens))),
            cache_max_entries=int(_env("CACHE_MAX_ENTRIES", str(cls.cache_max_entries))),
            cache_ttl_seconds=float(_env("CACHE_TTL_SECONDS", str(cls.cache_ttl_seconds))),
            semantic_cache_enabled=_env("SEMANTIC_CACHE", "true").lower() in {"1", "true", "yes"},
            semantic_threshold=float(_env("SEMANTIC_THRESHOLD", str(cls.semantic_threshold))),
            price_per_1k_tokens=float(_env("PRICE_PER_1K_TOKENS", str(cls.price_per_1k_tokens))),
        )
