#!/usr/bin/env python3
"""Cross-platform desktop launcher for the Codex capacity watcher.

The GUI starts the same watcher module used by the command-line script. When
packaged with PyInstaller, --worker runs that module inside the bundled
executable, so the end user does not need to open a terminal.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    from PySide6.QtCore import QProcess, Qt
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as error:  # Keep the worker mode usable without GUI dependencies.
    QProcess = None  # type: ignore[assignment]
    QT_IMPORT_ERROR: ImportError | None = error
else:
    QT_IMPORT_ERROR = None


APP_TITLE = "Codex Capacity Watcher"
SETTINGS_FILE = Path.home() / ".codex" / "capacity-watcher-gui.json"
SCRIPT_PATH = Path(__file__).with_name("codex_capacity_watcher.py")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_state_file(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    v2 = home / "capacity-watcher-state-v2.json"
    if v2.exists():
        return v2
    return home / "capacity-watcher-state.json"


def default_codex_executable() -> str:
    return shutil.which("codex") or ("codex.exe" if os.name == "nt" else "codex")


def default_settings() -> dict[str, Any]:
    codex_home = default_codex_home()
    state_file = default_state_file(codex_home)
    return {
        "codex_home": str(codex_home),
        "state_file": str(state_file),
        "codex": default_codex_executable(),
        "message": "continue",
        "interval": "2",
        "recover_hours": "6",
        "recover": False,
        "all_sessions": False,
        "include_subagents": False,
        "dry_run": False,
    }


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, Any]:
    settings = default_settings()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if isinstance(value, dict):
        for key in settings:
            if key in value:
                settings[key] = value[key]
    return settings


def save_settings(settings: dict[str, Any], path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _normalise_interval(value: str) -> str:
    interval = float(value)
    if interval <= 0:
        raise ValueError("扫描间隔必须大于 0 秒")
    return f"{interval:g}"


def _normalise_recover_hours(value: str) -> str:
    hours = float(value)
    if hours <= 0:
        raise ValueError("恢复时长必须大于 0 小时")
    return f"{hours:g}"


def watcher_arguments(settings: dict[str, Any], *, stop: bool = False) -> list[str]:
    state_file = _path(str(settings["state_file"]))
    pid_file = state_file.with_name("capacity-watcher.pid")
    args = [
        "--state-file",
        str(state_file),
        "--pid-file",
        str(pid_file),
    ]
    if stop:
        args.insert(0, "--stop")
        return args

    codex_home = _path(str(settings["codex_home"]))
    args[0:0] = ["--codex-home", str(codex_home)]
    args.extend(
        [
            "--codex",
            str(settings["codex"]).strip() or default_codex_executable(),
            "--message",
            str(settings["message"]).strip() or "continue",
            "--interval",
            _normalise_interval(str(settings["interval"])),
        ]
    )
    if bool(settings.get("recover")):
        args.extend(
            [
                "--recover",
                "--recover-hours",
                _normalise_recover_hours(str(settings.get("recover_hours", "6"))),
            ]
        )
    if bool(settings.get("all_sessions")):
        args.append("--all-sessions")
    if bool(settings.get("include_subagents")):
        args.append("--include-subagents")
    if bool(settings.get("dry_run")):
        args.append("--dry-run")
    return args


def _worker_command(arguments: Iterable[str], *, frozen: bool | None = None) -> list[str]:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return [sys.executable, "--worker", *arguments]
    return [sys.executable, str(SCRIPT_PATH), "--worker", *arguments]


if QT_IMPORT_ERROR is None:

    class CapacityWatcherApp(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(APP_TITLE)
            self.setMinimumSize(760, 600)
            self.resize(900, 700)
            self.settings = load_settings()
            self.process: QProcess | None = None
            self.stop_process: QProcess | None = None
            self.running_settings: dict[str, Any] | None = None
            self.close_requested = False

            self.codex_home = QLineEdit(str(self.settings["codex_home"]))
            self.state_file = QLineEdit(str(self.settings["state_file"]))
            self.codex = QLineEdit(str(self.settings["codex"]))
            self.message = QLineEdit(str(self.settings["message"]))
            self.interval = self._double_box(float(self.settings["interval"]), 0.1, 86400.0)
            self.recover_hours = self._double_box(
                float(self.settings.get("recover_hours", "6")), 0.1, 720.0
            )
            self.recover = QCheckBox("启动时恢复历史容量错误")
            self.recover.setChecked(bool(self.settings["recover"]))
            self.all_sessions = QCheckBox("包含 VS Code / exec 会话")
            self.all_sessions.setChecked(bool(self.settings["all_sessions"]))
            self.include_subagents = QCheckBox("包含子代理会话")
            self.include_subagents.setChecked(bool(self.settings["include_subagents"]))
            self.dry_run = QCheckBox("仅预览，不实际发送")
            self.dry_run.setChecked(bool(self.settings["dry_run"]))

            self.start_button = QPushButton("开始监控")
            self.stop_button = QPushButton("停止监控")
            self.save_button = QPushButton("保存设置")
            self.stop_button.setEnabled(False)
            self.start_button.clicked.connect(self._start)
            self.stop_button.clicked.connect(self._stop)
            self.save_button.clicked.connect(self._save)

            self.status = QLabel("已停止")
            self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(2000)

            self._build_ui()
            self._append_log("准备就绪。点击“开始监控”即可运行。")

        @staticmethod
        def _double_box(value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
            box = QDoubleSpinBox()
            box.setRange(minimum, maximum)
            box.setDecimals(2)
            box.setSingleStep(0.5)
            box.setValue(value)
            return box

        def _build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(20, 18, 20, 18)

            heading = QLabel("Codex 容量自动继续")
            heading.setStyleSheet("font-size: 20px; font-weight: 600;")
            layout.addWidget(heading)
            subtitle = QLabel("容量不足时自动向原会话发送 continue。普通启动只监听新事件。")
            subtitle.setStyleSheet("color: #666;")
            layout.addWidget(subtitle)

            paths = QFormLayout()
            paths.setHorizontalSpacing(12)
            paths.setVerticalSpacing(8)
            paths.addRow("Codex 主目录", self._path_widget(self.codex_home, directory=True))
            paths.addRow("状态文件", self._path_widget(self.state_file))
            paths.addRow("Codex 程序", self._path_widget(self.codex, executable=True))
            layout.addLayout(paths)

            options_box = QGroupBox("运行选项")
            options = QGridLayout(options_box)
            options.setHorizontalSpacing(12)
            options.setVerticalSpacing(8)
            options.addWidget(QLabel("发送内容"), 0, 0)
            options.addWidget(self.message, 0, 1)
            options.addWidget(QLabel("扫描间隔（秒）"), 0, 2)
            options.addWidget(self.interval, 0, 3)
            options.addWidget(QLabel("恢复时长（小时）"), 0, 4)
            options.addWidget(self.recover_hours, 0, 5)
            options.addWidget(self.recover, 1, 0, 1, 2)
            options.addWidget(self.all_sessions, 1, 2, 1, 2)
            options.addWidget(self.include_subagents, 2, 0, 1, 2)
            options.addWidget(self.dry_run, 2, 2, 1, 2)
            options.setColumnStretch(1, 1)
            layout.addWidget(options_box)

            controls = QHBoxLayout()
            controls.addWidget(self.start_button)
            controls.addWidget(self.stop_button)
            controls.addWidget(self.save_button)
            controls.addStretch()
            controls.addWidget(self.status)
            layout.addLayout(controls)

            log_box = QGroupBox("运行日志")
            log_layout = QVBoxLayout(log_box)
            log_layout.addWidget(self.log)
            layout.addWidget(log_box, 1)

        def _path_widget(
            self,
            line_edit: QLineEdit,
            *,
            directory: bool = False,
            executable: bool = False,
        ) -> QWidget:
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(line_edit, 1)
            button = QPushButton("选择目录" if directory else "选择程序" if executable else "选择文件")
            if directory:
                button.clicked.connect(lambda: self._choose_directory(line_edit))
            elif executable:
                button.clicked.connect(lambda: self._choose_file(line_edit, executable=True))
            else:
                button.clicked.connect(lambda: self._choose_file(line_edit))
            row.addWidget(button)
            return container

        @staticmethod
        def _choose_directory(line_edit: QLineEdit) -> None:
            selected = QFileDialog.getExistingDirectory(
                None, "选择 Codex 主目录", line_edit.text() or str(Path.home())
            )
            if selected:
                line_edit.setText(selected)

        @staticmethod
        def _choose_file(line_edit: QLineEdit, *, executable: bool = False) -> None:
            initial = line_edit.text() or str(Path.home())
            directory = str(Path(initial).parent)
            if executable:
                selected, _ = QFileDialog.getOpenFileName(None, "选择 Codex 程序", directory)
            else:
                selected, _ = QFileDialog.getSaveFileName(
                    None,
                    "选择状态文件",
                    str(Path(directory) / Path(initial).name),
                    "JSON 文件 (*.json);;所有文件 (*)",
                )
            if selected:
                line_edit.setText(selected)

        def _settings_from_form(self) -> dict[str, Any]:
            codex_home = self.codex_home.text().strip()
            state_file = self.state_file.text().strip()
            if not codex_home:
                raise ValueError("请填写 Codex 主目录")
            if not state_file:
                raise ValueError("请填写状态文件")
            return {
                "codex_home": str(_path(codex_home)),
                "state_file": str(_path(state_file)),
                "codex": self.codex.text().strip() or default_codex_executable(),
                "message": self.message.text().strip() or "continue",
                "interval": _normalise_interval(str(self.interval.value())),
                "recover_hours": _normalise_recover_hours(str(self.recover_hours.value())),
                "recover": self.recover.isChecked(),
                "all_sessions": self.all_sessions.isChecked(),
                "include_subagents": self.include_subagents.isChecked(),
                "dry_run": self.dry_run.isChecked(),
            }

        def _save(self) -> bool:
            try:
                settings = self._settings_from_form()
                save_settings(settings)
            except (OSError, ValueError) as error:
                QMessageBox.critical(self, "设置无效", str(error))
                return False
            self.settings = settings
            self._append_log(f"设置已保存：{SETTINGS_FILE}")
            return True

        def _start(self) -> None:
            if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
                return
            try:
                settings = self._settings_from_form()
                save_settings(settings)
            except (OSError, ValueError) as error:
                QMessageBox.critical(self, "无法启动", str(error))
                return
            self.settings = settings
            self.running_settings = settings
            command = _worker_command(watcher_arguments(settings))
            self._append_log("启动：" + " ".join(self._display_argument(item) for item in command))

            process = QProcess(self)
            process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            process.readyReadStandardOutput.connect(lambda: self._read_output(process))
            process.finished.connect(self._watcher_finished)
            process.errorOccurred.connect(self._watcher_error)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            self.process = process
            process.start()
            if not process.waitForStarted(3000):
                self._append_log(f"启动失败：{process.errorString()}")
                self._reset_watcher_state()
                QMessageBox.critical(self, "无法启动", process.errorString())

        def _stop(self) -> None:
            if self.stop_process and self.stop_process.state() != QProcess.ProcessState.NotRunning:
                return
            settings = self.running_settings or self.settings
            if self.process is None:
                try:
                    settings = self._settings_from_form()
                except ValueError:
                    settings = self.settings
            command = _worker_command(watcher_arguments(settings, stop=True))
            self._append_log("停止监控…")

            process = QProcess(self)
            process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            process.readyReadStandardOutput.connect(lambda: self._read_output(process))
            process.finished.connect(self._stop_finished)
            process.errorOccurred.connect(self._stop_error)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            self.stop_process = process
            process.start()
            if not process.waitForStarted(3000):
                self._append_log(f"停止失败：{process.errorString()}")
                self.stop_process = None

        @staticmethod
        def _read_output(process: QProcess) -> None:
            data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if data:
                window = process.parent()
                if isinstance(window, CapacityWatcherApp):
                    window._append_log(data.rstrip("\n"))

        def _watcher_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
            if self.process is not None:
                self._read_output(self.process)
            self.status.setText("已停止" if exit_code == 0 else f"已退出（代码 {exit_code}）")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.process = None
            self.running_settings = None
            self._maybe_close()

        def _stop_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
            if self.stop_process is not None:
                self._read_output(self.stop_process)
            if exit_code != 0:
                self._append_log(f"停止命令退出代码：{exit_code}")
            self.stop_process = None
            self._maybe_close()

        def _watcher_error(self, _error: QProcess.ProcessError) -> None:
            if self.process is not None:
                self._append_log(f"监控进程错误：{self.process.errorString()}")

        def _stop_error(self, _error: QProcess.ProcessError) -> None:
            if self.stop_process is not None:
                self._append_log(f"停止进程错误：{self.stop_process.errorString()}")

        def _reset_watcher_state(self) -> None:
            self.process = None
            self.running_settings = None
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status.setText("启动失败")

        def _maybe_close(self) -> None:
            if self.close_requested and self.process is None and self.stop_process is None:
                self.close_requested = False
                self._save()
                self.close()

        def _append_log(self, text: str) -> None:
            self.log.appendPlainText(text)

        @staticmethod
        def _display_argument(value: str) -> str:
            return f'"{value}"' if any(char.isspace() for char in value) else value

        def closeEvent(self, event: QCloseEvent) -> None:
            if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
                answer = QMessageBox.question(
                    self,
                    "退出",
                    "监控仍在运行，是否先停止再退出？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
                self.close_requested = True
                self._stop()
                event.ignore()
                return
            if self.stop_process and self.stop_process.state() != QProcess.ProcessState.NotRunning:
                self.close_requested = True
                event.ignore()
                return
            self._save()
            event.accept()


else:
    CapacityWatcherApp = None  # type: ignore[assignment]


def run_gui() -> int:
    if QT_IMPORT_ERROR is not None:
        raise SystemExit(
            "GUI requires PySide6. Install it with: python3 -m pip install PySide6"
        )
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
