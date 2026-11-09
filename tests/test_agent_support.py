import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_support_matrix_is_shared_and_honest():
    data = json.loads((ROOT / "landing/data/agent-support.json").read_text())
    harnesses = json.loads((ROOT / "landing/data/harness-guides.json").read_text())
    assert data["time_basis"] == "UTC"
    assert data["sse_required"] is False
    assert {agent["id"] for agent in data["agents"]} == {
        "claude-code",
        "codex",
        "cursor",
        "muse",
        "hermes",
        "openclaw",
    }
    harness_routes = {f"/guide/{guide['slug']}" for guide in harnesses["guides"]}
    for agent in data["agents"]:
        assert agent["overall_status"] in {
            "supported",
            "in_progress",
            "planned",
            "unsupported",
            "unverified",
        }
        assert agent["verified_version"]
        assert agent["limitations"]
        assert agent["installation_url"] in harness_routes

    component = (ROOT / "landing/components/AgentSupportMatrix.tsx").read_text()
    assert 'from "@/data/agent-support.json"' in component
    assert "이 연동에 SSE 연결은 필요하지 않습니다" in component


def test_product_harness_guides_cover_every_supported_agent():
    support = json.loads((ROOT / "landing/data/agent-support.json").read_text())
    data = json.loads((ROOT / "landing/data/harness-guides.json").read_text())
    guides = data["guides"]

    assert data["time_basis"] == "UTC"
    assert data["verified_at"].endswith("Z")
    assert {guide["id"] for guide in guides} == {agent["id"] for agent in support["agents"]}
    assert len({guide["slug"] for guide in guides}) == len(guides)
    for guide in guides:
        assert guide["minimum_version"]
        assert guide["install_commands"]
        assert guide["mcp_commands"]
        assert guide["hook_adapter"]
        assert guide["config_paths"]
        assert guide["events"]
        assert guide["verify_commands"]
        assert guide["update_commands"]
        assert guide["uninstall_commands"]
        assert guide["limitation"]
        assert all(item["url"].startswith("https://") for item in guide["official_docs"])

    assert (ROOT / "landing/app/guide/harnesses/page.tsx").is_file()
    assert (ROOT / "landing/app/guide/[harness]/page.tsx").is_file()
    assert (ROOT / "landing/components/HarnessGuidePage.tsx").is_file()
    assert (ROOT / "landing/public/assets/harness-guide.css").is_file()


def test_generated_agent_support_document_is_current():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_agent_support.py"), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
