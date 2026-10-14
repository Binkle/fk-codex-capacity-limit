#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
if ! "$PYTHON_BIN" -c 'import PyInstaller, PySide6' >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --upgrade pyinstaller PySide6
fi

ICON_FILE="$PROJECT_ROOT/packaging/assets/CodexCapacityWatcher.icns"
ICON_SOURCE="$PROJECT_ROOT/packaging/assets/codex-capacity-watcher-icon.png"
if [ ! -f "$ICON_FILE" ] || [ ! -f "$ICON_SOURCE" ]; then
  echo "Missing application icon assets under packaging/assets" >&2
  exit 1
fi

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name CodexCapacityWatcher \
  --icon "$ICON_FILE" \
  --add-data "$ICON_SOURCE:assets" \
  --hidden-import codex_capacity_watcher \
  scripts/codex_capacity_watcher_gui.py

# Keep macOS symlinks intact in the distributable archive. Copying the .app
# with a tool that follows symlinks can expand the Qt/PySide6 payload several
# times and make a normal build appear to be hundreds of megabytes larger.
ditto -c -k --sequesterRsrc --keepParent \
  dist/CodexCapacityWatcher.app \
  dist/CodexCapacityWatcher-macos.zip

hdiutil create \
  -volname "Codex Capacity Watcher" \
  -srcfolder dist/CodexCapacityWatcher.app \
  -ov \
  -format UDZO \
  dist/CodexCapacityWatcher-macos.dmg >/dev/null

echo "Built dist/CodexCapacityWatcher.app"
echo "Built dist/CodexCapacityWatcher-macos.zip"
echo "Built dist/CodexCapacityWatcher-macos.dmg"
