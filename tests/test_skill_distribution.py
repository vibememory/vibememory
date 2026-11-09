import hashlib
import importlib.util
import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = ROOT / "skills/vibe-memory"


def distributed_skill_files():
    return {"SKILL.md", "scripts/memory.py"} | {
        path.relative_to(SKILL_SOURCE).as_posix()
        for path in (SKILL_SOURCE / "references").glob("*.md")
    }


def skill_bundle(path):
    text = path.read_text()
    references = path.parent / "references"
    if references.is_dir():
        text += "\n" + "\n".join(item.read_text() for item in sorted(references.glob("*.md")))
    return text


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
    expected_files = distributed_skill_files()
    assert manifest["schema_version"] == 2
    assert set(manifest["files"]) == expected_files
    assert manifest["native_cli"]["repository"] == "https://github.com/vibememory/cli"
    assert manifest["native_cli"]["version"] == "3.14.0"
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
    assert hashlib.sha256(archive_response.content).hexdigest() == manifest["archive_sha256"]
    assert manifest["official_archive_mirror"] == (
        "https://github.com/vibememory/vibememory/releases/latest/download/"
        "vibe-memory-skill.zip"
    )
    assert manifest["official_manifest_mirror"].endswith("/manifest-v2.json")
    assert set(manifest["release_assets"]) == expected_files
    assert manifest["release_assets"]["SKILL.md"] == "SKILL.md"
    assert manifest["release_assets"]["scripts/memory.py"] == "memory.py"
    assert all(
        manifest["release_assets"][name] == "reference-" + Path(name).name
        for name in expected_files
        if name.startswith("references/")
    )
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        assert set(archive.namelist()) == {"vibe-memory/" + name for name in expected_files}
        skill = archive.read("vibe-memory/SKILL.md")
        bundle = b"\n".join(archive.read("vibe-memory/" + name) for name in expected_files)
        assert b"native binary" in skill
        assert b"Product feedback and operator workflow" in bundle
        assert b"feedback-list" in bundle
        assert b"feedback-admin-list" in bundle
        assert b"feature_request_operator" in bundle
        assert b"context-bundle" in bundle
        assert b"graph-diff" in bundle
        assert b"check-update" in skill
        assert b"Normal data, login, message, and Vault commands" in bundle
        assert b"never creates lexical/full-text indexes" in bundle
        assert b"VM_SKILL_DIR" in skill
        assert b"Never invoke a bare global" in skill
        assert b"Do not use curl, direct API calls" in skill
        assert len(skill) < 8_000
        assert b"Do not preload every reference" in skill
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


