"""Settings window.

Lets the user configure the API key (stored in the OS keychain), model IDs
(which must be verified at docs.claude.com), capture device, confidence
threshold, and privacy options. Requires PySide6 (``ui`` extra).
"""

from __future__ import annotations

from PySide6 import QtWidgets

from copilot import secrets
from copilot.audio import instructions
from copilot.config import Config


class SettingsWindow(QtWidgets.QWidget):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle("Meeting Co-pilot — Settings")
        self.resize(520, 420)
        self._build()

    def _build(self) -> None:
        form = QtWidgets.QFormLayout(self)

        self._api_key = QtWidgets.QLineEdit()
        self._api_key.setEchoMode(QtWidgets.QLineEdit.Password)
        self._api_key.setPlaceholderText("sk-ant-... (stored in OS keychain)")
        form.addRow("Anthropic API key", self._api_key)

        self._model_fast = QtWidgets.QLineEdit(self.config.model_fast)
        self._model_fast.setPlaceholderText("fast model id (verify at docs.claude.com)")
        form.addRow("Fast model (suggestions)", self._model_fast)

        self._model_strong = QtWidgets.QLineEdit(self.config.model_strong)
        self._model_strong.setPlaceholderText("strong model id (verify at docs.claude.com)")
        form.addRow("Strong model (notes)", self._model_strong)

        self._confidence = QtWidgets.QDoubleSpinBox()
        self._confidence.setRange(0.0, 1.0)
        self._confidence.setSingleStep(0.05)
        self._confidence.setValue(self.config.min_confidence)
        form.addRow("Min suggestion confidence", self._confidence)

        self._persist_audio = QtWidgets.QCheckBox(
            "Allow writing raw audio to disk (debug only)"
        )
        self._persist_audio.setChecked(self.config.persist_audio)
        form.addRow("Privacy", self._persist_audio)

        note = QtWidgets.QLabel(
            "Audio is processed locally and never sent to the cloud — only "
            "transcript text is sent to the AI. Model ids change over time; "
            "verify current ids, limits, and pricing at docs.claude.com."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; font-size: 10px;")
        form.addRow(note)

        setup = QtWidgets.QPlainTextEdit()
        setup.setReadOnly(True)
        import sys

        setup.setPlainText(instructions.for_platform(sys.platform))
        setup.setMaximumHeight(120)
        form.addRow("Audio setup", setup)

        save = QtWidgets.QPushButton("Save")
        save.clicked.connect(self._save)
        form.addRow(save)

    def _save(self) -> None:
        key = self._api_key.text().strip()
        if key:
            if not secrets.set_api_key(key):
                QtWidgets.QMessageBox.warning(
                    self, "Keychain unavailable",
                    "Could not store the key in the OS keychain. Set the "
                    "ANTHROPIC_API_KEY environment variable instead.",
                )
            self._api_key.clear()
        self.config.model_fast = self._model_fast.text().strip()
        self.config.model_strong = self._model_strong.text().strip()
        self.config.min_confidence = float(self._confidence.value())
        self.config.persist_audio = bool(self._persist_audio.isChecked())
        self.hide()
