"""Persistent GUI settings and worker command construction."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from codex_capacity_watcher_i18n import (
    LANGUAGE_ZH,
    normalize_language,
    system_language,
)


APP_TITLE = "Codex Capacity Watcher"
SETTINGS_FILE = Path.home() / ".codex" / "capacity-watcher-gui.json"
SCRIPT_PATH = Path(__file__).with_name("codex_capacity_watcher.py")
SESSION_TYPE_KEYS = ("cli", "vscode", "desktop", "exec")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_state_file(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    v2 = home / "capacity-watcher-state-v2.json"
    return v2 if v2.exists() else home / "capacity-watcher-state.json"


def default_codex_executable() -> str:
    return shutil.which("codex") or ("codex.exe" if os.name == "nt" else "codex")


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
        "language": system_language(),
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
    settings["language"] = normalize_language(settings.get("language", system_language()))
    return settings


def save_settings(settings: dict[str, Any], path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
