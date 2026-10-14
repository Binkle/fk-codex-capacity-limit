#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

python3 -m pip install --upgrade pyinstaller PySide6
python3 -m PyInstaller \
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
