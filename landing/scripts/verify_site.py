"""Browser checks for the static landing and downloadable skill."""
import json
import sys
from pathlib import Path
import zipfile

from playwright.sync_api import sync_playwright

base = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:4321').rstrip('/')
artifacts = Path('/tmp/vibe-memory-landing-qa')
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    assert page.goto(base).status == 200
    page.wait_for_timeout(300)
    assert page.title().startswith('Vibe Memory')
    assert page.locator('h1').inner_text().startswith('에이전트가 바뀌어도')
    assert page.locator('[data-agent]').count() == 4
    for name, label in [('claude', 'Claude Code'), ('codex', 'Codex'), ('openclaw', 'OpenClaw'), ('hermes', 'Hermes')]:
        page.locator(f'[data-agent="{name}"]').click()
        assert page.locator('#agent-description').inner_text().startswith(label)
        assert page.locator(f'[data-agent="{name}"]').get_attribute('aria-pressed') == 'true'
        assert page.locator('[data-agent][aria-pressed="true"]').count() == 1
    page.locator('[data-demo="file"]').click()
    assert page.locator('#code-method').inner_text() == 'POST /v1/documents'
    assert json.loads(page.locator('#demo-code').inner_text())['file_id']
    page.locator('[data-demo="file"]').press('ArrowRight')
    assert page.locator('[data-demo="search"]').get_attribute('aria-selected') == 'true'
    assert json.loads(page.locator('#demo-code').inner_text())['keywords'] == ['개발 언어', '선호']
    context.grant_permissions(['clipboard-read', 'clipboard-write'])
    page.locator('#copy-example').click()
    assert json.loads(page.evaluate('navigator.clipboard.readText()'))['scope'] == 'memories'
    page.locator('details').first.locator('summary').click()
    assert page.locator('details').first.get_attribute('open') == ''
    with page.expect_download() as info:
        page.locator('.start-card [download]').click()
    download = info.value
    target = artifacts / 'skill.zip'
    download.save_as(target)
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == {'vibe-memory/SKILL.md', 'vibe-memory/scripts/memory.py'}
        assert b'/v1/files' in archive.read('vibe-memory/scripts/memory.py')
    page.locator('[data-demo="memory"]').click()
    page.evaluate("document.querySelector('#toast').classList.remove('visible'); window.scrollTo(0,0)")
    page.screenshot(path=str(artifacts / 'desktop.png'), full_page=True, animations='disabled')
    # Check all static page links and assets, including fragments and no accidental private URLs.
    for anchor in page.locator('a[href]').all():
        href = anchor.get_attribute('href')
        if href.startswith('#'):
            assert page.locator(href).count(), href
        elif href.startswith('/'):
            assert context.request.get(base + href).status == 200, href
        assert 'localhost:8080' not in href and '127.0.0.1:8080' not in href
    for width in [375, 390, 768, 1024, 1440]:
        page.set_viewport_size({'width': width, 'height': 900})
        page.goto(base)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'overflow at {width}px'
        boxes = page.locator('[data-agent], .memory-core').evaluate_all('(nodes) => nodes.map(node => { const r = node.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}; })')
        for i, box in enumerate(boxes):
            for other in boxes[i+1:]:
                assert not (box['left'] < other['right'] and box['right'] > other['left'] and box['top'] < other['bottom'] and box['bottom'] > other['top']), f'graph overlap at {width}px'
        if width == 390:
            page.screenshot(path=str(artifacts / 'mobile.png'), full_page=True, animations='disabled')
        page.goto(base + '/guide.html')
        assert page.locator('h1').count() == 1
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'guide overflow at {width}px'
    page.goto(base + '/404.html')
    assert page.locator('h1').inner_text().startswith('이 페이지는')
    assert not errors, errors
    browser.close()
print('PASS: graph interaction, keyboard tabs, clipboard, FAQ, real skill download, links, guide, 404, five responsive widths, no JS errors.')
print('Screenshots:', artifacts)
