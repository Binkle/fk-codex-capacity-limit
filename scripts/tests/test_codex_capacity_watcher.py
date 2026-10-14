import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import codex_capacity_watcher as watcher_module  # noqa: E402
from codex_capacity_watcher import (  # noqa: E402
    CapacityEvent,
    CapacityWatcher,
    _acquire_pid_file,
    _parser,
    _release_pid_file,
    queue_message,
    session_allowed,
    session_type,
    stop_watcher,
)


MESSAGE = "Selected model is at capacity. Please try a different model."


def _line(record):
    return (json.dumps(record, ensure_ascii=False) + "\n").encode()


def _meta(session_id, *, thread_source="user", source=None, originator="codex-tui"):
    payload = {
        "session_id": session_id,
        "cwd": "/tmp/codex-watcher-test",
        "thread_source": thread_source,
        "originator": originator,
    }
    if source is not None:
        payload["source"] = source
    return {
        "type": "session_meta",
        "payload": payload,
    }


def _complete(session_id, turn_id, *, error=True):
    payload = {
        "type": "task_complete",
        "thread_id": session_id,
        "turn_id": turn_id,
    }
    if error:
        payload["error"] = {"message": MESSAGE, "codex_error_info": "server_overloaded"}
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "type": "event_msg", "payload": payload}


def _rollout(home, session_id, records):
    path = home / "sessions/2026/10"
    path.mkdir(parents=True)
    target = path / f"rollout-2026-10-13T00-00-00-{session_id}.jsonl"
    target.write_bytes(b"".join(_line(record) for record in records))
    return target


def _watcher(home, state, sent, **kwargs):
    return CapacityWatcher(home, state, lambda event: sent.append(event), **kwargs)


def test_new_capacity_event_is_queued_once(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000001"
    path = _rollout(home, session, [_meta(session)])
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent)

    assert watcher.scan() == 0
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-1")))
    assert watcher.scan() == 1
    assert watcher.scan() == 0
    assert [event.key for event in sent] == [f"{session}:turn-1"]


def test_partial_jsonl_line_is_retried(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000002"
    path = _rollout(home, session, [_meta(session)])
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent)
    watcher.scan()
    raw = _line(_complete(session, "turn-2"))
    with path.open("ab") as stream:
        stream.write(raw[:-1])
    assert watcher.scan() == 0
    with path.open("ab") as stream:
        stream.write(raw[-1:])
    assert watcher.scan() == 1
    assert len(sent) == 1


