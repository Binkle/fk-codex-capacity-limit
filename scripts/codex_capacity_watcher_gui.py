#!/usr/bin/env python3
"""Cross-platform desktop launcher for the Codex capacity watcher.

The GUI intentionally starts the same watcher module used by the command-line
script.  When packaged with PyInstaller, ``--worker`` runs that module inside
the bundled executable, so the end user does not need to open a terminal.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Iterable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


APP_TITLE = "Codex Capacity Watcher"
SETTINGS_FILE = Path.home() / ".codex" / "capacity-watcher-gui.json"
SCRIPT_PATH = Path(__file__).with_name("codex_capacity_watcher.py")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_state_file(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    v2 = home / "capacity-watcher-state-v2.json"
    if v2.exists():
        return v2
    return home / "capacity-watcher-state.json"


def default_codex_executable() -> str:
    return shutil.which("codex") or ("codex.exe" if os.name == "nt" else "codex")


def default_settings() -> dict[str, Any]:
    codex_home = default_codex_home()
    state_file = default_state_file(codex_home)
    return {
        "codex_home": str(codex_home),
        "state_file": str(state_file),
        "codex": default_codex_executable(),
        "message": "continue",
        "interval": "2",
        "recover_hours": "6",
        "recover": False,
        "all_sessions": False,
        "include_subagents": False,
        "dry_run": False,
    }


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, Any]:
    settings = default_settings()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if isinstance(value, dict):
        for key in settings:
            if key in value:
                settings[key] = value[key]
    return settings


def save_settings(settings: dict[str, Any], path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _normalise_interval(value: str) -> str:
    interval = float(value)
    if interval <= 0:
        raise ValueError("扫描间隔必须大于 0 秒")
    return f"{interval:g}"


def _normalise_recover_hours(value: str) -> str:
    hours = float(value)
    if hours <= 0:
        raise ValueError("恢复时长必须大于 0 小时")
    return f"{hours:g}"


def watcher_arguments(settings: dict[str, Any], *, stop: bool = False) -> list[str]:
    state_file = _path(str(settings["state_file"]))
    pid_file = state_file.with_name("capacity-watcher.pid")
    args = [
        "--state-file",
        str(state_file),
        "--pid-file",
        str(pid_file),
    ]
    if stop:
        args.insert(0, "--stop")
        return args

    codex_home = _path(str(settings["codex_home"]))
    args[0:0] = ["--codex-home", str(codex_home)]
    args.extend(
        [
            "--codex",
            str(settings["codex"]).strip() or default_codex_executable(),
            "--message",
            str(settings["message"]).strip() or "continue",
            "--interval",
            _normalise_interval(str(settings["interval"])),
        ]
    )
    if bool(settings.get("recover")):
        args.extend(["--recover", "--recover-hours", _normalise_recover_hours(str(settings["recover_hours"]))])
    if bool(settings.get("all_sessions")):
        args.append("--all-sessions")
    if bool(settings.get("include_subagents")):
        args.append("--include-subagents")
    if bool(settings.get("dry_run")):
        args.append("--dry-run")
    return args


def _worker_command(arguments: Iterable[str], *, frozen: bool | None = None) -> list[str]:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return [sys.executable, "--worker", *arguments]
    return [sys.executable, str(SCRIPT_PATH), "--worker", *arguments]


class CapacityWatcherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(720, 560)
        self.root.geometry("820x650")
        self.settings = load_settings()
        self.process: subprocess.Popen[str] | None = None
        self.stop_process: subprocess.Popen[str] | None = None
        self.running_settings: dict[str, Any] | None = None
        self.close_requested = False
        self.output_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.codex_home = tk.StringVar(value=str(self.settings["codex_home"]))
        self.state_file = tk.StringVar(value=str(self.settings["state_file"]))
        self.codex = tk.StringVar(value=str(self.settings["codex"]))
        self.message = tk.StringVar(value=str(self.settings["message"]))
        self.interval = tk.StringVar(value=str(self.settings["interval"]))
        self.recover_hours = tk.StringVar(value=str(self.settings["recover_hours"]))
        self.recover = tk.BooleanVar(value=bool(self.settings["recover"]))
        self.all_sessions = tk.BooleanVar(value=bool(self.settings["all_sessions"]))
        self.include_subagents = tk.BooleanVar(value=bool(self.settings["include_subagents"]))
        self.dry_run = tk.BooleanVar(value=bool(self.settings["dry_run"]))
        self.status = tk.StringVar(value="已停止")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(100, self._drain_output)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(6, weight=1)

        heading = ttk.Label(outer, text="Codex 容量自动继续", font=("TkDefaultFont", 16, "bold"))
        heading.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        subtitle = ttk.Label(
            outer,
            text="容量不足时自动向原会话发送 continue。普通启动只监听新事件。",
            foreground="#555555",
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        self._path_row(outer, 2, "Codex 主目录", self.codex_home, directory=True)
        self._path_row(outer, 3, "状态文件", self.state_file, directory=False)
        self._path_row(outer, 4, "Codex 程序", self.codex, directory=False, executable=True)

        options = ttk.Frame(outer)
        options.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="发送内容").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(options, textvariable=self.message, width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(options, text="扫描间隔（秒）").grid(row=0, column=2, sticky="w", padx=(20, 8))
        ttk.Entry(options, textvariable=self.interval, width=8).grid(row=0, column=3, sticky="w")
        ttk.Label(options, text="恢复时长（小时）").grid(row=0, column=4, sticky="w", padx=(20, 8))
        ttk.Entry(options, textvariable=self.recover_hours, width=8).grid(row=0, column=5, sticky="w")
        ttk.Checkbutton(options, text="启动时恢复历史容量错误", variable=self.recover).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(options, text="包含 VS Code / exec 会话", variable=self.all_sessions).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(options, text="包含子代理会话", variable=self.include_subagents).grid(
            row=2, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(options, text="仅预览，不实际发送", variable=self.dry_run).grid(
            row=2, column=2, columnspan=2, sticky="w"
        )

        controls = ttk.Frame(outer)
        controls.grid(row=6, column=0, columnspan=3, sticky="new", pady=(4, 8))
        self.start_button = ttk.Button(controls, text="开始监控", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="停止监控", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="保存设置", command=self._save).pack(side="left", padx=(8, 0))
        ttk.Label(controls, textvariable=self.status).pack(side="right")

        log_frame = ttk.LabelFrame(outer, text="运行日志", padding=6)
        log_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        outer.rowconfigure(7, weight=1)
        self.log = ScrolledText(log_frame, height=15, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)
        self._append_log("准备就绪。点击“开始监控”即可运行。")

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        directory: bool,
        executable: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
        if directory:
            command = lambda: self._choose_directory(variable)
            button_text = "选择目录"
        elif executable:
            command = lambda: self._choose_file(variable, executable=True)
            button_text = "选择程序"
        else:
            command = lambda: self._choose_file(variable)
            button_text = "选择文件"
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, pady=4, padx=(8, 0))

    def _choose_directory(self, variable: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=variable.get() or str(Path.home()))
        if selected:
            variable.set(selected)

    def _choose_file(self, variable: tk.StringVar, *, executable: bool = False) -> None:
        initial = variable.get() or str(Path.home())
        if executable:
            selected = filedialog.askopenfilename(initialdir=str(Path(initial).parent))
        else:
            selected = filedialog.asksaveasfilename(
                initialdir=str(Path(initial).parent),
                initialfile=Path(initial).name,
                defaultextension=".json",
                filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            )
        if selected:
            variable.set(selected)

    def _settings_from_form(self) -> dict[str, Any]:
        codex_home_value = self.codex_home.get().strip()
        state_file_value = self.state_file.get().strip()
        if not codex_home_value:
            raise ValueError("请填写 Codex 主目录")
        if not state_file_value:
            raise ValueError("请填写状态文件")
        settings = {
            "codex_home": str(_path(codex_home_value)),
            "state_file": str(_path(state_file_value)),
            "codex": self.codex.get().strip() or default_codex_executable(),
            "message": self.message.get().strip() or "continue",
            "interval": _normalise_interval(self.interval.get().strip()),
            "recover_hours": _normalise_recover_hours(self.recover_hours.get().strip()),
            "recover": self.recover.get(),
            "all_sessions": self.all_sessions.get(),
            "include_subagents": self.include_subagents.get(),
            "dry_run": self.dry_run.get(),
        }
        return settings

    def _save(self) -> bool:
        try:
            settings = self._settings_from_form()
            save_settings(settings)
        except (OSError, ValueError) as error:
            messagebox.showerror("设置无效", str(error), parent=self.root)
            return False
        self.settings = settings
        self._append_log(f"设置已保存：{SETTINGS_FILE}")
        return True

    def _start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            settings = self._settings_from_form()
            save_settings(settings)
        except (OSError, ValueError) as error:
            messagebox.showerror("无法启动", str(error), parent=self.root)
            return
        self.settings = settings
        self.running_settings = settings
        arguments = watcher_arguments(settings)
        command = _worker_command(arguments)
        self._append_log("启动：" + " ".join(self._display_argument(item) for item in command))
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except (OSError, ValueError) as error:
            self.process = None
            self.status.set("启动失败")
            self._append_log(f"启动失败：{error}")
            messagebox.showerror("无法启动", str(error), parent=self.root)
            return
        self.status.set(f"运行中（PID {self.process.pid}）")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        threading.Thread(target=self._read_process_output, args=(self.process,), daemon=True).start()

    def _stop(self) -> None:
        if self.stop_process and self.stop_process.poll() is None:
            return
        settings = self.running_settings or self.settings
        if self.process is None:
            try:
                settings = self._settings_from_form()
            except ValueError:
                settings = self.settings
        command = _worker_command(watcher_arguments(settings, stop=True))
        self._append_log("停止监控…")
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.stop_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except (OSError, ValueError) as error:
            self._append_log(f"停止失败：{error}")
            return
        threading.Thread(target=self._read_process_output, args=(self.stop_process,), daemon=True).start()

    def _read_process_output(self, process: subprocess.Popen[str]) -> None:
        if process.stdout is not None:
            for line in process.stdout:
                self.output_queue.put(("log", line.rstrip()))
        return_code = process.wait()
        kind = "watcher_exit" if process is self.process else "stop_exit"
        self.output_queue.put((kind, return_code))

    def _drain_output(self) -> None:
        try:
            while True:
                kind, value = self.output_queue.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "watcher_exit":
                    self.status.set("已停止" if value == 0 else f"已退出（代码 {value}）")
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.process = None
                    self.running_settings = None
                elif kind == "stop_exit":
                    if value != 0:
                        self._append_log(f"停止命令退出代码：{value}")
                    self.stop_process = None
        except queue.Empty:
            pass
        if self.close_requested and self.process is None and self.stop_process is None:
            self.root.destroy()
            return
        self.root.after(100, self._drain_output)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    @staticmethod
    def _display_argument(value: str) -> str:
        return f'"{value}"' if any(char.isspace() for char in value) else value

    def _close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("退出", "监控仍在运行，是否先停止再退出？", parent=self.root):
                return
            self.close_requested = True
            self._stop()
            return
        self._save()
        self.root.destroy()


def run_gui() -> int:
    root = tk.Tk()
    CapacityWatcherApp(root)
    root.mainloop()
    return 0


def dispatch(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--worker":
        from codex_capacity_watcher import main as watcher_main

        return watcher_main(arguments[1:])
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(dispatch())
