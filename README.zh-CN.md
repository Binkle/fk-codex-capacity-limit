# fk-codex-capacity-limit

[English](README.md)

当 Codex CLI 因模型容量不足而结束当前任务时，这个脚本会监控本地 rollout 日志，并向原会话自动发送一条后续消息。默认消息是 `continue`，因此可以让会话在容量错误后自动继续处理。

## 功能

- 监控 `CODEX_HOME/sessions/**/rollout-*.jsonl` 中的新任务完成事件。
- 只处理容量错误：`Selected model is at capacity. Please try a different model`。
- 使用 `codex queue --thread <session-id> --message continue` 发送消息，消息会进入发生错误的原会话。
- 默认只处理终端 CLI 会话，并为每个失败 turn 发送一次。
- 用状态文件记录已处理事件，重启监控脚本后不会重复发送。
- 用 PID 文件记录运行中的监控进程，可通过 `--stop` 停止它。
- 可选恢复启动前最近一段时间内仍停在容量错误的会话。

## 环境要求

- Python 3.10 或更高版本。
- 已安装并可调用的 Codex CLI，且支持 `codex queue`。
- Codex CLI 生成的本地 rollout 文件。

## 使用

在仓库根目录运行：

```bash
python3 scripts/codex_capacity_watcher.py
```

默认配置如下：

| 配置 | 默认值 |
| --- | --- |
| Codex 主目录 | `$CODEX_HOME`，未设置时为 `~/.codex` |
| 状态文件 | `$CODEX_HOME/capacity-watcher-state.json` |
| PID 文件 | 状态文件所在目录中的 `capacity-watcher.pid` |
| Codex 命令 | `$CODEX_BIN`，未设置时为 `codex` |
| 发送内容 | `continue` |
| 扫描间隔 | 2 秒 |

先观察而不发送消息：

```bash
python3 scripts/codex_capacity_watcher.py --dry-run --once
```

停止已经运行的监控进程：

```bash
python3 scripts/codex_capacity_watcher.py --stop
```

如果启动时使用了自定义 PID 文件，停止时传入相同路径：

```bash
python3 scripts/codex_capacity_watcher.py --stop --pid-file /path/to/capacity-watcher.pid
```

启动时恢复最近 6 小时内仍停在容量错误的会话：

```bash
python3 scripts/codex_capacity_watcher.py --recover --recover-hours 6
```

默认只监控终端 CLI 会话。如需同时监控 VS Code 和 `codex exec` 会话：

```bash
python3 scripts/codex_capacity_watcher.py --all-sessions
```

如需监控子代理会话：

```bash
python3 scripts/codex_capacity_watcher.py --include-subagents
```

完整参数：

```bash
python3 scripts/codex_capacity_watcher.py --help
```

## 桌面 GUI

仓库还提供了给非开发人员使用的桌面界面。界面支持点击“开始监控”和
“停止监控”，设置扫描间隔，选择 Codex 主目录、状态文件和 Codex 程序，
修改发送内容，选择是否恢复历史、是否包含其他会话，并查看实时日志。
恢复历史时还可以设置恢复时长。

macOS 可以双击 `run-codex-capacity-watcher.command`，Windows 可以双击
`run-codex-capacity-watcher.bat`。直接运行源码时需要 Python 3.10 及以上并
并安装 PySide6。源码运行前可以执行
`python3 -m pip install -r requirements-gui.txt`。

如果希望交付给完全不需要 Python 的用户，可以在对应系统上构建独立应用：

```bash
# macOS
sh packaging/build-macos.sh

# Windows（命令提示符）
packaging\build-windows.bat
```

macOS 构建结果是 `dist/CodexCapacityWatcher.app`，Windows 构建结果是
`dist\CodexCapacityWatcher.exe`。PyInstaller 会把 GUI 和监控脚本一起打包，
使用者不需要再手动运行 Python 脚本。

仓库还提供了 `.github/workflows/build-desktop.yml`。可以在 GitHub 的
Actions 页面手动运行它，或者推送 `v*` 标签，生成可下载的 macOS 和
Windows 应用构建产物。

## 工作方式

脚本会保存每个 rollout 文件的读取位置，并将已发送的事件写入状态文件。检测到新的容量错误后，它会提取 session ID 和 turn ID，调用 `codex queue` 向原会话发送消息。发送失败时不会把事件标记为已处理，下一轮扫描可以再次尝试。运行期间，脚本会将进程号写入 PID 文件；`--stop` 会发送 `SIGTERM` 请求优雅退出，退出时自动清理 PID 文件。如果没有有效的 PID 文件，`--stop` 还会查找正在运行的旧版本脚本进程并停止它们。

普通重启会跳过监控停止期间追加的历史事件，从每个 rollout 文件的当前末尾开始监听。只有显式使用 `--recover` 时，脚本才会在启动时检查已有历史记录；恢复检查完成后也只监听新事件。状态文件和 PID 文件可以分别通过 `--state-file`、`--pid-file` 指定到其他位置。

## 测试

运行语法检查：

```bash
python3 -m py_compile scripts/codex_capacity_watcher.py
```

如果环境已安装 pytest，运行测试：

```bash
python3 -m pytest -q scripts/tests
```
