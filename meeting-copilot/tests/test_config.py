from copilot.config import Config


def test_model_ids_not_hardcoded(monkeypatch):
    # No memorised defaults: model ids are empty until configured.
    for var in ("COPILOT_MODEL_FAST", "COPILOT_MODEL_STRONG"):
        monkeypatch.delenv(var, raising=False)
    cfg = Config.from_env()
    assert cfg.model_fast == ""
    assert cfg.model_strong == ""


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MODEL_FAST", "fast-x")
    monkeypatch.setenv("COPILOT_MODEL_STRONG", "strong-y")
    monkeypatch.setenv("COPILOT_MIN_CONFIDENCE", "0.7")
    monkeypatch.setenv("COPILOT_PERSIST_AUDIO", "1")
    monkeypatch.setenv("COPILOT_DATA_DIR", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.model_fast == "fast-x"
    assert cfg.model_strong == "strong-y"
    assert cfg.min_confidence == 0.7
    assert cfg.persist_audio is True
    assert cfg.db_path == tmp_path / "copilot.db"


def test_persist_audio_defaults_off(monkeypatch):
    monkeypatch.delenv("COPILOT_PERSIST_AUDIO", raising=False)
    assert Config.from_env().persist_audio is False
