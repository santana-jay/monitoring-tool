"""Anthropic Claude client wrapper.

A thin wrapper over the official ``anthropic`` SDK (lazily imported) exposing
streaming and non-streaming message calls. Two model roles are configured: a
fast model for real-time suggestions and a stronger model for note
summarization.

IMPORTANT: model IDs are NOT hardcoded here. They are supplied via
:class:`copilot.config.Config` (env/.env) and must be verified against
https://docs.claude.com at build time, because Anthropic model IDs change.

The API key is obtained from the keychain/env via :mod:`copilot.secrets` and is
never logged. ``LLMClient`` is an interface so a fake can be injected in tests.
"""

from __future__ import annotations

import abc
from typing import Callable, List, Optional

from copilot import secrets


class LLMClient(abc.ABC):
    """Minimal interface used by the pipelines (so tests can fake it)."""

    @abc.abstractmethod
    def complete(self, *, system: str, messages: List[dict], model: str,
                 max_tokens: int = 1024, temperature: float = 0.2,
                 on_delta: Optional[Callable[[str], None]] = None) -> str:
        """Return the full text completion, optionally streaming deltas."""


class AnthropicClient(LLMClient):
    """Concrete client backed by the Anthropic Messages API (streaming)."""

    def __init__(self, api_key: Optional[str] = None):
        # Resolve from keychain/env; never store it anywhere it could be logged.
        self._api_key = api_key or secrets.get_api_key()
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _ensure(self):  # pragma: no cover - requires anthropic + key
        if not self._api_key:
            raise RuntimeError(
                "No Anthropic API key configured. Set ANTHROPIC_API_KEY or store "
                "it in the OS keychain (see README)."
            )
        if self._client is None:
            try:
                import anthropic
            except Exception as exc:
                raise RuntimeError(
                    "anthropic SDK not installed. Install with: "
                    "pip install 'meeting-copilot[ai]'"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, *, system: str, messages: List[dict], model: str,
                 max_tokens: int = 1024, temperature: float = 0.2,
                 on_delta: Optional[Callable[[str], None]] = None
                 ) -> str:  # pragma: no cover - network call
        if not model:
            raise RuntimeError(
                "No model id configured. Set COPILOT_MODEL_FAST / "
                "COPILOT_MODEL_STRONG (verify current ids at docs.claude.com)."
            )
        client = self._ensure()
        chunks: List[str] = []
        with client.messages.stream(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                if on_delta is not None:
                    on_delta(text)
        return "".join(chunks)
