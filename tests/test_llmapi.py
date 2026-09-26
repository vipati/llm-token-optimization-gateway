from fastapi.testclient import TestClient

from llmapi.api import app
from llmapi.model import FALLBACK_ANSWER, LocalLLM, LocalLLMRequest

PROMPT = (
    "Context:\nUsers reset a password with Forgot Password. Invoices are monthly.\n\n"
    "Question: How can I reset my password?"
)


def test_local_llm_extracts_best_matching_sentence() -> None:
    response = LocalLLM().complete(LocalLLMRequest(prompt=PROMPT))

    assert response.text == "Users reset a password with Forgot Password."
    assert response.prompt_tokens > 0


def test_local_llm_falls_back_when_nothing_matches() -> None:
    response = LocalLLM().complete(LocalLLMRequest(prompt="Context:\nHello.\n\nQuestion: xyz?"))

    assert response.text == FALLBACK_ANSWER


def test_llmapi_complete_endpoint() -> None:
    response = TestClient(app).post("/complete", json={"prompt": PROMPT})

    assert response.status_code == 200
    assert response.json()["model"] == "tiny-local-model"


def test_llmapi_openai_compatible_endpoint() -> None:
    response = TestClient(app).post(
        "/v1/chat/completions",
        json={"model": "tiny-local-model", "messages": [{"role": "user", "content": PROMPT}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Forgot Password" in body["choices"][0]["message"]["content"]
    assert body["usage"]["prompt_tokens"] > 0
