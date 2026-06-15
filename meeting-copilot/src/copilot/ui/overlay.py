"""Frameless, always-on-top suggestions overlay.

Local-only window that shows grounded suggestions with their citations and a
visible "recording active" indicator. It is configured to:
  * stay on top without stealing focus (never activates),
  * be frameless and translucent,
  * be excluded from screen capture where the OS/Qt supports it, so it does not
    appear in shared screens — supporting the requirement that no one but the
    local operator sees that the tool is running.

Importing this module requires PySide6 (the ``ui`` extra).
"""

from __future__ import annotations

from typing import List

from PySide6 import QtCore, QtGui, QtWidgets

from copilot.ai.grounding import GatedSuggestions
from copilot.core.models import Suggestion


class SuggestionOverlay(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool,
        )
        # Do not steal focus when shown.
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.92)
        self._build()
        self._exclude_from_capture()
        self.resize(360, 220)
        self._move_to_corner()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._indicator = QtWidgets.QLabel("● RECORDING")
        self._indicator.setStyleSheet("color: #ff5555; font-weight: bold;")
        layout.addWidget(self._indicator)

        self._consent = QtWidgets.QLabel(
            "Local capture active. Ensure you have consent to record where required."
        )
        self._consent.setWordWrap(True)
        self._consent.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(self._consent)

        self._list = QtWidgets.QVBoxLayout()
        container = QtWidgets.QWidget()
        container.setLayout(self._list)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(scroll, 1)

        self._empty = QtWidgets.QLabel("No confident suggestion.")
        self._empty.setStyleSheet("color: #888888; font-style: italic;")
        self._list.addWidget(self._empty)

        self.setStyleSheet(
            "SuggestionOverlay { background: rgba(20,20,28,230); border-radius: 10px; }"
            "QLabel { color: #eeeeee; }"
        )

    def _exclude_from_capture(self) -> None:
        """Best-effort: hide the overlay from screen-sharing/capture."""
        try:
            # Qt 6.7+ exposes a screen-capture exclusion hint on some platforms.
            self.setProperty("_q_excludeFromCapture", True)
            handle = self.windowHandle()
            if handle is not None:
                handle.setProperty("_q_excludeFromCapture", True)
        except Exception:
            pass

    def _move_to_corner(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 24, geo.top() + 24)

    # -- updates -----------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state == "recording":
            self._indicator.setText("● RECORDING")
            self._indicator.setStyleSheet("color: #ff5555; font-weight: bold;")
        elif state == "paused":
            self._indicator.setText("❚❚ PAUSED")
            self._indicator.setStyleSheet("color: #ffaa00; font-weight: bold;")
        else:
            self._indicator.setText("■ STOPPED")
            self._indicator.setStyleSheet("color: #888888; font-weight: bold;")

    def _clear(self) -> None:
        while self._list.count():
            item = self._list.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def show_suggestions(self, gated: GatedSuggestions) -> None:
        self._clear()
        if not gated.has_confident:
            label = QtWidgets.QLabel("No confident suggestion.")
            label.setStyleSheet("color: #888888; font-style: italic;")
            self._list.addWidget(label)
            return
        for sug in gated.suggestions:
            self._list.addWidget(self._render_suggestion(sug))

    def _render_suggestion(self, sug: Suggestion) -> QtWidgets.QWidget:
        box = QtWidgets.QFrame()
        box.setStyleSheet("QFrame { background: rgba(40,40,56,200); border-radius: 8px; }")
        v = QtWidgets.QVBoxLayout(box)
        text = QtWidgets.QLabel(sug.text)
        text.setWordWrap(True)
        v.addWidget(text)
        cites = ", ".join(
            f"[{c.start:.0f}-{c.end:.0f}s]" for c in sug.citations
        ) or "(no citation)"
        meta = QtWidgets.QLabel(f"AI proposal · confidence {sug.confidence:.0%} · {cites}")
        meta.setStyleSheet("color: #9aa; font-size: 10px;")
        meta.setWordWrap(True)
        v.addWidget(meta)
        return box

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
