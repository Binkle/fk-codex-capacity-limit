"""System-tray controller for the capacity watcher GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from codex_capacity_watcher_gui_config import APP_ICON_NAME, asset_path


class TrayHost(Protocol):
    def t(self, key: str, **values: Any) -> str: ...

    def _toggle_watcher(self) -> None: ...

    def _request_quit(self) -> None: ...

    def showNormal(self) -> None: ...

    def raise_(self) -> None: ...

    def activateWindow(self) -> None: ...

    def windowIcon(self) -> QIcon: ...


class TrayController:
    """Own the platform tray icon and its small set of quick actions."""

    def __init__(self, host: TrayHost) -> None:
        self.host = host
        self.icon = QSystemTrayIcon(host)  # type: ignore[arg-type]
        icon_path = asset_path(APP_ICON_NAME)
        icon = QIcon(str(icon_path)) if Path(icon_path).is_file() else host.windowIcon()
        self.icon.setIcon(icon)
        self.icon.setToolTip(host.t("tray.tooltip"))
        self.menu = QMenu(host)  # type: ignore[arg-type]
        self.show_action = QAction(host.t("tray.show"), host)  # type: ignore[arg-type]
        self.show_action.triggered.connect(self.restore_window)
        self.menu.addAction(self.show_action)
        self.menu.addSeparator()
        self.toggle_action = QAction(host.t("tray.start"), host)  # type: ignore[arg-type]
        self.toggle_action.triggered.connect(host._toggle_watcher)
        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()
        self.quit_action = QAction(host.t("tray.quit"), host)  # type: ignore[arg-type]
        self.quit_action.triggered.connect(host._request_quit)
        self.menu.addAction(self.quit_action)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        # macOS can report a false availability value while its status item works.
        self.icon.setVisible(True)
        self.icon.show()
        self.update("idle", stop_busy=False)

    def update(self, state: str, *, stop_busy: bool) -> None:
        self.icon.setToolTip(self.host.t("tray.tooltip"))
        self.show_action.setText(self.host.t("tray.show"))
        self.toggle_action.setText(
            self.host.t("tray.stop" if state == "running" else "tray.start")
        )
        self.toggle_action.setEnabled(not stop_busy)
        self.quit_action.setText(self.host.t("tray.quit"))

    def restore_window(self) -> None:
        self.host.showNormal()
        self.host.raise_()
        self.host.activateWindow()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_window()
