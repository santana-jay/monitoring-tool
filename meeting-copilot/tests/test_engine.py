import time

import numpy as np

from copilot.audio.base import AudioCapture, AudioFrame
from copilot.config import Config
from copilot.core.engine import Engine, EngineCallbacks
from copilot.retrieval.embeddings import HashingEmbedder
from copilot.retrieval.store import RetrievalStore
from copilot.stt.base import STTResult, Transcriber
from copilot.store.db import Store
from tests.conftest import FakeLLM
from copilot.ai.pipelines import SuggestionsPipeline


class ScriptedCapture(AudioCapture):
    """Pushes a fixed sequence of speech/silence frames synchronously."""

    def __init__(self):
        self._running = False

    @property
    def is_running(self):
        return self._running

    def start(self, on_frame):
        self._running = True
        sr = 16_000
        speech = (np.random.RandomState(1).randn(sr // 2) * 0.1).astype(np.float32)
        silence = np.zeros(sr // 2, dtype=np.float32)
        t = 0.0
        for chunk in [speech, speech, silence, silence]:
            on_frame(AudioFrame(samples=chunk, sample_rate=sr, timestamp=t))
            t += 0.5

    def stop(self):
        self._running = False


class ScriptedSTT(Transcriber):
    def transcribe(self, samples, sample_rate, offset=0.0):
        return [STTResult(text="We ship the API on Friday", start=offset, end=offset + 1)]


def _build(tmp_db, with_ai=True):
    store = Store(tmp_db)
    config = Config(data_dir="/tmp/copilot-test")
    retr = RetrievalStore(store, embedder=HashingEmbedder())
    sug = None
    if with_ai:
        llm = FakeLLM(
            '{"suggestions": [{"text": "Confirm Friday", "confidence": 0.9,'
            ' "citations": [{"start": 0, "end": 1, "quote": "ship the API"}]}]}'
        )
        sug = SuggestionsPipeline(client=llm, model="fast", retrieval=retr,
                                  min_confidence=0.5)
    segs, suggs, states = [], [], []
    cb = EngineCallbacks(
        on_segment=segs.append,
        on_suggestions=suggs.append,
        on_state=states.append,
    )
    eng = Engine(config, store, ScriptedCapture(), ScriptedSTT(), retr,
                 suggestions=sug, callbacks=cb)
    return eng, store, segs, suggs, states


def test_engine_captures_and_stores(tmp_db):
    eng, store, segs, suggs, states = _build(tmp_db)
    eng.start("meeting")
    time.sleep(0.5)
    eng.stop()
    assert len(segs) >= 1
    assert "recording" in states and "stopped" in states
    assert len(store.get_segments(eng.meeting_id)) >= 1


def test_engine_emits_suggestions(tmp_db):
    eng, store, segs, suggs, states = _build(tmp_db)
    eng.start()
    time.sleep(0.5)
    eng.stop()
    assert any(s.has_confident for s in suggs)


def test_engine_pause_blocks_processing(tmp_db):
    eng, store, segs, suggs, states = _build(tmp_db, with_ai=False)
    eng.start()
    eng.pause()
    assert eng.is_paused
    eng.resume()
    assert not eng.is_paused
    eng.stop()


def test_engine_purge(tmp_db):
    eng, store, segs, suggs, states = _build(tmp_db, with_ai=False)
    eng.start()
    time.sleep(0.3)
    eng.stop()
    eng.purge()
    assert store.all_segments() == []
