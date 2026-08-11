from fastapi.testclient import TestClient

from llmapi.api import app
from llmapi.model import LocalLLM, LocalLLMRequest


def test_local_llm_model_answers_password_question() -> None:
    response = LocalLLM().complete(LocalLLMRequest(prompt="How can I reset my password?"))

    assert "Forgot Password" in response.text


def test_llmapi_complete_endpoint() -> None:
    response = TestClient(app).post(
        "/complete",
        json={"prompt": "How can I reset my password?"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "tiny-local-model"

