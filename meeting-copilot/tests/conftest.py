"""Shared test fixtures and fakes."""

from __future__ import annotations

from typing import List

import numpy as np
import pytest

from copilot.ai.client import LLMClient


class FakeLLM(LLMClient):
    """An LLM client that returns a canned response (or raises)."""

    def __init__(self, response: str = "{}"):
        self.response = response
        self.calls: List[dict] = []

    def complete(self, *, system, messages, model, max_tokens=1024,
                 temperature=0.2, on_delta=None):
        self.calls.append(
            {"system": system, "messages": messages, "model": model,
             "temperature": temperature}
        )
        if on_delta:
            on_delta(self.response)
        return self.response


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


def make_speech(seconds: float, sr: int = 16_000, amp: float = 0.1) -> np.ndarray:
    return (np.random.RandomState(0).randn(int(sr * seconds)) * amp).astype(np.float32)


def make_silence(seconds: float, sr: int = 16_000) -> np.ndarray:
    return np.zeros(int(sr * seconds), dtype=np.float32)
