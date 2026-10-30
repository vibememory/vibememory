import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_support_matrix_is_shared_and_honest():
    data = json.loads((ROOT / "landing/data/agent-support.json").read_text())
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
    guide = (ROOT / "landing/templates/guide.html").read_text()
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
        assert agent["installation_url"].split("#", 1)[1] in guide

    component = (ROOT / "landing/components/AgentSupportMatrix.tsx").read_text()
    assert 'from "@/data/agent-support.json"' in component
    assert "이 연동에 SSE 연결은 필요하지 않습니다" in component


def test_generated_agent_support_document_is_current():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_agent_support.py"), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
