"""Exercise real signup/login, session isolation, console actions, and revocable agent keys."""
import json
from pathlib import Path
import secrets
import sys
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

base = (sys.argv[1] if len(sys.argv) > 1 else 'https://vibememory.io').rstrip('/')
email = 'console-qa-' + uuid4().hex + '@example.invalid'
password = secrets.token_urlsafe(24)
artifacts = Path('/tmp/vibe-memory-console-qa')
artifacts.mkdir(exist_ok=True)
created = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width':1440,'height':1000})
    page = context.new_page()
    errors = []
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.goto(base + '/console')
    page.wait_for_url('**/login')
    page.locator('[data-mode="signup"]').click()
    page.locator('#name').fill('콘솔 검증')
    page.locator('#email').fill(email)
    page.locator('#password').fill(password)
    page.locator('#auth-submit').click()
    page.wait_for_url('**/console',timeout=30000)
    expect(page.locator('#view-title')).to_have_text('대시보드')
    expect(page.locator('.dashboard-guide')).to_be_visible()
    expect(page.locator('.stat-card')).to_have_count(4)
    page.locator('[data-action="dismiss-dashboard-guide"]').click()
    expect(page.locator('.dashboard-guide')).not_to_be_visible()
    page.reload()
    expect(page.locator('.dashboard-guide')).not_to_be_visible()
    expect(page.locator('.dashboard-status-panel')).to_be_visible()
    page.locator('.topbar-search').click()
    expect(page.locator('#view-title')).to_have_text('기억')
    expect(page.locator('#search-records [name="keywords"]')).to_be_focused()
    stored = [item for origin in context.storage_state()['origins'] for item in origin['localStorage']]
    assert stored == [{'name':'vibe-memory:dashboard-guide:hidden','value':'1'}], 'Only the dashboard display preference may enter localStorage'
    session = next(cookie for cookie in context.cookies() if cookie['name']=='vm_session')
    assert session['httpOnly'] and session['secure'] == base.startswith('https://') and session['sameSite']=='Lax'
    page.locator('#primary-action').click()
    page.locator('#editor [name="content"]').fill('검증용 기억: Python을 선호한다')
    page.locator('#editor [name="keywords"]').fill('Python, 개발 언어')
    page.locator('#editor-submit').click()
    expect(page.locator('#editor')).not_to_be_visible(timeout=30000)
    expect(page.locator('.record-title')).to_contain_text('Python')
    records = context.request.get(base + '/v1/records').json()['items']
    created.extend(record['id'] for record in records)
    memory_id = records[0]['id']
    page.locator('.sidebar [data-view="keys"]').click()
    page.locator('#primary-action').click()
    page.locator('#editor [name="name"]').fill('QA Claude Code')
    page.locator('#editor [name="vault_access"]').check()
    page.locator('#editor-submit').click()
    expect(page.locator('#new-key')).to_be_visible()
    agent_key = page.locator('#new-key').inner_text()
    page.locator('#detail-dialog button.close-detail').first.click()
    expect(page.locator('.records-table')).to_contain_text('QA Claude Code')
    agent = p.request.new_context(base_url=base,extra_http_headers={'Authorization':'Bearer '+agent_key})
    assert agent.get('/v1/records').json()['items'][0]['id'] == memory_id
    page.locator('.sidebar [data-view="vault"]').click()
    page.locator('#primary-action').click()
    page.locator('#editor [name="name"]').fill('CONSOLE_QA_SECRET')
    page.locator('#editor [name="description"]').fill('브라우저 검증 전용')
    page.locator('#editor [name="value"]').fill('console-qa-secret-value')
    page.locator('#editor-submit').click()
    expect(page.locator('#editor')).not_to_be_visible(timeout=30000)
    expect(page.locator('.records-table')).to_contain_text('CONSOLE_QA_SECRET')
    assert 'console-qa-secret-value' not in page.locator('body').inner_text()
    assert agent.get('/v1/vault/CONSOLE_QA_SECRET').json()['value'] == 'console-qa-secret-value'
    entity_response = agent.post('/v1/entities', data={'name':'QA developer','entity_type':'Person','keywords':['개발자']})
    assert entity_response.status == 201, entity_response.text()
    entity_id = entity_response.json()['id']; created.append(entity_id)
    relation = agent.post('/v1/relations',data={'source_id':entity_id,'target_id':memory_id,'relation':'PREFERS','reason':'QA explicit preference'})
    assert relation.status == 201
    page.locator('.sidebar [data-view="relations"]').click()
    expect(page.locator('.relationship-graph-stage')).to_be_visible()
    expect(page.locator('.relationship-graph-stage canvas')).not_to_have_count(0)
    expect(page.locator('.relationship-graph-a11y [data-action="graph"]')).to_have_count(2)
    expect(page.locator('.relationship-graph-a11y [data-action="relation-detail"]')).to_contain_text('PREFERS')
    page.locator('.relationship-graph-a11y [data-action="graph"]').first.click()
    expect(page.locator('.graph-node')).to_have_count(2)
    page.locator('#detail-dialog button.close-detail').first.click()
    page.locator('.sidebar [data-view="documents"]').click()
    page.locator('#primary-action').click()
    page.locator('#editor [type="file"]').set_input_files({'name':'console-qa.bin','mimeType':'application/octet-stream','buffer':bytes(range(256))})
    page.locator('#editor-submit').click()
    expect(page.locator('#editor')).not_to_be_visible(timeout=30000)
    expect(page.locator('.record-title')).to_have_text('console-qa.bin')
    file_record = agent.get('/v1/records?kind=file').json()['items'][0]; created.append(file_record['id'])
    assert agent.get('/v1/files/'+file_record['id']).body() == bytes(range(256))
    page.locator('.sidebar [data-view="requests"]').click()
    page.locator('#primary-action').click()
    page.locator('#editor [name="title"]').fill('콘솔 기능 요청 검증')
    page.locator('#editor [name="description"]').fill('자동 브라우저 검증에서 제출한 요청입니다.')
    page.locator('#editor-submit').click()
    expect(page.locator('#editor')).not_to_be_visible(timeout=30000)
    expect(page.locator('.record-title')).to_contain_text('콘솔 기능 요청 검증')
    # A separate browser/account must never see the first account's data or keys.
    other = browser.new_context()
    other_email = 'console-qa-' + uuid4().hex + '@example.invalid'
    result = other.request.post(base+'/auth/signup',headers={'Origin':base},data={'name':'다른 검증 계정','email':other_email,'password':password})
    assert result.status == 200,result.text()
    assert other.request.get(base+'/v1/records').json()['items'] == []
    assert other.request.get(base+'/v1/records/'+memory_id).status == 404
    assert other.request.get(base+'/auth/api-keys').json()['items'] == []
    assert other.request.get(base+'/v1/vault').json()['items'] == []
    assert other.request.get(base+'/v1/feature-requests').json()['items'] == []
    other.request.post(base+'/auth/logout',headers={'Origin':base})
    other.close()
    # Screenshot real populated console, with no API key left in the DOM.
    page.locator('.sidebar [data-view="overview"]').click()
    expect(page.locator('.stat-card')).to_have_count(4)
    expect(page.locator('.agent-brand-grid img')).to_have_count(4)
    assert not page.locator('#detail-content').inner_text()
    page.evaluate("document.querySelector('#toast').classList.remove('visible')")
    page.screenshot(path=str(artifacts/'desktop.png'),full_page=True,animations='disabled')
    for width in (375,390,768,1440):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),width
        if width==390:
            expect(page.locator('.sidebar')).to_have_css('transform', 'matrix(1, 0, 0, 1, -250, 0)')
            page.screenshot(path=str(artifacts/'mobile.png'),full_page=True,animations='disabled')
            page.locator('#menu-toggle').click()
            expect(page.locator('.sidebar')).to_have_class('sidebar open')
            page.locator('.sidebar [data-view="memories"]').click()
            expect(page.locator('.sidebar')).to_have_class('sidebar')
    page.set_viewport_size({'width':1440,'height':1000})
    for id in created:
        response = context.request.delete(base+'/v1/records/'+id,headers={'Origin':base})
        assert response.status == 204,response.text()
    page.locator('.sidebar [data-view="keys"]').click()
    page.once('dialog',lambda dialog:dialog.accept())
    page.locator('[data-action="revoke"]').click()
    expect(page.locator('[data-action="revoke"]')).to_have_count(0)
    assert agent.get('/v1/records').status == 401
    page.locator('.sidebar [data-view="vault"]').click()
    page.once('dialog',lambda dialog:dialog.accept())
    page.locator('[data-action="delete-vault"]').click()
    expect(page.locator('[data-action="delete-vault"]')).to_have_count(0)
    page.locator('#account-menu').click()
    page.locator('#logout').click()
    page.wait_for_url('**/login')
    assert context.request.get(base+'/auth/me').status == 401
    page.locator('#email').fill(email);page.locator('#password').fill(password)
    page.locator('#auth-submit').click();page.wait_for_url('**/console')
    expect(page.locator('#user-name')).to_have_text('콘솔 검증')
    page.locator('#account-menu').click();page.locator('#logout').click();page.wait_for_url('**/login')
    page.screenshot(path=str(artifacts/'login.png'),full_page=True)
    assert not errors,errors
    agent.dispose();context.close();browser.close()
print('PASS: real public signup/login/logout, HttpOnly session, memories, file byte upload/download, graph, feature requests, agent key issue/revocation, account isolation, mobile console, no JS errors.')
print('Screenshots:',artifacts)
