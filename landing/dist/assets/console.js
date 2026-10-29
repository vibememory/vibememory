'use strict';
const $ = selector => document.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const date = value => value ? new Date(typeof value === 'number' ? value * 1000 : value).toLocaleDateString('ko-KR') : '—';
let currentView = 'overview', pageOffset = 0, recordKind = 'memory', generation = 0;
let user, toastTimer;
async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  let data = null;
  if (response.status !== 204) {
    try { data = await response.json(); } catch { throw new Error('서버 응답을 확인할 수 없습니다. 잠시 후 다시 시도해주세요.'); }
  }
  if (!response.ok) {
    if (response.status === 401) { location.replace('/login'); throw new Error('로그인이 필요합니다.'); }
    const message = typeof data?.detail === 'string' ? data.detail : '입력한 내용을 확인해주세요.';
    throw new Error(message);
  }
  return data;
}
function toast(message) {
  $('#toast').textContent = message; $('#toast').classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 2800);
}
function empty(title, description, action = '') {
  return `<div class="empty-state"><span class="empty-icon">◈</span><h3>${h(title)}</h3><p>${h(description)}</p>${action}</div>`;
}
function tags(keywords) { return (keywords || []).slice(0, 5).map(tag => `<span class="tag">${h(tag)}</span>`).join('') || '<span class="record-subtitle">키워드 없음</span>'; }
function recordRows(items, deletable = true) {
  return `<div class="table-scroll"><table class="records-table"><thead><tr><th>이름 · 내용</th><th>키워드</th><th>등록일</th><th></th></tr></thead><tbody>${items.map(item => `<tr><td><button class="record-title" data-action="detail" data-id="${h(item.id)}">${h(item.title || item.content?.slice(0, 70) || '이름 없는 기록')}</button><span class="record-subtitle">${h(item.kind === 'entity' ? item.subtype : item.source || ({memory:'기억', document:'문서', file:'원본 파일'}[item.kind] || item.kind))}</span></td><td>${tags(item.keywords)}</td><td>${date(item.created_at)}</td><td><div class="row-actions">${item.kind === 'file' ? `<a href="/v1/files/${h(item.id)}" download>다운로드 ↓</a>` : ''}${deletable ? `<button class="danger" data-action="delete" data-id="${h(item.id)}">삭제</button>` : ''}</div></td></tr>`).join('')}</tbody></table></div>`;
}
const viewInfo = {
  overview: ['개요','YOUR MEMORY, AT A GLANCE','나의 기억, 한눈에.','에이전트와 함께 쌓아가는 맥락을 관리하세요.'],
  memories: ['기억','YOUR PERSONAL CONTEXT','기억','내가 남긴 사실과 취향, 에이전트가 구성한 엔티티를 확인하세요.','+ 기억 추가'],
  documents: ['문서 · 파일','YOUR KNOWLEDGE, CONNECTED','문서 · 파일','원본과 에이전트가 분석한 문서 메타정보를 관리하세요.','↑ 원본 업로드'],
  relations: ['관계 그래프','CONNECTIONS WITH A REASON','관계 그래프','에이전트가 구성한 기억의 연결과 근거를 살펴보세요.'],
  keys: ['에이전트 API 키','ONE MEMORY, YOUR AGENTS','에이전트 연결','키를 발급하고 Claude Code, Codex, OpenClaw, Hermes에 연결하세요.','+ API 키 만들기'],
  requests: ['기능 요청','HELP SHAPE VIBE MEMORY','기능 요청','필요한 기능과 실제 사용 사례를 남겨주세요.','+ 기능 요청']
};
async function navigate(view, reset = true) {
  const ticket = ++generation;
  currentView = view;
  if (reset) { pageOffset = 0; recordKind = view === 'documents' ? 'document' : 'memory'; }
  for (const button of document.querySelectorAll('.sidebar nav [data-view]')) {
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  }
  const info = viewInfo[view];
  $('#breadcrumb').textContent = info[0]; $('#view-eyebrow').textContent = info[1];
  $('#view-title').textContent = info[2]; $('#view-description').textContent = info[3];
  $('#primary-action').hidden = !info[4]; $('#primary-action').textContent = info[4] || '';
  $('#console-error').hidden = true; $('#view-content').innerHTML = '<div class="loading-state">불러오는 중…</div>';
  $('.sidebar').classList.remove('open'); $('#menu-toggle').setAttribute('aria-expanded', 'false');
  try {
    let html;
    if (view === 'overview') {
      const [stats, recent] = await Promise.all([api('/v1/stats'), api('/v1/records?limit=5')]);
      html = `<div class="stats-grid">${[['기억',stats.memory,'쌓아가는 나의 맥락'],['문서 · 파일',stats.document + stats.file,'연결된 원문과 메타정보'],['엔티티',stats.entity,'에이전트가 식별한 대상'],['활성 관계',stats.relations,'기억 사이의 연결']].map(([label,count,caption]) => `<article class="stat-card"><span>${h(label)}</span><strong>${count}</strong><small>${h(caption)}</small></article>`).join('')}</div><div class="onboarding-panel"><div><p class="eyebrow">START WITH YOUR FIRST AGENT</p><h2>나의 에이전트에게<br>기억할 공간을 더하세요.</h2><p>에이전트별 API 키를 발급하고 Skill을 연결하면,<br>어떤 도구에서든 같은 기억을 이어갈 수 있어요.</p><button class="button primary" data-view="keys">에이전트 연결하기 ↗</button></div><div class="terminal-block"><small># 에이전트 환경에 설정</small>\nexport MEMORY_URL=${h(location.origin)}\nexport MEMORY_API_KEY=your-agent-key\n\n<small># 에이전트가 추출한 키워드로 검색</small>\npython3 scripts/memory.py recall Python 개발언어</div></div><section class="console-panel"><div class="panel-heading"><h2>최근 기록</h2><button data-view="memories">모두 보기 ↗</button></div>${recent.items.length ? recordRows(recent.items, false) : empty('아직 저장된 기억이 없어요.','API 키를 발급하고 에이전트를 연결하거나, 기억을 직접 추가해보세요.','<button data-view="memories">첫 기억 남기기 ↗</button>')}</section>`;
    } else if (view === 'memories' || view === 'documents') {
      const result = await api(`/v1/records?kind=${recordKind}&limit=50&offset=${pageOffset}`);
      const options = view === 'memories' ? [['memory','기억'],['entity','엔티티']] : [['document','문서 메타정보'],['file','원본 파일']];
      html = `<section class="console-panel"><form id="search-records" class="list-toolbar"><select id="kind-filter" aria-label="기록 종류">${options.map(([value,label]) => `<option value="${value}" ${recordKind === value ? 'selected' : ''}>${label}</option>`).join('')}</select><input name="keywords" placeholder="검색 키워드를 쉼표로 구분" aria-label="검색 키워드"><button class="secondary-button" type="submit">키워드 검색</button><button class="secondary-button" type="button" data-action="reload">초기화</button></form><div id="record-results">${result.items.length ? recordRows(result.items) : empty('아직 기록이 없어요.',view === 'documents' ? '에이전트에서 파일을 등록하거나 원본을 업로드해보세요. 분석과 키워드 추출은 에이전트가 담당합니다.' : '기억을 직접 남기거나 에이전트에서 데이터를 보내보세요.')}</div><div class="pager"><button data-action="previous" ${pageOffset === 0 ? 'disabled' : ''}>← 이전</button><span>${Math.floor(pageOffset / 50) + 1} 페이지</span><button data-action="next" ${result.items.length < 50 ? 'disabled' : ''}>다음 →</button></div></section>`;
    } else if (view === 'keys') {
      const result = await api('/auth/api-keys');
      html = `<div class="agent-catalog" aria-label="연결할 에이전트">${[['Claude Code','claude-code.png'],['Codex','codex.png'],['OpenClaw','openclaw.svg'],['Hermes','hermes.png']].map(([name,file]) => `<span><img src="/assets/brands/${file}" alt="" width="22" height="22">${name}</span>`).join('')}</div><section class="console-panel"><p class="key-note">에이전트마다 별도 키를 발급해도 같은 내 기억을 공유합니다. 키는 생성 직후 한 번만 표시되며, 삭제하면 즉시 사용할 수 없게 됩니다.</p>${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>에이전트 이름</th><th>키</th><th>생성일</th><th></th></tr></thead><tbody>${result.items.map(key => `<tr><td><strong>${h(key.name)}</strong></td><td><code>${h(key.prefix)}</code></td><td>${date(key.created_at)}</td><td><div class="row-actions"><button class="danger" data-action="revoke" data-id="${h(key.id)}">삭제</button></div></td></tr>`).join('')}</tbody></table></div>` : empty('첫 에이전트를 연결해보세요.','API 키를 만들고 에이전트의 MEMORY_API_KEY로 설정하세요.','<button data-action="create-key">API 키 만들기 ↗</button>')}</section><p class="section-caption">Skill을 내려받아 에이전트의 skill 디렉터리에 넣어주세요. 저장·추론·검색 키워드 추출 절차가 포함되어 있습니다.</p><a class="secondary-button" href="/downloads/vibe-memory-skill.zip" download>Skill 다운로드 ↓</a>`;
    } else if (view === 'requests') {
      const result = await api(`/v1/feature-requests?limit=50&offset=${pageOffset}`);
      html = `<section class="console-panel">${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>요청 내용</th><th>에이전트</th><th>상태</th><th>등록일</th></tr></thead><tbody>${result.items.map(item => `<tr><td><button class="record-title" data-action="request-detail" data-id="${h(item.id)}">${h(item.title)}</button><span class="record-subtitle">${h(item.description.slice(0,100))}</span></td><td>${h(item.agent_name)}</td><td><span class="tag">접수됨</span></td><td>${date(item.created_at)}</td></tr>`).join('')}</tbody></table></div>` : empty('더 나은 기억을 위한 아이디어가 있나요?','에이전트에서 요청을 보내거나 콘솔에서 필요한 기능과 사용 사례를 남겨주세요.')}</section>`;
    } else {
      const result = await api('/v1/relations');
      const ids = [...new Set(result.items.flatMap(edge => [edge.source_id,edge.target_id]))];
      const names = new Map(await Promise.all(ids.map(async id => { const record = await api('/v1/records/' + encodeURIComponent(id)); return [id,record.title]; })));
      html = `<section class="console-panel"><div class="panel-heading"><h2>활성 관계 <span class="tag">${result.items.length}</span></h2></div>${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>시작</th><th>관계</th><th>대상 · 근거</th><th></th></tr></thead><tbody>${result.items.map(edge => `<tr><td><button class="record-title" data-action="detail" data-id="${h(edge.source_id)}">${h(names.get(edge.source_id))}</button></td><td><span class="tag">${h(edge.relation)}</span></td><td><button class="record-title" data-action="detail" data-id="${h(edge.target_id)}">${h(names.get(edge.target_id))}</button><span class="record-subtitle">${h(edge.reason)}</span></td><td><div class="row-actions"><button data-action="graph" data-id="${h(edge.source_id)}">연결 보기 ↗</button></div></td></tr>`).join('')}</tbody></table></div>` : empty('기억 사이의 연결을 기다리고 있어요.','에이전트가 엔티티와 관계를 구성해 등록하면 여기에 표시됩니다.')}</section>`;
    }
    if (ticket !== generation) return;
    $('#view-content').innerHTML = html;
    const filter = $('#kind-filter');
    if (filter) filter.addEventListener('change', () => { recordKind = filter.value; pageOffset = 0; navigate(view, false); });
    const search = $('#search-records');
    if (search) search.addEventListener('submit', searchRecords);
  } catch (error) { if (ticket === generation) { $('#view-content').replaceChildren(); $('#console-error').textContent = error.message; $('#console-error').hidden = false; } }
}
async function searchRecords(event) {
  event.preventDefault();
  const keywords = new FormData(event.target).get('keywords').split(',').map(word => word.trim()).filter(Boolean);
  if (!keywords.length) return toast('검색할 키워드를 입력해주세요.');
  const button = event.target.querySelector('[type=submit]'); button.disabled = true;
  try {
    const data = await api('/v1/search', {method:'POST',body:JSON.stringify({keywords,scope:currentView === 'documents' ? 'documents' : recordKind === 'entity' ? 'entities' : 'memories',limit:50})});
    const records = await Promise.all(data.hits.map(hit => api('/v1/records/' + encodeURIComponent(hit.id))));
    $('#record-results').innerHTML = records.length ? recordRows(records) : empty('검색 결과가 없어요.','다른 키워드로 검색해보세요.');
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
}
function editor(title, fields, onSave, submitLabel = '저장') {
  $('#editor-title').textContent = title; $('#editor-fields').innerHTML = fields;
  $('#editor-error').hidden = true; $('#editor-submit').textContent = submitLabel; $('#editor-submit').disabled = false;
  $('#editor-form').onsubmit = async event => {
    event.preventDefault(); $('#editor-submit').disabled = true; $('#editor-error').hidden = true;
    try { await onSave(new FormData(event.target)); $('#editor').close(); await navigate(currentView, false); }
    catch (error) { $('#editor-error').textContent = error.message; $('#editor-error').hidden = false; }
    finally { $('#editor-submit').disabled = false; }
  };
  $('#editor').showModal();
}
function detail(title, html) { $('#detail-title').textContent = title; $('#detail-content').innerHTML = html; $('#detail-dialog').showModal(); }
function createKey() {
  editor('에이전트 API 키 만들기','<p class="dialog-help">어떤 에이전트에 사용할 키인지 이름을 붙여주세요.</p><label>에이전트 이름<input name="name" placeholder="예: Claude Code, Codex, OpenClaw, Hermes" maxlength="80" required></label>', async data => {
    const record = await api('/auth/api-keys',{method:'POST',body:JSON.stringify({name:data.get('name')})});
    detail('새 API 키가 만들어졌어요.',`<div class="key-once"><p>지금 한 번만 확인할 수 있어요. 에이전트 설정에 저장해주세요.</p><code id="new-key">${h(record.key)}</code><button class="secondary-button" id="copy-key">API 키 복사 ⧉</button></div><pre class="detail-pre">export MEMORY_URL=${h(location.origin)}\nexport MEMORY_API_KEY=${h(record.key)}</pre>`);
    $('#copy-key').addEventListener('click',async () => { try { await navigator.clipboard.writeText(record.key); toast('API 키를 복사했습니다.'); } catch { toast('표시된 키를 선택해 복사해주세요.'); } });
  },'키 만들기');
}
function primaryAction() {
  if (currentView === 'keys') return createKey();
  if (currentView === 'memories') return editor('새 기억 남기기','<label>기억할 내용<textarea name="content" maxlength="10000" required placeholder="기억할 사실이나 선호를 입력하세요."></textarea></label><label>종류<select name="kind"><option value="fact">사실</option><option value="preference">선호</option><option value="event">이벤트</option><option value="instruction">지침</option></select></label><label>키워드<input name="keywords" required placeholder="예: Python, 개발 언어"></label><p class="dialog-help">키워드를 쉼표로 구분해주세요. 입력한 키워드만 임베딩하며, 원문은 분석하지 않습니다.</p>',async data => {
    const keywords = data.get('keywords').split(',').map(word => word.trim()).filter(Boolean);
    await api('/v1/memories',{method:'POST',body:JSON.stringify({content:data.get('content'),kind:data.get('kind'),keywords,source:'web-console'})});
    toast('기억을 저장했습니다.');
  });
  if (currentView === 'documents') return editor('원본 파일 업로드','<label>파일<input type="file" name="file" required></label><p class="dialog-help">원본 바이트만 저장합니다. 분석·키워드·문서 메타정보 등록은 연결된 에이전트가 수행합니다. 최대 100 MiB까지 업로드할 수 있습니다.</p>',async data => {
    const file = data.get('file');
    await api('/v1/files?filename=' + encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});
    recordKind = 'file'; pageOffset = 0; toast('원본 파일을 업로드했습니다.');
  },'업로드');
  if (currentView === 'requests') return editor('기능 요청 남기기','<label>제목<input name="title" maxlength="200" required placeholder="어떤 기능이 필요한가요?"></label><label>상세 설명<textarea name="description" maxlength="10000" required></textarea></label><label>사용 사례<textarea name="use_case" maxlength="4000" placeholder="이 기능이 어떤 작업에 도움이 되나요?"></textarea></label>',async data => {
    await api('/v1/feature-requests',{method:'POST',body:JSON.stringify({title:data.get('title'),description:data.get('description'),use_case:data.get('use_case'),agent_name:'web-console',source:'console'})}); toast('기능 요청을 접수했습니다.');
  },'요청 보내기');
}
$('#primary-action').addEventListener('click', primaryAction);
document.addEventListener('click', async event => {
  const nav = event.target.closest('[data-view]');
  if (nav) return navigate(nav.dataset.view);
  const button = event.target.closest('[data-action]'); if (!button) return;
  const {action,id} = button.dataset;
  try {
    if (action === 'create-key') return createKey();
    if (action === 'reload') return navigate(currentView, false);
    if (action === 'next') { pageOffset += 50; return navigate(currentView, false); }
    if (action === 'previous') { pageOffset = Math.max(0,pageOffset - 50); return navigate(currentView, false); }
    if (action === 'detail') { const record = await api('/v1/records/' + encodeURIComponent(id)); return detail(record.title || '기록 상세', `<p class="detail-content-text">${h(record.content)}</p><pre class="detail-pre">${h(JSON.stringify(record,null,2))}</pre>`); }
    if (action === 'request-detail') { const record = await api('/v1/feature-requests/' + encodeURIComponent(id)); return detail(record.title,`<pre class="detail-pre">${h(JSON.stringify(record,null,2))}</pre>`); }
    if (action === 'graph') {
      const graph = await api('/v1/graph/' + encodeURIComponent(id) + '?depth=2');
      return detail('연결된 기억',`<div class="graph-nodes">${graph.nodes.map(node => `<div class="graph-node"><strong>${h(node.kind)}</strong>${h(node.title)}</div>`).join('')}</div><pre class="detail-pre">${h(JSON.stringify(graph.relations.map(edge => ({relation:edge.relation,reason:edge.reason,source:edge.source_id,target:edge.target_id})),null,2))}</pre>`);
    }
    if (action === 'revoke' && confirm('이 API 키를 삭제할까요? 연결된 에이전트에서 더 이상 사용할 수 없습니다.')) {
      await api('/auth/api-keys/' + encodeURIComponent(id),{method:'DELETE'}); toast('API 키를 삭제했습니다.'); await navigate(currentView,false);
    }
    if (action === 'delete' && confirm('이 기록을 삭제할까요? 연결된 키워드와 관계도 삭제됩니다.')) {
      await api('/v1/records/' + encodeURIComponent(id),{method:'DELETE'}); toast('기록을 삭제했습니다.'); await navigate(currentView,false);
    }
  } catch (error) { toast(error.message); }
});
for (const button of document.querySelectorAll('.close-dialog')) button.addEventListener('click',() => $('#editor').close());
for (const button of document.querySelectorAll('.close-detail')) button.addEventListener('click',() => { $('#detail-dialog').close(); $('#detail-content').replaceChildren(); });
$('#detail-dialog').addEventListener('close',() => $('#detail-content').replaceChildren());
$('#menu-toggle').addEventListener('click',() => { const open = $('.sidebar').classList.toggle('open'); $('#menu-toggle').setAttribute('aria-expanded',String(open)); });
$('#logout').addEventListener('click',async () => {
  try { await api('/auth/logout',{method:'POST'}); $('#detail-content').replaceChildren(); $('#view-content').replaceChildren(); location.replace('/login'); }
  catch (error) { toast(error.message); }
});
(async () => {
  try {
    const data = await api('/auth/me'); user = data.user;
    $('#user-name').textContent = user.name; $('#user-email').textContent = user.email;
    $('#user-initial').textContent = user.name[0].toUpperCase(); $('#workspace-name').textContent = user.name + '의 기억';
    await navigate('overview');
  } catch (error) { $('#console-error').textContent = error.message; $('#console-error').hidden = false; }
})();
