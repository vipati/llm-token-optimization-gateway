def estimate_cost(tokens: int, price_per_1k_tokens: float = 0.002) -> float:
    return round((tokens / 1000) * price_per_1k_tokens, 6)


def reduction_percentage(before: int, after: int) -> float:
    if before <= 0:
        return 0.0
    return round(((before - after) / before) * 100, 2)

