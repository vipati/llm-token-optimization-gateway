from pathlib import Path

from token_gateway.benchmark import run_benchmark
from token_gateway.metrics import percentile

DATASET = Path(__file__).resolve().parents[1] / "data" / "benchmark" / "support_kb.json"


def test_benchmark_reports_savings_without_losing_answers() -> None:
    result = run_benchmark(DATASET, repeats=2)

    assert result.end_to_end_reduction_percent > result.compression_reduction_percent > 0
    assert result.context_recall == 1.0
    assert result.gateway_accuracy >= result.baseline_accuracy
    assert result.semantic_false_matches == 0
    assert "| Metric | Result |" in result.to_markdown()


def test_percentile_nearest_rank() -> None:
    assert percentile([], 95) == 0.0
    assert percentile([1, 2, 3, 4], 50) == 2
    assert percentile([1, 2, 3, 4], 95) == 4
