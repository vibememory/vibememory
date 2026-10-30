import io
import zipfile

import pytest
from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app


def test_console_and_api_share_one_origin(settings):
    settings = settings.model_copy(update={"public_origin": "http://testserver"})
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        for route, phrase in [
            ("/", "Vibe Memory"),
            ("/login", "auth-form"),
            ("/console", "console-main"),
            ("/admin", "admin-main"),
            ("/guide", "Vibe Memory"),
            ("/capture", "capture-form"),
        ]:
            response = client.get(route)
            assert response.status_code == 200
            assert phrase in response.text
        landing = client.get("/").text
        guide = client.get("/guide").text
        login = client.get("/login").text
        capture = client.get("/capture").text
        console = client.get("/console").text
        admin = client.get("/admin").text
        connect = client.get("/connect").text
        install_script = client.get("/assets/install-prompt.js")
        locale_script = client.get("/assets/i18n.js")
        console_script = client.get("/assets/console.js")
        console_styles = client.get("/assets/console.css")
        ui_script = client.get("/assets/ui-kit.js")
        ui_styles = client.get("/assets/ui-kit.css")
        admin_script = client.get("/assets/admin.js")
        admin_styles = client.get("/assets/admin.css")
        landing_script = client.get("/assets/app.js")
        login_script = client.get("/assets/login.js")
        capture_script = client.get("/assets/capture.js")
        landing_styles = client.get("/assets/style.css")
        product_styles = client.get("/assets/product-ui.css")
        icon_sprite = client.get("/assets/icons.svg")
        social_image = client.get("/assets/og-vibe-memory-v2.png")
        web_manifest = client.get("/site.webmanifest")
        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")
        llms = client.get("/llms.txt")
        assert "Vibe Memory — AI 에이전트를 위한 공유 기억 레이어" in landing
        assert 'rel="canonical" href="https://vibememory.io"' in landing
        assert 'name="twitter:card" content="summary_large_image"' in landing
        assert 'property="og:image" content="https://vibememory.io/assets/og-vibe-memory-v2.png"' in landing
        assert 'type="application/ld+json"' in landing
        assert '"@type":"SoftwareApplication"' in landing
        assert '"@type":"WebSite"' in landing
        assert '"@type":"TechArticle"' in guide
        assert 'rel="canonical" href="https://vibememory.io/guide"' in guide
        for auth_page in (login, capture, connect):
            assert 'class="auth-header"' in auth_page
            assert 'class="header-actions auth-header-actions"' in auth_page
        assert social_image.status_code == 200
        assert social_image.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert web_manifest.status_code == 200
        assert web_manifest.json()["name"] == "Vibe Memory"
        assert robots.status_code == 200
        assert "Disallow: /v1/" in robots.text
        assert sitemap.status_code == 200
        assert "https://vibememory.io/guide" in sitemap.text
        assert llms.status_code == 200
        assert "Vibe Memory does not call an LLM" in llms.text
        assert install_script.status_code == 200
        assert "Skip this step for other agents" not in install_script.text
        assert "Identify the current agent host first" in install_script.text
        assert "tree/main/agent-adapters" in install_script.text
        assert "${adapterRoot}/codex" in install_script.text
        assert "${adapterRoot}/cursor" in install_script.text
        assert "${adapterRoot}/muse" in install_script.text
        assert "${adapterRoot}/hermes" in install_script.text
        assert "loop_limit: 1" in install_script.text
        assert "nonexistent muse hooks command" in install_script.text
        assert "hooks_auto_accept: false" in install_script.text
        assert "openclaw plugins install --link ./agent-adapters/openclaw" in install_script.text
        assert "openclaw plugins inspect vibe-memory-hooks --runtime --json" in install_script.text
        assert "Work Cloud without local command execution" in install_script.text
        assert locale_script.status_code == 200
        assert console_script.status_code == 200
        assert console_styles.status_code == 200
        assert ui_script.status_code == 200
        assert ui_styles.status_code == 200
        assert admin_script.status_code == 200
        assert admin_styles.status_code == 200
        assert landing_script.status_code == 200
        assert login_script.status_code == 200
        assert capture_script.status_code == 200
        assert landing_styles.status_code == 200
        assert product_styles.status_code == 200
        assert icon_sprite.status_code == 200
        assert '<symbol id="sparkles"' in icon_sprite.text
        assert '<symbol id="copy"' in icon_sprite.text
        assert '<symbol id="external-link"' in icon_sprite.text
        assert '/assets/icons.svg#sparkles' in landing
        assert '/assets/icons.svg#copy' in landing
        assert '/assets/icons.svg#external-link' in landing
        assert 'class="landing-page"' in landing
        assert "Readable landing typography" in landing_styles.text
        assert "Large-screen readability pass" in landing_styles.text
        assert ".landing-page .feature p{font-size:14px}" in landing_styles.text
        assert ".landing-page .faq details p{font-size:14px}" in landing_styles.text
        assert ".landing-page .feature p{font-size:15px}" in landing_styles.text
        assert ".landing-page .faq details p{font-size:15px}" in landing_styles.text
        assert ".landing-page .hero-connect{padding:0;border:0;border-radius:0;background:none;box-shadow:none}" in landing_styles.text
        assert ".landing-page .hero{align-items:center}" in landing_styles.text
        assert ".landing-page .hero-copy{padding-top:0}" in landing_styles.text
        assert ".landing-page .hero-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))" in landing_styles.text
        assert "스킬 설치 프롬프트 복사" in landing
        assert "data-copy-install-prompt" in landing
        assert "ChatGPT Work에 바로 설치" in landing
        assert "Claude에서 사용" in landing
        assert "사용할 서비스들에" not in landing
        assert 'id="connect-ways-title"' not in landing
        assert 'aria-label="Vibe Memory 연결 방법"' in landing
        assert 'class="skill-agent-tools"' in landing
        assert "Claude Code" in landing
        assert "Codex" in landing
        assert "Cursor" in landing
        assert "Muse Code" in landing
        assert "OpenClaw" in landing
        assert "Hermes" in landing
        assert '/assets/brands/cursor.svg' in landing
        assert '/assets/brands/muse.svg' in landing
        assert "edge-support" not in landing
        assert 'class="mini-graph"' not in landing
        assert 'class="relation-preview"' not in landing
        assert 'class="life-graph"' in landing
        assert "여름 여행" in landing
        assert "아이스 아메리카노" in landing
        assert "사이드 프로젝트" in landing
        assert "저녁 러닝" in landing
        assert 'class="hero-connect"' in landing
        assert 'class="button button-outline" href="/guide"' in landing
        assert 'class="hero-support"' in landing
        assert 'class="memory-showcase wrap"' in landing
        assert 'class="connect-ways wrap section"' not in landing
        assert landing.index('class="hero-connect"') < landing.index('id="how"')
        assert 'href="https://chatgpt.com/plugins/plugins_6ae31884dce08191b5b77fc3e1844cec"' in landing
        assert 'href="https://claude.ai/customize/connectors"' in landing
        assert 'data-use-mcp="chatgpt"' in landing
        assert "`${location.origin}/mcp`" in landing_script.text
        assert '<script src="/assets/theme-init.js?v=20261030-v029-1"></script>' in landing
        assert '<link rel="stylesheet" href="/assets/theme.css?v=20261030-v029-1"' in landing
        assert '<link rel="stylesheet" href="/assets/product-ui.css?v=20261030-v029-1"' in landing
        assert '<script src="/assets/theme.js?v=20261030-v029-1" defer="">' in landing
        assert '<script src="/assets/i18n.js?v=20261030-v029-1" defer="">' in landing
        assert '<script src="/assets/install-prompt.js?v=20261030-v029-1" defer="">' in landing
        assert '<script src="/assets/app.js?v=20261030-v029-1" defer="">' in landing
        assert '<script src="/assets/vendor/cytoscape.min.js?v=20261030-v029-1" defer="">' in console
        assert '<script src="/assets/ui-kit.js?v=20261030-v029-1" defer="">' in console
        assert '<script src="/assets/console.js?v=20261030-v029-1" defer="">' in console
        assert '<script src="/assets/ui-kit.js?v=20261030-v029-1" defer="">' in admin
        assert '<script src="/assets/admin.js?v=20261030-v029-1" defer="">' in admin
        assert 'self.__next_s||[]).push(["/assets/i18n.js"' not in landing
        assert landing.index("/assets/install-prompt.js") < landing.index("/assets/app.js")
        assert console.index("/assets/install-prompt.js") < console.index("/assets/console.js")
        assert console.index("/assets/ui-kit.js") < console.index("/assets/console.js")
        assert admin.index("/assets/ui-kit.js") < admin.index("/assets/admin.js")
        assert 'class="ui-flyout" id="detail-dialog"' in console
        assert 'class="ui-modal ui-modal--compact" id="confirm-dialog"' in console
        assert "window.VMUI.openFlyout" in console_script.text
        assert "window.VMUI.confirm" in console_script.text
        assert "function openFlyout" in ui_script.text
        assert ".ui-flyout.is-open" in ui_styles.text
        assert "window.confirm(" not in console_script.text
        assert "manage-agent-permissions" in console_script.text
        assert "manage-mcp-permissions" in console_script.text
        assert console.index(">CONNECT</p>") < console.index('data-view="mcp"')
        assert console.index('data-view="mcp"') < console.index('data-view="agents"')
        assert console.index('data-view="agents"') < console.index(">WORKSPACE</p>")
        assert console.index(">WORKSPACE</p>") < console.index(">MANAGE</p>")
        assert 'data-view="keys"' not in console
        assert "view === 'mcp'" in console_script.text
        assert "view === 'agents'" in console_script.text
        assert "requestedView === 'keys' ? 'agents'" in console_script.text
        assert "const mcp = await api('/auth/mcp-connections');" in console_script.text
        assert "const result = await api('/auth/api-keys');" in console_script.text
        assert "Promise.all([api('/auth/api-keys'), api('/auth/mcp-connections')])" not in console_script.text
        assert "/auth/mcp-connections/" in console_script.text
        assert "MCP 연결 권한을 저장했습니다." in console_script.text
        assert "/permission-events?limit=5" in console_script.text
        assert "agent-permission-list" in console_styles.text
        assert "설치·최신화 프롬프트 복사" in console_script.text
        assert "vibeMemoryInstallPrompt" in console_script.text
        assert "icon('copy')" in console_script.text
        assert '설치 프롬프트 복사 ⧉' not in console_script.text
        assert "if (currentView === 'overview') return copyInstallPrompt();" in console_script.text
        assert "async function copyInstallPrompt()" in console_script.text
        assert "vibeMemoryInstallPrompt" in landing_script.text
        assert "fetch('/auth/me', {cache:'no-store', credentials:'same-origin'})" in landing_script.text
        assert "window.location.replace('/console')" in landing_script.text
        assert "/auth/login/otp" in login_script.text
        assert 'data-view="security"' in console
        assert "/auth/totp/setup" in console_script.text
        assert "/auth/totp/recovery-codes" in console_script.text
        assert ".security-card" in console_styles.text
        assert "location.hash.slice(1)" in capture_script.text
        assert "sessionStorage.setItem('vibe-memory-vault-capture'" in capture_script.text
        assert "history.replaceState(null, '', '/capture')" in capture_script.text
        assert "location.origin" in install_script.text
        assert "releases/latest/download/vibe-memory-skill.zip" in install_script.text
        assert "releases/latest/download/SKILL.md" in install_script.text
        assert "login --url" in install_script.text
        assert "--vault-access --no-browser" in install_script.text
        assert 'id="vault-access" type="checkbox" checked' in connect
        assert 'class="ui-choice-card ui-choice-card--sensitive"' in connect
        assert 'class="ui-choice-control"' in connect
        assert 'class="ui-choice-state"' in connect
        assert '/assets/ui-kit.css?v=20261030-v029-1' in connect
        assert '/assets/theme.css?v=20261030-v029-1' in connect
        assert '/assets/product-ui.css?v=20261030-v029-1' in connect
        theme_init_script = client.get("/assets/theme-init.js").text
        theme_script = client.get("/assets/theme.js").text
        theme_styles = client.get("/assets/theme.css").text
        assert "prefers-color-scheme: dark" in landing
        assert "localStorage.getItem('vm-theme')" in theme_init_script
        assert landing.index('<script src="/assets/theme-init.js') < landing.index('<link rel="stylesheet" href="/assets/theme.css')
        assert "window.vmTheme" in theme_script
        assert "vm-theme-change" in theme_script
        assert 'id="moon"' in client.get("/assets/icons.svg").text
        assert 'id="sun"' in client.get("/assets/icons.svg").text
        assert 'html[data-theme="dark"]' in theme_styles
        assert "relationshipGraphStyles" in console_script.text
        assert "'width':192" in console_script.text
        assert "'font-size':12" in console_script.text
        assert "vm-theme-change" in console_script.text
        assert "--sidebar-width: 260px" in product_styles.text
        assert '.sidebar nav button[aria-current="page"] { box-shadow: none; }' in product_styles.text
        assert "inset 3px 0 0 var(--tool-blue)" not in product_styles.text
        assert ".auth-header-actions .vm-theme-toggle" in product_styles.text
        assert "position: static !important" in product_styles.text
        assert ".landing-page .header-actions .vm-language-switcher" in product_styles.text
        assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in product_styles.text
        assert "min-height: 108px" in product_styles.text
        assert '.ui-choice-input:checked+.ui-choice-control' in ui_styles.text
        assert '.ui-choice-card--sensitive:has(.ui-choice-input:checked)' in ui_styles.text
        assert "Vault 권한:" in client.get("/assets/connect.js").text
        assert "기본 맥락 계층으로 적극 사용해" in install_script.text
        assert "default continuity layer, not an optional command" in install_script.text
        assert "Do not wait for me to repeat" in install_script.text
        assert install_script.text.count("vault capture") == 7
        assert "canonical time basis is UTC" in install_script.text
        assert "标准时间为 UTC" in install_script.text
        assert "基準時刻はUTC" in install_script.text
        assert "base temporal canónica" in install_script.text
        assert "Mốc thời gian chuẩn của Vibe Memory là UTC" in install_script.text
        assert "เวลามาตรฐานของ Vibe Memory คือ UTC" in install_script.text
        assert "['ko', 'en', 'zh', 'ja', 'es', 'vi', 'th']" in locale_script.text
        assert "Một bộ nhớ cho mọi tác nhân" in locale_script.text
        assert "หนึ่งความทรงจำสำหรับทุกเอเจนต์" in locale_script.text
        assert "vm-language" in locale_script.text
        assert "window.vmSetLocale = setLocale" in locale_script.text
        assert "guideHtmlRows" in locale_script.text
        assert "attributeFilter:['placeholder','aria-label','title']" in locale_script.text
        assert "Cursor, Muse Code, OpenClaw" in console_script.text
        assert "_next/static" in landing
        assert "vault exec" in console_script.text
        assert "/v1/vault-access-audit?limit=100" in console_script.text
        assert "비밀키 조회 내역" in console_script.text
        assert "비밀값 원문은 감사 기록에 저장되지 않습니다." in console_script.text
        assert ".vault-audit-status.success" in console_styles.text
        assert "relationship-graph-stage" in console_script.text
        assert "window.cytoscape" in console_script.text
        assert "name:records.length > 1 ? 'cose' : 'grid'" in console_script.text
        assert "foreignObject" not in console_script.text
        assert "classList.toggle('is-graph-view', view === 'relations')" in console_script.text
        assert "function viewFromLocation()" in console_script.text
        assert "location.hash.slice(1)" in console_script.text
        assert "history[mode === 'replace' ? 'replaceState' : 'pushState']" in console_script.text
        assert "await navigate(viewFromLocation(), true, 'replace')" in console_script.text
        assert "window.addEventListener('popstate'" in console_script.text
        assert "function dashboardGuideHidden()" in console_script.text
        assert "localStorage.setItem(dashboardGuideKey, '1')" in console_script.text
        assert 'data-action="dismiss-dashboard-guide"' in console_script.text
        assert "Dashboard console: operational data first" in console_styles.text
        assert "내 기억 용량" in console_script.text
        assert "formatBytes(stats.storage_bytes)" in console_script.text
        assert ".storage-usage-card" in console_styles.text
        assert "처리 결과" in console_script.text
        assert "featureRequestDetail" in console_script.text
        assert ".request-status.completed" in console_styles.text
        assert 'id="admin-link" href="/admin" hidden' in console
        assert "if (data.is_admin) $('#admin-link').hidden = false" in console_script.text
        assert "/v1/admin/feature-requests" in admin_script.text
        assert "/v1/admin/operator-agents" in admin_script.text
        assert "운영 에이전트로 승인" in admin_script.text
        assert 'id="operator-agent-list"' in admin
        assert 'request-edit-title' in admin
        assert 'request-edit-description' in admin
        assert 'request-edit-priority' in admin
        assert "title:$('#request-edit-title').value" in admin_script.text
        assert "user.totp_enabled" in admin_script.text
        assert "PRODUCT OPERATIONS" in admin
        assert ".admin-stats" in admin_styles.text
        assert "Console UI refresh" in console_styles.text
        assert ".console-page{\n  --sidebar-width:280px" in console_styles.text
        assert ".welcome-panel{grid-template-columns:minmax(0,1fr);gap:22px" in console_styles.text
        assert ".topbar-actions{min-width:0;flex:0 0 auto}" in console_styles.text
        assert "/auth/mcp-connections" in console_script.text
        assert "copy-mcp-url" in console_script.text
        assert console.index("/assets/vendor/cytoscape.min.js") < console.index("/assets/console.js")
        assert client.get("/assets/vendor/cytoscape.min.js").status_code == 200
        assert "visibleIds.size + additions > 21" in console_script.text
        assert "visibleRelations.length >= 36" in console_script.text
        assert client.get("/assets/console-fixes.css").status_code == 200
        assert "prefers-reduced-motion" in client.get("/assets/console.css").text
        assert "topbar-search" in console
        assert "sidebar-backdrop" in console
        assert 'data-view="vault"' in console
        assert "vault-scope" in client.get("/connect").text
        assert client.get("/assets/brands/openclaw.svg").status_code == 200
        assert client.get("/v1/records").status_code == 401
        assert client.get("/.env").status_code == 404
        assert client.get("/../../.env").status_code == 404
        signup = client.post(
            "/auth/signup",
            headers={"Origin": "http://testserver"},
            json={
                "name": "Self host",
                "email": "selfhost@example.invalid",
                "password": "long-enough-password",
            },
        )
        assert signup.status_code == 200, signup.text
        stats = client.get("/v1/stats").json()
        assert stats["memory"] == 0
        assert stats["storage_bytes"] == 0
        key = client.post(
            "/auth/api-keys",
            headers={"Origin": "http://testserver"},
            json={"name": "Self-hosted agent"},
        )
        assert key.status_code == 201
        result = client.post(
            "/v1/memories",
            headers={"Authorization": "Bearer " + key.json()["key"]},
            json={"content": "Self-hosted memory", "keywords": ["Python"]},
        )
        assert result.status_code == 201, result.text
        assert result.json()["created_at"].endswith("+00:00")
        assert client.get("/v1/records").json()["items"][0]["id"] == result.json()["id"]
        archive = client.get("/downloads/vibe-memory-skill.zip")
        with zipfile.ZipFile(io.BytesIO(archive.content)) as skill:
            assert set(skill.namelist()) == {
                "vibe-memory/SKILL.md",
                "vibe-memory/scripts/memory.py",
            }


def test_explicit_web_directory_rejects_missing_index(settings, tmp_path):
    with pytest.raises(ValueError, match="MEMORY_WEB_DIR"):
        create_app(settings.model_copy(update={"web_dir": tmp_path / "missing"}), SpyEmbedder())
