from token_gateway.text import split_sentences, term_vector
from token_gateway.tokenizer import count_tokens


def select_relevant_context(question: str, context: str, max_tokens: int = 120) -> str:
    """Keep the context sentences that share the most terms with the question.

    Sentences are ranked by term overlap, added greedily until the token budget is spent, and
    then emitted one per line in their original order so the model still reads coherent text.
    If nothing
    overlaps, the first sentence that fits is kept so the prompt is never empty.
    """
    question_vector = term_vector(question)
    # Section headings ("Billing policy:") share terms with questions but carry no facts.
    sentences = [s for s in split_sentences(context) if not s.endswith(":")]
    scores = [
        sum(min(count, question_vector[term]) for term, count in term_vector(sentence).items())
        for sentence in sentences
    ]
    ranked = sorted(range(len(sentences)), key=lambda index: scores[index], reverse=True)

    chosen: set[int] = set()
    used_tokens = 0
    for index in ranked:
        if scores[index] <= 0 and chosen:
            break
        sentence_tokens = count_tokens(sentences[index])
        if used_tokens + sentence_tokens > max_tokens:
            continue
        chosen.add(index)
        used_tokens += sentence_tokens

    return "\n".join(sentences[index] for index in sorted(chosen))
