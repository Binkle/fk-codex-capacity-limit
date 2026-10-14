#!/usr/bin/env python3
"""Cross-platform launcher for the Codex capacity watcher GUI."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_capacity_watcher_gui_config import (  # noqa: E402
    APP_TITLE,
    LANGUAGE_FILE,
    SCRIPT_PATH,
    SETTINGS_FILE,
    SESSION_TYPE_KEYS,
    default_settings,
    load_settings,
    load_language,
    normalise_interval,
    normalise_lookback_hours,
    normalise_session_types,
    path_value,
    save_settings,
    save_language,
    runtime_path,
    watcher_arguments,
    worker_command,
)

_normalise_interval = normalise_interval
_normalise_recover_hours = normalise_lookback_hours
_normalise_session_types = normalise_session_types
_path = path_value
_worker_command = worker_command

try:
    from PySide6.QtWidgets import QApplication
except ImportError as error:  # Keep worker mode available without GUI dependencies.
    QApplication = None  # type: ignore[assignment]
    QT_IMPORT_ERROR: ImportError | None = error
    CapacityWatcherApp = None  # type: ignore[assignment,misc]
else:
    QT_IMPORT_ERROR = None
    from codex_capacity_watcher_gui_window import CapacityWatcherWindow  # noqa: E402

    CapacityWatcherApp = CapacityWatcherWindow


def run_gui() -> int:
    if QT_IMPORT_ERROR is not None or QApplication is None:
        raise SystemExit("GUI requires PySide6. Install it with: python3 -m pip install PySide6")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")
    window = CapacityWatcherApp()
    window.show()
    return app.exec()


def dispatch(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--worker":
        from codex_capacity_watcher import main as watcher_main

        return watcher_main(arguments[1:])
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(dispatch())
