"""Engine: orchestrates capture → VAD → STT → store → retrieval → AI.

Runs the audio/STT work on a background thread and exposes thread-safe controls
(pause/resume/stop/purge) plus callbacks the UI subscribes to. The UI never
blocks on this work. AI calls are dispatched off the capture thread so
transcription latency is unaffected.

Privacy: audio is processed in memory and (by default) never written to disk.
Only transcript text is ever sent to the AI. The engine emits a clear
"recording active" state that the local-only UI reflects.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from copilot.ai.client import LLMClient
from copilot.ai.grounding import GatedSuggestions
from copilot.ai.pipelines import NotesPipeline, SuggestionsPipeline
from copilot.audio.base import AudioCapture, AudioFrame, CaptureUnavailable
from copilot.config import Config
from copilot.core.models import Notes, TranscriptSegment
from copilot.retrieval.store import RetrievalStore
from copilot.stt.base import Transcriber
from copilot.stt.vad import EnergyVAD
from copilot.store.db import Store


@dataclass
class EngineCallbacks:
    """Optional callbacks invoked by the engine (all may be None)."""

    on_segment: Optional[Callable[[TranscriptSegment], None]] = None
    on_suggestions: Optional[Callable[[GatedSuggestions], None]] = None
    on_notes: Optional[Callable[[Notes], None]] = None
    on_state: Optional[Callable[[str], None]] = None
    on_error: Optional[Callable[[str], None]] = None


class Engine:
    """Coordinates the live meeting pipeline for a single meeting at a time."""

    def __init__(
        self,
        config: Config,
        store: Store,
        capture: AudioCapture,
        transcriber: Transcriber,
        retrieval: RetrievalStore,
        suggestions: Optional[SuggestionsPipeline] = None,
        notes: Optional[NotesPipeline] = None,
        callbacks: Optional[EngineCallbacks] = None,
        vad: Optional[EnergyVAD] = None,
        notes_interval: float = 60.0,
    ):
        self.config = config
        self.store = store
        self.capture = capture
        self.transcriber = transcriber
        self.retrieval = retrieval
        self.suggestions = suggestions
        self.notes = notes
        self.cb = callbacks or EngineCallbacks()
        self.vad = vad or EnergyVAD()
        self.notes_interval = notes_interval

        self._meeting_id: Optional[int] = None
        self._paused = threading.Event()
        self._running = False
        self._lock = threading.Lock()
        self._last_notes_at = 0.0
        self._recent: List[TranscriptSegment] = []

    # -- state -------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    @property
    def meeting_id(self) -> Optional[int]:
        return self._meeting_id

    def _emit_state(self) -> None:
        if self.cb.on_state:
            if not self._running:
                state = "stopped"
            elif self._paused.is_set():
                state = "paused"
            else:
                state = "recording"
            self.cb.on_state(state)

    def _error(self, msg: str) -> None:
        if self.cb.on_error:
            self.cb.on_error(msg)

    # -- lifecycle ---------------------------------------------------------
    def start(self, title: Optional[str] = None) -> None:
        if self._running:
            return
        self._meeting_id = self.store.create_meeting(title)
        self._running = True
        self._paused.clear()
        self._last_notes_at = time.monotonic()
        try:
            self.capture.start(self._on_frame)
        except CaptureUnavailable as exc:
            self._running = False
            self._emit_state()
            self._error(str(exc))
            raise
        self._emit_state()

    def pause(self) -> None:
        self._paused.set()
        self._emit_state()

    def resume(self) -> None:
        self._paused.clear()
        self._emit_state()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        try:
            self.capture.stop()
        finally:
            # Flush any partial utterance before closing the meeting.
            utt = self.vad.flush()
            if utt is not None:
                self._transcribe_utterance(utt.samples, utt.start, utt.end)
            if self._meeting_id is not None:
                self.store.end_meeting(self._meeting_id)
        self._emit_state()

    def purge(self) -> None:
        """Stop and delete ALL stored data (transcripts, notes, embeddings)."""
        if self._running:
            self.stop()
        self.store.purge_all()
        self._recent = []

    # -- audio path --------------------------------------------------------
    def _on_frame(self, frame: AudioFrame) -> None:
        if self._paused.is_set() or not self._running:
            return
        try:
            utt = self.vad.accept(frame.samples, frame.sample_rate, frame.timestamp)
            if utt is not None:
                self._transcribe_utterance(utt.samples, utt.start, utt.end)
        except Exception as exc:  # never let the capture thread die
            self._error(f"audio processing error: {exc}")

    def _transcribe_utterance(self, samples, start: float, end: float) -> None:
        results = self.transcriber.transcribe(samples, self.vad._sample_rate, offset=start)
        for res in results:
            seg = TranscriptSegment(
                meeting_id=self._meeting_id or 0,
                start=res.start,
                end=res.end,
                text=res.text,
                speaker=res.speaker,
                is_final=res.is_final,
            )
            seg.id = self.store.add_segment(seg)
            self.retrieval.index_segment(seg)
            self._recent.append(seg)
            self._recent = self._recent[-30:]
            if self.cb.on_segment:
                self.cb.on_segment(seg)
            self._maybe_suggest()
            self._maybe_take_notes()

    # -- AI dispatch (off the capture thread) ------------------------------
    def _maybe_suggest(self) -> None:
        if self.suggestions is None or not self._recent:
            return
        recent = list(self._recent[-8:])
        meeting_id = self._meeting_id

        def work():
            try:
                gated = self.suggestions.run(recent, meeting_id=meeting_id)
                if self._meeting_id is not None:
                    import json

                    payload = json.dumps(
                        {"suggestions": [s.model_dump() for s in gated.suggestions],
                         "abstained": gated.abstained}
                    )
                    self.store.save_suggestions(self._meeting_id, payload)
                if self.cb.on_suggestions:
                    self.cb.on_suggestions(gated)
            except Exception as exc:
                self._error(f"suggestion error: {exc}")

        threading.Thread(target=work, name="suggest", daemon=True).start()

    def _maybe_take_notes(self) -> None:
        if self.notes is None:
            return
        now = time.monotonic()
        if now - self._last_notes_at < self.notes_interval:
            return
        self._last_notes_at = now
        recent = list(self._recent)
        meeting_id = self._meeting_id

        def work():
            try:
                notes = self.notes.run(recent)
                if meeting_id is not None:
                    self.store.save_notes(meeting_id, notes.model_dump_json())
                if self.cb.on_notes:
                    self.cb.on_notes(notes)
            except Exception as exc:
                self._error(f"notes error: {exc}")

        threading.Thread(target=work, name="notes", daemon=True).start()