def test_recover_only_queues_latest_capacity_completion(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000003"
    _rollout(home, session, [_meta(session), _complete(session, "turn-3")])
    sent = []
    watcher = _watcher(
        home,
        tmp_path / "state.json",
        sent,
        recover=True,
    )
    assert watcher.scan() == 1
    assert watcher.scan() == 0
    assert sent[0].turn_id == "turn-3"


def test_recover_does_not_queue_when_latest_completion_succeeded(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000004"
    _rollout(home, session, [_meta(session), _complete(session, "turn-4"), _complete(session, "turn-5", error=False)])
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent, recover=True)
    assert watcher.scan() == 0
    assert sent == []


def test_distinct_capacity_events_are_each_queued_once(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000007"
    path = _rollout(home, session, [_meta(session)])
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent)

    assert watcher.scan() == 0
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-7a")))
    assert watcher.scan() == 1
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-7b")))
    assert watcher.scan() == 1
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-7c", error=False)))
    assert watcher.scan() == 0
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-7d")))
    assert watcher.scan() == 1
    assert [event.turn_id for event in sent] == ["turn-7a", "turn-7b", "turn-7d"]


def test_recover_existing_state_catches_unqueued_latest_event(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000008"
    path = _rollout(home, session, [_meta(session)])
    state = tmp_path / "state.json"
    first_sent = []
    first = _watcher(home, state, first_sent)
    first.scan()
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-8a")))
    assert first.scan() == 1
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-8b")))

    recovered = []
    second = _watcher(home, state, recovered, recover=True)
    assert second.scan() == 1
    assert [event.turn_id for event in recovered] == ["turn-8b"]


def test_restart_skips_events_written_while_stopped_by_default(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000012"
    path = _rollout(home, session, [_meta(session)])
    state = tmp_path / "state.json"

    first = _watcher(home, state, [])
    assert first.scan() == 0
    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-12a")))

    restarted_sent = []
    restarted = _watcher(home, state, restarted_sent)
    assert restarted.scan() == 0
    assert restarted_sent == []

    with path.open("ab") as stream:
        stream.write(_line(_complete(session, "turn-12b")))
    assert restarted.scan() == 1
    assert [event.turn_id for event in restarted_sent] == ["turn-12b"]


def test_subagent_is_ignored_by_default(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000005"
    _rollout(home, session, [_meta(session, thread_source="subagent"), _complete(session, "turn-5")])
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent, recover=True)
    assert watcher.scan() == 0
    assert sent == []


def test_vscode_session_is_ignored_by_default(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000009"
    _rollout(
        home,
        session,
        [_meta(session, source="vscode", originator="Codex Desktop"), _complete(session, "turn-9")],
    )
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent, recover=True)
    assert watcher.scan() == 0
    assert sent == []


def test_cli_tui_with_vscode_source_is_allowed_by_default(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000013"
    _rollout(
        home,
        session,
        [_meta(session, source="vscode", originator="codex-tui"), _complete(session, "turn-13")],
    )
    sent = []
    watcher = _watcher(home, tmp_path / "state.json", sent, recover=True)
    assert watcher.scan() == 1
    assert sent[0].session_id == session


def test_session_types_distinguish_cli_vscode_desktop_and_exec():
    assert session_type("vscode", "codex-tui") == "cli"
    assert session_type("vscode", "Codex Desktop") == "desktop"
    assert session_type("vscode", "Codex VS Code") == "vscode"
    assert session_type("exec", "codex_exec") == "exec"
    assert session_allowed("vscode", "codex-tui", frozenset({"cli"}))
    assert not session_allowed("vscode", "Codex Desktop", frozenset({"cli"}))


def test_all_sessions_can_include_vscode_session(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000010"
    _rollout(home, session, [_meta(session, source="vscode"), _complete(session, "turn-10")])
    sent = []
    watcher = _watcher(
        home,
        tmp_path / "state.json",
        sent,
        recover=True,
        terminal_only=False,
    )
    assert watcher.scan() == 1
    assert sent[0].session_id == session


def test_active_terminal_directory_can_allow_vscode_metadata(tmp_path):
    home = tmp_path / "codex"
    session = "00000000-0000-0000-0000-000000000011"
    _rollout(home, session, [_meta(session, source="vscode"), _complete(session, "turn-11")])
    sent = []
    watcher = _watcher(
        home,
        tmp_path / "state.json",
        sent,
        recover=True,
        terminal_cwd_provider=lambda: {"/tmp/codex-watcher-test"},
    )
    assert watcher.scan() == 1
    assert sent[0].session_id == session


def test_queue_message_targets_the_session_and_sends_continue(tmp_path):
    output = tmp_path / "args.txt"
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$CODEX_WATCHER_ARGS\"\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    event = CapacityEvent(
        session_id="00000000-0000-0000-0000-000000000006",
        turn_id="turn-6",
        timestamp="",
        path=tmp_path / "rollout.jsonl",
        cwd=None,
        thread_source="user",
        originator="codex-tui",
    )
    previous = os.environ.get("CODEX_WATCHER_ARGS")
    os.environ["CODEX_WATCHER_ARGS"] = str(output)
    try:
        queue_message(str(fake_codex), "continue", event)
    finally:
        if previous is None:
            os.environ.pop("CODEX_WATCHER_ARGS", None)
        else:
            os.environ["CODEX_WATCHER_ARGS"] = previous
    assert output.read_text(encoding="utf-8").splitlines() == [
        "queue",
        "--thread",
        event.session_id,
        "--message",
        "continue",
    ]


def test_pid_file_prevents_duplicate_watchers_and_can_be_released(tmp_path):
    pid_file = tmp_path / "capacity-watcher.pid"
    pid = _acquire_pid_file(pid_file)
    try:
        assert int(pid_file.read_text(encoding="utf-8")) == pid
        try:
            _acquire_pid_file(pid_file)
        except RuntimeError as error:
            assert str(pid) in str(error)
        else:
            raise AssertionError("a second watcher should not acquire the PID file")
    finally:
        _release_pid_file(pid_file, pid)
    assert not pid_file.exists()


def test_stop_watcher_removes_stale_pid_file(tmp_path, monkeypatch):
    pid_file = tmp_path / "capacity-watcher.pid"
    pid_file.write_text("999999999\n", encoding="utf-8")
    monkeypatch.setattr(watcher_module, "_discover_watcher_pids", lambda: ())

    assert stop_watcher(pid_file) == 0
    assert not pid_file.exists()


def test_stop_option_and_custom_pid_file_are_parsed(tmp_path):
    pid_file = tmp_path / "custom.pid"

    args = _parser().parse_args(["--stop", "--pid-file", str(pid_file)])

    assert args.stop is True
    assert args.pid_file == pid_file
