"""Rollout parsing, session classification, and state storage."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

CAPACITY_MESSAGE = "Selected model is at capacity. Please try a different model"

SESSION_TYPE_CLI = "cli"

SESSION_TYPE_VSCODE = "vscode"

SESSION_TYPE_DESKTOP = "desktop"

SESSION_TYPE_EXEC = "exec"

SESSION_TYPES = (SESSION_TYPE_CLI, SESSION_TYPE_VSCODE, SESSION_TYPE_DESKTOP, SESSION_TYPE_EXEC)

SESSION_ID_PATTERN = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
    re.IGNORECASE,
)

@dataclass(frozen=True)
class SessionContext:
    session_id: str
    cwd: str | None
    thread_source: str | None
    originator: str | None
    source: str | None = None

@dataclass(frozen=True)
class CapacityEvent:
    session_id: str
    turn_id: str
    timestamp: str
    path: Path
    cwd: str | None
    thread_source: str | None
    originator: str | None
    source: str | None = None

    @property
    def key(self) -> str:
        return f"{self.session_id}:{self.turn_id}"

def _record(line: bytes) -> dict | None:
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None

def _session_id(path: Path) -> str | None:
    match = SESSION_ID_PATTERN.search(path.name)
    return match.group(1) if match else None

def read_session_context(path: Path) -> SessionContext | None:
    """Read the small ``session_meta`` record at the start of a rollout."""
    fallback = _session_id(path)
    try:
        with path.open("rb") as stream:
            for _ in range(64):
                record = _record(stream.readline())
                if not record:
                    continue
                payload = record.get("payload") or {}
                if record.get("type") != "session_meta":
                    continue
                return SessionContext(
                    session_id=str(payload.get("session_id") or fallback or ""),
                    cwd=payload.get("cwd"),
                    thread_source=payload.get("thread_source"),
                    originator=payload.get("originator"),
                    source=payload.get("source"),
                )
    except OSError:
        return None
    return SessionContext(fallback or "", None, None, None) if fallback else None

def _capacity_event(record: dict, path: Path, context: SessionContext | None) -> CapacityEvent | None:
    if record.get("type") != "event_msg":
        return None
    payload = record.get("payload") or {}
    if payload.get("type") != "task_complete":
        return None
    error = payload.get("error") or {}
    message = str(error.get("message") or "")
    if CAPACITY_MESSAGE not in message:
        return None
    session_id = str(payload.get("thread_id") or (context.session_id if context else ""))
    turn_id = str(payload.get("turn_id") or payload.get("root_turn_id") or "")
    if not session_id or not turn_id:
        return None
    return CapacityEvent(
        session_id=session_id,
        turn_id=turn_id,
        timestamp=str(record.get("timestamp") or ""),
        path=path,
        cwd=context.cwd if context else None,
        thread_source=context.thread_source if context else None,
        originator=context.originator if context else None,
        source=context.source if context else None,
    )

def _task_completion(record: dict) -> bool:
    return record.get("type") == "event_msg" and (record.get("payload") or {}).get("type") == "task_complete"

def read_new_events(path: Path, offset: int, context: SessionContext | None) -> tuple[int, tuple[CapacityEvent, ...]]:
    """Read complete appended lines and leave a partial final line for retry."""
    try:
        if path.stat().st_size < offset:
            offset = 0
        events: list[CapacityEvent] = []
        with path.open("rb") as stream:
            stream.seek(offset)
            while True:
                line_start = stream.tell()
                line = stream.readline()
                if not line:
                    return stream.tell(), tuple(events)
                if not line.endswith(b"\n"):
                    return line_start, tuple(events)
                record = _record(line)
                if record:
                    event = _capacity_event(record, path, context)
                    if event:
                        events.append(event)
    except OSError:
        return offset, ()

def latest_pending_event(path: Path, max_age: timedelta) -> CapacityEvent | None:
    """Return the latest terminal capacity error for optional startup recovery."""
    context = read_session_context(path)
    latest: CapacityEvent | None = None
    latest_completion = None
    try:
        with path.open("rb") as stream:
            for line in stream:
                record = _record(line)
                if not record or not _task_completion(record):
                    continue
                latest_completion = record
                event = _capacity_event(record, path, context)
                latest = event
    except OSError:
        return None
    if latest is None or latest_completion is None:
        return None
    if _event_age(latest.timestamp) > max_age:
        return None
    return latest

def _event_age(timestamp: str) -> timedelta:
    try:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return max(timedelta(0), datetime.now(timezone.utc) - value.astimezone(timezone.utc))
    except ValueError:
        return timedelta.max

def _file_age(path: Path) -> timedelta:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        return max(timedelta(0), datetime.now(timezone.utc) - modified)
    except OSError:
        return timedelta.max

def discover_rollouts(codex_home: Path) -> Iterable[Path]:
    return sorted(codex_home.joinpath("sessions").glob("**/rollout-*.jsonl"))

def session_type(source: str | None, originator: str | None) -> str | None:
    """Return the user-facing session kind from Codex rollout metadata."""
    originator_key = str(originator or "").strip().lower()
    source_key = str(source or "").strip().lower()
    if originator_key in {"codex-tui", "codex_cli_rs"}:
        return SESSION_TYPE_CLI
    if originator_key in {"codex desktop", "chatgpt desktop"}:
        return SESSION_TYPE_DESKTOP
    if originator_key in {"codex_exec", "codex-exec", "codex exec"}:
        return SESSION_TYPE_EXEC
    if source_key == SESSION_TYPE_EXEC:
        return SESSION_TYPE_EXEC
    if source_key == SESSION_TYPE_VSCODE:
        return SESSION_TYPE_VSCODE
    if source_key == SESSION_TYPE_CLI:
        return SESSION_TYPE_CLI
    return None

def parse_session_types(value: str) -> frozenset[str]:
    selected = frozenset(item.strip().lower() for item in value.split(",") if item.strip())
    unknown = sorted(selected.difference(SESSION_TYPES))
    if unknown:
        choices = ", ".join(SESSION_TYPES)
        raise argparse.ArgumentTypeError(
            f"未知会话类型：{', '.join(unknown)}；可选值：{choices}"
        )
    return selected

def _terminal_session(source: str | None, originator: str | None) -> bool:
    """Keep interactive CLI sessions while excluding editor and exec origins.

    Recent Codex CLI releases create TUI threads through the shared app-server,
    which persists ``source="vscode"`` even though the client is still the
    terminal TUI.  ``originator="codex-tui"`` is the reliable client marker in
    that case, so it takes precedence over the persisted source value.
    """
    if originator in {"codex-tui", "codex_cli_rs"}:
        return True
    if originator is not None:
        return False
    return source in {None, "cli"}

def session_allowed(
    source: str | None,
    originator: str | None,
    selected: frozenset[str],
) -> bool:
    """Check whether a session kind is included by an explicit selection."""
    return session_type(source, originator) in selected

def _file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_size, stat.st_mtime_ns

def discover_terminal_cwds() -> set[str] | None:
    """Return working directories of Codex processes attached to a TTY."""
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,tty=,command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    cwds: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3 or parts[1] in {"??", "-"}:
            continue
        command = parts[2].lower()
        if "codex" not in command or any(
            marker in command for marker in ("app-server", "code-mode-host", "capacity_watcher")
        ):
            continue
        try:
            cwd = subprocess.run(
                ["lsof", "-a", "-p", parts[0], "-d", "cwd", "-Fn"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        for cwd_line in cwd.stdout.splitlines():
            if cwd_line.startswith("n") and len(cwd_line) > 1:
                cwds.add(cwd_line[1:])
    return cwds

def _load_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        value = {}
    return {
        "version": 2,
        "files": value.get("files", {}) if isinstance(value, dict) else {},
        "queued": value.get("queued", {}) if isinstance(value, dict) else {},
    }

def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
