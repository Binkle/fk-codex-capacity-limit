"""Persistent GUI settings and worker command construction."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from codex_capacity_watcher_i18n import (
    normalize_language,
    system_language,
)


APP_TITLE = "Codex Capacity Watcher"
APP_ICON_NAME = "codex-capacity-watcher-icon.png"
SETTINGS_FILE = Path.home() / ".codex" / "capacity-watcher-gui.json"
LANGUAGE_FILE = Path.home() / ".codex" / "capacity-watcher-language.json"
SCRIPT_PATH = Path(__file__).with_name("codex_capacity_watcher.py")
SESSION_TYPE_KEYS = ("cli", "vscode", "desktop", "exec")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_state_file(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    v2 = home / "capacity-watcher-state-v2.json"
    return v2 if v2.exists() else home / "capacity-watcher-state.json"


def default_codex_executable() -> str:
    found = shutil.which("codex")
    if found:
        return found
    for directory in tool_path_candidates():
        candidate = directory / ("codex.exe" if os.name == "nt" else "codex")
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "codex.exe" if os.name == "nt" else "codex"


def default_settings() -> dict[str, Any]:
    codex_home = default_codex_home()
    return {
        "codex_home": str(codex_home),
        "state_file": str(default_state_file(codex_home)),
        "codex": default_codex_executable(),
        "message": "continue",
        "interval": "2",
        "recover_hours": "6",
        "recover": False,
        "all_sessions": True,
        "session_types": list(SESSION_TYPE_KEYS),
        "include_subagents": False,
        "dry_run": False,
    }


def normalise_session_types(value: Any) -> list[str]:
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = []
    selected = {
        str(item).strip().lower()
        for item in values
        if str(item).strip().lower() in SESSION_TYPE_KEYS
    }
    return [key for key in SESSION_TYPE_KEYS if key in selected]


def load_settings(path: Path | None = None) -> dict[str, Any]:
    settings = default_settings()
    settings_path = path or SETTINGS_FILE
    try:
        value = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if not isinstance(value, dict):
        return settings
    for key in settings:
        if key in value:
            settings[key] = value[key]
    if "session_types" not in value:
        settings["session_types"] = list(SESSION_TYPE_KEYS) if bool(settings["all_sessions"]) else ["cli"]
    settings["session_types"] = normalise_session_types(settings["session_types"])
    settings["all_sessions"] = set(settings["session_types"]) == set(SESSION_TYPE_KEYS)
    return settings


def save_settings(settings: dict[str, Any], path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    runtime_settings = {key: value for key, value in settings.items() if key != "language"}
    path.write_text(json.dumps(runtime_settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_language(path: Path = LANGUAGE_FILE) -> str:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "language" in value:
            return normalize_language(value["language"])
    except (OSError, json.JSONDecodeError):
        pass
    try:
        legacy = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(legacy, dict) and "language" in legacy:
            return normalize_language(legacy["language"])
    except (OSError, json.JSONDecodeError):
        pass
    return system_language()


def save_language(language: str, path: Path = LANGUAGE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"language": normalize_language(language)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def asset_path(name: str) -> Path:
    """Resolve a bundled asset in both source and frozen applications."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    candidates = []
    if frozen_root:
        candidates.append(Path(frozen_root) / "assets" / name)
    source_root = Path(__file__).resolve().parents[1]
    candidates.append(source_root / "packaging" / "assets" / name)
    candidates.append(Path(__file__).resolve().parent / "assets" / name)
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def tool_path_candidates() -> list[Path]:
    home = Path.home()
    candidates = [
        home / ".nvm" / "versions" / "node",
        home / ".volta" / "bin",
        home / ".local" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path("/usr/bin"),
    ]
    result: list[Path] = []
    for candidate in candidates:
        if candidate.name == "node" and candidate.is_dir():
            result.extend(sorted((item / "bin" for item in candidate.iterdir() if item.is_dir()), reverse=True))
        else:
            result.append(candidate)
    if os.name == "nt":
        result.extend(
            [
                Path(os.environ.get("APPDATA", "")) / "npm",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs",
            ]
        )
    return [path for path in result if str(path) and path.is_dir()]


def runtime_path(codex: str | None = None) -> str:
    entries: list[str] = []
    if codex:
        executable = Path(codex).expanduser()
        if executable.parent != Path("."):
            entries.append(str(executable.parent))
    entries.extend(os.environ.get("PATH", "").split(os.pathsep))
    entries.extend(str(path) for path in tool_path_candidates())
    unique = list(dict.fromkeys(entry for entry in entries if entry))
    return os.pathsep.join(unique)


def path_value(value: str) -> Path:
    return Path(value).expanduser()


def normalise_interval(value: str) -> str:
    interval = float(value)
    if interval <= 0:
        raise ValueError("interval must be greater than zero")
    return f"{interval:g}"


def normalise_lookback_hours(value: str) -> str:
    hours = float(value)
    if hours <= 0:
        raise ValueError("look-back window must be greater than zero")
    return f"{hours:g}"


def watcher_arguments(settings: dict[str, Any], *, stop: bool = False) -> list[str]:
    state_file = path_value(str(settings["state_file"]))
    pid_file = state_file.with_name("capacity-watcher.pid")
    args = ["--state-file", str(state_file), "--pid-file", str(pid_file)]
    if stop:
        args.insert(0, "--stop")
        return args

    args[0:0] = ["--codex-home", str(path_value(str(settings["codex_home"]))) ]
    args.extend(
        [
            "--codex",
            str(settings["codex"]).strip() or default_codex_executable(),
            "--message",
            str(settings["message"]).strip() or "continue",
            "--interval",
            normalise_interval(str(settings["interval"])),
        ]
    )
    if bool(settings.get("recover")):
        args.extend(
            [
                "--recover",
                "--recover-hours",
                normalise_lookback_hours(str(settings.get("recover_hours", "6"))),
            ]
        )
    selected = normalise_session_types(settings.get("session_types"))
    if "session_types" in settings:
        args.extend(["--session-types", ",".join(selected)])
    elif bool(settings.get("all_sessions")):
        args.append("--all-sessions")
    if bool(settings.get("include_subagents")):
        args.append("--include-subagents")
    if bool(settings.get("dry_run")):
        args.append("--dry-run")
    return args


def worker_command(arguments: Iterable[str], *, frozen: bool | None = None) -> list[str]:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return [sys.executable, "--worker", *arguments]
    return [sys.executable, str(SCRIPT_PATH), "--worker", *arguments]
