from fastapi import FastAPI
from pydantic import BaseModel

from token_gateway.gateway import GatewayRequest, GatewayResponse, TokenOptimizationGateway
from token_gateway.metrics import OptimizationMetrics
from token_gateway.tokenizer import count_tokens

app = FastAPI(title="LLM Token Optimization Gateway", version="0.1.0")
gateway = TokenOptimizationGateway()
last_metrics: list[OptimizationMetrics] = []


class OptimizeRequest(BaseModel):
    question: str
    context: str


class OptimizeResponse(BaseModel):
    optimized_prompt: str
    metrics: OptimizationMetrics


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    gateway_response = gateway.complete(
        GatewayRequest(question=request.question, context=request.context)
    )
    return OptimizeResponse(
        optimized_prompt=gateway_response.optimized_prompt,
        metrics=gateway_response.metrics,
    )


@app.post("/complete", response_model=GatewayResponse)
def complete(request: GatewayRequest) -> GatewayResponse:
    response = gateway.complete(request)
    last_metrics.append(response.metrics)
    return response


@app.get("/metrics")
def metrics() -> dict[str, int | float]:
    total = len(last_metrics)
    cache_hits = sum(1 for metric in last_metrics if metric.cache_hit)
    tokens_saved = sum(metric.tokens_saved for metric in last_metrics)
    return {
        "requests": total,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / total, 3) if total else 0.0,
        "tokens_saved": tokens_saved,
    }


@app.get("/tokens")
def tokens(text: str) -> dict[str, int]:
    return {"tokens": count_tokens(text)}

