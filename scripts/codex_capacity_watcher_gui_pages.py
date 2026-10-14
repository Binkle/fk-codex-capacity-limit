"""View construction for the desktop watcher window."""

from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from codex_capacity_watcher_gui_config import SESSION_TYPE_KEYS
from codex_capacity_watcher_i18n import SUPPORTED_LANGUAGES


class UiHost(Protocol):
    language: str

    def t(self, key: str, **values: Any) -> str: ...

    def _show_page(self, page_index: int) -> None: ...

    def _language_changed(self, index: int) -> None: ...

    def _choose_directory(self, line_edit: QLineEdit) -> None: ...

    def _choose_file(self, line_edit: QLineEdit, *, executable: bool = False) -> None: ...

    def _set_status(self, text: str | None, state: str) -> None: ...


def build_shell(host: UiHost) -> None:
    host.setStyleSheet(host.stylesheet)
    host.setMinimumSize(980, 680)
    host.resize(1120, 760)

    central = QWidget()
    central.setObjectName("appRoot")
    host.setCentralWidget(central)
    root = QHBoxLayout(central)
    root.setContentsMargins(16, 16, 16, 16)
    root.setSpacing(16)
    root.addWidget(build_sidebar(host))

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(4, 2, 4, 2)
    content_layout.setSpacing(13)
    content_layout.addLayout(build_page_header(host))
    host.page_stack = QStackedWidget()
    host.page_stack.setObjectName("pageStack")
    host.page_stack.addWidget(build_monitor_page(host))
    host.page_stack.addWidget(build_settings_page(host))
    host.page_stack.addWidget(build_help_page(host))
    content_layout.addWidget(host.page_stack, 1)
    root.addWidget(content, 1)
    host._show_page(0)


def build_sidebar(host: UiHost) -> QFrame:
    sidebar = QFrame()
    sidebar.setObjectName("sidebar")
    sidebar.setFixedWidth(214)
    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(16, 18, 16, 16)
    layout.setSpacing(6)

    brand_row = QHBoxLayout()
    brand_row.setSpacing(10)
    mark = QLabel("CW")
    mark.setObjectName("brandMark")
    mark.setFixedSize(38, 38)
    mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    brand_row.addWidget(mark)
    brand_text = QVBoxLayout()
    brand_text.setSpacing(1)
    title = QLabel("Capacity Watcher")
    title.setObjectName("brandTitle")
    caption = QLabel(host.t("brand.caption"))
    caption.setObjectName("brandCaption")
    brand_text.addWidget(title)
    brand_text.addWidget(caption)
    brand_row.addLayout(brand_text, 1)
    layout.addLayout(brand_row)
    layout.addSpacing(26)

    workspace = QLabel(host.t("nav.workspace"))
    workspace.setObjectName("eyebrow")
    layout.addWidget(workspace)
    host.nav_buttons = []
    for index, key in enumerate(("nav.monitor", "nav.settings", "nav.help")):
        button = nav_item(host.t(key), active=index == 0)
        button.clicked.connect(lambda _checked=False, page=index: host._show_page(page))
        host.nav_buttons.append(button)
        layout.addWidget(button)
    layout.addStretch(1)

    status_frame = QFrame()
    status_frame.setObjectName("sideStatus")
    status_layout = QVBoxLayout(status_frame)
    status_layout.setContentsMargins(12, 11, 12, 11)
    status_layout.setSpacing(4)
    status_title = QLabel(host.t("side.process"))
    status_title.setObjectName("sideStatusTitle")
    host.side_status_value = QLabel(host.t("side.not_running"))
    host.side_status_value.setObjectName("sideStatusValue")
    status_layout.addWidget(status_title)
    status_layout.addWidget(host.side_status_value)
    layout.addWidget(status_frame)
    layout.addSpacing(10)
    footer = QLabel(host.t("side.footer"))
    footer.setObjectName("sideCaption")
    footer.setWordWrap(True)
    layout.addWidget(footer)
    return sidebar


