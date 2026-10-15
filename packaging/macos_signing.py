"""Local Developer ID signing, resumable notarization, and Gatekeeper checks."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def run(*arguments: str, stdout_only: bool = False) -> str:
    result = subprocess.run(arguments, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"{arguments[0]} failed ({result.returncode}):\n"
            f"{result.stdout}{result.stderr}"
        )
    return result.stdout if stdout_only else result.stdout + result.stderr


@dataclass(frozen=True)
class Signing:
    fingerprint: str
    team: str
    profile: str


def signing_config() -> Signing | None:
    identity = os.environ.get("MACOS_SIGN_IDENTITY", "").strip()
    profile = os.environ.get("MACOS_NOTARY_PROFILE", "").strip()
    if not identity:
        if profile:
            raise ValueError("MACOS_NOTARY_PROFILE requires MACOS_SIGN_IDENTITY")
        return None
    identities = run("security", "find-identity", "-v", "-p", "codesigning")
    matches = [
        (fingerprint, team)
        for fingerprint, label, team in re.findall(
            r'([A-Fa-f0-9]{40}) "(Developer ID Application: [^"\n]+ \(([A-Z0-9]+)\))"',
            identities,
        )
        if identity == label or identity.upper() == fingerprint.upper()
    ]
    if len(matches) != 1:
        raise ValueError("Select one valid Developer ID Application identity by full name or SHA-1")
    fingerprint, team = matches[0]
    return Signing(fingerprint, team, profile)


def check_credentials(signing: Signing | None) -> None:
    if signing and signing.profile:
        run("xcrun", "notarytool", "history", "--keychain-profile", signing.profile,
            "--output-format", "json")


def verify_developer_signature(path: Path, team: str, *, application: bool) -> None:
    arguments = ["codesign", "--verify", "--strict"]
    if application:
        arguments.append("--deep")
    run(*arguments, str(path))
    details = run("codesign", "--display", "--verbose=4", str(path))
    if "Authority=Developer ID Application:" not in details:
        raise RuntimeError(f"Missing Developer ID Application signature: {path}")
    if f"TeamIdentifier={team}" not in details.splitlines():
        raise RuntimeError(f"Signing team does not match the selected identity: {path}")
    if not any(line.startswith("Timestamp=") for line in details.splitlines()):
        raise RuntimeError(f"Missing secure timestamp: {path}")
    if application and "(runtime)" not in details:
        raise RuntimeError(f"Hardened runtime is not enabled: {path}")


def notarize(archive: Path, profile: str, reports: Path) -> None:
    """Reuse the submission ID when a wait times out; never resubmit identical bytes."""
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    reports.mkdir(parents=True, exist_ok=True)
    receipt = reports / f"{digest.hexdigest()}.json"
    if receipt.exists():
        submission = json.loads(receipt.read_text())
    else:
        submission = json.loads(run(
            "xcrun", "notarytool", "submit", str(archive),
            "--keychain-profile", profile, "--output-format", "json",
            stdout_only=True,
        ))
        receipt.write_text(json.dumps(submission, indent=2) + "\n")
    identifier = submission["id"]
    print(f"Apple notarization: {identifier} (receipt: {receipt})", flush=True)
    try:
        result = json.loads(run(
            "xcrun", "notarytool", "wait", identifier,
            "--keychain-profile", profile, "--timeout", "15m", "--output-format", "json",
            stdout_only=True,
        ))
    except RuntimeError as error:
        raise RuntimeError(f"{error}\nSubmission is saved; inspect it with notarytool info {identifier}.") from error
    status = result.get("status")
    if status != "Accepted":
        log = reports / f"{identifier}.log.json"
        run("xcrun", "notarytool", "log", identifier,
            "--keychain-profile", profile, str(log))
        raise RuntimeError(f"Apple notarization returned {status}; see {log}")
    print(f"Apple notarization accepted: {identifier}", flush=True)


def staple(path: Path) -> None:
    run("xcrun", "stapler", "staple", str(path))
    run("xcrun", "stapler", "validate", str(path))


def verify_gatekeeper(path: Path, *, application: bool) -> None:
    run("xcrun", "stapler", "validate", str(path))
    arguments = ["spctl", "--assess", "--verbose=2"]
    arguments += ["--type", "execute"] if application else [
        "--type", "open", "--context", "context:primary-signature",
    ]
    run(*arguments, str(path))


if __name__ == "__main__":
    check_credentials(signing_config())
