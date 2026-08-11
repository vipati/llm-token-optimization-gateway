from token_gateway.selection import select_relevant_context


def compress_prompt(question: str, context: str, max_context_tokens: int = 120) -> str:
    deduped_context = remove_duplicate_lines(context)
    relevant_context = select_relevant_context(
        question=question,
        context=deduped_context,
        max_tokens=max_context_tokens,
    )
    return (
        "Answer the question using only the relevant context.\n\n"
        f"Question: {question.strip()}\n\n"
        f"Relevant context:\n{relevant_context}"
    ).strip()


def remove_duplicate_lines(text: str) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for line in text.splitlines():
        normalized = line.strip().lower()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line.strip())
    return "\n".join(lines)

