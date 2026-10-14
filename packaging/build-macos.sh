#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name CodexCapacityWatcher \
  --hidden-import codex_capacity_watcher \
  scripts/codex_capacity_watcher_gui.py

echo "Built dist/CodexCapacityWatcher.app"
