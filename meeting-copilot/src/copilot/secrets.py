"""Secrets handling.

The Anthropic API key is read from the OS keychain (via ``keyring``) or from
an environment variable as a fallback. It is never hardcoded and never logged.
A redaction helper is provided so callers can scrub secrets from any text that
might otherwise be written to logs.
"""

from __future__ import annotations

import os
import re

SERVICE_NAME = "meeting-copilot"
KEY_USERNAME = "anthropic_api_key"
ENV_VAR = "ANTHROPIC_API_KEY"

# Anthropic keys look like "sk-ant-..."; redact those plus our env var value.
_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")


def get_api_key() -> str | None:
    """Return the Anthropic API key, or ``None`` if not configured.

    Resolution order:
      1. OS keychain (``keyring``), if available.
      2. ``ANTHROPIC_API_KEY`` environment variable.
    """
    try:  # keyring is optional
        import keyring

        value = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
        if value:
            return value
    except Exception:  # pragma: no cover - keyring backend may be absent
        pass

    env = os.environ.get(ENV_VAR)
    return env or None


def set_api_key(value: str) -> bool:
    """Store the API key in the OS keychain. Returns True on success."""
    try:
        import keyring

        keyring.set_password(SERVICE_NAME, KEY_USERNAME, value)
        return True
    except Exception:  # pragma: no cover - depends on platform backend
        return False


def redact(text: str) -> str:
    """Remove any API-key-looking substrings from ``text`` before logging."""
    if not text:
        return text
    redacted = _KEY_PATTERN.sub("sk-ant-***REDACTED***", text)
    live = os.environ.get(ENV_VAR)
    if live:
        redacted = redacted.replace(live, "***REDACTED***")
    return redacted
