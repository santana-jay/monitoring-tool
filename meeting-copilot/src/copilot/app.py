"""Application assembly / bootstrap.

Builds the engine from config, selecting concrete backends and degrading
gracefully when optional dependencies (STT, embeddings, AI, audio) are missing.
Kept UI-free so it can be exercised in tests; the tray entry point lives in
:mod:`copilot.__main__`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from copilot.ai.client import AnthropicClient, LLMClient
from copilot.ai.pipelines import NotesPipeline, SuggestionsPipeline
from copilot.audio.base import AudioCapture
from copilot.audio.backends import create_capture
from copilot.config import Config
from copilot.core.engine import Engine, EngineCallbacks
from copilot.retrieval.store import RetrievalStore
from copilot.stt.base import NullTranscriber, Transcriber
from copilot.store.db import Store


def build_transcriber(config: Config) -> Transcriber:
    try:
        from copilot.stt.whisper_backend import WhisperTranscriber

        return WhisperTranscriber(model_size=config.whisper_model)
    except Exception:
        return NullTranscriber()


def build_engine(
    config: Config,
    store: Optional[Store] = None,
    capture: Optional[AudioCapture] = None,
    transcriber: Optional[Transcriber] = None,
    llm: Optional[LLMClient] = None,
    callbacks: Optional[EngineCallbacks] = None,
) -> Engine:
    """Assemble a fully-wired :class:`Engine` from configuration."""
    config.ensure_dirs()
    store = store or Store(config.db_path)
    retrieval = RetrievalStore(store)
    capture = capture or create_capture(device=None)
    transcriber = transcriber or build_transcriber(config)
    llm = llm or AnthropicClient()

    suggestions = None
    notes = None
    # Only build AI pipelines when a key and model ids are present; otherwise the
    # app still runs (capture + transcript) without AI features.
    configured = getattr(llm, "configured", True)
    if configured and config.model_fast:
        suggestions = SuggestionsPipeline(
            client=llm,
            model=config.model_fast,
            retrieval=retrieval,
            min_confidence=config.min_confidence,
        )
    if configured and config.model_strong:
        notes = NotesPipeline(client=llm, model=config.model_strong)

    return Engine(
        config=config,
        store=store,
        capture=capture,
        transcriber=transcriber,
        retrieval=retrieval,
        suggestions=suggestions,
        notes=notes,
        callbacks=callbacks,
    )
