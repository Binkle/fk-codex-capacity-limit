#!/usr/bin/env python3
"""Watch local Codex CLI rollouts and queue ``continue`` after capacity errors.

The watcher reads the append-only JSONL rollout files under ``CODEX_HOME``.
It uses ``codex queue`` to send a follow-up to the exact session, so it does
not depend on which terminal window currently has focus.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable


CAPACITY_MESSAGE = "Selected model is at capacity. Please try a different model"
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


def _terminal_session(source: str | None, originator: str | None) -> bool:
    """Keep interactive CLI sessions while excluding editor and exec origins."""
    if source is not None and source != "cli":
        return False
    return originator in {None, "codex-tui", "codex_cli_rs"}


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


def _default_pid_file(state_file: Path) -> Path:
    return state_file.with_name("capacity-watcher.pid")


def _read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if value > 0 else None


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _acquire_pid_file(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    for _ in range(2):
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            existing = _read_pid(path)
            if existing is not None and _pid_is_running(existing):
                raise RuntimeError(f"watcher is already running with PID {existing}")
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{pid}\n")
        return pid
    raise RuntimeError(f"could not acquire PID file: {path}")


def _release_pid_file(path: Path, pid: int) -> None:
    if _read_pid(path) != pid:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _discover_watcher_pids() -> tuple[int, ...]:
    """Find watcher processes started before PID-file support was added."""
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,comm=,args="],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if result.returncode:
        return ()
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3:
            continue
        try:
            pid = int(parts[0])
            command = shlex.split(parts[2])
        except (ValueError, TypeError):
            continue
        if pid == os.getpid() or not command:
            continue
        executable = Path(command[0]).name.lower()
        if "python" not in executable:
            continue
        if not any(Path(argument).name == "codex_capacity_watcher.py" for argument in command):
            continue
        pids.add(pid)
    return tuple(sorted(pids))


def _send_stop_signal(pid: int) -> bool | None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    except PermissionError as error:
        print(f"[watcher] cannot stop PID {pid}: {error}", file=sys.stderr, flush=True)
        return None
    print(f"[watcher] stop requested for PID {pid}", flush=True)
    return True


def stop_watcher(pid_file: Path) -> int:
    pid = _read_pid(pid_file)
    if pid is None:
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
    else:
        if not _pid_is_running(pid):
            _release_pid_file(pid_file, pid)
            print(f"[watcher] removed stale PID file: {pid_file}", flush=True)
        else:
            result = _send_stop_signal(pid)
            if result is True:
                return 0
            if result is None:
                return 1
            _release_pid_file(pid_file, pid)

    legacy_pids = _discover_watcher_pids()
    if legacy_pids:
        results = [_send_stop_signal(legacy_pid) for legacy_pid in legacy_pids]
        return 1 if any(result is None for result in results) else 0
    if pid is None:
        print(f"[watcher] no running watcher found (PID file: {pid_file})", flush=True)
    return 0


class CapacityWatcher:
    """Poll rollout files and queue one follow-up per failed turn."""

    def __init__(
        self,
        codex_home: Path,
        state_file: Path,
        send: Callable[[CapacityEvent], None],
        *,
        include_subagents: bool = False,
        recover: bool = False,
        recover_age: timedelta = timedelta(hours=6),
        dry_run: bool = False,
        terminal_only: bool = True,
        terminal_cwd_provider: Callable[[], set[str] | None] | None = None,
    ) -> None:
        self.codex_home = codex_home
        self.state_file = state_file
        self.send = send
        self.include_subagents = include_subagents
        self.recover = recover
        self.recover_age = recover_age
        self.dry_run = dry_run
        self.terminal_only = terminal_only
        self.terminal_cwd_provider = terminal_cwd_provider
        self._terminal_cwds: set[str] | None = None
        self.state = _load_state(state_file)
        self._attempted: dict[str, float] = {}
        self._dry_run_seen: set[str] = set()
        self._bootstrapped = bool(self.state["files"])
        self._recovery_checked = not recover
        # A normal restart follows only events written after it starts.  Any
        # bytes appended while the previous process was stopped are history;
        # ``--recover`` is the explicit opt-in for inspecting that history.
        self._startup_synced = not self._bootstrapped or recover

    def scan(self) -> int:
        if self.terminal_cwd_provider:
            self._terminal_cwds = self.terminal_cwd_provider()
        paths = tuple(discover_rollouts(self.codex_home))
        if not self._bootstrapped:
            sent = self._bootstrap(paths)
            self._bootstrapped = True
            self._recovery_checked = True
            self._startup_synced = True
            self._persist_state()
            return sent
        if not self.recover and not self._startup_synced:
            self._sync_to_current_end(paths)
            self._startup_synced = True
            self._persist_state()
            return 0
        sent = 0
        if self.recover and not self._recovery_checked:
            sent += self._recover_existing(paths)
            self._recovery_checked = True
            # Recovery handled history explicitly.  Begin live polling at
            # the current end so the normal scan cannot replay it again.
            self._sync_to_current_end(paths)
            self._startup_synced = True
            self._persist_state()
            return sent
        for path in paths:
            sent += self._scan_path(path)
        self._persist_state()
        return sent

    def _persist_state(self) -> None:
        if not self.dry_run:
            _save_state(self.state_file, self.state)

    def _recover_existing(self, paths: tuple[Path, ...]) -> int:
        sent = 0
        for path in paths:
            if _file_age(path) > self.recover_age:
                continue
            event = latest_pending_event(path, self.recover_age)
            if event:
                sent += self._handle(event)
        return sent

    def _sync_to_current_end(self, paths: tuple[Path, ...]) -> None:
        """Set all discovered rollout offsets to their current end."""
        for path in paths:
            signature = _file_signature(path)
            if signature is None:
                continue
            self.state["files"][str(path)] = {
                "offset": signature[0],
                "size": signature[0],
                "mtime_ns": signature[1],
            }

    def _bootstrap(self, paths: tuple[Path, ...]) -> int:
        sent = 0
        for path in paths:
            key = str(path)
            signature = _file_signature(path)
            if signature is None:
                continue
            if self.recover:
                if _file_age(path) > self.recover_age:
                    self.state["files"][key] = {
                        "offset": signature[0],
                        "size": signature[0],
                        "mtime_ns": signature[1],
                    }
                    continue
                event = latest_pending_event(path, self.recover_age)
                if event:
                    sent += self._handle(event)
                # Recovery inspects history once. Start live watching at the
                # current end so the next poll cannot replay old failures.
                self.state["files"][key] = {
                    "offset": signature[0],
                    "size": signature[0],
                    "mtime_ns": signature[1],
                }
            else:
                self.state["files"][key] = {
                    "offset": signature[0],
                    "size": signature[0],
                    "mtime_ns": signature[1],
                }
        return sent

    def _scan_path(self, path: Path) -> int:
        key = str(path)
        record = self.state["files"].setdefault(key, {"offset": 0})
        signature = _file_signature(path)
        if signature is None:
            return 0
        if (
            record.get("size") == signature[0]
            and record.get("mtime_ns") == signature[1]
        ):
            return 0
        context = read_session_context(path)
        offset, events = read_new_events(path, int(record.get("offset", 0)), context)
        record["offset"] = offset
        record["size"], record["mtime_ns"] = signature
        return sum(self._handle(event) for event in events)

    def _handle(self, event: CapacityEvent) -> int:
        if self.terminal_only:
            if self.terminal_cwd_provider:
                if self._terminal_cwds is not None and event.cwd not in self._terminal_cwds:
                    return 0
            elif not _terminal_session(event.source, event.originator):
                return 0
        if not self.include_subagents and event.thread_source not in {None, "user"}:
            return 0
        if self.dry_run and event.key in self._dry_run_seen:
            return 0
        if not self.dry_run and event.key in self.state["queued"]:
            return 0
        now = time.monotonic()
        if now - self._attempted.get(event.key, 0) < 30:
            return 0
        self._attempted[event.key] = now
        try:
            self.send(event)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"[watcher] queue failed for {event.session_id}: {error}", file=sys.stderr, flush=True)
            return 0
        if self.dry_run:
            self._dry_run_seen.add(event.key)
        else:
            self.state["queued"][event.key] = datetime.now(timezone.utc).isoformat()
        action = "would queue continue" if self.dry_run else "queued continue"
        print(f"[watcher] {action} -> {event.session_id} ({event.cwd or 'unknown cwd'})", flush=True)
        return 1


def queue_message(codex_bin: str, message: str, event: CapacityEvent) -> None:
    result = subprocess.run(
        [codex_bin, "queue", "--thread", event.session_id, "--message", message],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
        raise RuntimeError(detail)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    default_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser.add_argument("--codex-home", type=Path, default=default_home)
    parser.add_argument("--state-file", type=Path, default=default_home / "capacity-watcher-state.json")
    parser.add_argument("--pid-file", type=Path, help="PID file used to start or stop the watcher")
    parser.add_argument("--codex", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--message", default="continue")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--recover", action="store_true", help="启动时恢复最近 6 小时仍停在容量错误的会话")
    parser.add_argument("--recover-hours", type=float, default=6.0)
    parser.add_argument("--include-subagents", action="store_true")
    parser.add_argument(
        "--all-sessions",
        action="store_true",
        help="同时监控 VS Code 和 codex exec 会话（默认只监控终端 CLI）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印，不调用 codex queue")
    parser.add_argument("--once", action="store_true", help="扫描一次后退出")
    parser.add_argument("--stop", action="store_true", help="停止已运行的监控进程")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    pid_file = args.pid_file or _default_pid_file(args.state_file)
    if args.stop:
        if args.once:
            raise SystemExit("--stop 不能与 --once 同时使用")
        return stop_watcher(pid_file)
    if args.interval <= 0 or args.recover_hours <= 0:
        raise SystemExit("--interval 和 --recover-hours 必须大于 0")
    send = (
        (lambda event: print(f"[watcher] dry-run: would queue continue -> {event.session_id}", flush=True))
        if args.dry_run
        else lambda event: queue_message(args.codex, args.message, event)
    )
    watcher = CapacityWatcher(
        args.codex_home,
        args.state_file,
        send,
        include_subagents=args.include_subagents,
        recover=args.recover,
        recover_age=timedelta(hours=args.recover_hours),
        dry_run=args.dry_run,
        terminal_only=not args.all_sessions,
        terminal_cwd_provider=None if args.all_sessions else discover_terminal_cwds,
    )
    if args.once:
        watcher.scan()
        return 0

    try:
        pid = _acquire_pid_file(pid_file)
    except (OSError, RuntimeError) as error:
        print(f"[watcher] cannot start: {error}", file=sys.stderr, flush=True)
        return 1
    stop_requested = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_requested.set()

    signal.signal(signal.SIGTERM, request_stop)
    try:
        mode = "terminal CLI" if not args.all_sessions else "all sessions"
        print(
            f"[watcher] started: {mode}, interval={args.interval:g}s, "
            f"state={args.state_file}, pid={pid}",
            flush=True,
        )
        while not stop_requested.is_set():
            watcher.scan()
            if stop_requested.is_set():
                break
            try:
                stop_requested.wait(args.interval)
            except KeyboardInterrupt:
                print("\n[watcher] stopped", flush=True)
                return 0
        print("[watcher] stopped", flush=True)
        return 0
    finally:
        _release_pid_file(pid_file, pid)


if __name__ == "__main__":
    raise SystemExit(main())
