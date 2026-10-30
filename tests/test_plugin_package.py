import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "vibe-memory"


def test_chatgpt_work_plugin_package():
    manifest = json.loads((PLUGIN / "plugin.json").read_text())
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["name"] == "vibe-memory"
    # Public-directory packages must remain usable without local lifecycle hooks.
    assert "hooks" not in manifest
    assert len(manifest["extensions"]["com.openai"]["interface"]["shortDescription"]) <= 30
    assert (PLUGIN / manifest["extensions"]["com.openai"]["interface"]["logo"]).is_file()

    mcp = json.loads((PLUGIN / "mcp.json").read_text())
    server = mcp["mcpServers"]["vibe-memory"]
    assert server["type"] == "streamable-http"
    assert server["url"] == "https://vibememory.io/mcp"
    auth = server["extensions"]["com.openai"]["auth"]
    assert auth["type"] == "oauth"
    assert auth["client"] == {"mode": "dcr"}
    assert set(auth["defaultScopes"]) == {
        "memory:read",
        "memory:write",
        "feature:write",
        "vault:read",
    }

    skill = (PLUGIN / "skills" / "vibe-memory" / "SKILL.md").read_text()
    _, frontmatter, body = skill.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["name"] == "vibe-memory"
    assert "memory_search" in body
    assert "memory_create" in body
    assert "without waiting" in metadata["description"]

    agent = yaml.safe_load(
        (PLUGIN / "skills" / "vibe-memory" / "agents" / "openai.yaml").read_text()
    )
    assert agent["policy"]["allow_implicit_invocation"] is True
