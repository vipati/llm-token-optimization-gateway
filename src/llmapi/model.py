from pydantic import BaseModel


class LocalLLMRequest(BaseModel):
    prompt: str
    model: str = "tiny-local-model"


class LocalLLMResponse(BaseModel):
    model: str
    text: str
    prompt_tokens: int


class LocalLLM:
    """Deterministic local model used to test the gateway without external services."""

    def complete(self, request: LocalLLMRequest) -> LocalLLMResponse:
        prompt_lower = request.prompt.lower()
        if "reset" in prompt_lower and "password" in prompt_lower:
            answer = (
                "Users can reset their password from the login page with Forgot Password. "
                "The reset link expires after 30 minutes."
            )
        elif "invoice" in prompt_lower or "billing" in prompt_lower:
            answer = "Invoices are generated monthly, and refunds require an invoice number."
        else:
            answer = "I can answer using the provided optimized context."

        return LocalLLMResponse(
            model=request.model,
            text=answer,
            prompt_tokens=len(request.prompt.split()),
        )

