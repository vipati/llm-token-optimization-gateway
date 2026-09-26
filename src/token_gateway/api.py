from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from token_gateway import __version__
from token_gateway.backends import BackendError
from token_gateway.config import Settings
from token_gateway.gateway import GatewayRequest, GatewayResponse, TokenOptimizationGateway
from token_gateway.metrics import build_metrics
from token_gateway.tokenizer import count_tokens, tokenizer_name


class OptimizeRequest(BaseModel):
    question: str
    context: str


class OptimizeResponse(BaseModel):
    optimized_prompt: str
    tokens_before: int
    tokens_after: int
    reduction_percent: float


def create_app(gateway: TokenOptimizationGateway | None = None) -> FastAPI:
    gateway = gateway or TokenOptimizationGateway.from_settings(Settings.from_env())
    app = FastAPI(title="LLM Token Optimization Gateway", version=__version__)
    app.state.gateway = gateway

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "backend": gateway.backend.name,
            "model": gateway.settings.model,
            "tokenizer": tokenizer_name(),
        }

    @app.post("/optimize", response_model=OptimizeResponse)
    def optimize(request: OptimizeRequest) -> OptimizeResponse:
        """Dry run: show the optimized prompt and savings without calling the model."""
        prompts = gateway.optimize(request.question, request.context)
        metrics = build_metrics(prompts.original_prompt, prompts.optimized_prompt, cache="miss")
        return OptimizeResponse(
            optimized_prompt=prompts.optimized_prompt,
            tokens_before=metrics.tokens_before,
            tokens_after=metrics.tokens_after,
            reduction_percent=metrics.reduction_percent,
        )

    @app.post("/complete", response_model=GatewayResponse)
    def complete(request: GatewayRequest) -> GatewayResponse:
        try:
            return gateway.complete(request)
        except BackendError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @app.get("/metrics")
    def metrics() -> dict[str, int | float]:
        return gateway.recorder.snapshot()

    @app.get("/metrics/prometheus", response_class=PlainTextResponse)
    def prometheus() -> str:
        return gateway.recorder.prometheus()

    @app.get("/tokens")
    def tokens(text: str) -> dict[str, int | str]:
        return {"tokens": count_tokens(text), "tokenizer": tokenizer_name()}

    return app


app = create_app()
