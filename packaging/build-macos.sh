#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
if ! "$PYTHON_BIN" -c 'import PyInstaller, PySide6' >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --upgrade pyinstaller PySide6
fi

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name CodexCapacityWatcher \
  --hidden-import codex_capacity_watcher \
  scripts/codex_capacity_watcher_gui.py

# Keep macOS symlinks intact in the distributable archive. Copying the .app
# with a tool that follows symlinks can expand the Qt/PySide6 payload several
# times and make a normal build appear to be hundreds of megabytes larger.
ditto -c -k --sequesterRsrc --keepParent \
  dist/CodexCapacityWatcher.app \
  dist/CodexCapacityWatcher-macos.zip

echo "Built dist/CodexCapacityWatcher.app"
echo "Built dist/CodexCapacityWatcher-macos.zip"
