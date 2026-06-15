"""Application configuration.

All settings come from environment variables (optionally loaded from a local
``.env`` file). Nothing sensitive is hardcoded. Model IDs are deliberately
configurable rather than baked into logic, because Anthropic model IDs change
over time and must be verified against https://docs.claude.com at build time.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    """Return an OS-appropriate per-user data directory."""
    override = os.environ.get("COPILOT_DATA_DIR")
    if override:
        return Path(override).expanduser()

    home = Path.home()
    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        return Path(base) / "MeetingCopilot"
    if sys.platform == "darwin":  # macOS
        return home / "Library" / "Application Support" / "MeetingCopilot"
    # Linux / other: respect XDG.
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else home / ".local" / "share"
    return base / "meeting-copilot"


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class Config:
    """Runtime configuration, assembled from the environment."""

    data_dir: Path = field(default_factory=_default_data_dir)
    db_path: Path | None = None

    # Model IDs MUST be supplied by the operator (env/.env) and verified against
    # docs.claude.com. They are intentionally not given memorised defaults.
    model_fast: str = ""
    model_strong: str = ""

    persist_audio: bool = False
    min_confidence: float = 0.55
    hotkey: str = "ctrl+shift+space"
    whisper_model: str = "base"
    consent_reminder: bool = True

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir).expanduser()
        if self.db_path is None:
            self.db_path = self.data_dir / "copilot.db"

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` from environment variables.

        Loads a local ``.env`` if python-dotenv is installed; absence of the
        package is non-fatal so the core stays dependency-light.
        """
        try:  # optional convenience only
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:  # pragma: no cover - dotenv is optional
            pass

        return cls(
            data_dir=_default_data_dir(),
            model_fast=os.environ.get("COPILOT_MODEL_FAST", "").strip(),
            model_strong=os.environ.get("COPILOT_MODEL_STRONG", "").strip(),
            persist_audio=_get_bool("COPILOT_PERSIST_AUDIO", False),
            min_confidence=_get_float("COPILOT_MIN_CONFIDENCE", 0.55),
            hotkey=os.environ.get("COPILOT_HOTKEY", "ctrl+shift+space"),
            whisper_model=os.environ.get("COPILOT_WHISPER_MODEL", "base"),
            consent_reminder=_get_bool("COPILOT_CONSENT_REMINDER", True),
        )

    def ensure_dirs(self) -> None:
        """Create the data directory (private to the current user)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.data_dir, 0o700)
        except OSError:  # pragma: no cover - best effort on non-POSIX
            pass
