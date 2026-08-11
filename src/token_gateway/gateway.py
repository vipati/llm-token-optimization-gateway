from pathlib import Path

from pydantic import BaseModel

from llmapi.model import LocalLLM, LocalLLMRequest
from token_gateway.cache import ExactPromptCache
from token_gateway.compression import compress_prompt
from token_gateway.metrics import OptimizationMetrics, build_metrics
from token_gateway.tokenizer import count_tokens


class GatewayRequest(BaseModel):
    question: str
    context: str
    model: str = "tiny-local-model"


class GatewayResponse(BaseModel):
    answer: str
    optimized_prompt: str
    metrics: OptimizationMetrics


class TokenOptimizationGateway:
    def __init__(
        self,
        cache: ExactPromptCache | None = None,
        llm: LocalLLM | None = None,
    ) -> None:
        self.cache = cache or ExactPromptCache()
        self.llm = llm or LocalLLM()

    @classmethod
    def with_file_cache(cls, path: Path) -> "TokenOptimizationGateway":
        return cls(cache=ExactPromptCache(path=path))

    def complete(self, request: GatewayRequest) -> GatewayResponse:
        original_prompt = f"Question: {request.question}\n\nContext:\n{request.context}"
        compressed_prompt = compress_prompt(request.question, request.context)
        optimized_prompt = (
            compressed_prompt
            if count_tokens(compressed_prompt) < count_tokens(original_prompt)
            else original_prompt
        )
        cached = self.cache.get(optimized_prompt)
        if cached:
            return GatewayResponse(
                answer=cached.response,
                optimized_prompt=optimized_prompt,
                metrics=build_metrics(original_prompt, optimized_prompt, cache_hit=True),
            )

        llm_response = self.llm.complete(
            LocalLLMRequest(prompt=optimized_prompt, model=request.model)
        )
        self.cache.set(optimized_prompt, llm_response.text)
        return GatewayResponse(
            answer=llm_response.text,
            optimized_prompt=optimized_prompt,
            metrics=build_metrics(original_prompt, optimized_prompt, cache_hit=False),
        )
