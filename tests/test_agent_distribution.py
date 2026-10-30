import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    path = ROOT / "scripts/check_agent_distribution.py"
    spec = importlib.util.spec_from_file_location("agent_distribution_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_distribution_check_explains_cloudflare_1010_without_unsafe_bypass(monkeypatch):
    checker = load_checker()

    def blocked(*_args, **_kwargs):
        raise HTTPError(
            "https://vibememory.io/downloads/vibe-memory-skill.zip",
            403,
            "Forbidden",
            {},
            io.BytesIO(b"error code: 1010\n"),
        )

    monkeypatch.setattr(checker, "urlopen", blocked)
    with pytest.raises(RuntimeError, match="path-scoped Browser Integrity Check") as failure:
        checker.fetch("https://vibememory.io/downloads/vibe-memory-skill.zip", 1024)
    assert "do not disable TLS verification" in str(failure.value)
