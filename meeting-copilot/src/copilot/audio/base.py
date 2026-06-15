"""Audio capture abstraction.

Defines the platform-independent ``AudioCapture`` interface and an
``AudioFrame`` container. Concrete backends live in :mod:`copilot.audio.backends`.

Design constraints:
  * Capture is **system/loopback only** — what the user already hears. We never
    open the microphone and never transmit audio anywhere. This is what keeps
    the tool invisible to other meeting participants.
  * Backends must **degrade gracefully**: if loopback isn't available, raise
    :class:`CaptureUnavailable` with actionable, per-OS setup guidance rather
    than crashing.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

# A frame callback receives mono float32 samples in [-1, 1].
FrameCallback = Callable[["AudioFrame"], None]


@dataclass
class AudioFrame:
    """A chunk of captured PCM audio.

    ``samples`` is mono float32 in [-1, 1]. ``timestamp`` is seconds since the
    capture started.
    """

    samples: np.ndarray
    sample_rate: int
    timestamp: float

    @property
    def duration(self) -> float:
        return len(self.samples) / float(self.sample_rate) if self.sample_rate else 0.0


class CaptureUnavailable(RuntimeError):
    """Raised when loopback capture can't be set up on this machine.

    The message should contain concrete, OS-specific setup instructions so the
    app can surface them to the user.
    """


class AudioCapture(abc.ABC):
    """Abstract base for a loopback/system-audio capture backend."""

    sample_rate: int = 16_000

    @abc.abstractmethod
    def start(self, on_frame: FrameCallback) -> None:
        """Begin capture, invoking ``on_frame`` for each chunk.

        Implementations must raise :class:`CaptureUnavailable` (ideally before
        any side effects) when loopback can't be initialised.
        """

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop capture and release the device. Idempotent."""

    @property
    @abc.abstractmethod
    def is_running(self) -> bool:
        ...

    # Convenience for setup screens; backends may override.
    @classmethod
    def setup_instructions(cls) -> str:
        return "No additional setup information available for this backend."
