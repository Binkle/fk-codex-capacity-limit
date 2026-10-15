"""Package the built app; publish final files only after the requested checks pass."""

import hashlib
from pathlib import Path
import plistlib
import shutil
import tempfile

from create_macos_dmg import create_image
from macos_signing import (
    check_credentials, notarize, run, signing_config, staple,
    verify_developer_signature, verify_gatekeeper,
)
from verify_macos_dmg import verify_image


ROOT = Path(__file__).resolve().parent.parent


def zip_application(application: Path, archive: Path) -> None:
    # Preserve Qt framework symlinks instead of expanding the bundle's size.
    run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(application), str(archive))


def staging_directory(application: Path, *, notarized: bool) -> Path:
    """Keep uploaded bytes for retries, keyed by the signed app and DMG layout."""
    info = plistlib.loads((application / "Contents/Info.plist").read_bytes())
    executable = application / "Contents/MacOS" / info["CFBundleExecutable"]
    digest = hashlib.sha256(executable.read_bytes())
    digest.update(b"notarized" if notarized else b"local")
    for name in ("create_macos_dmg.py", "macos_dmg_background.py"):
        digest.update((ROOT / "packaging" / name).read_bytes())
    staging = ROOT / "build/macos-staging" / digest.hexdigest()
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def publish_file(source: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=".macos-publish-", dir=destination.parent) as tmp:
        copied = Path(tmp) / source.name
        shutil.copy2(source, copied)
        copied.replace(destination)


def package() -> None:
    signing = signing_config()
    check_credentials(signing)
    dist = ROOT / "dist"
    app = dist / "CodexCapacityWatcher.app"
    reports = ROOT / "build/notarization"
    if not app.is_dir():
        raise ValueError(f"Build the application first: {app}")
    if signing:
        verify_developer_signature(app, signing.team, application=True)
    else:
        run("codesign", "--verify", "--deep", "--strict", str(app))

    staging = staging_directory(app, notarized=bool(signing and signing.profile))
    archive = staging / "CodexCapacityWatcher-macos.zip"
    image = staging / "CodexCapacityWatcher-macos.dmg"
    if signing and signing.profile:
        upload = staging / "notarization-upload.zip"
        if not upload.exists():
            zip_application(app, upload)
        notarize(upload, signing.profile, reports)
        staple(app)
        verify_gatekeeper(app, application=True)
    zip_application(app, archive)
    if not image.exists():
        with tempfile.TemporaryDirectory(prefix=".dmg-build-", dir=staging) as tmp:
            temporary_image = Path(tmp) / image.name
            create_image(app, temporary_image)
            if signing:
                run("codesign", "--force", "--sign", signing.fingerprint, "--timestamp", str(temporary_image))
            temporary_image.replace(image)
    if signing:
        verify_developer_signature(image, signing.team, application=False)
        if signing.profile:
            notarize(image, signing.profile, reports)
            staple(image)
            verify_gatekeeper(image, application=False)
    verify_image(image, team=signing.team if signing else None,
                 notarized=bool(signing and signing.profile))
    publish_file(archive, dist / archive.name)
    publish_file(image, dist / image.name)
    if signing and signing.profile:
        print("Mac distribution verified: Developer ID, Apple notarization and Gatekeeper accepted")
    else:
        print("Local build only: this package has not been verified by Apple notarization")
    print(f"Built {dist / 'CodexCapacityWatcher-macos.zip'}")
    print(f"Built {dist / 'CodexCapacityWatcher-macos.dmg'}")


if __name__ == "__main__":
    package()
