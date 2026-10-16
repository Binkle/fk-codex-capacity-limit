"""Path discovery must reuse state and never mistake app caches for sessions."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import codex_capacity_watcher_gui_config as config
import codex_capacity_watcher_paths as paths


@pytest.fixture
def user_home(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def make_home(path, *, sessions=True):
    path.mkdir(parents=True)
    if sessions:
        (path / "sessions").mkdir()
    else:
        (path / "config.toml").write_text("# local configuration\n")
    return path


@pytest.mark.parametrize("environment", [None, "", "  "])
def test_default_home_works_without_a_shell_environment(user_home, monkeypatch, environment):
    if environment is not None:
        monkeypatch.setenv("CODEX_HOME", environment)
    home = make_home(user_home / ".codex")
    found = paths.discover_paths()
    assert found.codex_home == home
    assert found.state_file == home / "capacity-watcher-state.json"
    assert found.has_sessions
    assert not found.state_file.exists()


def test_environment_home_precedes_shared_default(user_home, monkeypatch):
    make_home(user_home / ".codex")
    custom = make_home(user_home / "Custom Codex")
    monkeypatch.setenv("CODEX_HOME", str(custom))
    assert paths.discover_paths().codex_home == custom


def test_environment_path_supports_tilde(monkeypatch):
    monkeypatch.setenv("CODEX_HOME", "~/Custom Codex")
    assert paths.default_codex_home() == Path("~/Custom Codex").expanduser()


def test_initial_settings_find_default_when_environment_path_is_stale(user_home, monkeypatch):
    home = make_home(user_home / ".codex")
    monkeypatch.setenv("CODEX_HOME", str(user_home / "missing"))
    settings = config.default_settings()
    assert settings["codex_home"] == str(home)
    assert settings["state_file"] == str(home / "capacity-watcher-state.json")


def test_empty_saved_paths_use_the_detected_home(user_home, monkeypatch):
    home = make_home(user_home / ".codex")
    monkeypatch.setenv("CODEX_HOME", str(user_home / "missing"))
    settings_path = user_home / "settings.json"
    settings_path.write_text('{"codex_home":"", "state_file":""}')
    settings = config.load_settings(settings_path)
    assert settings["codex_home"] == str(home)
    assert settings["state_file"] == str(home / "capacity-watcher-state.json")


def test_valid_manual_home_and_state_take_precedence(user_home, monkeypatch):
    manual = make_home(user_home / "manual")
    environment = make_home(user_home / "environment")
    monkeypatch.setenv("CODEX_HOME", str(environment))
    state = manual / "capacity-watcher-state.json"
    state.write_text('{"queued":{"already-processed":"timestamp"}}')
    (manual / "capacity-watcher-state-v2.json").write_text("{}")
    original = state.read_bytes()
    found = paths.discover_paths(str(manual), str(state))
    assert found.codex_home == manual
    assert found.state_file == state
    assert state.read_bytes() == original


def test_detect_repairs_stale_default_paths(user_home):
    home = make_home(user_home / ".codex")
    state = home / "capacity-watcher-state-v2.json"
    state.write_text("{}")
    old_home = user_home / "previous-account" / ".codex"
    found = paths.discover_paths(str(old_home), str(old_home / "capacity-watcher-state.json"))
    assert found.codex_home == home
    assert found.state_file == state


@pytest.mark.parametrize("existing", [False, True])
def test_custom_state_path_is_kept_even_before_first_run(user_home, existing):
    home = make_home(user_home / ".codex")
    state = user_home / "custom-state.json"
    if existing:
        state.write_text("{}")
    assert paths.discover_paths(str(home), str(state)).state_file == state


def test_config_only_home_reports_that_sessions_are_not_created(user_home):
    home = make_home(user_home / ".codex", sessions=False)
    found = paths.discover_paths()
    assert found.codex_home == home
    assert not found.has_sessions


def test_chatgpt_local_codex_uses_the_shared_home_not_the_chat_cache(user_home):
    cache = user_home / "Library/Application Support/com.openai.chat"
    cache.mkdir(parents=True)
    (cache / "preferences.json").write_text("{}")
    home = make_home(user_home / ".codex")
    assert paths.discover_paths(str(cache)).codex_home == home


def test_watcher_settings_alone_are_not_a_codex_installation(user_home):
    home = user_home / ".codex"
    home.mkdir()
    (home / "capacity-watcher-gui.json").write_text("{}")
    assert paths.discover_paths() is None
    assert sorted(path.name for path in home.iterdir()) == ["capacity-watcher-gui.json"]


def test_state_directory_is_not_mistaken_for_a_state_file(user_home):
    home = make_home(user_home / ".codex")
    (home / "capacity-watcher-state-v2.json").mkdir()
    assert paths.discover_paths().state_file == home / "capacity-watcher-state.json"


def test_unreadable_candidate_does_not_crash_detection(user_home, monkeypatch):
    home = make_home(user_home / ".codex")
    original = Path.is_file

    def is_file(path):
        if path.name == "capacity-watcher-state-v2.json":
            raise PermissionError("unreadable state path")
        return original(path)

    monkeypatch.setattr(Path, "is_file", is_file)
    found = paths.discover_paths()
    assert found.codex_home == home
    assert not found.state_exists


@pytest.mark.parametrize("saved_state", [None, "", "  "])
def test_missing_saved_state_defaults_to_the_saved_home(user_home, saved_state):
    home = make_home(user_home / "manual")
    state = home / "capacity-watcher-state-v2.json"
    state.write_text("{}")
    settings_path = user_home / "settings.json"
    settings_path.write_text(json.dumps({"codex_home": str(home), "state_file": saved_state}))
    assert config.load_settings(settings_path)["state_file"] == str(state)


def test_loading_keeps_a_nonempty_manual_selection_even_when_unavailable(user_home):
    make_home(user_home / ".codex")
    saved = {"codex_home": str(user_home / "offline-drive"), "state_file": str(user_home / "custom.json")}
    settings_path = user_home / "settings.json"
    settings_path.write_text(json.dumps(saved))
    loaded = config.load_settings(settings_path)
    assert {key: loaded[key] for key in saved} == saved
