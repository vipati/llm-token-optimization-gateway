import time

from fastapi import FastAPI
from pydantic import BaseModel

from llmapi.model import LocalLLM, LocalLLMRequest, LocalLLMResponse

app = FastAPI(title="Local LLM API", version="0.2.0")
model = LocalLLM()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "tiny-local-model"
    messages: list[ChatMessage]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/complete", response_model=LocalLLMResponse)
def complete(request: LocalLLMRequest) -> LocalLLMResponse:
    return model.complete(request)


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> dict:
    """Minimal OpenAI-compatible endpoint so the gateway can reach this service over HTTP."""
    prompt = "\n".join(message.content for message in request.messages)
    result = model.complete(LocalLLMRequest(prompt=prompt, model=request.model))
    return {
        "id": f"chatcmpl-local-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "model": result.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.prompt_tokens + result.completion_tokens,
        },
    }
