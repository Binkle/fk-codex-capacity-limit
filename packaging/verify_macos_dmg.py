"""Mount the finished DMG and verify the installable bundle and Finder layout."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile

from ds_store import DSStore
from mac_alias import Alias


@contextmanager
def mounted_image(image: Path):
    with tempfile.TemporaryDirectory(prefix="capacity-watcher-dmg-check-") as tmp:
        mount = Path(tmp) / "volume"
        subprocess.run([
            "hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen",
            "-mountpoint", str(mount), str(image.resolve()),
        ], check=True, capture_output=True)
        try:
            yield mount
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)], check=True,
                           capture_output=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_image(image: Path) -> None:
    with mounted_image(image) as mount:
        app = mount / "CodexCapacityWatcher.app"
        link = mount / "Applications"
        require(app.is_dir(), "The application bundle is missing from the DMG root")
        require(link.is_symlink() and os.readlink(link) == "/Applications",
                "Applications must link to the system Applications folder")
        with (app / "Contents" / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        executable = app / "Contents" / "MacOS" / info["CFBundleExecutable"]
        require(os.access(executable, os.X_OK), "The app executable is missing")
        for path in app.rglob("*"):
            require(not path.is_symlink() or path.exists(), f"Broken bundle symlink: {path}")
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)],
                       check=True)

        with DSStore.open(str(mount / ".DS_Store"), "r") as store:
            view = store["."]["icvp"]
            window = store["."]["bwsp"]
            require(store["."]["icvl"] == (b"type", b"icnv"),
                    "The installation window must open in icon view")
            require(not window["ShowToolbar"] and not window["ShowSidebar"],
                    "Finder chrome must not cover the installation background")
            require(view["backgroundType"] == 2, "The installation background is missing")
            background = Alias.from_bytes(view["backgroundImageAlias"]).target.filename
            require((mount / background).is_file(), "Finder's background reference is broken")
            app_position = store[app.name]["Iloc"]
            destination = store["Applications"]["Iloc"]
            require(app_position[0] < destination[0] and app_position[1] == destination[1],
                    "The app and Applications icons must align left to right")
            require(view["arrangeBy"] == "none", "Automatic sorting would move the icons")
    print("DMG verified: app signature, bundle links, Applications shortcut and Finder layout")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    verify_image(parser.parse_args().image)
