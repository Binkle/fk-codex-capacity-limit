"""Locate the shared local Codex home and preserve watcher state paths."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


STATE_NAMES = ("capacity-watcher-state-v2.json", "capacity-watcher-state.json")


@dataclass(frozen=True)
class DetectedPaths:
    codex_home: Path
    state_file: Path
    has_sessions: bool

    @property
    def state_exists(self) -> bool:
        return _is_file(self.state_file)


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except (OSError, ValueError):
        return False


def _expanded(value: str) -> Path | None:
    try:
        return Path(value.strip()).expanduser() if value.strip() else None
    except (RuntimeError, ValueError):
        return None


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME", "").strip()
    return _expanded(configured) or Path.home() / ".codex"


def default_state_file(codex_home: Path | None = None) -> Path:
    home = codex_home if codex_home is not None else default_codex_home()
    for name in STATE_NAMES:
        candidate = home / name
        if _is_file(candidate):
            return candidate
    return home / STATE_NAMES[-1]


def _existing_codex_home(path: Path) -> bool:
    # ChatGPT's local Codex sessions use the same home as the CLI and IDE.
    # An application cache or a watcher settings file alone is not evidence.
    try:
        return path.is_dir() and (
            (path / "sessions").is_dir() or (path / "config.toml").is_file()
        )
    except (OSError, ValueError):
        return False


def _state_for_home(home: Path, previous_home: str, previous_state: str) -> Path:
    if previous_state.strip():
        state = _expanded(previous_state)
        previous = _expanded(previous_home) or home
        if state is None:
            return default_state_file(home)
        # Keep custom paths, including files that will be created on first run.
        custom = state.name not in STATE_NAMES or state.parent != previous
        if custom or (home == previous and _is_file(state)):
            return state
    return default_state_file(home)


def discover_paths(current_home: str = "", current_state: str = "") -> DetectedPaths | None:
    """Check known locations without scanning disks or reading user config contents.

    Existing manual selections take precedence. A stale selection can be repaired
    by the explicit Detect action; simply opening the app never replaces it.
    """
    candidates = []
    preferred = _expanded(current_home)
    if preferred is not None:
        candidates.append(preferred)
    candidates.extend((default_codex_home(), Path.home() / ".codex"))
    for home in dict.fromkeys(candidates):
        if _existing_codex_home(home):
            return DetectedPaths(
                home, _state_for_home(home, current_home, current_state),
                (home / "sessions").is_dir(),
            )
    return None
