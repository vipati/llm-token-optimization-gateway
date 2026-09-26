"""Replay a synthetic support workload through the gateway and report measured results."""

import json
import random
from dataclasses import dataclass
from pathlib import Path

from llmapi.model import LocalLLM, LocalLLMRequest
from token_gateway.compression import build_original_prompt
from token_gateway.config import Settings
from token_gateway.gateway import GatewayRequest, TokenOptimizationGateway
from token_gateway.metrics import percentile
from token_gateway.tokenizer import tokenizer_name


@dataclass
class WorkloadItem:
    context: str
    question: str
    gold: str


@dataclass
class BenchmarkResult:
    requests: int
    unique_questions: int
    baseline_tokens: int
    gateway_tokens: int
    compression_reduction_percent: float
    end_to_end_reduction_percent: float
    context_recall: float
    baseline_accuracy: float
    gateway_accuracy: float
    exact_hit_rate: float
    semantic_hit_rate: float
    semantic_false_matches: int
    overhead_ms_p50: float
    overhead_ms_p95: float
    tokenizer: str

    def to_markdown(self) -> str:
        rows = [
            ("Requests replayed", f"{self.requests} ({self.unique_questions} unique questions)"),
            ("Prompt tokens without gateway", f"{self.baseline_tokens:,}"),
            ("Prompt tokens sent to model", f"{self.gateway_tokens:,}"),
            ("**End-to-end token reduction**", f"**{self.end_to_end_reduction_percent:.1f}%**"),
            ("Reduction from compression alone", f"{self.compression_reduction_percent:.1f}%"),
            ("Context recall (answer fact kept)", f"{self.context_recall:.0%}"),
            (
                "Answer accuracy: direct vs gateway",
                f"{self.baseline_accuracy:.0%} vs {self.gateway_accuracy:.0%}",
            ),
            ("Exact cache hit rate", f"{self.exact_hit_rate:.0%}"),
            ("Semantic cache hit rate", f"{self.semantic_hit_rate:.0%}"),
            (
                "Semantic hits matched to a different question",
                str(self.semantic_false_matches),
            ),
            (
                "Gateway overhead p50 / p95",
                f"{self.overhead_ms_p50:.2f} ms / {self.overhead_ms_p95:.2f} ms",
            ),
        ]
        lines = ["| Metric | Result |", "| --- | --- |"]
        lines += [f"| {name} | {value} |" for name, value in rows]
        lines.append("")
        lines.append(f"Tokenizer: `{self.tokenizer}`. Model backend: deterministic mock.")
        return "\n".join(lines)


def load_workload(path: Path, repeats: int, seed: int) -> tuple[list[WorkloadItem], int]:
    """Every question is asked verbatim once, then its paraphrases and repeats arrive shuffled.

    This mirrors real traffic, where a popular question is seen first and then asked again,
    sometimes in other words.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    first_asks: list[WorkloadItem] = []
    follow_ups: list[WorkloadItem] = []
    for context in data["contexts"]:
        for entry in context["questions"]:
            first_asks.append(WorkloadItem(context["text"], entry["question"], entry["gold"]))
            later = [*entry["paraphrases"], *[entry["question"]] * max(repeats - 1, 0)]
            follow_ups += [WorkloadItem(context["text"], text, entry["gold"]) for text in later]
    random.Random(seed).shuffle(follow_ups)
    return first_asks + follow_ups, len(first_asks)


def run_benchmark(
    dataset: Path,
    repeats: int = 3,
    seed: int = 7,
    settings: Settings | None = None,
) -> BenchmarkResult:
    settings = settings or Settings()
    workload, unique = load_workload(dataset, repeats, seed)

    gateway = TokenOptimizationGateway(settings=settings)
    direct_model = LocalLLM()

    baseline_tokens = gateway_tokens = 0
    miss_before = miss_after = 0
    exact = semantic = semantic_false = 0
    gold_by_question = {(item.context, item.question): item.gold for item in workload}
    baseline_correct = gateway_correct = 0
    overhead: list[float] = []
    recall_hits: dict[tuple[str, str], bool] = {}

    for item in workload:
        original = build_original_prompt(item.question, item.context)
        direct = direct_model.complete(LocalLLMRequest(prompt=original))
        baseline_correct += _contains(direct.text, item.gold)

        response = gateway.complete(GatewayRequest(question=item.question, context=item.context))
        metrics = response.metrics
        baseline_tokens += metrics.tokens_before
        gateway_tokens += metrics.tokens_after
        overhead.append(metrics.gateway_overhead_ms)
        correct = _contains(response.answer, item.gold)
        gateway_correct += correct

        if metrics.cache == "miss":
            miss_before += metrics.tokens_before
            miss_after += metrics.tokens_after
            recall_hits.setdefault(
                (item.context, item.gold), _contains(response.optimized_prompt, item.gold)
            )
        elif metrics.cache == "exact":
            exact += 1
        else:
            semantic += 1
            matched_gold = gold_by_question.get((item.context, metrics.semantic_match or ""))
            semantic_false += matched_gold != item.gold

    total = len(workload)
    return BenchmarkResult(
        requests=total,
        unique_questions=unique,
        baseline_tokens=baseline_tokens,
        gateway_tokens=gateway_tokens,
        compression_reduction_percent=_pct_reduction(miss_before, miss_after),
        end_to_end_reduction_percent=_pct_reduction(baseline_tokens, gateway_tokens),
        context_recall=sum(recall_hits.values()) / len(recall_hits) if recall_hits else 0.0,
        baseline_accuracy=baseline_correct / total,
        gateway_accuracy=gateway_correct / total,
        exact_hit_rate=exact / total,
        semantic_hit_rate=semantic / total,
        semantic_false_matches=semantic_false,
        overhead_ms_p50=percentile(overhead, 50),
        overhead_ms_p95=percentile(overhead, 95),
        tokenizer=tokenizer_name(),
    )


def _contains(text: str, gold: str) -> bool:
    return gold.lower() in text.lower()


def _pct_reduction(before: int, after: int) -> float:
    return (before - after) / before * 100 if before else 0.0
