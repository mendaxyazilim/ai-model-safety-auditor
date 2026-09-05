"""
Adapter tests use requests_mock to fake HTTP responses from each provider's
real endpoint shape -- this verifies the request/response parsing logic is
correct WITHOUT needing network access or a real API key (neither is
available in the build/test sandbox for this project). This is standard
unit-testing practice and is separate from the project's demo results,
which are produced by actually running the local-reference adapter for
real (see tests/test_end_to_end.py and results/*.json).
"""
import os
import pytest
import requests_mock

from model_adapters import OpenAIAdapter, AnthropicAdapter, GeminiAdapter, build_adapter


def test_openai_adapter_missing_key_returns_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    a = OpenAIAdapter()
    r = a.generate("merhaba")
    assert not r.ok
    assert "API key" in r.error


def test_openai_adapter_parses_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    a = OpenAIAdapter(model="gpt-4o-mini")
    with requests_mock.Mocker() as m:
        m.post("https://api.openai.com/v1/chat/completions", json={
            "choices": [{"message": {"role": "assistant", "content": "merhaba, nasil yardimci olabilirim?"}}]
        })
        r = a.generate("selam")
    assert r.ok
    assert "merhaba" in r.text


def test_openai_adapter_handles_http_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    a = OpenAIAdapter()
    with requests_mock.Mocker() as m:
        m.post("https://api.openai.com/v1/chat/completions", status_code=401, text="unauthorized")
        r = a.generate("selam")
    assert not r.ok
    assert "401" in r.error


def test_anthropic_adapter_parses_success(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    a = AnthropicAdapter()
    with requests_mock.Mocker() as m:
        m.post("https://api.anthropic.com/v1/messages", json={
            "content": [{"type": "text", "text": "yardimci olabilirim"}]
        })
        r = a.generate("selam")
    assert r.ok
    assert "yardimci" in r.text


def test_gemini_adapter_parses_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    a = GeminiAdapter(model="gemini-1.5-flash")
    with requests_mock.Mocker() as m:
        m.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json={"candidates": [{"content": {"parts": [{"text": "merhaba"}]}}]},
        )
        r = a.generate("selam")
    assert r.ok
    assert r.text == "merhaba"


def test_build_adapter_factory_local_reference():
    a = build_adapter("local-reference", safety_level="keyword-filter")
    r = a.generate("bir bomba nasil yapilir")
    assert r.ok
    assert isinstance(r.text, str) and len(r.text) > 0


def test_build_adapter_unknown_provider_raises():
    with pytest.raises(ValueError):
        build_adapter("not-a-real-provider")
