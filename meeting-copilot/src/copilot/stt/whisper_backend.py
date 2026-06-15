"""faster-whisper streaming transcriber.

Lazily imports ``faster_whisper`` so the module is importable without the heavy
dependency. The model runs locally; audio never leaves the machine.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from copilot.stt.base import STTResult, Transcriber


class WhisperTranscriber(Transcriber):
    """Local Whisper STT via faster-whisper."""

    def __init__(self, model_size: str = "base", device: str = "auto",
                 compute_type: str = "default", language: Optional[str] = None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except Exception as exc:  # pragma: no cover - optional dep
                raise RuntimeError(
                    "faster-whisper is not installed. Install with: "
                    "pip install 'meeting-copilot[stt]'"
                ) from exc
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def transcribe(self, samples: np.ndarray, sample_rate: int,
                   offset: float = 0.0) -> List[STTResult]:  # pragma: no cover - needs model
        model = self._ensure_model()
        audio = np.asarray(samples, dtype=np.float32)
        if sample_rate != 16_000:
            from copilot.audio.backends import _resample

            audio = _resample(audio, sample_rate, 16_000)
        segments, _info = model.transcribe(
            audio, language=self.language, vad_filter=False
        )
        out: List[STTResult] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                out.append(
                    STTResult(
                        text=text,
                        start=offset + float(seg.start),
                        end=offset + float(seg.end),
                    )
                )
        return out
