"""Language selection and translations for the desktop watcher."""

from __future__ import annotations

import locale
import os
from typing import Any


LANGUAGE_ZH = "zh-CN"
LANGUAGE_EN = "en-US"
SUPPORTED_LANGUAGES = (LANGUAGE_ZH, LANGUAGE_EN)


TRANSLATIONS: dict[str, dict[str, str]] = {
    LANGUAGE_ZH: {
        "brand.caption": "本地自动继续工具",
        "nav.workspace": "工作区",
        "nav.monitor": "实时监控",
        "nav.settings": "运行设置",
        "nav.help": "使用说明",
        "side.process": "本地进程",
        "side.not_running": "未运行",
        "side.footer": "配置保存在本机\n不会上传会话内容",
        "page.eyebrow": "CAPACITY WATCHER",
        "page.monitor.title": "自动继续",
        "page.monitor.subtitle": "监听容量限制事件，并把消息发送回原会话。",
        "page.settings.title": "运行设置",
        "page.settings.subtitle": "配置 Codex 路径、发送内容和扫描范围。",
        "page.help.title": "使用说明",
        "page.help.subtitle": "快速了解如何启动、停止和配置监控。",
        "monitor.control.title": "监控控制",
        "monitor.control.hint": "准备好后即可在后台运行",
        "monitor.control.note": "需要调整路径或扫描范围？打开左侧的“运行设置”。",
        "monitor.log.title": "运行日志",
        "monitor.log.hint": "实时显示 watcher 输出",
        "monitor.log.clear": "清空",
        "monitor.log.placeholder": "启动监控后，运行信息会显示在这里。",
        "settings.paths.title": "连接配置",
        "settings.paths.hint": "选择 Codex 数据目录和可执行程序",
        "settings.options.title": "运行选项",
        "settings.options.hint": "按需调整发送内容、扫描间隔和会话类型",
        "settings.save.hint": "修改配置后点击保存，开始监控时也会自动保存。",
        "settings.save": "保存设置",
        "field.codex_home": "Codex 主目录",
        "field.state_file": "状态文件",
        "field.codex": "Codex 程序",
        "field.message": "发送内容",
        "field.interval": "扫描间隔",
        "field.lookback": "回看时间",
        "field.session_types": "监控会话",
        "field.language": "界面语言",
        "unit.seconds": " 秒",
        "unit.hours": " 小时",
        "language.zh-CN": "中文",
        "language.en-US": "English",
        "choose.directory": "选择目录",
        "choose.program": "选择程序",
        "choose.file": "选择文件",
        "dialog.choose_home": "选择 Codex 主目录",
        "dialog.choose_program": "选择 Codex 程序",
        "dialog.choose_state": "选择状态文件",
        "dialog.json_files": "JSON 文件 (*.json);;所有文件 (*)",
        "session.cli": "终端 CLI",
        "session.vscode": "VS Code",
        "session.desktop": "ChatGPT 桌面端",
        "session.exec": "codex exec",
        "session.tooltip": "监控 {name} 会话的容量错误",
        "option.recover": "启动时处理停机期间的限流会话",
        "option.recover.tooltip": "检查停机期间最近一段时间内仍因模型容量不足而停止的会话，并发送一次后续消息。",
        "option.subagents": "包含子代理会话",
        "option.dry_run": "仅预览，不实际发送",
        "help.start.title": "三步开始",
        "help.start.body": "1. 在“运行设置”中确认 Codex 主目录和程序路径。\n2. 按需设置发送内容、扫描间隔和会话范围。\n3. 回到“实时监控”，点击“开始监控”。",
        "help.recover.title": "启动时处理停机期间的限流",
        "help.recover.body": "普通启动只处理 watcher 启动后出现的新容量错误。\n如果需要处理停机期间最近仍处于限流状态的会话，请勾选“启动时处理停机期间的限流会话”，并设置回看时间。处理完成后，监控会继续只监听新事件。",
        "help.stop.title": "停止运行",
        "help.stop.body": "回到“实时监控”后点击“停止监控”。关闭窗口时，如果 watcher 仍在运行，应用会先询问是否停止再退出。",
        "status.idle": "已停止",
        "status.running": "运行中",
        "status.exited": "已退出（代码 {code}）",
        "status.side_running": "运行中",
        "button.start": "开始监控",
        "button.stop": "停止监控",
        "button.restart": "重新启动",
        "tooltip.start": "启动容量监控",
        "tooltip.stop": "停止当前容量监控",
        "tooltip.restart": "重新启动容量监控",
        "dialog.invalid": "设置无效",
        "dialog.cannot_start": "无法启动",
        "dialog.start_failed": "启动失败",
        "dialog.exit": "退出",
        "dialog.running_question": "监控仍在运行，是否先停止再退出？",
        "error.codex_home": "请填写 Codex 主目录",
        "error.state_file": "请填写状态文件",
        "error.session_types": "请至少选择一种监控会话类型",
        "error.interval": "扫描间隔必须大于 0 秒",
        "error.lookback": "回看时间必须大于 0 小时",
        "log.ready": "准备就绪。点击“开始监控”即可运行。",
        "log.saved": "设置已保存：{path}",
        "log.detected": "检测到监控已在运行（PID {pid}）。",
        "log.already_running": "监控已经在运行（PID {pid}），无需重复启动。",
        "log.starting": "启动：{command}",
        "log.stopping": "停止监控…",
        "log.stop_code": "停止命令退出代码：{code}",
        "log.process_error": "监控进程错误：{error}",
        "log.stop_error": "停止进程错误：{error}",
    },
    LANGUAGE_EN: {
        "brand.caption": "Local auto-continue tool",
        "nav.workspace": "Workspace",
        "nav.monitor": "Live monitor",
        "nav.settings": "Settings",
        "nav.help": "How to use",
        "side.process": "Local process",
        "side.not_running": "Not running",
        "side.footer": "Settings stay on this device\nSession content is never uploaded",
        "page.eyebrow": "CAPACITY WATCHER",
        "page.monitor.title": "Auto-continue",
        "page.monitor.subtitle": "Watch capacity-limit events and send a message back to the original session.",
        "page.settings.title": "Settings",
        "page.settings.subtitle": "Configure Codex paths, the follow-up message, and the scan scope.",
        "page.help.title": "How to use",
        "page.help.subtitle": "Learn how to start, stop, and configure the watcher.",
        "monitor.control.title": "Monitor control",
        "monitor.control.hint": "Ready to run in the background",
        "monitor.control.note": "Need to change paths or the scan scope? Open “Settings” on the left.",
        "monitor.log.title": "Runtime log",
        "monitor.log.hint": "Live watcher output",
        "monitor.log.clear": "Clear",
        "monitor.log.placeholder": "Runtime information will appear here after monitoring starts.",
        "settings.paths.title": "Connection",
        "settings.paths.hint": "Choose the Codex data directory and executable",
        "settings.options.title": "Run options",
        "settings.options.hint": "Adjust the message, scan interval, and session types",
        "settings.save.hint": "Click save after changing settings. Starting the monitor also saves them.",
        "settings.save": "Save settings",
        "field.codex_home": "Codex home",
        "field.state_file": "State file",
        "field.codex": "Codex executable",
        "field.message": "Follow-up message",
        "field.interval": "Scan interval",
        "field.lookback": "Look-back window",
        "field.session_types": "Sessions to monitor",
        "field.language": "Interface language",
        "unit.seconds": " sec",
        "unit.hours": " hours",
        "language.zh-CN": "中文",
        "language.en-US": "English",
        "choose.directory": "Choose folder",
        "choose.program": "Choose program",
        "choose.file": "Choose file",
        "dialog.choose_home": "Choose Codex home",
        "dialog.choose_program": "Choose Codex program",
        "dialog.choose_state": "Choose state file",
        "dialog.json_files": "JSON files (*.json);;All files (*)",
        "session.cli": "Terminal CLI",
        "session.vscode": "VS Code",
        "session.desktop": "ChatGPT desktop",
        "session.exec": "codex exec",
        "session.tooltip": "Monitor capacity errors from {name} sessions",
        "option.recover": "Process capacity-limited sessions from downtime at startup",
        "option.recover.tooltip": "Check sessions that stopped because of model capacity during the recent look-back window and send one follow-up message.",
        "option.subagents": "Include subagent sessions",
        "option.dry_run": "Preview only; do not send",
        "help.start.title": "Start in three steps",
        "help.start.body": "1. Confirm the Codex home and executable in “Settings”.\n2. Set the message, scan interval, and session scope if needed.\n3. Return to “Live monitor” and click “Start monitoring”.",
        "help.recover.title": "Process downtime capacity limits at startup",
        "help.recover.body": "A normal start handles only new capacity errors after the watcher starts.\nTo process sessions that remained capacity-limited during downtime, enable “Process capacity-limited sessions from downtime at startup” and set the look-back window. After the one-time check, monitoring continues with new events only.",
        "help.stop.title": "Stop the watcher",
        "help.stop.body": "Return to “Live monitor” and click “Stop monitoring”. If the watcher is running when you close the window, the app asks whether to stop it first.",
        "status.idle": "Stopped",
        "status.running": "Running",
        "status.exited": "Exited (code {code})",
        "status.side_running": "Running",
        "button.start": "Start monitoring",
        "button.stop": "Stop monitoring",
        "button.restart": "Restart",
        "tooltip.start": "Start capacity monitoring",
        "tooltip.stop": "Stop the current capacity monitor",
        "tooltip.restart": "Restart capacity monitoring",
        "dialog.invalid": "Invalid settings",
        "dialog.cannot_start": "Unable to start",
        "dialog.start_failed": "Start failed",
        "dialog.exit": "Exit",
        "dialog.running_question": "Monitoring is still running. Stop it before exiting?",
        "error.codex_home": "Enter the Codex home directory",
        "error.state_file": "Enter a state file",
        "error.session_types": "Select at least one session type",
        "error.interval": "The scan interval must be greater than 0 seconds",
        "error.lookback": "The look-back window must be greater than 0 hours",
        "log.ready": "Ready. Click “Start monitoring” to run.",
        "log.saved": "Settings saved: {path}",
        "log.detected": "Monitoring is already running (PID {pid}).",
        "log.already_running": "Monitoring is already running (PID {pid}); no duplicate was started.",
        "log.starting": "Starting: {command}",
        "log.stopping": "Stopping monitoring…",
        "log.stop_code": "Stop command exited with code: {code}",
        "log.process_error": "Watcher process error: {error}",
        "log.stop_error": "Stop process error: {error}",
    },
}


def system_language() -> str:
    """Map the host locale to one of the two languages we ship."""
    candidates = []
    try:
        language, _encoding = locale.getlocale()
        candidates.append(language or "")
    except ValueError:
        pass
    candidates.extend(
        os.environ.get(name, "")
        for name in ("LC_ALL", "LC_MESSAGES", "LANG")
    )
    for value in candidates:
        normalized = value.lower().replace("_", "-")
        if normalized.startswith("zh"):
            return LANGUAGE_ZH
        if normalized.startswith("en"):
            return LANGUAGE_EN
    return LANGUAGE_EN


def normalize_language(value: Any) -> str:
    return str(value).strip() if str(value).strip() in SUPPORTED_LANGUAGES else system_language()


def translate(language: str, key: str, **values: Any) -> str:
    selected = TRANSLATIONS.get(normalize_language(language), TRANSLATIONS[LANGUAGE_EN])
    text = selected.get(key, TRANSLATIONS[LANGUAGE_EN].get(key, key))
    return text.format(**values) if values else text
