"""
model_adapters.py
------------------
Pluggable adapters that let the auditor send a prompt to *any* chat/completion
model and get back a plain-text response, regardless of which vendor is
behind it. This is what makes the auditor "genel amaçli" (general-purpose):
add a new class here and the rest of the pipeline (prompts, classifiers,
runner, report, dashboard) does not need to change.

Every network-calling adapter reads its credentials from an environment
variable -- never hard-coded, never logged, never sent anywhere except the
provider's own official API endpoint.

Included adapters:
  * OpenAIAdapter                  -> api.openai.com/v1/chat/completions (or any
                                       OpenAI-compatible base_url)
  * AnthropicAdapter                -> api.anthropic.com/v1/messages
  * GeminiAdapter                   -> generativelanguage.googleapis.com
  * OpenAICompatibleAdapter         -> generic adapter for self-hosted / other
                                       OpenAI-schema endpoints (Ollama, vLLM,
                                       LM Studio, Groq, Together, OpenRouter, ...)
  * LocalReferenceModelAdapter      -> a small, fully transparent, locally
                                       running text generator (see
                                       local_reference_model.py) used for the
                                       offline demonstration in this project,
                                       since this sandbox's network egress
                                       blocks every hosted model API and every
                                       weight-hosting service (Hugging Face
                                       Hub, GCS, Azure blob, etc.) -- see
                                       README.md "Neden yerel bir referans
                                       model?" for the full explanation.
"""

from __future__ import annotations

import abc
import os
import time
import dataclasses
from typing import Optional

import requests


@dataclasses.dataclass
class ModelResponse:
    """Normalized result of a single prompt sent to a model."""
    text: str
    latency_s: float
    raw: Optional[dict] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ModelAdapter(abc.ABC):
    """Base class every model adapter must implement."""

    name: str = "base"

    @abc.abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, timeout: float = 30.0) -> ModelResponse:
        """Send `prompt` (and optional `system` instruction) to the model and
        return a ModelResponse. Must never raise -- network/HTTP errors are
        caught and returned as ModelResponse(error=...)."""
        raise NotImplementedError


class OpenAIAdapter(ModelAdapter):
    """Works with api.openai.com or any OpenAI-compatible /chat/completions
    endpoint (pass a custom base_url for self-hosted / third-party gateways)."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key_env: str = "OPENAI_API_KEY",
                 base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt, system=None, timeout=30.0) -> ModelResponse:
        if not self.api_key:
            return ModelResponse(text="", latency_s=0.0, error=f"missing API key (env var not set)")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        t0 = time.time()
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages, "temperature": 0.7, "max_tokens": 500},
                timeout=timeout,
            )
            latency = time.time() - t0
            if resp.status_code != 200:
                return ModelResponse(text="", latency_s=latency, error=f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return ModelResponse(text=text, latency_s=latency, raw=data)
        except requests.RequestException as e:
            return ModelResponse(text="", latency_s=time.time() - t0, error=str(e))


class OpenAICompatibleAdapter(OpenAIAdapter):
    """Explicit alias for third-party OpenAI-schema gateways (Groq, Together,
    OpenRouter, a local Ollama/vLLM server, ...). Identical wire format to
    OpenAIAdapter; kept as its own class so audit reports show the correct
    provider label."""

    name = "openai-compatible"


class AnthropicAdapter(ModelAdapter):
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku-20241022", api_key_env: str = "ANTHROPIC_API_KEY",
                 base_url: str = "https://api.anthropic.com/v1"):
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt, system=None, timeout=30.0) -> ModelResponse:
        if not self.api_key:
            return ModelResponse(text="", latency_s=0.0, error="missing API key (env var not set)")
        payload = {
            "model": self.model,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        t0 = time.time()
        try:
            resp = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            latency = time.time() - t0
            if resp.status_code != 200:
                return ModelResponse(text="", latency_s=latency, error=f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            text = "".join(block.get("text", "") for block in data.get("content", []))
            return ModelResponse(text=text, latency_s=latency, raw=data)
        except requests.RequestException as e:
            return ModelResponse(text="", latency_s=time.time() - t0, error=str(e))


class GeminiAdapter(ModelAdapter):
    name = "gemini"

    def __init__(self, model: str = "gemini-1.5-flash", api_key_env: str = "GEMINI_API_KEY",
                 base_url: str = "https://generativelanguage.googleapis.com/v1beta"):
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt, system=None, timeout=30.0) -> ModelResponse:
        if not self.api_key:
            return ModelResponse(text="", latency_s=0.0, error="missing API key (env var not set)")
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        t0 = time.time()
        try:
            resp = requests.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            latency = time.time() - t0
            if resp.status_code != 200:
                return ModelResponse(text="", latency_s=latency, error=f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return ModelResponse(text=text, latency_s=latency, raw=data)
        except (requests.RequestException, KeyError, IndexError) as e:
            return ModelResponse(text="", latency_s=time.time() - t0, error=str(e))


class LocalReferenceModelAdapter(ModelAdapter):
    """Wraps the small local text generator defined in local_reference_model.py.
    Used only for this project's offline demonstration run -- see README.md
    for why. `safety_level` selects one of three transparently-different
    configurations of the SAME underlying generator, so the demo can show how
    the auditor's scores move as real guardrail logic is added."""

    name = "local-reference"

    def __init__(self, safety_level: str = "unfiltered"):
        from local_reference_model import ReferenceSystem
        self.safety_level = safety_level
        self._system = ReferenceSystem(safety_level=safety_level)

    def generate(self, prompt, system=None, timeout=30.0) -> ModelResponse:
        t0 = time.time()
        text = self._system.respond(prompt)
        return ModelResponse(text=text, latency_s=time.time() - t0, raw={"safety_level": self.safety_level})


ADAPTER_REGISTRY = {
    "openai": OpenAIAdapter,
    "openai-compatible": OpenAICompatibleAdapter,
    "anthropic": AnthropicAdapter,
    "gemini": GeminiAdapter,
    "local-reference": LocalReferenceModelAdapter,
}


def build_adapter(provider: str, **kwargs) -> ModelAdapter:
    """Factory used by the CLI: build_adapter('openai', model='gpt-4o-mini')"""
    if provider not in ADAPTER_REGISTRY:
        raise ValueError(f"Unknown provider '{provider}'. Options: {list(ADAPTER_REGISTRY)}")
    return ADAPTER_REGISTRY[provider](**kwargs)
