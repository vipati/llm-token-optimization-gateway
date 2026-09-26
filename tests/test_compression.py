from token_gateway.compression import compress_prompt, remove_duplicate_lines
from token_gateway.selection import select_relevant_context


def test_remove_duplicate_lines() -> None:
    text = "Always be concise.\nAlways be concise.\nReset passwords from login."

    assert remove_duplicate_lines(text).splitlines() == [
        "Always be concise.",
        "Reset passwords from login.",
    ]


def test_compress_prompt_keeps_relevant_context() -> None:
    prompt = compress_prompt(
        "How do I reset my password?",
        "Billing happens monthly. Users reset passwords from the login page.",
    )

    assert "reset passwords" in prompt
    assert "Billing" not in prompt
    assert "Question:" in prompt


def test_selection_keeps_original_sentence_order() -> None:
    context = "Refunds need an invoice. The weather is nice. Invoices are sent monthly."

    selected = select_relevant_context("invoice refunds invoices", context)

    assert selected.splitlines() == ["Refunds need an invoice.", "Invoices are sent monthly."]


def test_selection_respects_token_budget() -> None:
    context = " ".join(f"Password fact number {i}." for i in range(50))

    selected = select_relevant_context("password fact", context, max_tokens=20)

    assert 0 < len(selected.split()) <= 20


def test_selection_skips_headings_and_never_returns_empty() -> None:
    context = "Billing policy:\nInvoices are sent monthly."

    assert select_relevant_context("billing", context) == "Invoices are sent monthly."
    assert select_relevant_context("unrelated", context) == "Invoices are sent monthly."
