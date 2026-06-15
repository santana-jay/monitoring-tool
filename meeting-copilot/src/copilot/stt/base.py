"""Speech-to-text abstraction.

``Transcriber`` is the pluggable interface; the default backend is local
streaming Whisper (faster-whisper), but a cloud STT can be dropped in by
implementing the same interface. STT keeps audio local — only the resulting
text ever leaves the machine (and only when the AI features are used).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class STTResult:
    """A transcription result for one audio segment."""

    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    is_final: bool = True


class Transcriber(abc.ABC):
    """Pluggable speech-to-text backend."""

    @abc.abstractmethod
    def transcribe(self, samples: np.ndarray, sample_rate: int,
                   offset: float = 0.0) -> List[STTResult]:
        """Transcribe a chunk of mono float32 audio.

        ``offset`` is added to result timestamps so they are absolute within
        the meeting.
        """


class NullTranscriber(Transcriber):
    """Returns nothing; used when no STT backend is installed."""

    def transcribe(self, samples, sample_rate, offset=0.0):
        return []
