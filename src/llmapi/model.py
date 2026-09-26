import re

from pydantic import BaseModel

from token_gateway.text import split_sentences, term_vector
from token_gateway.tokenizer import count_tokens

QUESTION_PATTERN = re.compile(r"question:\s*(.+)", re.IGNORECASE)
FALLBACK_ANSWER = "I could not find an answer in the provided context."


class LocalLLMRequest(BaseModel):
    prompt: str
    model: str = "tiny-local-model"


class LocalLLMResponse(BaseModel):
    model: str
    text: str
    prompt_tokens: int
    completion_tokens: int


class LocalLLM:
    """Deterministic extractive stand-in for a real model.

    It answers with the context sentence that best matches the question, which is enough to
    exercise the gateway end to end (and to notice when compression drops the answer) without
    API keys, GPUs, or network access.
    """

    def complete(self, request: LocalLLMRequest) -> LocalLLMResponse:
        question, context = _split_prompt(request.prompt)
        question_vector = term_vector(question)
        best_sentence, best_score = FALLBACK_ANSWER, 0
        for sentence in split_sentences(context):
            vector = term_vector(sentence)
            score = sum(min(count, question_vector[term]) for term, count in vector.items())
            if score > best_score:
                best_sentence, best_score = sentence, score

        return LocalLLMResponse(
            model=request.model,
            text=best_sentence,
            prompt_tokens=count_tokens(request.prompt),
            completion_tokens=count_tokens(best_sentence),
        )


def _split_prompt(prompt: str) -> tuple[str, str]:
    match = QUESTION_PATTERN.search(prompt)
    if not match:
        return prompt, prompt
    question = match.group(1).strip()
    context = prompt[: match.start()] + prompt[match.end() :]
    return question, context
