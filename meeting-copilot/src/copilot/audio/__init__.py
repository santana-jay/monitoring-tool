"""Audio capture layer."""

from copilot.audio.base import (
    AudioCapture,
    AudioFrame,
    CaptureUnavailable,
    FrameCallback,
)
from copilot.audio.backends import (
    NullCapture,
    SoundDeviceCapture,
    WindowsLoopbackCapture,
    create_capture,
)

__all__ = [
    "AudioCapture",
    "AudioFrame",
    "CaptureUnavailable",
    "FrameCallback",
    "NullCapture",
    "SoundDeviceCapture",
    "WindowsLoopbackCapture",
    "create_capture",
]
