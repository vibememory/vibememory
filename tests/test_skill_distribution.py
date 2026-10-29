import hashlib
import importlib.util
import json
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_public_distribution_matches_sources_and_zip(client):
    import io
    import zipfile

    client.headers.pop("Authorization")
    response = client.get("/skills/vibe-memory/manifest.json")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    manifest = response.json()
    with zipfile.ZipFile(io.BytesIO(client.get(manifest["archive"]).content)) as archive:
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
    spec = importlib.util.spec_from_file_location("skill_adapter", installed / "scripts/memory.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
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
        assert (installed / "SKILL.md").read_bytes() == (ROOT / "skills/vibe-memory/SKILL.md").read_bytes()
        assert adapter.sync_skill()["updated"] is False
        manifest = json.loads((public / "skills/vibe-memory/manifest.json").read_text())
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
    spec = importlib.util.spec_from_file_location(
        "skill_cli", ROOT / "skills/vibe-memory/scripts/memory.py"
    )
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    monkeypatch.setattr(adapter, "sync_skill", lambda: {"updated": True})
    calls = []
    monkeypatch.setattr(adapter, "call", lambda *args: calls.append(args))
    monkeypatch.setattr("sys.argv", ["memory.py", "recall", "tea"])
    with pytest.raises(RuntimeError, match="Read SKILL.md again"):
        adapter.main()
    assert calls == []
