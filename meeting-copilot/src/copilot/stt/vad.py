"""Voice-activity detection.

A dependency-free energy-based VAD is provided for low latency and testability.
It segments a stream of audio frames into utterances so the STT backend only
runs on speech, reducing latency and cost. The interface allows swapping in a
stronger model (e.g. Silero) later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class Utterance:
    """A contiguous speech region accumulated by the VAD."""

    samples: np.ndarray
    start: float
    end: float


@dataclass
class EnergyVAD:
    """Simple RMS-energy voice-activity detector with hangover.

    Feed it audio chunks via :meth:`accept`; it returns a completed
    :class:`Utterance` once trailing silence exceeds ``hangover_seconds`` (or
    the buffer exceeds ``max_seconds``), otherwise ``None``.
    """

    threshold: float = 0.012
    hangover_seconds: float = 0.6
    min_speech_seconds: float = 0.3
    max_seconds: float = 20.0

    _buf: List[np.ndarray] = field(default_factory=list)
    _sample_rate: int = 16_000
    _start_ts: Optional[float] = None
    _last_voice_ts: Optional[float] = None
    _silence: float = 0.0
    _voiced_seconds: float = 0.0

    @staticmethod
    def _rms(x: np.ndarray) -> float:
        if x.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))

    def accept(self, samples: np.ndarray, sample_rate: int,
               timestamp: float) -> Optional[Utterance]:
        self._sample_rate = sample_rate
        dur = len(samples) / float(sample_rate) if sample_rate else 0.0
        voiced = self._rms(samples) >= self.threshold

        if voiced:
            if self._start_ts is None:
                self._start_ts = timestamp
            self._buf.append(samples)
            self._voiced_seconds += dur
            self._silence = 0.0
            self._last_voice_ts = timestamp + dur
        elif self._start_ts is not None:
            # In an utterance but this chunk is silence: keep it (natural gap)
            # and accumulate hangover.
            self._buf.append(samples)
            self._silence += dur

        buffered = sum(len(b) for b in self._buf) / float(sample_rate)
        if self._start_ts is not None and (
            self._silence >= self.hangover_seconds or buffered >= self.max_seconds
        ):
            return self._flush()
        return None

    def flush(self) -> Optional[Utterance]:
        """Force-complete any in-progress utterance (e.g. on stop)."""
        if self._start_ts is not None and self._voiced_seconds >= self.min_speech_seconds:
            return self._flush()
        self._reset()
        return None

    def _flush(self) -> Optional[Utterance]:
        if self._voiced_seconds < self.min_speech_seconds or not self._buf:
            self._reset()
            return None
        samples = np.concatenate(self._buf)
        start = self._start_ts or 0.0
        end = self._last_voice_ts if self._last_voice_ts is not None else (
            start + len(samples) / float(self._sample_rate)
        )
        self._reset()
        return Utterance(samples=samples, start=start, end=end)

    def _reset(self) -> None:
        self._buf = []
        self._start_ts = None
        self._last_voice_ts = None
        self._silence = 0.0
        self._voiced_seconds = 0.0
