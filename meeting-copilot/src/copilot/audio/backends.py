"""Concrete audio-capture backends and a runtime factory.

Heavy / platform-specific imports (``pyaudiowpatch``, ``sounddevice``) are done
lazily inside ``start`` so the module imports cleanly on any OS and in CI where
no audio stack is present. When a backend can't initialise it raises
:class:`CaptureUnavailable` carrying per-OS setup guidance.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import Optional

import numpy as np

from copilot.audio import instructions
from copilot.audio.base import (
    AudioCapture,
    AudioFrame,
    CaptureUnavailable,
    FrameCallback,
)

_CHUNK_SECONDS = 0.5


def _to_mono_float32(data: np.ndarray, channels: int) -> np.ndarray:
    """Convert interleaved int16/float frames to mono float32 in [-1, 1]."""
    arr = np.asarray(data)
    if arr.dtype == np.int16:
        arr = arr.astype(np.float32) / 32768.0
    else:
        arr = arr.astype(np.float32)
    if channels > 1 and arr.ndim == 1:
        arr = arr.reshape(-1, channels)
    if arr.ndim == 2:
        arr = arr.mean(axis=1)
    return np.clip(arr, -1.0, 1.0)


class _ThreadedCapture(AudioCapture):
    """Base providing start/stop/thread bookkeeping for streaming backends."""

    def __init__(self, sample_rate: int = 16_000, device: Optional[int] = None):
        self.sample_rate = sample_rate
        self.device = device
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._on_frame: Optional[FrameCallback] = None
        self._started_at = 0.0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, on_frame: FrameCallback) -> None:
        if self.is_running:
            return
        self._on_frame = on_frame
        self._stop.clear()
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="audio-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        if t is not None:
            t.join(timeout=2.0)
        self._thread = None

    def _emit(self, mono: np.ndarray) -> None:
        if self._on_frame is not None:
            self._on_frame(
                AudioFrame(
                    samples=mono,
                    sample_rate=self.sample_rate,
                    timestamp=time.monotonic() - self._started_at,
                )
            )

    def _run(self) -> None:  # pragma: no cover - backend-specific
        raise NotImplementedError


class WindowsLoopbackCapture(_ThreadedCapture):
    """WASAPI loopback via PyAudioWPatch."""

    @classmethod
    def setup_instructions(cls) -> str:
        return instructions.WINDOWS

    def _run(self) -> None:  # pragma: no cover - requires Windows + device
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            raise CaptureUnavailable(instructions.WINDOWS) from exc

        pa = pyaudio.PyAudio()
        try:
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out = pa.get_device_info_by_index(wasapi["defaultOutputDevice"])
            loopback = None
            for info in pa.get_loopback_device_info_generator():
                if default_out["name"] in info["name"]:
                    loopback = info
                    break
            if loopback is None:
                raise CaptureUnavailable(instructions.WINDOWS)

            channels = int(loopback["maxInputChannels"]) or 2
            native_rate = int(loopback["defaultSampleRate"])
            frames_per_buffer = int(native_rate * _CHUNK_SECONDS)
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=native_rate,
                frames_per_buffer=frames_per_buffer,
                input=True,
                input_device_index=loopback["index"],
            )
            try:
                while not self._stop.is_set():
                    raw = stream.read(frames_per_buffer, exception_on_overflow=False)
                    data = np.frombuffer(raw, dtype=np.int16)
                    mono = _to_mono_float32(data, channels)
                    mono = _resample(mono, native_rate, self.sample_rate)
                    self._emit(mono)
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()


class SoundDeviceCapture(_ThreadedCapture):
    """Generic backend using ``sounddevice`` (PortAudio).

    Used for the Linux PulseAudio/PipeWire monitor source and as the macOS
    BlackHole virtual-device fallback. The caller selects the loopback/monitor
    device via ``device``.
    """

    def __init__(self, sample_rate: int = 16_000, device: Optional[int] = None,
                 platform_hint: str = ""):
        super().__init__(sample_rate=sample_rate, device=device)
        self._platform_hint = platform_hint or sys.platform

    @classmethod
    def setup_instructions(cls) -> str:
        return instructions.for_platform(sys.platform)

    def _run(self) -> None:  # pragma: no cover - requires audio device
        try:
            import sounddevice as sd
        except Exception as exc:
            raise CaptureUnavailable(instructions.for_platform(self._platform_hint)) from exc

        blocksize = int(self.sample_rate * _CHUNK_SECONDS)
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                device=self.device,
                channels=1,
                dtype="float32",
                blocksize=blocksize,
            ) as stream:
                while not self._stop.is_set():
                    data, _ = stream.read(blocksize)
                    mono = _to_mono_float32(data[:, 0] if data.ndim == 2 else data, 1)
                    self._emit(mono)
        except CaptureUnavailable:
            raise
        except Exception as exc:
            raise CaptureUnavailable(
                instructions.for_platform(self._platform_hint)
            ) from exc


class NullCapture(AudioCapture):
    """No-op fallback used when no loopback backend is available.

    Lets the rest of the app start and show setup instructions instead of
    crashing — the graceful-degradation path.
    """

    def __init__(self, reason: str = ""):
        self.reason = reason or instructions.for_platform(sys.platform)
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, on_frame: FrameCallback) -> None:
        self._running = False
        raise CaptureUnavailable(self.reason)

    def stop(self) -> None:
        self._running = False

    @classmethod
    def setup_instructions(cls) -> str:
        return instructions.for_platform(sys.platform)


def _resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Cheap linear resampler (dependency-free) for rate conversion."""
    if src_rate == dst_rate or len(samples) == 0:
        return samples
    duration = len(samples) / float(src_rate)
    dst_len = max(1, int(round(duration * dst_rate)))
    src_idx = np.linspace(0, len(samples) - 1, num=dst_len)
    return np.interp(src_idx, np.arange(len(samples)), samples).astype(np.float32)


def create_capture(
    sample_rate: int = 16_000,
    device: Optional[int] = None,
    platform: Optional[str] = None,
) -> AudioCapture:
    """Return an appropriate capture backend for the current platform.

    Never raises for platform reasons: if a real backend's dependencies are
    missing the returned object will raise :class:`CaptureUnavailable` (with
    setup guidance) only when :meth:`AudioCapture.start` is called.
    """
    plat = (platform or sys.platform).lower()
    if plat.startswith("win"):
        return WindowsLoopbackCapture(sample_rate=sample_rate, device=device)
    # macOS and Linux both go through PortAudio/sounddevice; the difference is
    # which device the user selects (BlackHole vs. a PulseAudio monitor).
    return SoundDeviceCapture(sample_rate=sample_rate, device=device, platform_hint=plat)
