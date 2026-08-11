from pydantic import BaseModel

from token_gateway.cost import estimate_cost, reduction_percentage
from token_gateway.tokenizer import count_tokens


class OptimizationMetrics(BaseModel):
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    reduction_percent: float
    estimated_cost_before: float
    estimated_cost_after: float
    estimated_cost_saved: float
    cache_hit: bool


def build_metrics(
    original_prompt: str,
    optimized_prompt: str,
    cache_hit: bool,
) -> OptimizationMetrics:
    before = count_tokens(original_prompt)
    after = count_tokens(optimized_prompt)
    before_cost = estimate_cost(before)
    after_cost = estimate_cost(after)
    return OptimizationMetrics(
        tokens_before=before,
        tokens_after=after,
        tokens_saved=max(before - after, 0),
        reduction_percent=reduction_percentage(before, after),
        estimated_cost_before=before_cost,
        estimated_cost_after=after_cost,
        estimated_cost_saved=round(max(before_cost - after_cost, 0), 6),
        cache_hit=cache_hit,
    )
