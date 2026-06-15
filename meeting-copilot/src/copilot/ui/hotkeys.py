"""Global hotkey support (optional).

Uses ``pynput`` if available to register a system-wide hotkey that toggles the
overlay without stealing focus. Degrades to a no-op if pynput isn't installed.
"""

from __future__ import annotations

from typing import Callable, Optional


class HotkeyManager:
    def __init__(self, hotkey: str, on_activate: Callable[[], None]):
        self.hotkey = hotkey
        self.on_activate = on_activate
        self._listener = None

    def start(self) -> bool:
        """Register the hotkey. Returns True if active, False if unavailable."""
        try:
            from pynput import keyboard
        except Exception:
            return False
        try:
            combo = self._to_pynput(self.hotkey)
            self._listener = keyboard.GlobalHotKeys({combo: self.on_activate})
            self._listener.start()
            return True
        except Exception:
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            finally:
                self._listener = None

    @staticmethod
    def _to_pynput(hotkey: str) -> str:
        """Convert e.g. 'ctrl+shift+space' to pynput's '<ctrl>+<shift>+<space>'."""
        special = {"ctrl", "shift", "alt", "cmd", "super", "space", "tab", "esc"}
        parts = []
        for raw in hotkey.lower().split("+"):
            key = raw.strip()
            if not key:
                continue
            if key in special or len(key) > 1:
                parts.append(f"<{key}>")
            else:
                parts.append(key)
        return "+".join(parts)
