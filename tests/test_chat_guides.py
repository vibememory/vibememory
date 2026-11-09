import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_general_chat_guides_cover_chatgpt_and_claude():
    data = json.loads((ROOT / "landing/data/chat-guides.json").read_text())
    assert data["time_basis"] == "UTC"
    assert data["mcp_url"] == "https://vibememory.io/mcp"
    guides = {guide["id"]: guide for guide in data["guides"]}
    assert set(guides) == {"chatgpt", "claude"}
    assert "chatgpt.com/plugins/" in guides["chatgpt"]["connect_url"]
    assert guides["claude"]["connect_url"] == "https://claude.ai/customize/connectors"
    for guide in guides.values():
        assert len(guide["steps"]) == 4
        assert guide["works"]
        assert guide["limits"]
        assert guide["starter_prompt"]
        assert guide["verify_prompts"]
        assert guide["remove_steps"]
        assert all(doc["url"].startswith("https://") for doc in guide["official_docs"])


def test_general_chat_guides_are_linked_from_public_entry_points():
    index = (ROOT / "landing/templates/index.html").read_text()
    guide = (ROOT / "landing/templates/guide.html").read_text()
    surface = json.loads((ROOT / "landing/data/surface-support.json").read_text())

    assert 'href="/guide/chat"' in index
    assert 'href="/guide/chatgpt"' in guide
    assert 'href="/guide/claude"' in guide
    urls = {
        surface_item["id"]: surface_item["connection_url"]
        for provider in surface["providers"]
        for surface_item in provider["surfaces"]
    }
    assert urls["chatgpt-chat"] == "/guide/chatgpt"
    assert urls["claude-chat"] == "/guide/claude"


def test_general_chat_routes_and_styles_are_present():
    for route in ("chat", "chatgpt", "claude"):
        assert (ROOT / f"landing/app/guide/{route}/page.tsx").is_file()
    css = (ROOT / "landing/public/assets/chat-guide.css").read_text()
    assert ".chat-directory-grid" in css
    assert ".chat-guide-hero" in css
    assert "@media(max-width:720px)" in css
