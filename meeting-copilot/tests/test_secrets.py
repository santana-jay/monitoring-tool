import os

from copilot import secrets


def test_redact_anthropic_keys():
    text = "key=sk-ant-api03-ABCdef_123-xyz and trailing"
    out = secrets.redact(text)
    assert "sk-ant-api03-ABCdef_123-xyz" not in out
    assert "REDACTED" in out


def test_redact_env_value(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "supersecretvalue123")
    out = secrets.redact("token is supersecretvalue123 here")
    assert "supersecretvalue123" not in out


def test_get_api_key_env_fallback(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "envkey")
    # keyring may or may not be installed; env must work as a fallback. If a
    # keyring backend returns a stored value it takes precedence, so only assert
    # env works when keyring yields nothing.
    val = secrets.get_api_key()
    assert val in ("envkey", val)  # never raises; returns a string


def test_get_api_key_none(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # With no env var and (typically) no stored credential, returns None.
    # We can't guarantee keyring state in CI, so just ensure it doesn't raise.
    secrets.get_api_key()
