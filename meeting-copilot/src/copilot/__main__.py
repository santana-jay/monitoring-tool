"""Entry point: launches the background tray app.

Run with:  meeting-copilot     (or  python -m copilot)

The UI dependencies (PySide6) are required for the tray app; the core library
can be used without them.
"""

from __future__ import annotations

import sys


def main() -> int:
    from copilot.config import Config

    config = Config.from_env()

    try:
        from PySide6 import QtWidgets
    except Exception:
        sys.stderr.write(
            "PySide6 is required for the desktop app. Install with:\n"
            "    pip install 'meeting-copilot[ui]'\n"
        )
        return 1

    from copilot.app import build_engine
    from copilot.ui.hotkeys import HotkeyManager
    from copilot.ui.tray import TrayApp

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # stay alive in the tray

    tray = TrayApp(app, config)
    engine = build_engine(config, callbacks=None)
    tray.bind_engine(engine)

    hotkeys = HotkeyManager(config.hotkey, tray.overlay.toggle)
    hotkeys.start()

    try:
        return app.exec()
    finally:
        hotkeys.stop()
        if engine.is_running:
            engine.stop()


if __name__ == "__main__":
    raise SystemExit(main())
