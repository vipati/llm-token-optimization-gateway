from fastapi.testclient import TestClient

from token_gateway.api import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_complete_endpoint_returns_metrics() -> None:
    response = TestClient(app).post(
        "/complete",
        json={
            "question": "How do I reset my password?",
            "context": (
                "Users can reset a password from the login page by clicking Forgot Password."
            ),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert body["metrics"]["tokens_before"] >= body["metrics"]["tokens_after"]
