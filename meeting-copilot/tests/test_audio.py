import numpy as np

from copilot.audio.backends import (
    NullCapture,
    SoundDeviceCapture,
    WindowsLoopbackCapture,
    _resample,
    _to_mono_float32,
    create_capture,
)
from copilot.audio.base import AudioCapture, AudioFrame, CaptureUnavailable
from copilot.audio import instructions


def test_create_capture_per_platform():
    assert isinstance(create_capture(platform="win32"), WindowsLoopbackCapture)
    assert isinstance(create_capture(platform="linux"), SoundDeviceCapture)
    assert isinstance(create_capture(platform="darwin"), SoundDeviceCapture)


def test_null_capture_raises_with_instructions():
    cap = NullCapture("set up loopback please")
    assert not cap.is_running
    try:
        cap.start(lambda f: None)
        assert False, "expected CaptureUnavailable"
    except CaptureUnavailable as exc:
        assert "loopback" in str(exc).lower()


def test_to_mono_float32_int16_stereo():
    data = np.array([32767, -32768, 0, 0], dtype=np.int16)  # 2 frames, 2ch
    mono = _to_mono_float32(data, channels=2)
    assert mono.shape == (2,)
    assert -1.0 <= mono.min() and mono.max() <= 1.0


def test_resample_changes_length():
    x = np.ones(16_000, dtype=np.float32)
    y = _resample(x, 16_000, 8_000)
    assert y.shape[0] == 8_000
    assert _resample(x, 16_000, 16_000) is x  # no-op


def test_instructions_cover_all_platforms():
    assert "WASAPI" in instructions.for_platform("win32")
    assert "BlackHole" in instructions.for_platform("darwin")
    assert "monitor" in instructions.for_platform("linux")


def test_threaded_capture_emits_frames():
    """A fake threaded backend should deliver frames to the callback."""
    from copilot.audio.backends import _ThreadedCapture

    class Fake(_ThreadedCapture):
        def _run(self):
            sr = 16_000
            for _ in range(3):
                if self._stop.is_set():
                    break
                self._emit(np.zeros(sr // 2, dtype=np.float32))

    frames = []
    cap = Fake()
    cap.start(frames.append)
    cap._thread.join(timeout=2)
    cap.stop()
    assert len(frames) == 3
    assert all(isinstance(f, AudioFrame) for f in frames)
