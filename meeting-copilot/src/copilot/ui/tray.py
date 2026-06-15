"""System-tray application shell.

Provides the tray icon and menu (start/pause/stop/purge, toggle overlay,
settings, quit). Keeps the app running in the background with no taskbar
window. Requires PySide6 (``ui`` extra).

Stealth: the only UI surfaces are the tray icon and the local-only overlay;
nothing is shown to other participants and no sounds are played.
"""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from copilot.ai.grounding import GatedSuggestions
from copilot.config import Config
from copilot.core.engine import Engine
from copilot.ui.overlay import SuggestionOverlay
from copilot.ui.settings import SettingsWindow


def _make_icon(color: str) -> QtGui.QIcon:
    pix = QtGui.QPixmap(64, 64)
    pix.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setBrush(QtGui.QColor(color))
    p.setPen(QtCore.Qt.NoPen)
    p.drawEllipse(12, 12, 40, 40)
    p.end()
    return QtGui.QIcon(pix)


class TrayApp(QtCore.QObject):
    """Wires the engine to a tray icon, overlay, and settings window."""

    # Marshal engine callbacks (which fire on worker threads) onto the UI thread.
    _state_signal = QtCore.Signal(str)
    _suggestions_signal = QtCore.Signal(object)
    _error_signal = QtCore.Signal(str)

    def __init__(self, app: QtWidgets.QApplication, config: Config,
                 engine: Optional[Engine] = None) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.engine = engine
        self.overlay = SuggestionOverlay()
        self.settings = SettingsWindow(config)

        self.tray = QtWidgets.QSystemTrayIcon(_make_icon("#888888"))
        self.tray.setToolTip("Meeting Co-pilot (idle)")
        self._build_menu()
        self.tray.show()

        self._state_signal.connect(self._on_state_ui)
        self._suggestions_signal.connect(self._on_suggestions_ui)
        self._error_signal.connect(self._on_error_ui)

        if self.config.consent_reminder:
            self.tray.showMessage(
                "Meeting Co-pilot",
                "Runs locally. Only transcript text is sent to the AI. Ensure "
                "you have consent to record where required.",
                QtWidgets.QSystemTrayIcon.Information,
                5000,
            )

    # -- menu --------------------------------------------------------------
    def _build_menu(self) -> None:
        menu = QtWidgets.QMenu()
        self.act_start = menu.addAction("Start recording", self.start)
        self.act_pause = menu.addAction("Pause", self.toggle_pause)
        self.act_stop = menu.addAction("Stop", self.stop)
        menu.addSeparator()
        menu.addAction("Toggle overlay", self.overlay.toggle)
        menu.addAction("Settings…", self.settings.show)
        menu.addSeparator()
        menu.addAction("Purge all data", self.purge)
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self._sync_actions("stopped")

    def _sync_actions(self, state: str) -> None:
        running = state in ("recording", "paused")
        self.act_start.setEnabled(not running)
        self.act_pause.setEnabled(running)
        self.act_stop.setEnabled(running)
        self.act_pause.setText("Resume" if state == "paused" else "Pause")

    # -- engine wiring -----------------------------------------------------
    def bind_engine(self, engine: Engine) -> None:
        self.engine = engine
        engine.cb.on_state = self._state_signal.emit
        engine.cb.on_suggestions = self._suggestions_signal.emit
        engine.cb.on_error = self._error_signal.emit

    # -- actions -----------------------------------------------------------
    def start(self) -> None:
        if self.engine is None:
            return
        try:
            self.engine.start()
            self.overlay.show()
        except Exception as exc:  # capture unavailable etc.
            self._on_error_ui(str(exc))

    def toggle_pause(self) -> None:
        if self.engine is None:
            return
        if self.engine.is_paused:
            self.engine.resume()
        else:
            self.engine.pause()

    def stop(self) -> None:
        if self.engine is not None:
            self.engine.stop()

    def purge(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            None, "Purge all data",
            "Delete ALL stored transcripts, notes, and embeddings? This cannot "
            "be undone.",
        )
        if confirm == QtWidgets.QMessageBox.Yes and self.engine is not None:
            self.engine.purge()

    def quit(self) -> None:
        if self.engine is not None and self.engine.is_running:
            self.engine.stop()
        self.app.quit()

    # -- UI-thread callbacks ----------------------------------------------
    def _on_state_ui(self, state: str) -> None:
        self.overlay.set_state(state)
        self._sync_actions(state)
        color = {"recording": "#ff5555", "paused": "#ffaa00"}.get(state, "#888888")
        self.tray.setIcon(_make_icon(color))
        self.tray.setToolTip(f"Meeting Co-pilot ({state})")

    def _on_suggestions_ui(self, gated: GatedSuggestions) -> None:
        self.overlay.show_suggestions(gated)

    def _on_error_ui(self, message: str) -> None:
        # Errors are shown locally only (no sound), e.g. capture setup guidance.
        QtWidgets.QMessageBox.information(None, "Meeting Co-pilot", message)
