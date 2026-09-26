from fastapi.testclient import TestClient

from token_gateway.api import create_app
from token_gateway.backends import BackendError, BackendResponse
from token_gateway.gateway import TokenOptimizationGateway

REQUEST = {
    "question": "How do I reset my password?",
    "context": (
        "Users can reset a password from the login page by clicking Forgot Password. "
        "Invoices are generated monthly. The dashboard color palette changed."
    ),
}


def client() -> TestClient:
    return TestClient(create_app(TokenOptimizationGateway()))


def test_health_reports_backend() -> None:
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["backend"] == "mock"


def test_complete_endpoint_returns_metrics() -> None:
    response = client().post("/complete", json=REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert "Forgot Password" in body["answer"]
    assert body["metrics"]["tokens_before"] > body["metrics"]["tokens_after"]


def test_optimize_is_a_dry_run() -> None:
    api = client()
    response = api.post("/optimize", json=REQUEST)

    assert response.status_code == 200
    assert "palette" not in response.json()["optimized_prompt"]
    assert api.get("/metrics").json()["requests"] == 0


def test_metrics_aggregate_cache_hits() -> None:
    api = client()
    api.post("/complete", json=REQUEST)
    api.post("/complete", json=REQUEST)

    metrics = api.get("/metrics").json()
    assert metrics["requests"] == 2
    assert metrics["exact_cache_hits"] == 1
    assert metrics["cache_hit_rate"] == 0.5
    assert metrics["tokens_saved"] > 0
    assert "token_gateway_requests 2" in api.get("/metrics/prometheus").text


def test_backend_failure_returns_502() -> None:
    class FailingBackend:
        name = "failing"

        def complete(self, prompt: str, model: str) -> BackendResponse:
            raise BackendError("backend unavailable")

    api = TestClient(create_app(TokenOptimizationGateway(backend=FailingBackend())))
    response = api.post("/complete", json=REQUEST)

    assert response.status_code == 502
    assert "backend unavailable" in response.json()["detail"]


def test_empty_question_is_rejected() -> None:
    response = client().post("/complete", json={"question": "", "context": "x"})

    assert response.status_code == 422
