from pathlib import Path

import typer

from token_gateway.benchmark import run_benchmark
from token_gateway.config import Settings
from token_gateway.gateway import GatewayRequest, TokenOptimizationGateway
from token_gateway.tokenizer import count_tokens

app = typer.Typer(help="Optimize prompts before sending them to an LLM.")


@app.command()
def count(path: Path) -> None:
    """Count the tokens in a file."""
    text = path.read_text(encoding="utf-8")
    typer.echo(f"Tokens: {count_tokens(text)}")


@app.command()
def complete(
    question: str,
    context_file: Path,
    cache_file: Path = Path("cache/exact-cache.json"),
    show_prompt: bool = False,
) -> None:
    """Answer a question about a context file through the gateway."""
    context = context_file.read_text(encoding="utf-8")
    gateway = TokenOptimizationGateway.with_file_cache(cache_file, Settings.from_env())
    response = gateway.complete(GatewayRequest(question=question, context=context))
    if show_prompt:
        typer.echo("Optimized prompt:\n" + response.optimized_prompt + "\n")
    metrics = response.metrics
    typer.echo(f"Answer: {response.answer}")
    typer.echo("")
    typer.echo(f"Tokens before: {metrics.tokens_before}")
    typer.echo(f"Tokens after: {metrics.tokens_after}")
    typer.echo(f"Tokens saved: {metrics.tokens_saved}")
    typer.echo(f"Reduction: {metrics.reduction_percent}%")
    typer.echo(f"Cache hit: {metrics.cache_hit} ({metrics.cache})")


@app.command()
def benchmark(
    dataset: Path = Path("data/benchmark/support_kb.json"),
    repeats: int = 3,
    seed: int = 7,
    output: Path | None = None,
) -> None:
    """Replay a support workload and print measured token, cache, and latency results."""
    result = run_benchmark(dataset, repeats=repeats, seed=seed, settings=Settings.from_env())
    report = result.to_markdown()
    typer.echo(report)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report + "\n", encoding="utf-8")
        typer.echo(f"\nWrote {output}")
