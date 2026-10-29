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
function installPromptCard() {
  return `<section class="install-prompt-card" aria-labelledby="install-prompt-title"><div class="install-prompt-copy"><span>RECOMMENDED · NO KEY COPY</span><h2 id="install-prompt-title">대화 한 번으로 에이전트를 연결하세요.</h2><p id="install-prompt-description">설치 프롬프트를 Claude Code, Codex, OpenClaw 또는 Hermes에 붙여넣으면 Skill 설치부터 웹 승인까지 에이전트가 진행합니다.</p></div><button class="button primary" type="button" data-action="copy-install-prompt" aria-describedby="install-prompt-description">설치 프롬프트 복사하기 <span aria-hidden="true">⧉</span></button></section>`;
}
function installPrompt() {
  const base = location.origin;
  return `Vibe Memory를 이 에이전트에 설치하고 내 계정에 연결해줘.

서비스 URL: ${base}
Skill 다운로드: ${base}/downloads/vibe-memory-skill.zip
최신 지침: ${base}/skills/vibe-memory/SKILL.md

진행 방법:
1. Skill ZIP을 내려받아 이 에이전트의 Skill 디렉터리에 설치하고 SKILL.md 전체를 읽어.
2. 설치된 vibe-memory 디렉터리에서 호환 설치기를 실행해 서비스 매니페스트가 지정한 현재 플랫폼용 배포 바이너리를 내려받고 SHA-256을 검증해. 작업 중 Rust를 직접 컴파일하지 마. Linux/macOS에서는 MEMORY_URL="${base}" python3 scripts/memory.py sync를 사용하고, Windows에서는 현재 셸 문법에 맞게 MEMORY_URL을 설정한 뒤 py scripts\\memory.py sync를 사용해.
3. 브라우저 승인 연결을 login --no-browser --name "현재 에이전트 이름"으로 시작하고 서비스 URL은 ${base}로 지정해.
4. 출력된 승인 URL과 확인 코드를 클릭 가능한 링크로 나에게 보여줘. 비밀번호나 API 키를 요청하거나 채팅에 노출하지 말고, 연결 프로세스를 유지한 채 내가 웹에서 승인할 때까지 기다려.
5. 승인 후 status로 연결을 확인해. 이후 작업부터 SKILL.md 지침에 따라 Vibe Memory를 적극 사용하고, API 요청을 직접 조립하지 말고 Rust CLI를 사용해.
6. 각 대화에서 관련 프로젝트 기억을 먼저 조회하고, 결정·수정·검증 완료·블로커·다음 작업이 바뀌면 전체 대화 대신 짧은 session checkpoint를 저장해. 인계, 컨텍스트 압축 또는 종료 전에는 아직 저장하지 않은 변경분을 체크포인트로 남기고, 이전 체크포인트와 달라진 내용이 없으면 중복 저장하지 마.`;
}
async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(value); return; } catch { /* Use the selection fallback below. */ }
  }
  const field = document.createElement('textarea');
  field.value = value; field.setAttribute('readonly', ''); field.style.position = 'fixed'; field.style.opacity = '0';
  document.body.append(field); field.select();
  const copied = document.execCommand('copy'); field.remove();
  if (!copied) throw new Error('copy failed');
}
function empty(title, description, action = '') {
  return `<div class="empty-state"><span class="empty-icon">◈</span><h3>${h(title)}</h3><p>${h(description)}</p>${action}</div>`;
}
function tags(keywords) { return (keywords || []).slice(0, 5).map(tag => `<span class="tag">${h(tag)}</span>`).join('') || '<span class="record-subtitle">키워드 없음</span>'; }
function recordRows(items, deletable = true) {
  return `<div class="table-scroll"><table class="records-table"><thead><tr><th>이름 · 내용</th><th>키워드</th><th>등록일</th><th></th></tr></thead><tbody>${items.map(item => `<tr><td><button class="record-title" data-action="detail" data-id="${h(item.id)}">${h(item.title || item.content?.slice(0, 70) || '이름 없는 기록')}</button><span class="record-subtitle">${h(item.kind === 'entity' ? item.subtype : item.source || ({memory:'기억', document:'문서', file:'원본 파일'}[item.kind] || item.kind))}</span></td><td>${tags(item.keywords)}</td><td>${date(item.created_at)}</td><td><div class="row-actions">${item.kind === 'file' ? `<a href="/v1/files/${h(item.id)}" download>다운로드 ↓</a>` : ''}${deletable ? `<button class="danger" data-action="delete" data-id="${h(item.id)}">삭제</button>` : ''}</div></td></tr>`).join('')}</tbody></table></div>`;
}
const viewInfo = {
  overview: ['대시보드','WORKSPACE OVERVIEW','대시보드','에이전트와 함께 쌓아가는 기억을 한곳에서 관리하세요.'],
  memories: ['기억','YOUR PERSONAL CONTEXT','기억','내가 남긴 사실과 취향, 에이전트가 구성한 엔티티를 확인하세요.','+ 기억 추가'],
  documents: ['문서 · 파일','YOUR KNOWLEDGE, CONNECTED','문서 · 파일','원본과 에이전트가 분석한 문서 메타정보를 관리하세요.','↑ 원본 업로드'],
  relations: ['관계 그래프','CONNECTIONS WITH A REASON','관계 그래프','에이전트가 구성한 기억의 연결과 근거를 살펴보세요.'],
  keys: ['에이전트 연결','ONE MEMORY, EVERY AGENT','에이전트 연결','연결된 에이전트를 확인하고 접근 권한을 관리하세요.','+ API 키 만들기'],
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
      const [stats, recent, keys] = await Promise.all([api('/v1/stats'), api('/v1/records?limit=6'), api('/auth/api-keys')]);
      const totalRecords = stats.memory + stats.document + stats.file + stats.entity;
      const setup = [true, keys.items.length > 0, totalRecords > 0, stats.relations > 0];
      const complete = setup.filter(Boolean).length;
      const statIcons = [
        '<svg viewBox="0 0 24 24"><path d="M9 4.5A3.5 3.5 0 0 0 5.5 8v1A3.5 3.5 0 0 0 4 15.5 3.5 3.5 0 0 0 7.5 19H9m6-14.5A3.5 3.5 0 0 1 18.5 8v1a3.5 3.5 0 0 1 1.5 6.5 3.5 3.5 0 0 1-3.5 3.5H15M9 4v16m6-16v16"/></svg>',
        '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6m-6 4h6"/></svg>',
        '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3"/><path d="M6 20a6 6 0 0 1 12 0"/></svg>',
        '<svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.3 11 7.4-3.7M8.3 13l7.4 3.7"/></svg>'
      ];
      const statsData = [
        ['기억', stats.memory, '저장된 사실과 선호', 'memories'],
        ['문서 · 파일', stats.document + stats.file, '연결된 지식 자료', 'documents'],
        ['엔티티', stats.entity, '식별된 사람과 대상', 'memories'],
        ['활성 관계', stats.relations, '기억 사이의 연결', 'relations']
      ];
      const setupItems = [
        ['워크스페이스 생성', '개인 데이터 공간이 준비됐어요.', 'overview'],
        ['에이전트 연결', keys.items.length ? `${keys.items.length}개 에이전트 키가 활성 상태예요.` : '승인 링크로 첫 에이전트를 연결하세요.', 'keys'],
        ['첫 기억 저장', totalRecords ? `${totalRecords}개의 기록이 쌓였어요.` : '에이전트 또는 콘솔에서 기억을 추가하세요.', 'memories'],
        ['관계 만들기', stats.relations ? `${stats.relations}개의 관계가 연결됐어요.` : '에이전트가 엔티티 사이의 관계를 등록해요.', 'relations']
      ];
      html = `<section class="welcome-panel"><div class="welcome-copy"><p class="welcome-kicker"><i></i>PERSONAL MEMORY WORKSPACE</p><h2>${h(user.name)}님, 기억이 이어지고 있어요.</h2><p>Claude Code, Codex, OpenClaw, Hermes가 같은 맥락을 사용할 수 있도록 기록과 연결 상태를 관리하세요.</p><div class="quick-actions"><button data-action="add-memory"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>기억 추가</button><button data-action="upload-file"><svg viewBox="0 0 24 24"><path d="M12 16V4m0 0L7 9m5-5 5 5M5 15v5h14v-5"/></svg>파일 업로드</button><button data-view="keys"><svg viewBox="0 0 24 24"><circle cx="9" cy="12" r="4"/><path d="M13 12h8m-3 0v3"/></svg>에이전트 연결</button></div></div><div class="memory-network-card"><div class="memory-network-top"><span>연결된 에이전트</span><strong>${keys.items.length}</strong></div><div class="agent-mini-list">${[['claude-code.png','Claude Code'],['codex.png','Codex'],['openclaw.svg','OpenClaw'],['hermes.png','Hermes']].map(([file,name]) => `<img src="/assets/brands/${file}" alt="${name}" title="${name}">`).join('')}<span class="agent-mini-more">+AI</span></div><div class="memory-network-foot"><i></i>${keys.items.length ? '연결된 키가 정상 작동 중입니다.' : '첫 에이전트를 연결해보세요.'}</div></div></section><div class="stats-grid">${statsData.map(([label,count,caption,target],index) => `<article class="stat-card"><div class="stat-card-top"><span class="stat-card-label">${h(label)}</span><span class="stat-card-icon">${statIcons[index]}</span></div><strong>${count}</strong><small>${h(caption)}</small><button class="stat-card-link" data-view="${target}" aria-label="${h(label)} 보기"></button></article>`).join('')}</div><div class="dashboard-grid"><section class="console-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>최근 기록</h2><p>가장 최근에 저장된 워크스페이스 데이터</p></div><button data-view="memories">전체 보기 →</button></div>${recent.items.length ? recordRows(recent.items, false) : empty('아직 저장된 기억이 없어요.','에이전트를 연결하거나 콘솔에서 첫 기억을 추가해보세요.','<button data-action="add-memory">첫 기억 추가하기</button>')}</section><div><section class="console-panel setup-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>시작 체크리스트</h2><p>워크스페이스 설정 상태</p></div></div><div class="setup-progress"><div class="setup-progress-top"><span>${complete}/4 완료</span><strong>${complete * 25}%</strong></div><div class="setup-progress-bar"><i style="width:${complete * 25}%"></i></div></div><div class="setup-list">${setupItems.map(([title,description,target],index) => `<div class="setup-item"><span class="setup-check ${setup[index] ? '' : 'pending'}">${setup[index] ? '✓' : '○'}</span><div class="setup-item-copy"><strong>${h(title)}</strong><span>${h(description)}</span></div><button data-view="${target}" aria-label="${h(title)} 보기">→</button></div>`).join('')}</div></section><section class="console-panel dashboard-agent-panel"><p>하나의 기억을 여러 코딩 에이전트에서 안전하게 이어가세요.</p><div class="agent-brand-grid">${[['claude-code.png','Claude Code'],['codex.png','Codex'],['openclaw.svg','OpenClaw'],['hermes.png','Hermes']].map(([file,name]) => `<span title="${name}"><img src="/assets/brands/${file}" alt="${name}"></span>`).join('')}</div></section></div></div>`;
    } else if (view === 'memories' || view === 'documents') {
      const result = await api(`/v1/records?kind=${recordKind}&limit=50&offset=${pageOffset}`);
      const options = view === 'memories' ? [['memory','기억'],['entity','엔티티']] : [['document','문서 메타정보'],['file','원본 파일']];
      html = `<section class="console-panel"><form id="search-records" class="list-toolbar"><select id="kind-filter" aria-label="기록 종류">${options.map(([value,label]) => `<option value="${value}" ${recordKind === value ? 'selected' : ''}>${label}</option>`).join('')}</select><input name="keywords" placeholder="검색 키워드를 쉼표로 구분" aria-label="검색 키워드"><button class="secondary-button" type="submit">키워드 검색</button><button class="secondary-button" type="button" data-action="reload">초기화</button></form><div id="record-results">${result.items.length ? recordRows(result.items) : empty('아직 기록이 없어요.',view === 'documents' ? '에이전트에서 파일을 등록하거나 원본을 업로드해보세요. 분석과 키워드 추출은 에이전트가 담당합니다.' : '기억을 직접 남기거나 에이전트에서 데이터를 보내보세요.')}</div><div class="pager"><button data-action="previous" ${pageOffset === 0 ? 'disabled' : ''}>← 이전</button><span>${Math.floor(pageOffset / 50) + 1} 페이지</span><button data-action="next" ${result.items.length < 50 ? 'disabled' : ''}>다음 →</button></div></section>`;
    } else if (view === 'keys') {
      const result = await api('/auth/api-keys');
      html = `<div class="agent-catalog" aria-label="지원하는 에이전트">${[['Claude Code','claude-code.png'],['Codex','codex.png'],['OpenClaw','openclaw.svg'],['Hermes','hermes.png']].map(([name,file]) => `<span><img src="/assets/brands/${file}" alt="" width="28" height="28">${name}</span>`).join('')}</div><section class="console-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>활성 연결</h2><p>${result.items.length}개의 에이전트 키가 이 워크스페이스에 접근할 수 있습니다.</p></div><a class="secondary-button" href="/downloads/vibe-memory-skill.zip" download>Skill 다운로드</a></div><p class="key-note">에이전트가 안내한 웹 승인 링크를 열면 키를 복사하지 않고 연결할 수 있습니다. 여기에서 각 연결을 확인하고 언제든 철회하세요.</p>${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>에이전트 이름</th><th>키 식별자</th><th>연결일</th><th></th></tr></thead><tbody>${result.items.map(key => `<tr><td><strong>${h(key.name)}</strong></td><td><code>${h(key.prefix)}</code></td><td>${date(key.created_at)}</td><td><div class="row-actions"><button class="danger" data-action="revoke" data-id="${h(key.id)}">연결 해제</button></div></td></tr>`).join('')}</tbody></table></div>` : empty('연결된 에이전트가 없어요.','에이전트에게 Vibe Memory 연결을 요청하면 웹 승인 링크를 안내합니다.','<a class="secondary-button" href="/guide.html" target="_blank">연결 방법 보기</a>')}</section><p class="section-caption">수동 키는 고급 설정용입니다. 새로 연결할 때는 에이전트가 만드는 웹 승인 링크를 권장합니다.</p>`;
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
    if (view === 'keys') $('#view-content').insertAdjacentHTML('afterbegin', installPromptCard());
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
    if (action === 'toggle-account') {
      if (window.innerWidth <= 820) {
        $('.sidebar').classList.add('open');
        $('#menu-toggle').setAttribute('aria-expanded','true');
      }
      const popover = $('#account-popover'); popover.hidden = !popover.hidden;
      $('#account-menu').setAttribute('aria-expanded', String(!popover.hidden));
      return;
    }
    if (action === 'home') return navigate('overview');
    if (action === 'focus-search') {
      await navigate('memories');
      $('#search-records [name="keywords"]')?.focus();
      return;
    }
    if (action === 'add-memory') { await navigate('memories'); return primaryAction(); }
    if (action === 'upload-file') { await navigate('documents'); return primaryAction(); }
    if (action === 'copy-install-prompt') {
      const prompt = installPrompt();
      try { await copyText(prompt); toast('설치 프롬프트를 복사했습니다. 에이전트 대화에 붙여넣으세요.'); }
      catch { detail('에이전트 설치 프롬프트', `<p class="dialog-help">자동 복사가 차단됐습니다. 아래 내용을 선택해 복사하세요.</p><pre class="detail-pre">${h(prompt)}</pre>`); }
      return;
    }
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
$('#sidebar-backdrop').addEventListener('click',() => { $('.sidebar').classList.remove('open'); $('#account-popover').hidden = true; $('#menu-toggle').setAttribute('aria-expanded','false'); $('#account-menu').setAttribute('aria-expanded','false'); });
$('#account-menu').addEventListener('click',event => {
  event.stopPropagation(); const popover = $('#account-popover'); popover.hidden = !popover.hidden;
  $('#account-menu').setAttribute('aria-expanded',String(!popover.hidden));
});
document.addEventListener('click',event => {
  if (!event.target.closest('.sidebar-bottom') && !event.target.closest('[data-action="toggle-account"]')) {
    $('#account-popover').hidden = true; $('#account-menu').setAttribute('aria-expanded','false');
  }
});
document.addEventListener('keydown',async event => {
  if (event.key !== '/' || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName)) return;
  event.preventDefault(); await navigate('memories'); $('#search-records [name="keywords"]')?.focus();
});
$('#logout').addEventListener('click',async () => {
  try { await api('/auth/logout',{method:'POST'}); $('#detail-content').replaceChildren(); $('#view-content').replaceChildren(); location.replace('/login'); }
  catch (error) { toast(error.message); }
});
(async () => {
  try {
    const data = await api('/auth/me'); user = data.user;
    $('#user-name').textContent = user.name; $('#user-email').textContent = user.email;
    const initial = user.name[0].toUpperCase();
    $('#user-initial').textContent = initial; $('#topbar-initial').textContent = initial;
    $('#workspace-initial').textContent = initial; $('#workspace-name').textContent = user.name + '의 기억';
    await navigate('overview');
  } catch (error) { $('#console-error').textContent = error.message; $('#console-error').hidden = false; }
})();
