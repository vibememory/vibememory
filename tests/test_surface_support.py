import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_surface_support_matrix_separates_product_runtime_capabilities():
    data = json.loads((ROOT / "landing/data/surface-support.json").read_text())
    assert data["time_basis"] == "UTC"
    assert {capability["id"] for capability in data["capabilities"]} == {
        "remote_mcp",
        "skill",
        "hooks",
        "local_runtime",
    }
    providers = {provider["id"]: provider for provider in data["providers"]}
    assert set(providers) == {"openai", "anthropic"}

    openai = {surface["id"]: surface for surface in providers["openai"]["surfaces"]}
    assert set(openai) == {"chatgpt-chat", "chatgpt-work", "codex-local"}
    assert openai["chatgpt-chat"]["capabilities"]["hooks"] == "unsupported"
    assert openai["chatgpt-work"]["capabilities"]["hooks"] == "limited"
    assert all(status == "supported" for status in openai["codex-local"]["capabilities"].values())

    anthropic = {surface["id"]: surface for surface in providers["anthropic"]["surfaces"]}
    assert set(anthropic) == {"claude-chat", "claude-desktop", "claude-cowork", "claude-code"}
    assert anthropic["claude-chat"]["capabilities"]["hooks"] == "unsupported"
    assert anthropic["claude-desktop"]["capabilities"]["local_runtime"] == "supported"
    assert all(status == "supported" for status in anthropic["claude-code"]["capabilities"].values())

    allowed = {"supported", "limited", "unsupported"}
    for provider in data["providers"]:
        assert provider["source_url"].startswith("https://")
        for surface in provider["surfaces"]:
            assert set(surface["capabilities"].values()) <= allowed
            assert surface["note"]
            assert surface["connection_url"]


def test_surface_support_is_visible_on_landing_and_guide():
    home = (ROOT / "landing/app/page.tsx").read_text()
    guide_page = (ROOT / "landing/app/guide/page.tsx").read_text()
    guide_template = (ROOT / "landing/templates/guide.html").read_text()
    component = (ROOT / "landing/components/SurfaceCapabilityGuide.tsx").read_text()

    assert "<SurfaceCapabilityGuide />" in home
    assert "<SurfaceCapabilityGuide />" in guide_page
    assert "<!-- SURFACE_SUPPORT_MATRIX -->" in guide_template
    assert 'from "@/data/surface-support.json"' in component
    assert "자동 Hook은 호스트의 생명주기 기능입니다" in component
