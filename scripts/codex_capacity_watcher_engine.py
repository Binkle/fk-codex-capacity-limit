"""Capacity event polling and follow-up message delivery."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from codex_capacity_watcher_core import (
    CapacityEvent,
    _file_age,
    _file_signature,
    _load_state,
    _save_state,
    _terminal_session,
    discover_rollouts,
    latest_pending_event,
    read_new_events,
    read_session_context,
    session_allowed,
)

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
        session_types: frozenset[str] | None = None,
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
        self.session_types = session_types
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
        if self.session_types is not None:
            if not session_allowed(event.source, event.originator, self.session_types):
                return 0
        elif self.terminal_only:
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
