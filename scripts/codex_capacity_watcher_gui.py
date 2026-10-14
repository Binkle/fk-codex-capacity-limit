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
        QFrame,
        QGridLayout,
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


APP_STYLESHEET = """
QMainWindow, QWidget#appRoot {
    background: #f5f7fb;
    color: #20283a;
}
QFrame#sidebar {
    background: #ffffff;
    border: 1px solid #e5e8f0;
    border-radius: 18px;
}
QLabel#brandMark {
    background: #5b5de2;
    color: #ffffff;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 700;
}
QLabel#brandTitle {
    color: #1c2435;
    font-size: 15px;
    font-weight: 700;
}
QLabel#brandCaption, QLabel#sideCaption {
    color: #9098aa;
    font-size: 11px;
}
QLabel#eyebrow {
    color: #6265d7;
    font-size: 10px;
    font-weight: 700;
}
QLabel#pageTitle {
    color: #161c2c;
    font-size: 26px;
    font-weight: 700;
}
QLabel#pageSubtitle, QLabel#sectionHint {
    color: #7f889b;
    font-size: 12px;
}
QLabel#sectionTitle {
    color: #20283a;
    font-size: 14px;
    font-weight: 700;
}
QLabel#fieldLabel {
    color: #6f788b;
    font-size: 11px;
    font-weight: 600;
}
QLabel#navItem, QLabel#navItemActive {
    border-radius: 10px;
    padding: 10px 12px;
    color: #687287;
    font-size: 12px;
}
QLabel#navItemActive {
    background: #eef0ff;
    color: #5558c9;
    font-weight: 700;
}
QFrame#sideStatus {
    background: #f8f9fc;
    border: 1px solid #eaecf3;
    border-radius: 12px;
}
QLabel#sideStatusTitle {
    color: #5f687b;
    font-size: 11px;
    font-weight: 700;
}
QLabel#sideStatusValue {
    color: #7f889b;
    font-size: 11px;
}
QFrame#card {
    background: #ffffff;
    border: 1px solid #e5e8f0;
    border-radius: 16px;
}
QLabel#statusPill {
    background: #eef1f5;
    color: #697386;
    border-radius: 10px;
    padding: 6px 11px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#statusPill[state="running"] {
    background: #e8f7ee;
    color: #16834a;
}
QLabel#statusPill[state="error"] {
    background: #fff0f0;
    color: #c04444;
}
QLineEdit, QDoubleSpinBox {
    background: #fafbfe;
    border: 1px solid #dfe3ec;
    border-radius: 9px;
    padding: 7px 10px;
    min-height: 18px;
    color: #273044;
    selection-background-color: #6669dc;
}
QLineEdit:focus, QDoubleSpinBox:focus {
    background: #ffffff;
    border: 1px solid #7a7de4;
}
QPushButton {
    background: #f5f6fa;
    border: 1px solid #e0e3eb;
    border-radius: 9px;
    padding: 8px 13px;
    color: #556075;
    font-size: 12px;
}
QPushButton:hover {
    background: #eef0ff;
    border-color: #cbd0ff;
    color: #5356c7;
}
QPushButton:pressed {
    background: #e1e4fc;
}
QPushButton:disabled {
    background: #f3f4f7;
    border-color: #e9ebf0;
    color: #adb4c2;
}
QPushButton#primaryButton {
    background: #5b5de2;
    border: none;
    color: #ffffff;
    font-weight: 700;
    min-width: 105px;
    padding: 10px 17px;
}
QPushButton#primaryButton:hover {
    background: #4e50cb;
    color: #ffffff;
}
QPushButton#dangerButton {
    background: #fff3f3;
    border-color: #f1caca;
    color: #bd4c4c;
    min-width: 105px;
    padding: 10px 17px;
}
QPushButton#dangerButton:hover {
    background: #ffe8e8;
    border-color: #e8adad;
    color: #a53d3d;
}
QPushButton#quietButton {
    background: transparent;
    border: none;
    color: #697386;
    padding: 5px 7px;
}
QPushButton#quietButton:hover {
    background: #f0f1f8;
    color: #5356c7;
}
QCheckBox {
    spacing: 8px;
    padding: 3px 0;
    color: #626d81;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cfd4df;
    border-radius: 5px;
    background: #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #8588e5;
}
QCheckBox::indicator:checked {
    background: #5b5de2;
    border-color: #5b5de2;
}
QPlainTextEdit {
    background: #171b2c;
    color: #dce1f4;
    border: none;
    border-radius: 11px;
    padding: 10px;
    selection-background-color: #484c78;
}
QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 3px;
}
QScrollBar::handle:vertical {
    background: #c7ccda;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
"""


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
            self.setStyleSheet(APP_STYLESHEET)
            self.setMinimumSize(980, 680)
            self.resize(1120, 760)

            central = QWidget()
            central.setObjectName("appRoot")
            self.setCentralWidget(central)
            layout = QHBoxLayout(central)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(16)

            sidebar = QFrame()
            sidebar.setObjectName("sidebar")
            sidebar.setFixedWidth(214)
            sidebar_layout = QVBoxLayout(sidebar)
            sidebar_layout.setContentsMargins(16, 18, 16, 16)
            sidebar_layout.setSpacing(6)

            brand_row = QHBoxLayout()
            brand_row.setSpacing(10)
            brand_mark = QLabel("CW")
            brand_mark.setObjectName("brandMark")
            brand_mark.setFixedSize(38, 38)
            brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            brand_row.addWidget(brand_mark)
            brand_text = QVBoxLayout()
            brand_text.setSpacing(1)
            brand_title = QLabel("Capacity Watcher")
            brand_title.setObjectName("brandTitle")
            brand_caption = QLabel("本地自动继续工具")
            brand_caption.setObjectName("brandCaption")
            brand_text.addWidget(brand_title)
            brand_text.addWidget(brand_caption)
            brand_row.addLayout(brand_text, 1)
            sidebar_layout.addLayout(brand_row)
            sidebar_layout.addSpacing(26)

            nav_caption = QLabel("工作区")
            nav_caption.setObjectName("eyebrow")
            sidebar_layout.addWidget(nav_caption)
            sidebar_layout.addWidget(self._nav_item("实时监控", active=True))
            sidebar_layout.addWidget(self._nav_item("运行设置"))
            sidebar_layout.addWidget(self._nav_item("使用说明"))
            sidebar_layout.addStretch(1)

            side_status = QFrame()
            side_status.setObjectName("sideStatus")
            side_status_layout = QVBoxLayout(side_status)
            side_status_layout.setContentsMargins(12, 11, 12, 11)
            side_status_layout.setSpacing(4)
            side_status_title = QLabel("本地进程")
            side_status_title.setObjectName("sideStatusTitle")
            self.side_status_value = QLabel("未运行")
            self.side_status_value.setObjectName("sideStatusValue")
            side_status_layout.addWidget(side_status_title)
            side_status_layout.addWidget(self.side_status_value)
            sidebar_layout.addWidget(side_status)
            sidebar_layout.addSpacing(10)
            footer = QLabel("配置保存在本机\n不会上传会话内容")
            footer.setObjectName("sideCaption")
            footer.setWordWrap(True)
            sidebar_layout.addWidget(footer)
            layout.addWidget(sidebar)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(4, 2, 4, 2)
            content_layout.setSpacing(13)

            page_header = QHBoxLayout()
            page_header.setSpacing(10)
            page_heading = QVBoxLayout()
            page_heading.setSpacing(2)
            eyebrow = QLabel("CAPACITY WATCHER")
            eyebrow.setObjectName("eyebrow")
            heading = QLabel("自动继续")
            heading.setObjectName("pageTitle")
            subtitle = QLabel("监听容量限制事件，并把消息发送回原会话。")
            subtitle.setObjectName("pageSubtitle")
            page_heading.addWidget(eyebrow)
            page_heading.addWidget(heading)
            page_heading.addWidget(subtitle)
            page_header.addLayout(page_heading, 1)
            self.status.setObjectName("statusPill")
            self.status.setMinimumWidth(72)
            self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_status("已停止", "idle")
            page_header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop)
            content_layout.addLayout(page_header)

            control_card = self._card()
            control_layout = QVBoxLayout(control_card)
            control_layout.setContentsMargins(17, 15, 17, 15)
            control_layout.setSpacing(11)
            control_header = QHBoxLayout()
            control_title = QLabel("监控控制")
            control_title.setObjectName("sectionTitle")
            control_hint = QLabel("准备好后即可在后台运行")
            control_hint.setObjectName("sectionHint")
            control_header.addWidget(control_title)
            control_header.addSpacing(10)
            control_header.addWidget(control_hint)
            control_header.addStretch(1)
            control_layout.addLayout(control_header)
            controls = QHBoxLayout()
            controls.setSpacing(8)
            self.start_button.setObjectName("primaryButton")
            self.stop_button.setObjectName("dangerButton")
            self.save_button.setObjectName("quietButton")
            controls.addWidget(self.start_button)
            controls.addWidget(self.stop_button)
            controls.addWidget(self.save_button)
            controls.addStretch(1)
            controls_hint = QLabel("普通启动从新事件开始监听；需要补发历史事件时再打开恢复选项。")
            controls_hint.setObjectName("sectionHint")
            controls.addWidget(controls_hint)
            control_layout.addLayout(controls)
            content_layout.addWidget(control_card)

            paths_card = self._card()
            paths_layout = QVBoxLayout(paths_card)
            paths_layout.setContentsMargins(17, 15, 17, 15)
            paths_layout.setSpacing(10)
            paths_header = QHBoxLayout()
            paths_title = QLabel("连接配置")
            paths_title.setObjectName("sectionTitle")
            paths_hint = QLabel("选择 Codex 数据目录和可执行程序")
            paths_hint.setObjectName("sectionHint")
            paths_header.addWidget(paths_title)
            paths_header.addSpacing(10)
            paths_header.addWidget(paths_hint)
            paths_header.addStretch(1)
            paths_layout.addLayout(paths_header)
            paths = QGridLayout()
            paths.setHorizontalSpacing(12)
            paths.setVerticalSpacing(8)
            paths.setColumnMinimumWidth(0, 84)
            paths.setColumnStretch(1, 1)
            paths.addWidget(self._field_label("Codex 主目录"), 0, 0)
            paths.addWidget(self._path_widget(self.codex_home, directory=True), 0, 1)
            paths.addWidget(self._field_label("状态文件"), 1, 0)
            paths.addWidget(self._path_widget(self.state_file), 1, 1)
            paths.addWidget(self._field_label("Codex 程序"), 2, 0)
            paths.addWidget(self._path_widget(self.codex, executable=True), 2, 1)
            paths_layout.addLayout(paths)
            content_layout.addWidget(paths_card)

            options_card = self._card()
            options_layout = QVBoxLayout(options_card)
            options_layout.setContentsMargins(17, 15, 17, 15)
            options_layout.setSpacing(10)
            options_header = QHBoxLayout()
            options_title = QLabel("运行选项")
            options_title.setObjectName("sectionTitle")
            options_hint = QLabel("按需调整发送内容和扫描范围")
            options_hint.setObjectName("sectionHint")
            options_header.addWidget(options_title)
            options_header.addSpacing(10)
            options_header.addWidget(options_hint)
            options_header.addStretch(1)
            options_layout.addLayout(options_header)

            fields = QHBoxLayout()
            fields.setSpacing(10)
            self.message.setPlaceholderText("continue")
            self.interval.setSuffix(" 秒")
            self.recover_hours.setSuffix(" 小时")
            fields.addWidget(self._field_column("发送内容", self.message), 2)
            fields.addWidget(self._field_column("扫描间隔", self.interval), 1)
            fields.addWidget(self._field_column("恢复时长", self.recover_hours), 1)
            options_layout.addLayout(fields)
            checks = QGridLayout()
            checks.setHorizontalSpacing(22)
            checks.setVerticalSpacing(2)
            checks.addWidget(self.recover, 0, 0)
            checks.addWidget(self.all_sessions, 0, 1)
            checks.addWidget(self.include_subagents, 1, 0)
            checks.addWidget(self.dry_run, 1, 1)
            options_layout.addLayout(checks)
            content_layout.addWidget(options_card)

            log_card = self._card()
            log_layout = QVBoxLayout(log_card)
            log_layout.setContentsMargins(17, 15, 17, 15)
            log_layout.setSpacing(9)
            log_header = QHBoxLayout()
            log_title = QLabel("运行日志")
            log_title.setObjectName("sectionTitle")
            log_hint = QLabel("实时显示 watcher 输出")
            log_hint.setObjectName("sectionHint")
            clear_button = QPushButton("清空")
            clear_button.setObjectName("quietButton")
            clear_button.clicked.connect(self.log.clear)
            log_header.addWidget(log_title)
            log_header.addSpacing(10)
            log_header.addWidget(log_hint)
            log_header.addStretch(1)
            log_header.addWidget(clear_button)
            log_layout.addLayout(log_header)
            self.log.setPlaceholderText("启动监控后，运行信息会显示在这里。")
            self.log.setMinimumHeight(150)
            log_layout.addWidget(self.log, 1)
            content_layout.addWidget(log_card, 1)
            layout.addWidget(content, 1)

        @staticmethod
        def _card() -> QFrame:
            card = QFrame()
            card.setObjectName("card")
            return card

        @staticmethod
        def _field_label(text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("fieldLabel")
            return label

        def _field_column(self, label_text: str, widget: QWidget) -> QWidget:
            container = QWidget()
            column = QVBoxLayout(container)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(5)
            column.addWidget(self._field_label(label_text))
            column.addWidget(widget)
            return container

        @staticmethod
        def _nav_item(text: str, *, active: bool = False) -> QLabel:
            label = QLabel(text)
            label.setObjectName("navItemActive" if active else "navItem")
            return label

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
                return
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self._set_status("运行中", "running")

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
                self.stop_button.setEnabled(True)
            else:
                self.stop_button.setEnabled(False)

        @staticmethod
        def _read_output(process: QProcess) -> None:
            data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if data:
                window = process.parent()
                if isinstance(window, CapacityWatcherApp):
                    window._append_log(data.rstrip("\n"))

        def _set_status(self, text: str, state: str) -> None:
            self.status.setText(text)
            self.status.setProperty("state", state)
            style = self.status.style()
            style.unpolish(self.status)
            style.polish(self.status)
            if hasattr(self, "side_status_value"):
                self.side_status_value.setText("运行中" if state == "running" else text)

        def _watcher_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
            if self.process is not None:
                self._read_output(self.process)
            if exit_code == 0:
                self._set_status("已停止", "idle")
            else:
                self._set_status(f"已退出（代码 {exit_code}）", "error")
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
            self._set_status("启动失败", "error")

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
