"""Command-line entry point and process lifecycle management."""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path

from codex_capacity_watcher_core import (
    CAPACITY_MESSAGE,
    SESSION_TYPE_CLI,
    SESSION_TYPE_DESKTOP,
    SESSION_TYPE_EXEC,
    SESSION_TYPE_VSCODE,
    SESSION_TYPES,
    CapacityEvent,
    SessionContext,
    _capacity_event,
    _event_age,
    _file_age,
    _file_signature,
    _load_state,
    _record,
    _save_state,
    _session_id,
    _task_completion,
    _terminal_session,
    discover_terminal_cwds,
    discover_rollouts,
    latest_pending_event,
    parse_session_types,
    read_new_events,
    read_session_context,
    session_allowed,
    session_type,
)
from codex_capacity_watcher_engine import CapacityWatcher, queue_message
from codex_capacity_watcher_process import pid_is_running, stop_pid

def _default_pid_file(state_file: Path) -> Path:
    return state_file.with_name("capacity-watcher.pid")

def _read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if value > 0 else None

def _pid_is_running(pid: int) -> bool:
    return pid_is_running(pid)

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
    result = stop_pid(pid)
    if result is None:
        print(f"[watcher] cannot stop PID {pid}", file=sys.stderr, flush=True)
        return None
    if result is False:
        return False
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
        help="监控所有会话类型（兼容旧参数；默认只监控终端 CLI）",
    )
    parser.add_argument(
        "--session-types",
        type=parse_session_types,
        metavar="LIST",
        help="逗号分隔的会话类型：cli、vscode、desktop、exec",
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
        terminal_only=args.session_types is None and not args.all_sessions,
        terminal_cwd_provider=(
            None if args.all_sessions or args.session_types is not None else discover_terminal_cwds
        ),
        session_types=args.session_types,
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
        if args.session_types is not None:
            mode = "selected sessions: " + ",".join(
                session_type_name for session_type_name in SESSION_TYPES if session_type_name in args.session_types
            )
        else:
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
