"""Keep window closing separate from application and worker shutdown."""

from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, QProcess, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox


class ApplicationLifecycle(QObject):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.app = QApplication.instance()
        self.quitting = False
        self.exiting = False
        self.started_at = 0.0
        self.settings = None
        self.forced = False
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.installEventFilter(self)
        self.menu = window.menuBar().addMenu("")
        self.close_action = QAction(self)
        self.close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.close_action.triggered.connect(window.close)
        self.menu.addAction(self.close_action)
        self.menu.addSeparator()
        self.quit_action = QAction(self)
        self.quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.request_quit)
        self.menu.addAction(self.quit_action)
        self.update_text()

    def update_text(self) -> None:
        self.menu.setTitle(self.window.t("menu.application"))
        self.close_action.setText(self.window.t("menu.close_window"))
        self.quit_action.setText(self.window.t("tray.quit"))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.app and event.type() == QEvent.Type.Quit and not self.exiting:
            event.ignore()
            QTimer.singleShot(0, self.request_quit)
            return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _active(process: QProcess | None) -> bool:
        return process is not None and process.state() != QProcess.ProcessState.NotRunning

    def request_quit(self) -> None:
        if self.quitting or self.exiting:
            return
        self.quitting = True
        self.forced = False
        self.started_at = time.monotonic()
        self.settings = dict(self.window.running_settings or self.window.settings)
        if self.window.running_settings is None and self.window._watcher_pid(self.settings) is not None:
            self.window.running_settings = dict(self.settings)
        self.window._save(quiet=True)
        self.window.toggle_button.setEnabled(False)
        self.window._update_tray()
        self.timer.start()
        if not self._active(self.window.stop_process) and (
            self._active(self.window.process) or self.window._watcher_pid(self.settings) is not None
        ):
            self.window._stop()
        self.poll()

    def poll(self) -> None:
        if not self.quitting:
            return
        worker = self.window.process
        stopper = self.window.stop_process
        external_pid = self.window._watcher_pid(self.settings)
        if not self._active(worker) and not self._active(stopper) and external_pid is None:
            self._finish()
            return
        elapsed = time.monotonic() - self.started_at
        if elapsed >= 5 and not self.forced:
            # Only force processes owned by this GUI; never kill an unrelated PID.
            self.forced = True
            for process in (worker, stopper):
                if self._active(process):
                    process.kill()
        if elapsed >= 10:
            self.timer.stop()
            self.quitting = False
            self.window.toggle_button.setEnabled(True)
            self.window._update_tray()
            self.window.tray.restore_window()
            QMessageBox.critical(
                self.window, self.window.t("dialog.exit"), self.window.t("error.quit_timeout")
            )

    def _finish(self) -> None:
        self.timer.stop()
        self.exiting = True
        self.window.external_poll.stop()
        self.window.tray.icon.hide()
        self.window.hide()
        # A closed/hidden window cannot be relied upon to emit lastWindowClosed.
        self.app.quit()
