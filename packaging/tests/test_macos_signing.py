"""Release gates: incorrect identities and rejected notarization must fail closed."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import macos_signing as signing


FINGERPRINT = "A" * 40
TEAM = "TEAM123456"
LABEL = f"Developer ID Application: Test Developer ({TEAM})"
IDENTITIES = f'1) {FINGERPRINT} "{LABEL}"\n'


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.delenv("MACOS_SIGN_IDENTITY", raising=False)
    monkeypatch.delenv("MACOS_NOTARY_PROFILE", raising=False)


def test_notary_profile_requires_a_certificate(monkeypatch):
    monkeypatch.setenv("MACOS_NOTARY_PROFILE", "test-profile")
    with pytest.raises(ValueError, match="requires MACOS_SIGN_IDENTITY"):
        signing.signing_config()


def test_app_store_certificate_is_rejected(monkeypatch):
    label = f"Apple Distribution: Test Developer ({TEAM})"
    monkeypatch.setenv("MACOS_SIGN_IDENTITY", FINGERPRINT)
    monkeypatch.setattr(signing, "run", lambda *args: f'1) {FINGERPRINT} "{label}"')
    with pytest.raises(ValueError, match="Developer ID Application"):
        signing.signing_config()


@pytest.mark.parametrize("identity", [FINGERPRINT, FINGERPRINT.lower(), LABEL])
def test_developer_identity_resolves_exactly(monkeypatch, identity):
    monkeypatch.setenv("MACOS_SIGN_IDENTITY", identity)
    monkeypatch.setattr(signing, "run", lambda *args: IDENTITIES)
    result = signing.signing_config()
    assert (result.fingerprint, result.team) == (FINGERPRINT, TEAM)


def test_ambiguous_developer_name_requires_fingerprint(monkeypatch):
    monkeypatch.setenv("MACOS_SIGN_IDENTITY", LABEL)
    output = IDENTITIES + f'2) {"B" * 40} "{LABEL}"'
    monkeypatch.setattr(signing, "run", lambda *args: output)
    with pytest.raises(ValueError, match="Select one"):
        signing.signing_config()


@pytest.mark.parametrize("missing", ["Authority=", "TeamIdentifier=", "Timestamp=", "flags="])
def test_application_signature_requirements(monkeypatch, tmp_path, missing):
    lines = [f"Authority={LABEL}", f"TeamIdentifier={TEAM}",
             "Timestamp=Oct 15, 2026", "CodeDirectory flags=0x10000(runtime)"]
    details = "\n".join(line for line in lines if missing not in line)
    monkeypatch.setattr(signing, "run", lambda *args: details if "--display" in args else "")
    with pytest.raises(RuntimeError):
        signing.verify_developer_signature(tmp_path / "Test.app", TEAM, application=True)


def test_rejected_notarization_cannot_pass(monkeypatch, tmp_path):
    archive = tmp_path / "app.zip"
    archive.write_bytes(b"signed-application")
    calls = []

    def notary(*args, **kwargs):
        calls.append(args)
        if "submit" in args:
            return json.dumps({"id": "submission-1"})
        if "wait" in args:
            return json.dumps({"status": "Invalid"})
        return ""

    monkeypatch.setattr(signing, "run", notary)
    with pytest.raises(RuntimeError, match="Invalid"):
        signing.notarize(archive, "test-profile", tmp_path / "reports")
    assert any("log" in call for call in calls)
    assert not any("staple" in call for call in calls)


def test_notarization_timeout_reuses_submission(monkeypatch, tmp_path):
    archive = tmp_path / "app.zip"
    archive.write_bytes(b"signed-application")
    submissions = []
    waits = []

    def notary(*args, **kwargs):
        if "submit" in args:
            submissions.append(args)
            return json.dumps({"id": "submission-1"})
        waits.append(args)
        if len(waits) == 1:
            raise RuntimeError("Timed out")
        return json.dumps({"status": "Accepted"})

    monkeypatch.setattr(signing, "run", notary)
    with pytest.raises(RuntimeError, match="Submission is saved"):
        signing.notarize(archive, "test-profile", tmp_path / "reports")
    signing.notarize(archive, "test-profile", tmp_path / "reports")
    assert len(submissions) == 1
    assert len(waits) == 2
    assert all("submission-1" in call for call in waits)
