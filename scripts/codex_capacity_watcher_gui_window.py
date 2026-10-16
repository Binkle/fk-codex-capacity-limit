"""Main window orchestration for the capacity watcher GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
)

from codex_capacity_watcher_gui_config import (
    APP_ICON_NAME,
    SETTINGS_FILE,
    SESSION_TYPE_KEYS,
    load_settings,
    load_language,
    normalise_interval,
    normalise_lookback_hours,
    normalise_session_types,
    path_value,
    asset_path,
    runtime_path,
    save_settings,
    save_language,
    watcher_arguments,
    worker_command,
)
from codex_capacity_watcher_i18n import normalize_language, translate
from codex_capacity_watcher_gui_pages import build_shell
from codex_capacity_watcher_gui_theme import APP_STYLESHEET
from codex_capacity_watcher_gui_tray import TrayController
from codex_capacity_watcher_gui_lifecycle import ApplicationLifecycle
from codex_capacity_watcher_process import pid_is_running
from codex_capacity_watcher_paths import discover_paths


class CapacityWatcherWindow(QMainWindow):
    """Coordinate settings, the Qt view, and the long-running worker."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Codex Capacity Watcher")
        icon = asset_path(APP_ICON_NAME)
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self.settings = load_settings()
        self.language = load_language()
        self.stylesheet = APP_STYLESHEET
        self.process: QProcess | None = None
        self.stop_process: QProcess | None = None
        self.running_settings: dict[str, Any] | None = None
        self.tray: TrayController | None = None
        self.lifecycle: ApplicationLifecycle | None = None
        self.current_page = 0
        self.status_error_code: int | None = None
        self.external_poll = QTimer(self)
        self.external_poll.setInterval(1000)
        self.external_poll.timeout.connect(self._poll_external_watcher)
        self._create_controls()
        build_shell(self)
        self.tray = TrayController(self)
        self.lifecycle = ApplicationLifecycle(self)
        self._append_log(self.t("log.ready"))
        self._poll_external_watcher()
        self.external_poll.start()

    def t(self, key: str, **values: Any) -> str:
        return translate(self.language, key, **values)

    def _create_controls(self) -> None:
        self.codex_home = QLineEdit(str(self.settings["codex_home"]))
        self.state_file = QLineEdit(str(self.settings["state_file"]))
        self.codex = QLineEdit(str(self.settings["codex"]))
        self.message = QLineEdit(str(self.settings["message"]))
        self.interval = self._double_box(float(self.settings["interval"]), 0.1, 86400.0)
        self.recover_hours = self._double_box(
            float(self.settings.get("recover_hours", "6")), 0.1, 720.0
        )
        self.recover = QCheckBox(self.t("option.recover"))
        self.recover.setToolTip(self.t("option.recover.tooltip"))
        self.recover.setChecked(bool(self.settings["recover"]))
        selected = set(normalise_session_types(self.settings.get("session_types")))
        self.session_checks = {
            key: QCheckBox(self.t(f"session.{key}")) for key in SESSION_TYPE_KEYS
        }
        for key, checkbox in self.session_checks.items():
            checkbox.setChecked(key in selected)
            checkbox.setToolTip(self.t("session.tooltip", name=self.t(f"session.{key}")))
        self.include_subagents = QCheckBox(self.t("option.subagents"))
        self.include_subagents.setChecked(bool(self.settings["include_subagents"]))
        self.dry_run = QCheckBox(self.t("option.dry_run"))
        self.dry_run.setChecked(bool(self.settings["dry_run"]))
        self.close_to_tray = QCheckBox(self.t("option.close_to_tray"))
        self.close_to_tray.setChecked(bool(self.settings.get("close_to_tray", True)))

        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("actionButton")
        self.toggle_button.clicked.connect(self._toggle_watcher)
        self.save_button = QPushButton(self.t("settings.save"))
        self.save_button.clicked.connect(self._save)
        self.detect_button = QPushButton(self.t("settings.paths.detect"))
        self.detect_button.clicked.connect(self._detect_paths)
        self.status = QLabel()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)

    @staticmethod
    def _double_box(value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(minimum, maximum)
        box.setDecimals(2)
        box.setSingleStep(0.5)
        box.setValue(value)
        return box

    def _show_page(self, page_index: int) -> None:
        if not hasattr(self, "page_stack"):
            return
        self.current_page = page_index
        self.page_stack.setCurrentIndex(page_index)
        keys = (
            ("page.monitor.title", "page.monitor.subtitle"),
            ("page.settings.title", "page.settings.subtitle"),
            ("page.help.title", "page.help.subtitle"),
        )
        title_key, subtitle_key = keys[page_index]
        self.page_title.setText(self.t(title_key))
        self.page_subtitle.setText(self.t(subtitle_key))
        for index, button in enumerate(self.nav_buttons):
            button.setChecked(index == page_index)

    def _language_changed(self, index: int) -> None:
        language = self.language_combo.itemData(index)
        if not language or language == self.language:
            return
        self.language = normalize_language(language)
        try:
            self.settings = self._settings_from_form()
            save_settings(self.settings)
        except (OSError, ValueError):
            pass
        save_language(self.language)
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        page_index = self.current_page
        state = self.status.property("state") or "idle"
        log_text = self.log.toPlainText()
        old_central = self.takeCentralWidget()
        if old_central is not None:
            old_central.deleteLater()
        self._create_controls()
        build_shell(self)
        self.log.setPlainText(log_text)
        self._show_page(page_index)
        self._set_status(None, str(state))

    def _update_tray(self) -> None:
        if self.tray is not None:
            self.tray.update(
                str(self.status.property("state")),
                stop_busy=self.stop_process is not None or bool(self.lifecycle and self.lifecycle.quitting),
            )
        if self.lifecycle is not None:
            self.lifecycle.update_text()

    def _settings_from_form(self) -> dict[str, Any]:
        codex_home = self.codex_home.text().strip()
        state_file = self.state_file.text().strip()
        if not codex_home:
            raise ValueError(self.t("error.codex_home"))
        if not state_file:
            raise ValueError(self.t("error.state_file"))
        session_types = [key for key in SESSION_TYPE_KEYS if self.session_checks[key].isChecked()]
        if not session_types:
            raise ValueError(self.t("error.session_types"))
        try:
            interval = normalise_interval(str(self.interval.value()))
            lookback = normalise_lookback_hours(str(self.recover_hours.value()))
        except ValueError as error:
            message = str(error)
            if "interval" in message:
                raise ValueError(self.t("error.interval")) from error
            raise ValueError(self.t("error.lookback")) from error
        return {
            "codex_home": str(path_value(codex_home)),
            "state_file": str(path_value(state_file)),
            "codex": self.codex.text().strip(),
            "message": self.message.text().strip() or "continue",
            "interval": interval,
            "recover_hours": lookback,
            "recover": self.recover.isChecked(),
            "all_sessions": set(session_types) == set(SESSION_TYPE_KEYS),
            "session_types": session_types,
            "include_subagents": self.include_subagents.isChecked(),
            "dry_run": self.dry_run.isChecked(),
            "close_to_tray": self.close_to_tray.isChecked(),
        }

    def _save(self, *, quiet: bool = False) -> bool:
        try:
            settings = self._settings_from_form()
            save_settings(settings)
        except (OSError, ValueError) as error:
            if quiet:
                self._append_log(self.t("dialog.invalid") + ": " + str(error))
            else:
                QMessageBox.critical(self, self.t("dialog.invalid"), str(error))
            return False
        self.settings = settings
        self._append_log(self.t("log.saved", path=str(SETTINGS_FILE)))
        return True

    def _detect_paths(self) -> None:
        if self.running_settings is not None or self.stop_process is not None:
            return
        found = discover_paths(self.codex_home.text(), self.state_file.text())
        if found is None:
            self.path_detection_hint.setText(self.t("settings.paths.not_found"))
            return
        self.codex_home.setText(str(found.codex_home))
        self.state_file.setText(str(found.state_file))
        state_key = "settings.paths.state_existing" if found.state_exists else "settings.paths.state_new"
        message = self.t("settings.paths.found") + " " + self.t(state_key)
        if not found.has_sessions:
            message += " " + self.t("settings.paths.no_sessions")
        self.path_detection_hint.setText(message)

    def _watcher_pid(self, settings: dict[str, Any]) -> int | None:
        pid_file = path_value(str(settings["state_file"])).with_name("capacity-watcher.pid")
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
        if pid <= 0:
            return None
        if not pid_is_running(pid):
            return None
        return pid

    def _poll_external_watcher(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        settings = self.running_settings or self.settings
        pid = self._watcher_pid(settings)
        if pid is not None:
            self.running_settings = settings
            self.toggle_button.setEnabled(self.stop_process is None)
            if self.status.property("state") != "running":
                self._append_log(self.t("log.detected", pid=pid))
                self._set_status(None, "running")
            return
        if self.stop_process is None and self.status.property("state") == "running":
            self.running_settings = None
            self.toggle_button.setEnabled(True)
            self._set_status(None, "idle")

    def _toggle_watcher(self) -> None:
        if self.lifecycle and self.lifecycle.quitting:
            return
        if self.stop_process and self.stop_process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._stop()
            return
        settings = self.running_settings or self.settings
        if self._watcher_pid(settings) is not None:
            self._stop()
            return
        self._start()

    def _request_quit(self) -> None:
        self.lifecycle.request_quit()

    def _start(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        try:
            settings = self._settings_from_form()
            save_settings(settings)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, self.t("dialog.cannot_start"), str(error))
            return
        self.settings = settings
        existing_pid = self._watcher_pid(settings)
        if existing_pid is not None:
            self.running_settings = settings
            self.toggle_button.setEnabled(True)
            self._append_log(self.t("log.already_running", pid=existing_pid))
            self._set_status(None, "running")
            return
        self.running_settings = settings
        command = worker_command(watcher_arguments(settings))
        self._append_log(self.t("log.starting", command=" ".join(self._display_argument(item) for item in command)))
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self._read_output(process))
        process.finished.connect(self._watcher_finished)
        process.errorOccurred.connect(self._watcher_error)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process_environment = QProcessEnvironment.systemEnvironment()
        process_environment.insert("PATH", runtime_path(str(settings.get("codex", ""))))
        process_environment.insert("CODEX_HOME", str(path_value(str(settings["codex_home"]))))
        process.setProcessEnvironment(process_environment)
        self.process = process
        process.start()
        if not process.waitForStarted(3000):
            self._append_log(self.t("dialog.start_failed") + ": " + process.errorString())
            self._reset_watcher_state()
            QMessageBox.critical(self, self.t("dialog.cannot_start"), process.errorString())
            return
        self.toggle_button.setEnabled(True)
        self._set_status(None, "running")

    def _stop(self) -> None:
        if self.stop_process and self.stop_process.state() != QProcess.ProcessState.NotRunning:
            return
        settings = self.running_settings or self.settings
        if self.process is None and self.running_settings is None:
            try:
                settings = self._settings_from_form()
            except ValueError:
                settings = self.settings
        command = worker_command(watcher_arguments(settings, stop=True))
        self._append_log(self.t("log.stopping"))
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self._read_output(process))
        process.finished.connect(self._stop_finished)
        process.errorOccurred.connect(self._stop_error)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process_environment = QProcessEnvironment.systemEnvironment()
        process_environment.insert("PATH", runtime_path(str(settings.get("codex", ""))))
        process_environment.insert("CODEX_HOME", str(path_value(str(settings["codex_home"]))))
        process.setProcessEnvironment(process_environment)
        self.stop_process = process
        process.start()
        if not process.waitForStarted(3000):
            self._append_log(self.t("log.stop_error", error=process.errorString()))
            self.stop_process = None
            self.toggle_button.setEnabled(True)
        else:
            self.toggle_button.setEnabled(False)
        self._update_tray()

    @staticmethod
    def _read_output(process: QProcess) -> None:
        data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            window = process.parent()
            if isinstance(window, CapacityWatcherWindow):
                window._append_log(data.rstrip("\n"))

    def _set_status(self, text: str | None, state: str) -> None:
        if text is None:
            if state == "running":
                text = self.t("status.running")
            elif state == "idle":
                text = self.t("status.idle")
            else:
                text = self.t("status.exited", code=self.status_error_code or "?")
        self.status.setText(text)
        self.status.setProperty("state", state)
        self.detect_button.setEnabled(state != "running" and self.stop_process is None)
        style = self.status.style()
        style.unpolish(self.status)
        style.polish(self.status)
        if hasattr(self, "side_status_value"):
            self.side_status_value.setText(
                self.t("status.side_running") if state == "running" else text
            )
        if hasattr(self, "toggle_button"):
            key = "button.stop" if state == "running" else "button.start" if state == "idle" else "button.restart"
            tooltip = "tooltip.stop" if state == "running" else "tooltip.start" if state == "idle" else "tooltip.restart"
            self.toggle_button.setText(self.t(key))
            self.toggle_button.setToolTip(self.t(tooltip))
            self.toggle_button.setProperty("state", state)
            button_style = self.toggle_button.style()
            button_style.unpolish(self.toggle_button)
            button_style.polish(self.toggle_button)
        self._update_tray()

    def _watcher_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.process is not None:
            self._read_output(self.process)
        self.status_error_code = None if exit_code == 0 else exit_code
        self._set_status(None, "idle" if exit_code == 0 else "error")
        self.toggle_button.setEnabled(True)
        self.process = None
        self.running_settings = None
        self._update_tray()

    def _stop_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.stop_process is not None:
            self._read_output(self.stop_process)
        if exit_code != 0:
            self._append_log(self.t("log.stop_code", code=exit_code))
        self.stop_process = None
        if self.process is None and exit_code == 0:
            self.running_settings = None
            self.toggle_button.setEnabled(True)
            self._set_status(None, "idle")
        self._update_tray()

    def _watcher_error(self, _error: QProcess.ProcessError) -> None:
        if self.process is not None:
            self._append_log(self.t("log.process_error", error=self.process.errorString()))

    def _stop_error(self, _error: QProcess.ProcessError) -> None:
        if self.stop_process is not None:
            self._append_log(self.t("log.stop_error", error=self.stop_process.errorString()))

    def _reset_watcher_state(self) -> None:
        self.process = None
        self.running_settings = None
        self.toggle_button.setEnabled(True)
        self._set_status(None, "error")

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    @staticmethod
    def _display_argument(value: str) -> str:
        return f'"{value}"' if any(char.isspace() for char in value) else value

    def _choose_directory(self, line_edit: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, self.t("dialog.choose_home"), line_edit.text() or str(Path.home())
        )
        if selected:
            line_edit.setText(selected)

    def _choose_file(self, line_edit: QLineEdit, *, executable: bool = False) -> None:
        initial = line_edit.text() or str(Path.home())
        directory = str(Path(initial).parent)
        if executable:
            selected, _ = QFileDialog.getOpenFileName(self, self.t("dialog.choose_program"), directory)
        else:
            selected, _ = QFileDialog.getSaveFileName(
                self,
                self.t("dialog.choose_state"),
                str(Path(directory) / Path(initial).name),
                self.t("dialog.json_files"),
            )
        if selected:
            line_edit.setText(selected)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.lifecycle.exiting:
            event.accept()
            return
        if self.close_to_tray.isChecked() and self.tray.is_available():
            self._save(quiet=True)
            # Accept the native close event. The application and tray stay alive.
            event.accept()
            return
        event.ignore()
        QTimer.singleShot(0, self._request_quit)
