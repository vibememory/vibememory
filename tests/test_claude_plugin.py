import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text())


def test_claude_marketplace_packages_nonblocking_lifecycle_hooks():
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    marketplace = load_json(".claude-plugin/marketplace.json")
    entry = marketplace["plugins"][0]
    assert marketplace["name"] == "vibe-memory"
    assert entry["name"] == "vibe-memory"
    assert entry["source"] == "./claude-plugins/vibe-memory"
    assert entry["version"] == project_version

    manifest = load_json("claude-plugins/vibe-memory/.claude-plugin/plugin.json")
    assert manifest["name"] == "vibe-memory"
    assert manifest["version"] == project_version

    hooks = load_json("claude-plugins/vibe-memory/hooks/hooks.json")["hooks"]
    expected = {
        "SessionStart": "session-start",
        "Stop": "stop",
        "PreCompact": "pre-compact",
    }
    assert set(hooks) == set(expected)
    for event, command in expected.items():
        handler = hooks[event][0]["hooks"][0]
        assert handler["type"] == "command"
        assert handler["command"] == "vibe-memory"
        assert handler["args"] == ["hook", command]
        assert handler.get("onFailure") != "block"
        assert handler["timeout"] <= 10

    skill = (ROOT / "claude-plugins/vibe-memory/skills/vibe-memory/SKILL.md").read_text()
    assert "20-minute" in skill
    assert "Never store secrets" in skill
    assert "without blocking compaction" in skill