def test_legacy_cli_receives_a_two_file_recovery_manifest(client):
    client.headers.pop("Authorization")
    legacy = client.get(
        "/skills/vibe-memory/manifest.json",
        headers={"User-Agent": "VibeMemoryCLI/3.9.1"},
    ).json()
    bootstrap = client.get(
        "/skills/vibe-memory/manifest.json",
        headers={"User-Agent": "VibeMemoryBootstrap/3.0"},
    ).json()
    modern = client.get(
        "/skills/vibe-memory/manifest.json",
        headers={"User-Agent": "VibeMemoryCLI/3.11.0"},
    ).json()
    progressive = client.get("/skills/vibe-memory/manifest-v2.json").json()

    assert legacy == bootstrap
    assert legacy["schema_version"] == 1
    assert set(legacy["files"]) == {"SKILL.md", "scripts/memory.py"}
    assert legacy["release_assets"] == {
        "SKILL.md": "SKILL-legacy.md",
        "scripts/memory.py": "memory.py",
    }
    assert legacy["compatibility"]["progressive_manifest"] == "manifest-v2.json"
    assert modern["schema_version"] == 2
    assert modern == progressive

    revision = hashlib.sha256(
        json.dumps(legacy["files"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert legacy["revision"] == revision
    for name, digest in legacy["files"].items():
        release = client.get(
            "/skills/vibe-memory/releases/" + legacy["revision"] + "/" + name
        )
        assert release.status_code == 200
        assert hashlib.sha256(release.content).hexdigest() == digest
    assert b"legacy update bridge" in client.get(
        "/skills/vibe-memory/releases/" + legacy["revision"] + "/SKILL.md"
    ).content


def test_bootstrap_selects_and_verifies_native_binary(tmp_path, monkeypatch):
    installed = tmp_path / "installed"
    (installed / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/vibe-memory/scripts/memory.py", installed / "scripts/memory.py")
    launcher = load_launcher(installed / "scripts/memory.py", "native_bootstrap")
    binary = b"native-rust-binary-for-test"
    digest = hashlib.sha256(binary).hexdigest()
    target_name = launcher.platform_target()
    manifest = {
        "files": {"SKILL.md": "0" * 64, "scripts/memory.py": "0" * 64},
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
    monkeypatch.setattr(launcher, "fetch_manifest", lambda url: manifest)
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


def test_skill_commands_are_anchored_to_the_loaded_skill_directory():
    skill = skill_bundle(ROOT / "skills/vibe-memory/SKILL.md")
    assert 'python3 "$VM_SKILL_DIR/scripts/memory.py" sync' in skill
    assert 'VM_CLI="$VM_SKILL_DIR/bin/vibe-memory"' in skill
    assert '$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"' in skill
    assert "canonical time basis for Vibe Memory is UTC" in skill
    assert "Never guess a missing UTC offset or time zone" in skill
    assert "Do not wait for the user to repeat" in skill
    assert "Do not repeatedly ask whether to perform ordinary recall or checkpointing" in skill
    assert "automatically checkpoint meaningful state changes" in skill
    assert "run `python3 scripts/memory.py" not in skill
    assert "execute `./bin/vibe-memory`" not in skill
    assert "releases/latest/download/vibe-memory-skill.zip" in skill
    assert "Cloudflare `1010`" in skill


def test_all_skill_variants_offer_repeatable_memory_hygiene():
    skill_paths = [
        ROOT / "skills/vibe-memory/SKILL.md",
        ROOT / "claude-plugins/vibe-memory/skills/vibe-memory/SKILL.md",
        ROOT / "plugins/vibe-memory/skills/vibe-memory/SKILL.md",
    ]
    for path in skill_paths:
        skill = skill_bundle(path)
        assert "## Periodic memory hygiene prompt" in skill
        assert "관계 그래프를 최신화하고 기억을 한 번 최적화할까요?" in skill
        assert "Do not impose a once-per-session quota" in skill
        assert "ask again whenever later accumulated changes" in skill
        assert "A decline or no reply applies only to that moment" in skill
        assert "the agent may offer again" in skill
        assert "Avoid immediate repeated prompts" in skill
        assert "ordinary proactive recall and checkpointing" in skill


def test_all_skill_variants_teach_retrievable_record_authoring():
    skill_paths = [
        ROOT / "skills/vibe-memory/SKILL.md",
        ROOT / "claude-plugins/vibe-memory/skills/vibe-memory/SKILL.md",
        ROOT / "plugins/vibe-memory/skills/vibe-memory/SKILL.md",
    ]
    for path in skill_paths:
        skill = skill_bundle(path)
        assert "## Authoring records that can be found again" in skill
        assert "Project context — good" in skill
        assert "Decision — good" in skill
        assert "Failure — good" in skill
        assert "Checkpoint — good" in skill
        assert "Correction — good" in skill
        assert "optionally verify retrieval once" in skill
        assert "Do not add verification calls to every save" in skill


def test_bootstrap_rejects_tampering_and_untrusted_configuration(tmp_path, monkeypatch):
    installed = tmp_path / "installed"
    (installed / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/vibe-memory/scripts/memory.py", installed / "scripts/memory.py")
    launcher = load_launcher(installed / "scripts/memory.py", "tampered_bootstrap")
    target_name = launcher.platform_target()
    manifest = {
        "files": {"SKILL.md": "0" * 64, "scripts/memory.py": "0" * 64},
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
    monkeypatch.setattr(launcher, "fetch_manifest", lambda url: manifest)
    monkeypatch.setattr(launcher, "fetch_release", lambda url: b"tampered")
    monkeypatch.setattr(launcher, "origin", lambda: "https://vibememory.io")
    with pytest.raises(ValueError, match="checksum mismatch"):
        launcher.ensure_cli()
    assert not launcher.executable_path().exists()
    launcher = load_launcher(installed / "scripts/memory.py", "untrusted_bootstrap")
    monkeypatch.setenv("MEMORY_URL", "http://untrusted.example")
    with pytest.raises(ValueError, match="HTTPS"):
        launcher.origin()


def test_bootstrap_separates_official_distribution_from_service_origin(tmp_path):
    installed = tmp_path / "installed"
    (installed / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/vibe-memory/scripts/memory.py", installed / "scripts/memory.py")
    launcher = load_launcher(installed / "scripts/memory.py", "distribution_origin_bootstrap")
    assert launcher.manifest_url("https://vibememory.io") == launcher.OFFICIAL_MANIFEST_URL
    assert launcher.manifest_url("https://memory.example.com") == (
        "https://memory.example.com/skills/vibe-memory/manifest-v2.json"
    )
    assert launcher.manifest_url("http://localhost:8080") == (
        "http://localhost:8080/skills/vibe-memory/manifest-v2.json"
    )
    assert launcher.manifest_urls("https://vibememory.io") == (
        launcher.OFFICIAL_MANIFEST_URL,
        launcher.OFFICIAL_LEGACY_MANIFEST_URL,
    )


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

    legacy_manifest = json.loads(
        (public / "skills/vibe-memory/manifest-v1.json").read_text()
    )
    legacy_revision = hashlib.sha256(
        json.dumps(
            legacy_manifest["files"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert legacy_revision == legacy_manifest["revision"]
    legacy_release = public / "skills/vibe-memory/releases" / legacy_revision
    for name, digest in legacy_manifest["files"].items():
        assert hashlib.sha256((legacy_release / name).read_bytes()).hexdigest() == digest
