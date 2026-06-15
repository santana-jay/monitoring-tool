import numpy as np

from copilot.stt.vad import EnergyVAD
from tests.conftest import make_silence, make_speech


def test_vad_segments_on_silence():
    vad = EnergyVAD(threshold=0.01, hangover_seconds=0.5, min_speech_seconds=0.2)
    sr = 16_000
    chunks = [make_speech(0.5), make_speech(0.5), make_silence(0.5), make_silence(0.5)]
    out = []
    t = 0.0
    for c in chunks:
        u = vad.accept(c, sr, t)
        t += 0.5
        if u:
            out.append(u)
    assert len(out) == 1
    assert out[0].end - out[0].start >= 0.9


def test_vad_ignores_pure_silence():
    vad = EnergyVAD(threshold=0.01, hangover_seconds=0.5)
    sr = 16_000
    for i in range(4):
        assert vad.accept(make_silence(0.5), sr, i * 0.5) is None
    assert vad.flush() is None


def test_vad_max_seconds_flush():
    vad = EnergyVAD(threshold=0.001, hangover_seconds=5.0, max_seconds=1.5,
                    min_speech_seconds=0.1)
    sr = 16_000
    out = []
    t = 0.0
    for _ in range(6):
        u = vad.accept(make_speech(0.5), sr, t)
        t += 0.5
        if u:
            out.append(u)
    assert len(out) >= 1  # forced to flush at max_seconds


def test_vad_flush_returns_partial():
    vad = EnergyVAD(threshold=0.01, hangover_seconds=5.0, min_speech_seconds=0.2)
    sr = 16_000
    vad.accept(make_speech(0.5), sr, 0.0)
    u = vad.flush()
    assert u is not None
