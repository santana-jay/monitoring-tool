"""Speech-to-text layer."""

from copilot.stt.base import STTResult, Transcriber, NullTranscriber
from copilot.stt.vad import EnergyVAD, Utterance

__all__ = [
    "STTResult",
    "Transcriber",
    "NullTranscriber",
    "EnergyVAD",
    "Utterance",
]
