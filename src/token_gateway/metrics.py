import math
import threading
from collections import deque
from typing import Literal

from pydantic import BaseModel

from token_gateway.cost import estimate_cost, reduction_percentage
from token_gateway.tokenizer import count_tokens

CacheResult = Literal["miss", "exact", "semantic"]


class OptimizationMetrics(BaseModel):
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    reduction_percent: float
    estimated_cost_before: float
    estimated_cost_after: float
    estimated_cost_saved: float
    cache_hit: bool
    cache: CacheResult = "miss"
    semantic_similarity: float | None = None
    semantic_match: str | None = None
    gateway_overhead_ms: float = 0.0
    llm_latency_ms: float = 0.0


def build_metrics(
    original_prompt: str,
    optimized_prompt: str,
    cache: CacheResult,
    price_per_1k_tokens: float = 0.002,
    semantic_similarity: float | None = None,
    semantic_match: str | None = None,
    gateway_overhead_ms: float = 0.0,
    llm_latency_ms: float = 0.0,
) -> OptimizationMetrics:
    """Token and cost figures for one request.

    On a cache hit no tokens are sent to the model at all, so everything counts as saved.
    """
    before = count_tokens(original_prompt)
    after = 0 if cache != "miss" else count_tokens(optimized_prompt)
    before_cost = estimate_cost(before, price_per_1k_tokens)
    after_cost = estimate_cost(after, price_per_1k_tokens)
    return OptimizationMetrics(
        tokens_before=before,
        tokens_after=after,
        tokens_saved=max(before - after, 0),
        reduction_percent=reduction_percentage(before, after),
        estimated_cost_before=before_cost,
        estimated_cost_after=after_cost,
        estimated_cost_saved=round(max(before_cost - after_cost, 0), 6),
        cache_hit=cache != "miss",
        cache=cache,
        semantic_similarity=semantic_similarity,
        semantic_match=semantic_match,
        gateway_overhead_ms=round(gateway_overhead_ms, 3),
        llm_latency_ms=round(llm_latency_ms, 3),
    )


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile; 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(math.ceil(pct / 100 * len(ordered)), 1)
    return ordered[rank - 1]


class MetricsRecorder:
    """Thread-safe running totals plus a bounded window of recent latencies."""

    def __init__(self, latency_window: int = 10_000) -> None:
        self._lock = threading.Lock()
        self._overhead_ms: deque[float] = deque(maxlen=latency_window)
        self._llm_ms: deque[float] = deque(maxlen=latency_window)
        self.requests = 0
        self.exact_hits = 0
        self.semantic_hits = 0
        self.backend_errors = 0
        self.tokens_before = 0
        self.tokens_after = 0
        self.cost_saved = 0.0

    def record(self, metrics: OptimizationMetrics) -> None:
        with self._lock:
            self.requests += 1
            self.exact_hits += metrics.cache == "exact"
            self.semantic_hits += metrics.cache == "semantic"
            self.tokens_before += metrics.tokens_before
            self.tokens_after += metrics.tokens_after
            self.cost_saved += metrics.estimated_cost_saved
            self._overhead_ms.append(metrics.gateway_overhead_ms)
            if metrics.cache == "miss":
                self._llm_ms.append(metrics.llm_latency_ms)

    def record_error(self) -> None:
        with self._lock:
            self.backend_errors += 1

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            overhead = list(self._overhead_ms)
            llm = list(self._llm_ms)
            hits = self.exact_hits + self.semantic_hits
            return {
                "requests": self.requests,
                "cache_hits": hits,
                "exact_cache_hits": self.exact_hits,
                "semantic_cache_hits": self.semantic_hits,
                "cache_hit_rate": round(hits / self.requests, 3) if self.requests else 0.0,
                "backend_errors": self.backend_errors,
                "tokens_before": self.tokens_before,
                "tokens_sent": self.tokens_after,
                "tokens_saved": self.tokens_before - self.tokens_after,
                "token_reduction_percent": reduction_percentage(
                    self.tokens_before, self.tokens_after
                ),
                "estimated_cost_saved": round(self.cost_saved, 6),
                "gateway_overhead_ms_p50": percentile(overhead, 50),
                "gateway_overhead_ms_p95": percentile(overhead, 95),
                "llm_latency_ms_p50": percentile(llm, 50),
                "llm_latency_ms_p95": percentile(llm, 95),
            }

    def prometheus(self) -> str:
        snapshot = self.snapshot()
        lines = []
        for name, value in snapshot.items():
            metric = f"token_gateway_{name}"
            lines.append(f"# TYPE {metric} gauge")
            lines.append(f"{metric} {value}")
        return "\n".join(lines) + "\n"
