from token_gateway.tokenizer import count_tokens


def select_relevant_context(question: str, context: str, max_tokens: int = 120) -> str:
    question_terms = {
        term.lower().strip(".,!?;:")
        for term in question.split()
        if len(term.strip(".,!?;:")) > 2
    }
    sentences = _split_sentences(context)
    scored = sorted(
        ((sentence, _score_sentence(sentence, question_terms)) for sentence in sentences),
        key=lambda item: item[1],
        reverse=True,
    )

    selected: list[str] = []
    for sentence, score in scored:
        if score <= 0 and selected:
            continue
        candidate = " ".join([*selected, sentence]).strip()
        if count_tokens(candidate) > max_tokens:
            continue
        selected.append(sentence)

    return " ".join(selected).strip()


def _split_sentences(text: str) -> list[str]:
    parts = text.replace("\n", " ").split(".")
    return [f"{part.strip()}." for part in parts if part.strip()]


def _score_sentence(sentence: str, question_terms: set[str]) -> int:
    terms = {term.lower().strip(".,!?;:") for term in sentence.split()}
    return len(terms & question_terms)

