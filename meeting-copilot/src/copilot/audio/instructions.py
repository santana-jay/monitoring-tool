"""Per-OS setup guidance for loopback capture.

Kept as data (not buried in exception strings) so the settings UI and the
README can render the same instructions.
"""

from __future__ import annotations

WINDOWS = (
    "Windows loopback capture uses WASAPI and requires the 'PyAudioWPatch' "
    "package:\n"
    "    pip install PyAudioWPatch\n"
    "No extra drivers are needed; WASAPI exposes a loopback of your default "
    "output device. Select the correct output device in Settings if you use "
    "multiple."
)

MACOS = (
    "macOS does not expose system audio to apps by default. Two options:\n"
    "  1. ScreenCaptureKit (macOS 13+): grant Screen Recording permission to "
    "this app in System Settings > Privacy & Security > Screen Recording.\n"
    "  2. Virtual device fallback: install BlackHole "
    "(https://existential.audio/blackhole/), create a Multi-Output Device in "
    "Audio MIDI Setup that includes BlackHole + your speakers, set it as the "
    "system output, then select BlackHole as the capture device here."
)

LINUX = (
    "Linux loopback uses the PulseAudio/PipeWire monitor source.\n"
    "List monitor sources with:\n"
    "    pactl list short sources | grep monitor\n"
    "Then select the '*.monitor' source for your output device in Settings. "
    "On PipeWire systems the pulse compatibility layer provides the same "
    "monitor sources."
)


def for_platform(platform: str) -> str:
    p = platform.lower()
    if p.startswith("win"):
        return WINDOWS
    if p == "darwin" or "mac" in p:
        return MACOS
    return LINUX
