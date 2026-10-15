#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
# Check the selected certificate and optional Keychain profile before building.
"$PYTHON_BIN" packaging/macos_signing.py
if ! "$PYTHON_BIN" -c 'import PyInstaller, PySide6' >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --upgrade pyinstaller PySide6
fi
if ! "$PYTHON_BIN" -c 'import dmgbuild' >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install 'dmgbuild==1.6.7'
fi

ICON_FILE="$PROJECT_ROOT/packaging/assets/CodexCapacityWatcher.icns"
ICON_SOURCE="$PROJECT_ROOT/packaging/assets/codex-capacity-watcher-icon.png"
if [ ! -f "$ICON_FILE" ] || [ ! -f "$ICON_SOURCE" ]; then
  echo "Missing application icon assets under packaging/assets" >&2
  exit 1
fi

"$PYTHON_BIN" -m PyInstaller --noconfirm --clean packaging/macos_app.spec
"$PYTHON_BIN" packaging/package_macos.py
