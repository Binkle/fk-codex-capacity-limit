"""Build a Finder drag-to-Applications image without UI automation."""

import argparse
import os
from pathlib import Path
import tempfile

import dmgbuild

from macos_dmg_background import (
    APP_POSITION,
    APPLICATIONS_POSITION,
    WINDOW_SIZE,
    render_background,
)


def create_image(application: Path, output: Path) -> None:
    application = application.resolve()
    output = output.resolve()
    if not (application / "Contents" / "Info.plist").is_file():
        raise ValueError(f"Application bundle not found: {application}")
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory(prefix="capacity-watcher-dmg-") as tmp:
        background = render_background(Path(tmp))
        dmgbuild.build_dmg(
            str(output),
            "Codex Capacity Watcher",
            settings={
                "format": "UDZO",
                "filesystem": "HFS+",
                "files": [str(application)],
                "symlinks": {"Applications": "/Applications"},
                "icon": str(Path(__file__).parent / "assets" / "CodexCapacityWatcher.icns"),
                "background": str(background),
                "window_rect": ((200, 200), WINDOW_SIZE),
                "default_view": "icon-view",
                "show_status_bar": False,
                "show_tab_view": False,
                "show_toolbar": False,
                "show_pathbar": False,
                "show_sidebar": False,
                "arrange_by": None,
                "icon_size": 88,
                "text_size": 12,
                "icon_locations": {
                    application.name: APP_POSITION,
                    "Applications": APPLICATIONS_POSITION,
                },
            },
        )
    print(f"Created drag-to-Applications image: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    create_image(args.application, args.output)
