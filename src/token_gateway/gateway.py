import time
from pathlib import Path

from pydantic import BaseModel, Field

from token_gateway.backends import LLMBackend, MockBackend, backend_from_settings
from token_gateway.cache import ExactPromptCache, SemanticCache
from token_gateway.compression import build_original_prompt, compress_prompt
from token_gateway.config import Settings
from token_gateway.metrics import MetricsRecorder, OptimizationMetrics, build_metrics
from token_gateway.normalization import fingerprint
from token_gateway.tokenizer import count_tokens


class GatewayRequest(BaseModel):
    question: str = Field(min_length=1)
    context: str
    model: str | None = None


class GatewayResponse(BaseModel):
    answer: str
    optimized_prompt: str
    metrics: OptimizationMetrics


class OptimizedPrompt(BaseModel):
    original_prompt: str
    optimized_prompt: str


class TokenOptimizationGateway:
    """Request pipeline: optimize prompt -> exact cache -> semantic cache -> model backend.

    Cache lookups happen after optimization so equivalent requests (whitespace, casing,
    duplicated boilerplate, irrelevant context) collapse onto the same key.
    """

    def __init__(
        self,
        cache: ExactPromptCache | None = None,
        semantic_cache: SemanticCache | None = None,
        backend: LLMBackend | None = None,
        settings: Settings | None = None,
        recorder: MetricsRecorder | None = None,
    ) -> None:
        self.settings = settings or Settings()
        # Compare with None: an empty cache has len() == 0 and would be falsy.
        if cache is None:
            cache = ExactPromptCache(
                max_entries=self.settings.cache_max_entries,
                ttl_seconds=self.settings.cache_ttl_seconds,
            )
        self.cache = cache
        self.semantic_cache = semantic_cache
        if semantic_cache is None and self.settings.semantic_cache_enabled:
            self.semantic_cache = SemanticCache(
                threshold=self.settings.semantic_threshold,
                max_entries=self.settings.cache_max_entries,
                ttl_seconds=self.settings.cache_ttl_seconds,
            )
        self.backend = backend or MockBackend()
        self.recorder = recorder or MetricsRecorder()

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenOptimizationGateway":
        return cls(settings=settings, backend=backend_from_settings(settings))

    @classmethod
    def with_file_cache(
        cls, path: Path, settings: Settings | None = None
    ) -> "TokenOptimizationGateway":
        settings = settings or Settings()
        return cls(
            cache=ExactPromptCache(path=path, max_entries=settings.cache_max_entries),
            settings=settings,
            backend=backend_from_settings(settings),
        )

    def optimize(self, question: str, context: str) -> OptimizedPrompt:
        original = build_original_prompt(question, context)
        compressed = compress_prompt(question, context, self.settings.max_context_tokens)
        # Compression adds an instruction line; never make a short prompt longer.
        optimized = compressed if count_tokens(compressed) < count_tokens(original) else original
        return OptimizedPrompt(original_prompt=original, optimized_prompt=optimized)

    def complete(self, request: GatewayRequest) -> GatewayResponse:
        started = time.perf_counter()
        model = request.model or self.settings.model
        prompts = self.optimize(request.question, request.context)
        semantic_scope = fingerprint(model, request.context)

        answer: str | None = None
        cache_result = "miss"
        similarity: float | None = None
        matched_question: str | None = None

        cached = self.cache.get(prompts.optimized_prompt, namespace=model)
        if cached:
            answer, cache_result = cached.response, "exact"
        elif self.semantic_cache is not None:
            match = self.semantic_cache.lookup(request.question, semantic_scope)
            if match:
                answer, cache_result = match.response, "semantic"
                similarity, matched_question = match.similarity, match.question

        llm_ms = 0.0
        if answer is None:
            llm_started = time.perf_counter()
            try:
                result = self.backend.complete(prompts.optimized_prompt, model)
            except Exception:
                self.recorder.record_error()
                raise
            llm_ms = (time.perf_counter() - llm_started) * 1000
            answer = result.text
            self.cache.set(prompts.optimized_prompt, answer, namespace=model)
            if self.semantic_cache is not None:
                self.semantic_cache.store(request.question, answer, semantic_scope)

        total_ms = (time.perf_counter() - started) * 1000
        metrics = build_metrics(
            prompts.original_prompt,
            prompts.optimized_prompt,
            cache=cache_result,
            price_per_1k_tokens=self.settings.price_per_1k_tokens,
            semantic_similarity=similarity,
            semantic_match=matched_question,
            gateway_overhead_ms=total_ms - llm_ms,
            llm_latency_ms=llm_ms,
        )
        self.recorder.record(metrics)
        return GatewayResponse(
            answer=answer, optimized_prompt=prompts.optimized_prompt, metrics=metrics
        )
