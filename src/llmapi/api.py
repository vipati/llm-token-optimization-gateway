from fastapi import FastAPI

from llmapi.model import LocalLLM, LocalLLMRequest, LocalLLMResponse

app = FastAPI(title="Local LLM API", version="0.1.0")
model = LocalLLM()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/complete", response_model=LocalLLMResponse)
def complete(request: LocalLLMRequest) -> LocalLLMResponse:
    return model.complete(request)