def build_page_header(host: UiHost) -> QHBoxLayout:
    header = QHBoxLayout()
    header.setSpacing(10)
    heading = QVBoxLayout()
    heading.setSpacing(2)
    eyebrow = QLabel(host.t("page.eyebrow"))
    eyebrow.setObjectName("eyebrow")
    host.page_title = QLabel()
    host.page_title.setObjectName("pageTitle")
    host.page_subtitle = QLabel()
    host.page_subtitle.setObjectName("pageSubtitle")
    heading.addWidget(eyebrow)
    heading.addWidget(host.page_title)
    heading.addWidget(host.page_subtitle)
    header.addLayout(heading, 1)
    language_label = field_label(host.t("field.language"))
    host.language_combo = QComboBox()
    for language in SUPPORTED_LANGUAGES:
        host.language_combo.addItem(host.t(f"language.{language}"), language)
    host.language_combo.setCurrentIndex(SUPPORTED_LANGUAGES.index(host.language))
    host.language_combo.currentIndexChanged.connect(host._language_changed)
    header.addWidget(language_label, 0, Qt.AlignmentFlag.AlignTop)
    header.addWidget(host.language_combo, 0, Qt.AlignmentFlag.AlignTop)
    host.status.setObjectName("statusPill")
    host.status.setMinimumWidth(84)
    host.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    host._set_status(None, "idle")
    header.addWidget(host.status, 0, Qt.AlignmentFlag.AlignTop)
    return header


def build_monitor_page(host: UiHost) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(13)

    control = card()
    control_layout = QVBoxLayout(control)
    control_layout.setContentsMargins(17, 15, 17, 15)
    control_layout.setSpacing(11)
    control_header = QHBoxLayout()
    title = section_title(host.t("monitor.control.title"))
    hint = section_hint(host.t("monitor.control.hint"))
    control_header.addWidget(title)
    control_header.addSpacing(10)
    control_header.addWidget(hint)
    control_header.addStretch(1)
    control_layout.addLayout(control_header)

    controls = QHBoxLayout()
    controls.setSpacing(8)
    controls.addWidget(host.toggle_button)
    controls.addStretch(1)
    note = section_hint(host.t("monitor.control.note"))
    note.setWordWrap(True)
    note.setMinimumWidth(250)
    note.setMaximumWidth(300)
    controls.addWidget(note)
    control_layout.addLayout(controls)
    layout.addWidget(control)

    log_card = card()
    log_layout = QVBoxLayout(log_card)
    log_layout.setContentsMargins(17, 15, 17, 15)
    log_layout.setSpacing(9)
    log_header = QHBoxLayout()
    log_header.addWidget(section_title(host.t("monitor.log.title")))
    log_header.addSpacing(10)
    log_header.addWidget(section_hint(host.t("monitor.log.hint")))
    log_header.addStretch(1)
    clear = QPushButton(host.t("monitor.log.clear"))
    clear.setObjectName("quietButton")
    clear.clicked.connect(host.log.clear)
    log_header.addWidget(clear)
    log_layout.addLayout(log_header)
    host.log.setPlaceholderText(host.t("monitor.log.placeholder"))
    host.log.setMinimumHeight(150)
    log_layout.addWidget(host.log, 1)
    layout.addWidget(log_card, 1)
    return page


def build_settings_page(host: UiHost) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(13)
    layout.addWidget(build_paths_card(host))
    layout.addWidget(build_options_card(host))

    save_card = card()
    save_layout = QHBoxLayout(save_card)
    save_layout.setContentsMargins(17, 13, 17, 13)
    save_hint = section_hint(host.t("settings.save.hint"))
    save_layout.addWidget(save_hint, 1)
    host.save_button.setObjectName("saveButton")
    save_layout.addWidget(host.save_button)
    layout.addWidget(save_card)
    layout.addStretch(1)
    return page


