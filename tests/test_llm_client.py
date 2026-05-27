from __future__ import annotations

from data_contract_review_agent.llm_client import create_openai_client, call_openai_summary


class _FakeResponse:
    output_text = "# LLM-Polished Summary\n\nhello"


class _FakeResponses:
    def create(self, *, model: str, input: str):
        assert model
        assert input
        return _FakeResponse()


class _FakeClient:
    responses = _FakeResponses()


def test_create_openai_client_returns_none_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    availability = create_openai_client()
    assert availability.client is None
    assert "OPENAI_API_KEY" in str(availability.reason)


def test_call_openai_summary_uses_client() -> None:
    text = call_openai_summary(client=_FakeClient(), prompt="x", model="gpt-test")
    assert "LLM-Polished Summary" in text
