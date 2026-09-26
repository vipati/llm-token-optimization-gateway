| Metric | Result |
| --- | --- |
| Requests replayed | 65 (16 unique questions) |
| Prompt tokens without gateway | 16,020 |
| Prompt tokens sent to model | 1,335 |
| **End-to-end token reduction** | **91.7%** |
| Reduction from compression alone | 71.8% |
| Context recall (answer fact kept) | 100% |
| Answer accuracy: direct vs gateway | 62% vs 68% |
| Exact cache hit rate | 49% |
| Semantic cache hit rate | 22% |
| Semantic hits matched to a different question | 0 |
| Gateway overhead p50 / p95 | 0.48 ms / 0.66 ms |

Tokenizer: `tiktoken/cl100k_base`. Model backend: deterministic mock.
