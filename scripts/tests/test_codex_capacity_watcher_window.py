"""Exercise real Qt close, reopen, worker and application quit lifecycles."""

import os
from pathlib import Path
import sys
import time
import subprocess

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parents[1]))
pytest.importorskip("PySide6")

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

import codex_capacity_watcher_gui_config as config
import codex_capacity_watcher_gui_window as gui
from codex_capacity_watcher_process import pid_is_running


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    settings = config.default_settings()
    settings.update(
        codex_home=str(tmp_path / "codex"),
        state_file=str(tmp_path / "state.json"),
        interval="0.1", dry_run=True,
    )
    monkeypatch.setattr(gui, "load_settings", lambda: dict(settings))
    monkeypatch.setattr(gui, "load_language", lambda: "en-US")
    monkeypatch.setattr(gui, "save_settings", lambda value: config.save_settings(value, tmp_path / "gui.json"))
    result = gui.CapacityWatcherWindow()
    monkeypatch.setattr(result.tray, "is_available", lambda: True)
    result.show()
    app.processEvents()
    yield result
    result.lifecycle.timer.stop()
    result.external_poll.stop()
    for process in (result.process, result.stop_process):
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()
            process.waitForFinished(3000)
    app.removeEventFilter(result.lifecycle)
    result.tray.icon.hide()
    result.hide()
    result.deleteLater()
    app.processEvents()


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(20)
    assert predicate()


def run_until_quit(app, action):
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(lambda: app.exit(99))
    timeout.start(12000)
    QTimer.singleShot(0, action)
    result = app.exec()
    timeout.stop()
    assert result == 0, "The application did not quit after the exit action"


def start_worker(window):
    window._start()
    wait_for(lambda: window._watcher_pid(window.settings) is not None)
    return int(window.process.processId())


def test_close_leaves_no_minimized_window_and_menu_reopens_it(window, app):
    assert not app.quitOnLastWindowClosed()
    assert window.close() is True
    app.processEvents()
    assert not window.isVisible()
    assert not window.isMinimized()
    assert window.tray.icon.isVisible()
    assert not window.lifecycle.quitting

    window.tray.show_action.trigger()
    assert window.isVisible()
    assert not window.isMinimized()


def test_close_keeps_same_worker_and_quit_from_closed_window_stops_it(window, app):
    pid = start_worker(window)
    assert window.close() is True
    QTest.qWait(200)
    assert not window.isVisible()
    assert not window.isMinimized()
    assert pid_is_running(pid)
    assert int(window.process.processId()) == pid
    assert window.tray.toggle_action.text() == "Stop monitoring"
    run_until_quit(app, window.tray.quit_action.trigger)
    assert not pid_is_running(pid)
    assert not window.tray.icon.isVisible()


@pytest.mark.parametrize("action", ["tray", "application_menu", "native_quit", "close_directly"])
@pytest.mark.parametrize("running", [False, True])
def test_explicit_quit_exits_even_when_window_was_closed(window, app, action, running):
    pid = start_worker(window) if running else None
    window.close()
    if action == "tray":
        trigger = window.tray.quit_action.trigger
    elif action == "application_menu":
        trigger = window.lifecycle.quit_action.trigger
    elif action == "native_quit":
        trigger = app.quit
    else:
        window.tray.restore_window()
        window.close_to_tray.setChecked(False)
        trigger = window.close
    run_until_quit(app, trigger)
    assert window.lifecycle.exiting
    assert not window.tray.icon.isVisible()
    if pid:
        assert not pid_is_running(pid)


def test_no_tray_exits_instead_of_leaving_an_inaccessible_app(window, app, monkeypatch):
    monkeypatch.setattr(window.tray, "is_available", lambda: False)
    run_until_quit(app, window.close)
    assert window.lifecycle.exiting


def test_invalid_form_does_not_block_close_or_quit(window, app, monkeypatch):
    def unexpected_dialog(*args):
        pytest.fail("Closing the app must not open a blocking settings dialog")

    monkeypatch.setattr(QMessageBox, "critical", unexpected_dialog)
    window.codex_home.clear()
    assert window.close() is True
    run_until_quit(app, window.tray.quit_action.trigger)
    assert window.lifecycle.exiting


def test_language_refresh_keeps_menu_actions_bound(window):
    window.language = "zh-CN"
    window._rebuild_ui()
    assert window.tray.quit_action.text() == "退出应用"
    assert window.lifecycle.close_action.text() == "关闭窗口"
    assert window.close_to_tray.text() == "关闭主窗口后继续后台运行"
    assert window.close() is True
    window.tray.show_action.trigger()
    assert window.isVisible()


def test_quit_stops_external_watcher_using_its_original_settings(window, app, tmp_path):
    command = config.worker_command(config.watcher_arguments(window.settings))
    external = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for(lambda: window._watcher_pid(window.settings) is not None)
        window._poll_external_watcher()
        assert window.process is None
        window.state_file.setText(str(tmp_path / "changed" / "state.json"))
        window.close()
        run_until_quit(app, window.tray.quit_action.trigger)
        assert external.wait(timeout=5) == 0
    finally:
        if external.poll() is None:
            external.kill()
        external.wait(timeout=5)


def test_quit_still_stops_owned_worker_when_stop_command_fails(window, app, monkeypatch):
    pid = start_worker(window)
    monkeypatch.setattr(window, "_stop", lambda: None)

    def trigger():
        window._request_quit()
        window.lifecycle.started_at -= 6
        window.lifecycle.poll()

    run_until_quit(app, trigger)
    assert not pid_is_running(pid)


def test_external_stop_timeout_restores_window_for_retry(window, monkeypatch):
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[2]))
    monkeypatch.setattr(window, "_watcher_pid", lambda _settings: 12345)
    monkeypatch.setattr(window, "_stop", lambda: None)
    window.close()
    window._request_quit()
    window.lifecycle.started_at -= 11
    window.lifecycle.poll()
    assert window.isVisible()
    assert not window.lifecycle.quitting
    assert not window.lifecycle.exiting
    assert window.toggle_button.isEnabled()
    assert errors
