import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_cli(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_public_distribution_matches_sources_and_zip(client):
    import io
    import zipfile

    client.headers.pop("Authorization")
    response = client.get("/skills/vibe-memory/manifest.json")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    manifest = response.json()
    with zipfile.ZipFile(io.BytesIO(client.get(manifest["archive"]).content)) as archive:
        cli = manifest["cli"]
        cli_data = client.get(cli["url"]).content
        assert hashlib.sha256(cli_data).hexdigest() == cli["sha256"]
        assert cli_data == (ROOT / "skills/vibe-memory" / cli["path"]).read_bytes()
        assert archive.read("vibe-memory/" + cli["path"]) == cli_data
        assert archive.getinfo("vibe-memory/" + cli["path"]).external_attr >> 16 & 0o111
        for name, digest in manifest["files"].items():
            release = client.get(
                "/skills/vibe-memory/releases/" + manifest["revision"] + "/" + name
            )
            assert release.status_code == 200
            assert hashlib.sha256(release.content).hexdigest() == digest
            assert release.content == (ROOT / "skills/vibe-memory" / name).read_bytes()
            assert archive.read("vibe-memory/" + name) == release.content


def test_updater_refreshes_and_rejects_tampered_release(tmp_path, monkeypatch):
    public = tmp_path / "public"
    shutil.copytree(ROOT / "landing/dist/skills", public / "skills")
    installed = tmp_path / "installed"
    shutil.copytree(ROOT / "skills/vibe-memory", installed)
    adapter = load_cli(installed / "bin/vibe-memory", "skill_adapter")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(public))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("MEMORY_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.delenv("MEMORY_API_KEY", raising=False)
    try:
        assert adapter.sync_skill()["updated"] is False
        (installed / "SKILL.md").write_text("old instructions")
        assert adapter.sync_skill()["updated"] is True
        assert (installed / "SKILL.md").read_bytes() == (
            ROOT / "skills/vibe-memory/SKILL.md"
        ).read_bytes()
        assert adapter.sync_skill()["updated"] is False
        manifest = json.loads((public / "skills/vibe-memory/manifest.json").read_text())
        (installed / "bin/vibe-memory").write_text("old cli")
        assert adapter.sync_skill()["updated"] is True
        assert (
            hashlib.sha256((installed / "bin/vibe-memory").read_bytes()).hexdigest()
            == (manifest["cli"]["sha256"])
        )
        assert adapter.sync_skill()["updated"] is False
        (installed / "SKILL.md").write_text("old instructions")
        release = public / "skills/vibe-memory/releases" / manifest["revision"]
        (release / "SKILL.md").write_text("tampered")
        with pytest.raises(ValueError, match="checksum mismatch"):
            adapter.sync_skill()
        assert (installed / "SKILL.md").read_text() == "old instructions"
        monkeypatch.setenv("MEMORY_URL", "http://untrusted.example")
        with pytest.raises(ValueError, match="HTTPS"):
            adapter.sync_skill()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_changed_instructions_stop_before_api(monkeypatch):
    adapter = load_cli(ROOT / "skills/vibe-memory/bin/vibe-memory", "skill_cli")
    monkeypatch.setattr(adapter, "sync_skill", lambda: {"updated": True})
    calls = []
    monkeypatch.setattr(adapter, "call", lambda *args: calls.append(args))
    monkeypatch.setattr("sys.argv", ["memory.py", "recall", "tea"])
    with pytest.raises(RuntimeError, match="Read SKILL.md again"):
        adapter.main()
    assert calls == []


def test_compatibility_launcher_bootstraps_verified_cli(tmp_path, monkeypatch):
    public = tmp_path / "public"
    shutil.copytree(ROOT / "landing/dist/skills", public / "skills")
    installed = tmp_path / "installed"
    shutil.copytree(ROOT / "skills/vibe-memory", installed)
    (installed / "bin/vibe-memory").unlink()
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(public))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = {**os.environ, "MEMORY_URL": f"http://127.0.0.1:{server.server_port}"}
        result = subprocess.run(
            [sys.executable, str(installed / "scripts/memory.py"), "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert "Vibe Memory CLI" in result.stdout
        manifest = json.loads((public / "skills/vibe-memory/manifest.json").read_text())
        assert (
            hashlib.sha256((installed / "bin/vibe-memory").read_bytes()).hexdigest()
            == (manifest["cli"]["sha256"])
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
