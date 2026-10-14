import importlib.util
import json
import os
from types import SimpleNamespace
from pathlib import Path

GUI_PATH = Path(__file__).parents[1] / "codex_capacity_watcher_gui.py"
SPEC = importlib.util.spec_from_file_location("codex_capacity_watcher_gui", GUI_PATH)
gui = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gui)
import codex_capacity_watcher_i18n as i18n


def test_watcher_arguments_include_gui_options(tmp_path):
    settings = gui.default_settings()
    settings.update(
        {
            "codex_home": str(tmp_path / "codex"),
            "state_file": str(tmp_path / "state.json"),
            "codex": "/opt/codex",
            "message": "continue",
            "interval": "0.5",
            "recover_hours": "12",
            "recover": True,
            "all_sessions": True,
            "include_subagents": True,
            "dry_run": True,
        }
    )

    arguments = gui.watcher_arguments(settings)

    assert arguments[:6] == [
        "--codex-home",
        str(tmp_path / "codex"),
        "--state-file",
        str(tmp_path / "state.json"),
        "--pid-file",
        str(tmp_path / "capacity-watcher.pid"),
    ]
    assert arguments[arguments.index("--interval") + 1] == "0.5"
    assert arguments[arguments.index("--recover-hours") + 1] == "12"
    assert all(option in arguments for option in ("--recover", "--session-types", "--include-subagents", "--dry-run"))
    assert arguments[arguments.index("--session-types") + 1] == "cli,vscode,desktop,exec"


def test_watcher_arguments_support_selected_session_types(tmp_path):
    settings = gui.default_settings()
    settings.update(
        {
            "codex_home": str(tmp_path / "codex"),
            "state_file": str(tmp_path / "state.json"),
            "session_types": ["cli", "desktop"],
        }
    )

    arguments = gui.watcher_arguments(settings)

    assert arguments[arguments.index("--session-types") + 1] == "cli,desktop"
    assert "--all-sessions" not in arguments


def test_stop_arguments_only_use_state_and_pid(tmp_path):
    settings = gui.default_settings()
    settings["state_file"] = str(tmp_path / "state.json")

    assert gui.watcher_arguments(settings, stop=True) == [
        "--stop",
        "--state-file",
        str(tmp_path / "state.json"),
        "--pid-file",
        str(tmp_path / "capacity-watcher.pid"),
    ]


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    settings = gui.default_settings()
    settings["interval"] = "3"
    settings["message"] = "continue"

    gui.save_settings(settings, path)

    assert gui.load_settings(path)["interval"] == "3"
    assert gui.load_settings(path)["message"] == "continue"


def test_language_preference_is_stored_separately(tmp_path):
    runtime_path = tmp_path / "settings.json"
    language_path = tmp_path / "language.json"
    settings = gui.default_settings()
    settings["language"] = "en-US"

    gui.save_settings(settings, runtime_path)
    gui.save_language("en-US", language_path)

    assert "language" not in json.loads(runtime_path.read_text(encoding="utf-8"))
    assert gui.load_language(language_path) == "en-US"


def test_runtime_path_includes_codex_parent(tmp_path):
    executable = tmp_path / "node-bin" / "codex"
    path = gui.runtime_path(str(executable))

    assert str(executable.parent) in path.split(os.pathsep)


def test_application_icon_is_available_from_source_tree():
    assert gui.asset_path(gui.APP_ICON_NAME).is_file()


def test_macos_system_language_uses_apple_languages(monkeypatch):
    monkeypatch.setattr(i18n.sys, "platform", "darwin")
    monkeypatch.setattr(
        i18n.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='(\n    "zh-Hans-CN",\n    "en-US",\n)\n',
        ),
    )

    assert i18n.system_language() == "zh-CN"


def test_new_defaults_select_all_session_types():
    settings = gui.default_settings()

    assert settings["session_types"] == list(gui.SESSION_TYPE_KEYS)
    assert settings["close_to_tray"] is True


def test_legacy_settings_migrate_to_session_type_selection(tmp_path):
    path = tmp_path / "legacy-settings.json"
    path.write_text('{"all_sessions": false}\n', encoding="utf-8")

    settings = gui.load_settings(path)

    assert settings["session_types"] == ["cli"]


def test_invalid_interval_is_rejected():
    for value in ("0", "-1", "not-a-number"):
        try:
            gui._normalise_interval(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"interval {value!r} should be rejected")


def test_invalid_recover_hours_is_rejected():
    for value in ("0", "-1", "not-a-number"):
        try:
            gui._normalise_recover_hours(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"recover hours {value!r} should be rejected")


def test_worker_command_supports_source_and_frozen_modes():
    source = gui._worker_command(["--stop"], frozen=False)
    frozen = gui._worker_command(["--stop"], frozen=True)

    assert source[2:] == ["--worker", "--stop"]
    assert frozen[1:] == ["--worker", "--stop"]
