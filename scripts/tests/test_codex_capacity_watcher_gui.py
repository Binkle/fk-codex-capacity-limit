import importlib.util
from pathlib import Path

GUI_PATH = Path(__file__).parents[1] / "codex_capacity_watcher_gui.py"
SPEC = importlib.util.spec_from_file_location("codex_capacity_watcher_gui", GUI_PATH)
gui = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gui)


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
    assert all(option in arguments for option in ("--recover", "--all-sessions", "--include-subagents", "--dry-run"))


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
