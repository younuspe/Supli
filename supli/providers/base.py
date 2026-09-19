"""AI provider abstraction (roadmap §27, SKILL §19).

The architecture must not permanently depend on one provider, so providers are
interchangeable behind this interface. Ollama is the current foundation; the
scripted provider makes the whole pipeline testable without a live model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    pass


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)


class Provider:
    """Base provider interface."""

    name: str = "base"
    is_local: bool = False

    def chat(self, messages: list[ChatMessage], model: str | None = None) -> ProviderResponse:
        raise NotImplementedError

    def models(self) -> list[str]:
        return []

    def status(self) -> dict[str, Any]:
        raise NotImplementedError


class ScriptedProvider(Provider):
    """Deterministic provider used for testing and offline operation.

    It answers by pattern so the full UI→backend→provider→UI path can be
    exercised without Ollama. It is explicitly not an AI model.
    """

    name = "scripted"
    is_local = True

    def __init__(self, model: str = "scripted-demo") -> None:
        self.model = model

    def chat(self, messages: list[ChatMessage], model: str | None = None) -> ProviderResponse:
        prompt = messages[-1].content if messages else ""
        reply = self._reply(prompt)
        return ProviderResponse(content=reply, model=model or self.model, provider=self.name)

    def _reply(self, prompt: str) -> str:
        text = prompt.lower()
        if "plan" in text:
            return (
                "Plan:\n1. Inspect the real workspace.\n2. Identify the files involved.\n"
                "3. Propose the smallest safe change.\n4. Apply and test.\n5. Review the result."
            )
        if "hello" in text or "hi" in text:
            return "Supli here. I operate on the real workspace. What should we work on?"
        return f"[scripted provider] received {len(prompt)} characters. No live model is configured."

    def models(self) -> list[str]:
        return [self.model]

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "available": True,
            "local": True,
            "models": self.models(),
            "note": "deterministic offline provider; not an AI model",
        }


class OllamaProvider(Provider):
    """Local Ollama provider (the current foundation)."""

    name = "ollama"
    is_local = True

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or "qwen2.5-coder:7b"
        self.timeout = 120.0

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("httpx is required for the Ollama provider") from exc
        try:
            response = httpx.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

    def chat(self, messages: list[ChatMessage], model: str | None = None) -> ProviderResponse:
        payload = {
            "model": model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        data = self._post("/api/chat", payload)
        message = data.get("message", {})
        return ProviderResponse(
            content=message.get("content", ""),
            model=data.get("model", model or self.model),
            provider=self.name,
            raw=data,
        )

    def models(self) -> list[str]:
        try:
            import httpx

            response = httpx.get(f"{self.base_url}/api/tags", timeout=8.0)
            response.raise_for_status()
            return [m.get("name", "") for m in response.json().get("models", [])]
        except Exception:
            return []

    def status(self) -> dict[str, Any]:
        try:
            import httpx

            response = httpx.get(f"{self.base_url}/api/tags", timeout=4.0)
            available = response.status_code == 200
            models = [m.get("name", "") for m in response.json().get("models", [])] if available else []
        except Exception as exc:
            return {
                "provider": self.name,
                "available": False,
                "local": True,
                "models": [],
                "error": str(exc),
                "base_url": self.base_url,
            }
        return {
            "provider": self.name,
            "available": available,
            "local": True,
            "models": models,
            "base_url": self.base_url,
            "configured_model": self.model,
            "model_present": self.model in models,
        }


class ProviderRegistry:
    """Holds configured providers and the active selection (roadmap §27)."""

    def __init__(self, default: Provider | None = None) -> None:
        self._providers: dict[str, Provider] = {}
        self._active: str | None = None
        if default is not None:
            self.register(default, activate=True)

    def register(self, provider: Provider, activate: bool = False) -> None:
        self._providers[provider.name] = provider
        if activate or self._active is None:
            self._active = provider.name

    def get(self, name: str) -> Provider | None:
        return self._providers.get(name)

    def active(self) -> Provider:
        if self._active is None or self._active not in self._providers:
            raise ProviderError("no provider is configured")
        return self._providers[self._active]

    def activate(self, name: str) -> None:
        if name not in self._providers:
            raise ProviderError(f"unknown provider: {name}")
        self._active = name

    def status(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "providers": [p.status() for p in self._providers.values()],
        }


def parse_tool_call(text: str) -> dict[str, Any] | None:
    """Extract a fenced JSON tool call from model output.

    Models are unreliable at emitting bare JSON, so only a fenced block that
    parses to an object with a "tool" key is accepted.
    """
    import re

    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "tool" in data:
            return data
    return None