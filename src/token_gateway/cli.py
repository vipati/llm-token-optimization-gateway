from pathlib import Path

import typer

from token_gateway.gateway import GatewayRequest, TokenOptimizationGateway
from token_gateway.tokenizer import count_tokens

app = typer.Typer(help="Optimize prompts before sending them to a local LLM service.")


@app.command()
def count(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    typer.echo(f"Tokens: {count_tokens(text)}")


@app.command()
def complete(
    question: str,
    context_file: Path,
    cache_file: Path = Path("cache/exact-cache.json"),
) -> None:
    context = context_file.read_text(encoding="utf-8")
    gateway = TokenOptimizationGateway.with_file_cache(cache_file)
    response = gateway.complete(GatewayRequest(question=question, context=context))
    typer.echo(response.answer)
    typer.echo("")
    typer.echo(f"Tokens before: {response.metrics.tokens_before}")
    typer.echo(f"Tokens after: {response.metrics.tokens_after}")
    typer.echo(f"Tokens saved: {response.metrics.tokens_saved}")
    typer.echo(f"Reduction: {response.metrics.reduction_percent}%")
    typer.echo(f"Cache hit: {response.metrics.cache_hit}")

