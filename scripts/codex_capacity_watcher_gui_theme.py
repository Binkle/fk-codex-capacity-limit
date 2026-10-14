"""Qt stylesheet for the desktop watcher."""

APP_STYLESHEET = """
QMainWindow, QWidget#appRoot {
    background: #f4f7fb;
    color: #1f2937;
}
QFrame#sidebar {
    background: #202a3a;
    border: none;
    border-radius: 18px;
}
QLabel#brandMark {
    background: #2f80ed;
    color: #ffffff;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 700;
}
QLabel#brandTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 700;
}
QLabel#brandCaption, QLabel#sideCaption {
    color: #aab6c9;
    font-size: 11px;
}
QLabel#eyebrow {
    color: #2f80ed;
    font-size: 10px;
    font-weight: 700;
}
QLabel#pageTitle {
    color: #172033;
    font-size: 26px;
    font-weight: 700;
}
QLabel#pageSubtitle, QLabel#sectionHint {
    color: #738096;
    font-size: 12px;
}
QLabel#sectionTitle {
    color: #1f2937;
    font-size: 14px;
    font-weight: 700;
}
QLabel#fieldLabel {
    color: #6f788b;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#navItem {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 10px 12px;
    color: #aeb9ca;
    font-size: 12px;
    text-align: left;
}
QPushButton#navItem:hover {
    background: #2b384c;
    color: #ffffff;
}
QPushButton#navItem:checked {
    background: #2f80ed;
    color: #ffffff;
    font-weight: 700;
}
QFrame#sideStatus {
    background: #293649;
    border: 1px solid #35445a;
    border-radius: 12px;
}
QLabel#sideStatusTitle {
    color: #b7c1d1;
    font-size: 11px;
    font-weight: 700;
}
QLabel#sideStatusValue {
    color: #f3f6fb;
    font-size: 11px;
}
QFrame#card {
    background: #ffffff;
    border: 1px solid #e3e9f2;
    border-radius: 16px;
}
QLabel#statusPill {
    background: #edf2f7;
    color: #5d6b7e;
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
    background: #fbfcfe;
    border: 1px solid #d8e1ec;
    border-radius: 9px;
    padding: 7px 10px;
    min-height: 18px;
    color: #27364a;
    selection-background-color: #2f80ed;
}
QLineEdit:focus, QDoubleSpinBox:focus {
    background: #ffffff;
    border: 1px solid #5595ed;
}
QPushButton {
    background: #f6f8fb;
    border: 1px solid #dce4ee;
    border-radius: 9px;
    padding: 8px 13px;
    color: #536277;
    font-size: 12px;
}
QPushButton:hover {
    background: #edf5ff;
    border-color: #a9c9f4;
    color: #2168c6;
}
QPushButton:pressed {
    background: #dcecff;
}
QPushButton:disabled {
    background: #f3f4f7;
    border-color: #e9ebf0;
    color: #adb4c2;
}
QPushButton#primaryButton {
    background: #2f80ed;
    border: none;
    color: #ffffff;
    font-weight: 700;
    min-width: 105px;
    padding: 10px 17px;
}
QPushButton#primaryButton:hover {
    background: #2168c6;
    color: #ffffff;
}
QPushButton#actionButton {
    background: #2f80ed;
    border: none;
    color: #ffffff;
    font-weight: 700;
    min-width: 130px;
    padding: 10px 17px;
}
QPushButton#actionButton:hover {
    background: #2168c6;
    color: #ffffff;
}
QPushButton#actionButton[state="running"] {
    background: #fff3f3;
    border: 1px solid #f1caca;
    color: #bd4c4c;
}
QPushButton#actionButton[state="running"]:hover {
    background: #ffe8e8;
    border-color: #e8adad;
    color: #a53d3d;
}
QPushButton#actionButton:disabled {
    background: #f3f4f7;
    border-color: #e9ebf0;
    color: #adb4c2;
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
    background: #edf5ff;
    color: #2168c6;
}
QPushButton#saveButton {
    background: #edf5ff;
    border-color: #b8d3f7;
    color: #2168c6;
    font-weight: 700;
    min-width: 88px;
}
QPushButton#saveButton:hover {
    background: #dcecff;
    border-color: #8fb9f0;
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
    border-color: #5997e8;
}
QCheckBox::indicator:checked {
    background: #2f80ed;
    border-color: #2f80ed;
}
QPlainTextEdit {
    background: #172334;
    color: #dce1f4;
    border: none;
    border-radius: 11px;
    padding: 10px;
    selection-background-color: #3e6b9e;
}
QStackedWidget#pageStack {
    background: transparent;
    border: none;
}
QLabel#helpBody {
    color: #64748b;
    font-size: 12px;
    line-height: 1.5;
}
QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 3px;
}
QScrollBar::handle:vertical {
    background: #b8c4d3;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
"""
