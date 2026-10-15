# -*- mode: python ; coding: utf-8 -*-
"""Build the macOS bundle, including nested code signatures and release metadata."""

import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(SPECPATH).parent
# The existing release workflow uses the MSI version as the release version.
package = ET.parse(root / "packaging/windows-installer.wxs").getroot()[0]
version = os.environ.get("APP_VERSION", package.attrib["Version"])
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    raise ValueError("APP_VERSION must contain three numeric components, e.g. 0.1.11")
icon = str(root / "packaging/assets/CodexCapacityWatcher.icns")

analysis = Analysis(
    [str(root / "scripts/codex_capacity_watcher_gui.py")],
    pathex=[str(root / "scripts")],
    datas=[(str(root / "packaging/assets/codex-capacity-watcher-icon.png"), "assets")],
    hiddenimports=["codex_capacity_watcher"],
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True,
    name="CodexCapacityWatcher", console=False, icon=icon,
    codesign_identity=os.environ.get("MACOS_SIGN_IDENTITY") or None,
)
collection = COLLECT(
    executable, analysis.binaries, analysis.datas, name="CodexCapacityWatcher",
)
application = BUNDLE(
    collection, name="CodexCapacityWatcher.app", icon=icon,
    bundle_identifier="io.github.binkle.CodexCapacityWatcher", version=version,
    info_plist={"CFBundleVersion": version, "NSHighResolutionCapable": True},
)