def build_paths_card(host: UiHost) -> QFrame:
    paths_card = card()
    layout = QVBoxLayout(paths_card)
    layout.setContentsMargins(17, 15, 17, 15)
    layout.setSpacing(10)
    header = QHBoxLayout()
    header.addWidget(section_title(host.t("settings.paths.title")))
    header.addSpacing(10)
    header.addWidget(section_hint(host.t("settings.paths.hint")))
    header.addStretch(1)
    layout.addLayout(header)

    fields = QGridLayout()
    fields.setHorizontalSpacing(12)
    fields.setVerticalSpacing(8)
    fields.setColumnMinimumWidth(0, 110)
    fields.setColumnStretch(1, 1)
    fields.addWidget(field_label(host.t("field.codex_home")), 0, 0)
    fields.addWidget(path_widget(host, host.codex_home, directory=True), 0, 1)
    fields.addWidget(field_label(host.t("field.state_file")), 1, 0)
    fields.addWidget(path_widget(host, host.state_file), 1, 1)
    fields.addWidget(field_label(host.t("field.codex")), 2, 0)
    fields.addWidget(path_widget(host, host.codex, executable=True), 2, 1)
    layout.addLayout(fields)
    return paths_card


def build_options_card(host: UiHost) -> QFrame:
    options_card = card()
    layout = QVBoxLayout(options_card)
    layout.setContentsMargins(17, 15, 17, 15)
    layout.setSpacing(10)
    header = QHBoxLayout()
    header.addWidget(section_title(host.t("settings.options.title")))
    header.addSpacing(10)
    header.addWidget(section_hint(host.t("settings.options.hint")))
    header.addStretch(1)
    layout.addLayout(header)

    fields = QHBoxLayout()
    fields.setSpacing(10)
    host.message.setPlaceholderText("continue")
    host.interval.setSuffix(host.t("unit.seconds"))
    host.recover_hours.setSuffix(host.t("unit.hours"))
    fields.addWidget(field_column(host.t("field.message"), host.message), 2)
    fields.addWidget(field_column(host.t("field.interval"), host.interval), 1)
    fields.addWidget(field_column(host.t("field.lookback"), host.recover_hours), 1)
    layout.addLayout(fields)

    layout.addWidget(field_label(host.t("field.session_types")))
    checks = QGridLayout()
    checks.setHorizontalSpacing(22)
    checks.setVerticalSpacing(2)
    for index, key in enumerate(SESSION_TYPE_KEYS):
        checks.addWidget(host.session_checks[key], index // 2, index % 2)
    checks.addWidget(host.recover, 2, 0)
    checks.addWidget(host.include_subagents, 2, 1)
    checks.addWidget(host.dry_run, 3, 0)
    checks.addWidget(host.close_to_tray, 3, 1)
    layout.addLayout(checks)
    return options_card


def build_help_page(host: UiHost) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(13)
    for title_key, body_key in (
        ("help.start.title", "help.start.body"),
        ("help.recover.title", "help.recover.body"),
        ("help.stop.title", "help.stop.body"),
    ):
        layout.addWidget(help_card(host.t(title_key), host.t(body_key)))
    layout.addStretch(1)
    return page


def help_card(title: str, body: str) -> QFrame:
    result = card()
    layout = QVBoxLayout(result)
    layout.setContentsMargins(17, 15, 17, 15)
    layout.setSpacing(7)
    layout.addWidget(section_title(title))
    body_label = QLabel(body)
    body_label.setObjectName("helpBody")
    body_label.setWordWrap(True)
    body_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(body_label)
    return result


def path_widget(host: UiHost, line_edit: QLineEdit, *, directory: bool = False, executable: bool = False) -> QWidget:
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(line_edit, 1)
    key = "choose.directory" if directory else "choose.program" if executable else "choose.file"
    button = QPushButton(host.t(key))
    if directory:
        button.clicked.connect(lambda: host._choose_directory(line_edit))
    elif executable:
        button.clicked.connect(lambda: host._choose_file(line_edit, executable=True))
    else:
        button.clicked.connect(lambda: host._choose_file(line_edit))
    row.addWidget(button)
    return container


def card() -> QFrame:
    result = QFrame()
    result.setObjectName("card")
    return result


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def field_column(label_text: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    layout.addWidget(field_label(label_text))
    layout.addWidget(widget)
    return container


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


def section_hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionHint")
    return label


def nav_item(text: str, *, active: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("navItem")
    button.setCheckable(True)
    button.setChecked(active)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button
