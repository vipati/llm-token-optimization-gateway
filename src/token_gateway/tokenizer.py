import re

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))
