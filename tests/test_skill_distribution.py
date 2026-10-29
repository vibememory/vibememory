import hashlib
import importlib.util
import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_launcher(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_distribution_matches_sources_and_native_manifest(client):
    client.headers.pop("Authorization")
    response = client.get("/skills/vibe-memory/manifest.json")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    manifest = response.json()
    assert set(manifest["files"]) == {"SKILL.md", "scripts/memory.py"}
    assert manifest["native_cli"]["repository"] == "https://github.com/vibememory/cli"
    assert set(manifest["native_cli"]["targets"]) == {
        "linux-x86_64",
        "macos-aarch64",
        "macos-x86_64",
        "windows-x86_64",
    }
    for target in manifest["native_cli"]["targets"].values():
        assert len(target["sha256"]) == 64
        assert target["url"].startswith(
            "https://github.com/vibememory/cli/releases/download/v"
            + manifest["native_cli"]["version"]
            + "/vibe-memory-"
        )

    archive_response = client.get(manifest["archive"])
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        assert set(archive.namelist()) == {
            "vibe-memory/SKILL.md",
            "vibe-memory/scripts/memory.py",
        }
        assert b"native Rust" in archive.read("vibe-memory/SKILL.md")
        assert b"native_cli" in archive.read("vibe-memory/scripts/memory.py")
        for name, digest in manifest["files"].items():
            release = client.get(
                "/skills/vibe-memory/releases/" + manifest["revision"] + "/" + name
            )
            assert release.status_code == 200
            assert hashlib.sha256(release.content).hexdigest() == digest
            assert release.content == (ROOT / "skills/vibe-memory" / name).read_bytes()
            assert archive.read("vibe-memory/" + name) == release.content

    legacy = client.get(manifest["cli"]["url"])
    assert legacy.status_code == 200
    assert hashlib.sha256(legacy.content).hexdigest() == manifest["cli"]["sha256"]


def test_bootstrap_selects_and_verifies_native_binary(tmp_path, monkeypatch):
    installed = tmp_path / "installed"
    (installed / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/vibe-memory/scripts/memory.py", installed / "scripts/memory.py")
    launcher = load_launcher(installed / "scripts/memory.py", "native_bootstrap")
    binary = b"native-rust-binary-for-test"
    digest = hashlib.sha256(binary).hexdigest()
    target_name = launcher.platform_target()
    manifest = {
        "native_cli": {
            "version": "3.0.0",
            "repository": "https://github.com/vibememory/cli",
            "targets": {
                target_name: {
                    "sha256": digest,
                    "url": "https://github.com/vibememory/cli/releases/download/v3.0.0/"
                    + (
                        "vibe-memory-windows-x86_64.exe"
                        if target_name.startswith("windows")
                        else "vibe-memory-test"
                    ),
                }
            },
        }
    }
    monkeypatch.setattr(launcher, "fetch_manifest", lambda base: manifest)
    monkeypatch.setattr(launcher, "fetch_release", lambda url: binary)
    monkeypatch.setattr(launcher, "origin", lambda: "https://vibememory.io")
    target = launcher.ensure_cli()
    assert target.read_bytes() == binary
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    if launcher.os.name != "nt":
        assert target.stat().st_mode & 0o100

    monkeypatch.setattr(
        launcher,
        "fetch_release",
        lambda url: (_ for _ in ()).throw(AssertionError("current binary was redownloaded")),
    )
    assert launcher.ensure_cli() == target


def test_bootstrap_rejects_tampering_and_untrusted_configuration(tmp_path, monkeypatch):
    installed = tmp_path / "installed"
    (installed / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/vibe-memory/scripts/memory.py", installed / "scripts/memory.py")
    launcher = load_launcher(installed / "scripts/memory.py", "tampered_bootstrap")
    target_name = launcher.platform_target()
    manifest = {
        "native_cli": {
            "version": "3.0.0",
            "repository": "https://github.com/vibememory/cli",
            "targets": {
                target_name: {
                    "sha256": "a" * 64,
                    "url": "https://github.com/vibememory/cli/releases/download/v3.0.0/vibe-memory-test",
                }
            },
        }
    }
    monkeypatch.setattr(launcher, "fetch_manifest", lambda base: manifest)
    monkeypatch.setattr(launcher, "fetch_release", lambda url: b"tampered")
    monkeypatch.setattr(launcher, "origin", lambda: "https://vibememory.io")
    with pytest.raises(ValueError, match="checksum mismatch"):
        launcher.ensure_cli()
    assert not launcher.executable_path().exists()
    launcher = load_launcher(installed / "scripts/memory.py", "untrusted_bootstrap")
    monkeypatch.setenv("MEMORY_URL", "http://untrusted.example")
    with pytest.raises(ValueError, match="HTTPS"):
        launcher.origin()


def test_published_revision_is_reproducible_and_releases_are_immutable(tmp_path):
    public = tmp_path / "public"
    shutil.copytree(ROOT / "landing/dist/skills", public / "skills")
    manifest = json.loads((public / "skills/vibe-memory/manifest.json").read_text())
    revision = hashlib.sha256(
        json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert revision == manifest["revision"]
    release = public / "skills/vibe-memory/releases" / revision
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((release / name).read_bytes()).hexdigest() == digest
