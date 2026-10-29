'use strict';
const $ = selector => document.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const date = value => value ? new Date(typeof value === 'number' ? value * 1000 : value).toLocaleDateString(window.vmLocaleTag?.() || 'ko-KR', {timeZone:'UTC'}) : '—';
let currentView = 'overview', pageOffset = 0, recordKind = 'memory', generation = 0;
let user, toastTimer;
let dashboardGuideDismissed = false;
const dashboardGuideKey = 'vibe-memory:dashboard-guide:hidden';
function dashboardGuideHidden() {
  if (dashboardGuideDismissed) return true;
  try { return localStorage.getItem(dashboardGuideKey) === '1'; } catch { return false; }
}
function dismissDashboardGuide() {
  dashboardGuideDismissed = true;
  try { localStorage.setItem(dashboardGuideKey, '1'); } catch { /* Keep it hidden for this session. */ }
}
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
  return `<section class="install-prompt-card" aria-labelledby="install-prompt-title"><div class="install-prompt-copy"><span>RECOMMENDED · NO KEY COPY</span><h2 id="install-prompt-title">대화 한 번으로 설치·최신화하고 연결하세요.</h2><p id="install-prompt-description">프롬프트를 Claude Code, Codex, OpenClaw 또는 Hermes에 붙여넣으면 오래된 Skill 교체부터 웹 승인까지 에이전트가 진행합니다.</p></div><button class="button primary" type="button" data-action="copy-install-prompt" aria-describedby="install-prompt-description">설치·최신화 프롬프트 복사 <span aria-hidden="true">⧉</span></button></section>`;
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
const graphKindLabel = kind => ({memory:'기억',entity:'엔티티',document:'문서',file:'파일'}[kind] || kind || '기록');
const graphTitle = record => record?.title || record?.content?.slice(0, 46) || '이름 없는 기록';
let relationshipCy = null, relationshipResizeObserver = null;
function destroyRelationshipGraph() {
  relationshipResizeObserver?.disconnect(); relationshipResizeObserver = null;
  relationshipCy?.destroy(); relationshipCy = null;
}
function cytoscapeRuntime() {
  if (window.cytoscape) return Promise.resolve(window.cytoscape);
  return Promise.reject(new Error('그래프 엔진 파일을 불러오지 못했습니다. 페이지를 새로고침해주세요.'));
}
function relationshipGraph(records, relations, totals) {
  const truncated = records.length < totals.nodes || relations.length < totals.relations;
  const summary = truncated ? `전체 ${totals.nodes}개 노드와 ${totals.relations}개 관계 중 연결 중심으로 표시합니다.` : `${records.length}개 노드와 ${relations.length}개 관계를 표시합니다.`;
  const recordMap = new Map(records.map(record => [record.id, record]));
  const accessibleNodes = records.map(record => `<button type="button" data-action="graph" data-id="${h(record.id)}">${h(graphTitle(record))}, ${h(graphKindLabel(record.kind))}</button>`).join('');
  const accessibleEdges = relations.map(edge => `<button type="button" data-action="relation-detail" data-source-name="${h(graphTitle(recordMap.get(edge.source_id)))}" data-target-name="${h(graphTitle(recordMap.get(edge.target_id)))}" data-relation="${h(edge.relation)}" data-reason="${h(edge.reason)}">${h(edge.relation)} 관계</button>`).join('');
  return `<section class="relationship-panel" aria-label="관계 그래프. ${h(summary)}"><div class="relationship-graph-stage" role="application" aria-label="기억 관계 그래프. 드래그하여 이동하고 휠로 확대할 수 있습니다."></div><div class="relationship-graph-a11y"><p>${h(summary)}</p>${accessibleNodes}${accessibleEdges}</div><div class="relationship-graph-meta"><span><i></i>${h(summary)}</span><span>노드나 관계를 선택하면 상세 정보를 확인할 수 있습니다.</span></div><div class="relationship-graph-controls" aria-label="그래프 화면 조절"><button type="button" data-graph-command="zoom-in" aria-label="확대">+</button><button type="button" data-graph-command="zoom-out" aria-label="축소">−</button><button type="button" data-graph-command="fit" aria-label="그래프 전체 보기">⌂</button></div></section>`;
}
async function bindRelationshipGraph(records, relations) {
  const stage = $('.relationship-graph-stage');
  if (!stage) return;
  const cytoscape = await cytoscapeRuntime();
  if (!stage.isConnected) return;
  const recordMap = new Map(records.map(record => [record.id, record]));
  const degree = new Map(records.map(record => [record.id, 0]));
  for (const edge of relations) {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  }
  const elements = [
    ...records.map(record => ({data:{
      id:record.id,
      label:`${graphTitle(record)}\n${graphKindLabel(record.kind)} · 연결 ${degree.get(record.id) || 0}`,
      title:graphTitle(record),
      kind:record.kind || 'record'
    },classes:`kind-${record.kind || 'record'}`})),
    ...relations.map((edge, index) => ({data:{
      id:`relation-${index}`,
      source:edge.source_id,
      target:edge.target_id,
      relation:edge.relation || 'RELATED_TO',
      reason:edge.reason || '',
      sourceName:graphTitle(recordMap.get(edge.source_id)),
      targetName:graphTitle(recordMap.get(edge.target_id))
    }}))
  ];
  relationshipCy = cytoscape({
    container:stage,
    elements,
    wheelSensitivity:.2,
    minZoom:.3,
    maxZoom:2.4,
    boxSelectionEnabled:false,
    style:[
      {selector:'node',style:{'shape':'roundrectangle','width':168,'height':60,'background-color':'#ffffff','border-width':1.4,'border-color':'#aebce0','label':'data(label)','color':'#3d4a62','font-family':'VibeSans, Arial, sans-serif','font-size':10,'font-weight':500,'text-wrap':'wrap','text-max-width':145,'text-valign':'center','text-halign':'center','line-height':1.45,'overlay-opacity':0,'transition-property':'border-color, border-width, background-color, opacity','transition-duration':'160ms'}},
      {selector:'node.kind-memory',style:{'border-color':'#7892ec','background-color':'#f9fbff'}},
      {selector:'node.kind-entity',style:{'border-color':'#a991d8','background-color':'#fcfaff'}},
      {selector:'node.kind-document',style:{'border-color':'#72b9a5','background-color':'#f8fdfa'}},
      {selector:'node.kind-file',style:{'border-color':'#d9a36d','background-color':'#fffaf5'}},
      {selector:'node:selected, node.highlighted',style:{'border-width':2.4,'border-color':'#315bfb','background-color':'#f0f4ff'}},
      {selector:'edge',style:{'width':1.45,'curve-style':'bezier','control-point-step-size':45,'line-color':'#aeb9d5','target-arrow-color':'#8fa0ca','target-arrow-shape':'triangle','arrow-scale':.85,'label':'data(relation)','font-family':'ui-monospace, SFMono-Regular, Consolas, monospace','font-size':8,'color':'#60719a','text-background-color':'#ffffff','text-background-opacity':.94,'text-background-padding':4,'text-border-color':'#dde4f2','text-border-width':1,'text-border-opacity':1,'text-rotation':'autorotate','text-margin-y':-9,'overlay-opacity':0,'transition-property':'line-color, target-arrow-color, width, opacity','transition-duration':'160ms'}},
      {selector:'edge:selected, edge.highlighted',style:{'width':2.4,'line-color':'#315bfb','target-arrow-color':'#315bfb','color':'#315bfb','z-index':10}},
      {selector:'.faded',style:{'opacity':.12,'text-opacity':.08}}
    ],
    layout:{
      name:records.length > 1 ? 'cose' : 'grid',
      animate:true,
      animationDuration:650,
      fit:true,
      padding:75,
      randomize:true,
      nodeRepulsion:650000,
      idealEdgeLength:155,
      edgeElasticity:100,
      nestingFactor:1.2,
      gravity:.16,
      numIter:1200,
      nodeOverlap:32,
      componentSpacing:130
    }
  });
  const clearFocus = () => relationshipCy?.elements().removeClass('faded highlighted');
  relationshipCy.on('mouseover','node',event => {
    const focus = event.target.closedNeighborhood();
    relationshipCy.elements().addClass('faded'); focus.removeClass('faded'); event.target.addClass('highlighted');
  });
  relationshipCy.on('mouseover','edge',event => {
    const focus = event.target.connectedNodes().union(event.target);
    relationshipCy.elements().addClass('faded'); focus.removeClass('faded'); event.target.addClass('highlighted');
  });
  relationshipCy.on('mouseout','node, edge',clearFocus);
  relationshipCy.on('tap','node',async event => {
    try {
      const graph = await api('/v1/graph/' + encodeURIComponent(event.target.id()) + '?depth=2');
      detail('연결된 기억',`<div class="graph-nodes">${graph.nodes.map(node => `<div class="graph-node"><strong>${h(node.kind)}</strong>${h(node.title)}</div>`).join('')}</div><pre class="detail-pre">${h(JSON.stringify(graph.relations.map(edge => ({relation:edge.relation,reason:edge.reason,source:edge.source_id,target:edge.target_id})),null,2))}</pre>`);
    } catch (error) { toast(error.message); }
  });
  relationshipCy.on('tap','edge',event => {
    const edge = event.target.data();
    detail('관계 근거',`<div class="relation-detail-route"><span>${h(edge.sourceName)}</span><strong>${h(edge.relation)}</strong><span>${h(edge.targetName)}</span></div><div class="relation-detail-reason"><span>에이전트가 등록한 근거</span><p>${h(edge.reason)}</p></div>`);
  });
  for (const button of document.querySelectorAll('[data-graph-command]')) {
    button.addEventListener('click', () => {
      if (!relationshipCy) return;
      if (button.dataset.graphCommand === 'fit') return relationshipCy.fit(undefined, 75);
      const factor = button.dataset.graphCommand === 'zoom-in' ? 1.22 : .82;
      relationshipCy.zoom({level:Math.max(relationshipCy.minZoom(), Math.min(relationshipCy.maxZoom(), relationshipCy.zoom() * factor)),renderedPosition:{x:stage.clientWidth / 2,y:stage.clientHeight / 2}});
    });
  }
  relationshipResizeObserver = new ResizeObserver(() => relationshipCy?.resize());
  relationshipResizeObserver.observe(stage);
}
const viewInfo = {
  overview: ['대시보드','WORKSPACE CONSOLE','대시보드','워크스페이스 데이터 · 연결 상태 · 최근 활동'],
  memories: ['기억','YOUR PERSONAL CONTEXT','기억','내가 남긴 사실과 취향, 에이전트가 구성한 엔티티를 확인하세요.','+ 기억 추가'],
  documents: ['문서 · 파일','YOUR KNOWLEDGE, CONNECTED','문서 · 파일','원본과 에이전트가 분석한 문서 메타정보를 관리하세요.','↑ 원본 업로드'],
  relations: ['관계 그래프','CONNECTIONS WITH A REASON','관계 그래프','에이전트가 구성한 기억의 연결과 근거를 살펴보세요.'],
  keys: ['에이전트 연결','ONE MEMORY, EVERY AGENT','에이전트 연결','연결된 에이전트를 확인하고 접근 권한을 관리하세요.','+ API 키 만들기'],
  vault: ['Vault','ENCRYPTED SECRETS','Vault','에이전트가 로컬 설정 파일 없이 사용할 비밀값을 암호화해 관리하세요.','+ 비밀 추가'],
  requests: ['기능 요청','HELP SHAPE VIBE MEMORY','기능 요청','필요한 기능과 실제 사용 사례를 남겨주세요.','+ 기능 요청']
};
function viewFromLocation() {
  const view = decodeURIComponent(location.hash.slice(1));
  return Object.hasOwn(viewInfo, view) ? view : 'overview';
}
function syncViewLocation(view, mode = 'push') {
  const hash = `#${view}`;
  if (location.hash === hash || mode === 'none') return;
  history[mode === 'replace' ? 'replaceState' : 'pushState']({view}, '', `${location.pathname}${location.search}${hash}`);
}
async function navigate(view, reset = true, historyMode = 'push') {
  if (!Object.hasOwn(viewInfo, view)) view = 'overview';
  syncViewLocation(view, historyMode);
  const ticket = ++generation;
  destroyRelationshipGraph();
  currentView = view;
  if (reset) { pageOffset = 0; recordKind = view === 'documents' ? 'document' : 'memory'; }
  for (const button of document.querySelectorAll('.sidebar nav [data-view]')) {
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  }
  const info = viewInfo[view];
  document.title = `${info[0]} — Vibe Memory`;
  $('#console-main').classList.toggle('is-graph-view', view === 'relations');
  $('#breadcrumb').textContent = info[0]; $('#view-eyebrow').textContent = info[1];
  $('#view-title').textContent = info[2]; $('#view-description').textContent = info[3];
  $('#primary-action').hidden = !info[4]; $('#primary-action').textContent = info[4] || '';
  $('#console-error').hidden = true; $('#view-content').innerHTML = '<div class="loading-state">불러오는 중…</div>';
  $('.sidebar').classList.remove('open'); $('#menu-toggle').setAttribute('aria-expanded', 'false');
  try {
    let html, graphPayload = null;
    if (view === 'overview') {
      const [stats, recent, keys] = await Promise.all([api('/v1/stats'), api('/v1/records?limit=6'), api('/auth/api-keys')]);
      const totalRecords = stats.memory + stats.document + stats.file + stats.entity;
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
      const guide = dashboardGuideHidden() ? '' : `<section class="dashboard-guide" aria-label="빠른 시작"><div class="dashboard-guide-copy"><span>QUICK START</span><strong>워크스페이스 빠른 작업</strong></div><div class="dashboard-guide-actions"><button data-action="add-memory">+ 기억 추가</button><button data-action="upload-file">↑ 파일 업로드</button><button data-view="keys">에이전트 연결</button><button class="dashboard-guide-dismiss" data-action="dismiss-dashboard-guide">다시 보지 않기 <span aria-hidden="true">×</span></button></div></section>`;
      const agentBrands = [['claude-code.png','Claude Code'],['codex.png','Codex'],['openclaw.svg','OpenClaw'],['hermes.png','Hermes']];
      html = `${guide}<div class="stats-grid">${statsData.map(([label,count,caption,target],index) => `<article class="stat-card"><div class="stat-card-top"><span class="stat-card-label">${h(label)}</span><span class="stat-card-icon">${statIcons[index]}</span></div><strong>${count}</strong><small>${h(caption)}</small><button class="stat-card-link" data-view="${target}" aria-label="${h(label)} 보기"></button></article>`).join('')}</div><div class="dashboard-grid"><section class="console-panel dashboard-recent-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>최근 기록</h2><p>최근 저장된 워크스페이스 데이터</p></div><button data-view="memories">전체 보기 →</button></div>${recent.items.length ? recordRows(recent.items, false) : empty('기록 없음','저장된 워크스페이스 데이터가 없습니다.')}</section><section class="console-panel dashboard-status-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>연결 상태</h2><p>Workspace runtime</p></div><span class="console-live-badge"><i></i>LIVE</span></div><div class="console-status-list"><div><span>API</span><strong class="status-ok">정상</strong></div><div><span>에이전트 키</span><strong>${keys.items.length}</strong></div><div><span>전체 기록</span><strong>${totalRecords}</strong></div><div><span>관계</span><strong>${stats.relations}</strong></div></div><div class="dashboard-status-agents">${agentBrands.map(([file,name]) => `<span title="${name}"><img src="/assets/brands/${file}" alt="${name}"><small>${name}</small></span>`).join('')}</div></section></div>`;
    } else if (view === 'memories' || view === 'documents') {
      const result = await api(`/v1/records?kind=${recordKind}&limit=50&offset=${pageOffset}`);
      const options = view === 'memories' ? [['memory','기억'],['entity','엔티티']] : [['document','문서 메타정보'],['file','원본 파일']];
      html = `<section class="console-panel"><form id="search-records" class="list-toolbar"><select id="kind-filter" aria-label="기록 종류">${options.map(([value,label]) => `<option value="${value}" ${recordKind === value ? 'selected' : ''}>${label}</option>`).join('')}</select><input name="keywords" placeholder="검색 키워드를 쉼표로 구분" aria-label="검색 키워드"><button class="secondary-button" type="submit">키워드 검색</button><button class="secondary-button" type="button" data-action="reload">초기화</button></form><div id="record-results">${result.items.length ? recordRows(result.items) : empty('아직 기록이 없어요.',view === 'documents' ? '에이전트에서 파일을 등록하거나 원본을 업로드해보세요. 분석과 키워드 추출은 에이전트가 담당합니다.' : '기억을 직접 남기거나 에이전트에서 데이터를 보내보세요.')}</div><div class="pager"><button data-action="previous" ${pageOffset === 0 ? 'disabled' : ''}>← 이전</button><span>${Math.floor(pageOffset / 50) + 1} 페이지</span><button data-action="next" ${result.items.length < 50 ? 'disabled' : ''}>다음 →</button></div></section>`;
    } else if (view === 'vault') {
      const result = await api('/v1/vault');
      html = `<section class="vault-note"><strong>값은 저장 후 다시 표시되지 않습니다.</strong><p>비밀값은 AES-256-GCM으로 암호화되며, Vault 권한을 따로 허용한 에이전트만 <code>vault exec</code>로 프로세스에 전달할 수 있습니다. 이름과 사용 기록은 이 화면에 표시됩니다.</p></section><section class="console-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>암호화된 비밀</h2><p>${result.items.length}개의 비밀값이 저장되어 있습니다.</p></div></div>${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>이름 · 설명</th><th>마지막 사용</th><th>사용 횟수</th><th></th></tr></thead><tbody>${result.items.map(item => `<tr><td><strong>${h(item.name)}</strong><span class="record-subtitle">${h(item.description || '설명 없음')}</span></td><td>${date(item.last_accessed_at)}</td><td>${h(item.access_count)}</td><td><div class="row-actions"><button data-action="rotate-vault" data-name="${h(item.name)}" data-description="${h(item.description)}">교체</button><button class="danger" data-action="delete-vault" data-name="${h(item.name)}">삭제</button></div></td></tr>`).join('')}</tbody></table></div>` : empty('저장된 비밀값이 없어요.','API 토큰과 자동화 자격 증명을 암호화해 저장하고 허용한 에이전트에서 사용하세요.')}</section>`;
    } else if (view === 'keys') {
      const [result, mcp] = await Promise.all([api('/auth/api-keys'), api('/auth/mcp-connections')]);
      const scopeName = {'memory:read':'기억 조회','memory:write':'기억 저장','feature:write':'기능 요청'};
      const mcpRows = mcp.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>MCP 클라이언트</th><th>허용 범위</th><th>마지막 사용</th><th></th></tr></thead><tbody>${mcp.items.map(connection => `<tr><td><strong>${h(connection.client_name)}</strong><span class="record-subtitle">OAuth · 웹 승인 연결</span></td><td>${connection.scopes.map(scope => `<span class="tag">${h(scopeName[scope] || scope)}</span>`).join('')}</td><td>${date(connection.last_used_at)}</td><td><div class="row-actions"><button class="danger" data-action="revoke-mcp" data-id="${h(connection.client_id)}">연결 해제</button></div></td></tr>`).join('')}</tbody></table></div>` : '<p class="mcp-empty">아직 연결된 원격 MCP 클라이언트가 없습니다.</p>';
      html = `<section class="mcp-connect-card"><div class="mcp-connect-copy"><span>REMOTE MCP · OAUTH 2.1</span><h2>GPT와 Claude에 바로 연결하세요.</h2><p>커스텀 MCP 서버에 아래 주소를 추가하면 Vibe Memory 로그인 화면으로 이동합니다. API 키를 복사하거나 채팅에 붙여넣지 않습니다.</p><code>${h(mcp.server_url)}</code></div><div class="mcp-connect-actions"><div><img src="/assets/brands/codex.png" alt=""><strong>GPT</strong></div><div><img src="/assets/brands/claude-code.png" alt=""><strong>Claude</strong></div><button class="button primary" type="button" data-action="copy-mcp-url" data-url="${h(mcp.server_url)}">MCP 주소 복사 ⧉</button><a href="/guide.html#mcp" target="_blank" rel="noopener">연결 방법 보기 ↗</a></div></section><section class="console-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>원격 MCP 연결</h2><p>${mcp.items.length}개의 GPT·Claude 연결이 활성 상태입니다.</p></div></div>${mcpRows}</section><div class="agent-catalog" aria-label="지원하는 에이전트">${[['Claude Code','claude-code.png'],['Codex','codex.png'],['OpenClaw','openclaw.svg'],['Hermes','hermes.png']].map(([name,file]) => `<span><img src="/assets/brands/${file}" alt="" width="28" height="28">${name}</span>`).join('')}</div><section class="console-panel"><div class="panel-heading"><div class="panel-heading-copy"><h2>CLI·Skill 연결</h2><p>${result.items.length}개의 에이전트 키가 이 워크스페이스에 접근할 수 있습니다.</p></div><a class="secondary-button" href="/downloads/vibe-memory-skill.zip" download>Skill 다운로드</a></div><p class="key-note">Vault 권한은 기억 접근과 별도로 관리됩니다. 신뢰하는 에이전트에만 허용하고 언제든 철회하세요.</p>${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>에이전트 이름</th><th>키 식별자</th><th>Vault</th><th>연결일</th><th></th></tr></thead><tbody>${result.items.map(key => `<tr><td><strong>${h(key.name)}</strong></td><td><code>${h(key.prefix)}</code></td><td><button class="permission-toggle ${key.vault_access ? 'enabled' : ''}" data-action="toggle-vault-access" data-id="${h(key.id)}" data-enabled="${key.vault_access}">${key.vault_access ? '허용됨' : '차단됨'}</button></td><td>${date(key.created_at)}</td><td><div class="row-actions"><button class="danger" data-action="revoke" data-id="${h(key.id)}">연결 해제</button></div></td></tr>`).join('')}</tbody></table></div>` : empty('연결된 에이전트가 없어요.','에이전트에게 Vibe Memory 연결을 요청하면 웹 승인 링크를 안내합니다.','<a class="secondary-button" href="/guide.html" target="_blank">연결 방법 보기</a>')}</section><p class="section-caption">수동 키는 고급 설정용입니다. 새로 연결할 때는 에이전트가 만드는 웹 승인 링크를 권장합니다.</p>`;
    } else if (view === 'requests') {
      const result = await api(`/v1/feature-requests?limit=50&offset=${pageOffset}`);
      html = `<section class="console-panel">${result.items.length ? `<div class="table-scroll"><table class="records-table"><thead><tr><th>요청 내용</th><th>에이전트</th><th>상태</th><th>등록일</th></tr></thead><tbody>${result.items.map(item => `<tr><td><button class="record-title" data-action="request-detail" data-id="${h(item.id)}">${h(item.title)}</button><span class="record-subtitle">${h(item.description.slice(0,100))}</span></td><td>${h(item.agent_name)}</td><td><span class="tag">접수됨</span></td><td>${date(item.created_at)}</td></tr>`).join('')}</tbody></table></div>` : empty('더 나은 기억을 위한 아이디어가 있나요?','에이전트에서 요청을 보내거나 콘솔에서 필요한 기능과 사용 사례를 남겨주세요.')}</section>`;
    } else {
      const result = await api('/v1/relations');
      if (!result.items.length) {
        html = `<section class="relationship-panel relationship-empty-panel">${empty('기억 사이의 연결을 기다리고 있어요.','에이전트가 엔티티와 관계를 구성해 등록하면 여기에 표시됩니다.')}</section>`;
      } else {
        const allIds = [...new Set(result.items.flatMap(edge => [edge.source_id,edge.target_id]))];
        const degree = new Map(allIds.map(id => [id, 0]));
        for (const edge of result.items) {
          degree.set(edge.source_id, degree.get(edge.source_id) + 1); degree.set(edge.target_id, degree.get(edge.target_id) + 1);
        }
        const ranked = [...result.items].sort((a, b) => (degree.get(b.source_id) + degree.get(b.target_id)) - (degree.get(a.source_id) + degree.get(a.target_id)));
        const visibleIds = new Set(), visibleRelations = [];
        for (const edge of ranked) {
          const additions = Number(!visibleIds.has(edge.source_id)) + Number(!visibleIds.has(edge.target_id));
          if (visibleIds.size + additions > 21 || visibleRelations.length >= 36) continue;
          visibleIds.add(edge.source_id); visibleIds.add(edge.target_id); visibleRelations.push(edge);
        }
        const records = await Promise.all([...visibleIds].map(id => api('/v1/records/' + encodeURIComponent(id))));
        graphPayload = {records,relations:visibleRelations};
        html = relationshipGraph(records, visibleRelations, {nodes:allIds.length,relations:result.items.length});
      }
    }
    if (ticket !== generation) return;
    $('#view-content').innerHTML = html;
    if (view === 'keys') $('#view-content').insertAdjacentHTML('afterbegin', installPromptCard());
    if (view === 'relations' && graphPayload) await bindRelationshipGraph(graphPayload.records, graphPayload.relations);
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
  editor('에이전트 API 키 만들기','<p class="dialog-help">어떤 에이전트에 사용할 키인지 이름을 붙여주세요.</p><label>에이전트 이름<input name="name" placeholder="예: Claude Code, Codex, OpenClaw, Hermes" maxlength="80" required></label><label class="check-field"><input type="checkbox" name="vault_access"> 이 키에 Vault 비밀값 사용 권한 허용</label><p class="dialog-help">Vault 권한은 저장된 모든 비밀값을 실행 프로세스에 전달할 수 있는 민감한 권한입니다.</p>', async data => {
    const record = await api('/auth/api-keys',{method:'POST',body:JSON.stringify({name:data.get('name'),vault_access:data.has('vault_access')})});
    detail('새 API 키가 만들어졌어요.',`<div class="key-once"><p>지금 한 번만 확인할 수 있어요. 에이전트에서 설치된 Skill 안의 Rust CLI를 절대 경로로 실행하고 <code>configure</code>의 숨김 입력으로 저장하세요. 채팅이나 환경변수에 붙여넣지 마세요.</p><code id="new-key">${h(record.key)}</code><button class="secondary-button" id="copy-key">API 키 복사 ⧉</button></div><pre class="detail-pre">"/absolute/path/to/vibe-memory/bin/vibe-memory" configure</pre>`);
    $('#copy-key').addEventListener('click',async () => { try { await navigator.clipboard.writeText(record.key); toast('API 키를 복사했습니다.'); } catch { toast('표시된 키를 선택해 복사해주세요.'); } });
  },'키 만들기');
}
function editVault(name = '', description = '') {
  const fixed = Boolean(name);
  editor(fixed ? 'Vault 비밀값 교체' : 'Vault 비밀값 추가',`<p class="dialog-help">값은 전송 후 이 화면에 다시 표시되지 않습니다. 이름에는 영문자, 숫자, 점, 밑줄, 하이픈만 사용할 수 있습니다.</p><label>이름<input name="name" value="${h(name)}" ${fixed ? 'readonly' : ''} pattern="[A-Za-z][A-Za-z0-9_.-]{0,99}" maxlength="100" placeholder="예: GITHUB_TOKEN" required></label><label>설명<input name="description" value="${h(description)}" maxlength="500" placeholder="어디에 사용하는 비밀값인지"></label><label>비밀값<textarea name="value" maxlength="65536" autocomplete="off" autocapitalize="off" spellcheck="false" required placeholder="값을 붙여넣으세요"></textarea></label>`,async data => {
    const vaultName = data.get('name');
    await api('/v1/vault/' + encodeURIComponent(vaultName),{method:'PUT',body:JSON.stringify({value:data.get('value'),description:data.get('description')})});
    toast(fixed ? '비밀값을 안전하게 교체했습니다.' : '비밀값을 암호화해 저장했습니다.');
  },fixed ? '교체' : '암호화 저장');
}
function primaryAction() {
  if (currentView === 'keys') return createKey();
  if (currentView === 'vault') return editVault();
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
  const {action,id,name,description,sourceName,targetName,relation,reason,url} = button.dataset;
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
    if (action === 'dismiss-dashboard-guide') {
      dismissDashboardGuide();
      toast('대시보드 안내를 숨겼습니다.');
      return navigate('overview', false);
    }
    if (action === 'focus-search') {
      await navigate('memories');
      $('#search-records [name="keywords"]')?.focus();
      return;
    }
    if (action === 'add-memory') { await navigate('memories'); return primaryAction(); }
    if (action === 'upload-file') { await navigate('documents'); return primaryAction(); }
    if (action === 'copy-install-prompt') {
      const prompt = window.vibeMemoryInstallPrompt();
      try { await copyText(prompt); toast('설치·최신화 프롬프트를 복사했습니다. 에이전트 대화에 붙여넣으세요.'); }
      catch { detail('에이전트 설치·최신화 프롬프트', `<p class="dialog-help">자동 복사가 차단됐습니다. 아래 내용을 선택해 복사하세요.</p><pre class="detail-pre">${h(prompt)}</pre>`); }
      return;
    }
    if (action === 'copy-mcp-url') {
      try { await copyText(url); toast('MCP 서버 주소를 복사했습니다.'); }
      catch { detail('Vibe Memory MCP 주소', `<pre class="detail-pre">${h(url)}</pre>`); }
      return;
    }
    if (action === 'create-key') return createKey();
    if (action === 'rotate-vault') return editVault(name, description);
    if (action === 'toggle-vault-access') {
      const enabled = button.dataset.enabled === 'true';
      if (!enabled && !confirm('이 에이전트에 Vault의 모든 비밀값을 사용할 권한을 허용할까요?')) return;
      await api('/auth/api-keys/' + encodeURIComponent(id),{method:'PATCH',body:JSON.stringify({vault_access:!enabled})});
      toast(enabled ? 'Vault 권한을 차단했습니다.' : 'Vault 권한을 허용했습니다.');
      return navigate(currentView,false);
    }
    if (action === 'reload') return navigate(currentView, false);
    if (action === 'next') { pageOffset += 50; return navigate(currentView, false); }
    if (action === 'previous') { pageOffset = Math.max(0,pageOffset - 50); return navigate(currentView, false); }
    if (action === 'detail') { const record = await api('/v1/records/' + encodeURIComponent(id)); return detail(record.title || '기록 상세', `<p class="detail-content-text">${h(record.content)}</p><pre class="detail-pre">${h(JSON.stringify(record,null,2))}</pre>`); }
    if (action === 'request-detail') { const record = await api('/v1/feature-requests/' + encodeURIComponent(id)); return detail(record.title,`<pre class="detail-pre">${h(JSON.stringify(record,null,2))}</pre>`); }
    if (action === 'relation-detail') {
      return detail('관계 근거',`<div class="relation-detail-route"><span>${h(sourceName)}</span><strong>${h(relation)}</strong><span>${h(targetName)}</span></div><div class="relation-detail-reason"><span>에이전트가 등록한 근거</span><p>${h(reason)}</p></div>`);
    }
    if (action === 'graph') {
      const graph = await api('/v1/graph/' + encodeURIComponent(id) + '?depth=2');
      return detail('연결된 기억',`<div class="graph-nodes">${graph.nodes.map(node => `<div class="graph-node"><strong>${h(node.kind)}</strong>${h(node.title)}</div>`).join('')}</div><pre class="detail-pre">${h(JSON.stringify(graph.relations.map(edge => ({relation:edge.relation,reason:edge.reason,source:edge.source_id,target:edge.target_id})),null,2))}</pre>`);
    }
    if (action === 'revoke' && confirm('이 API 키를 삭제할까요? 연결된 에이전트에서 더 이상 사용할 수 없습니다.')) {
      await api('/auth/api-keys/' + encodeURIComponent(id),{method:'DELETE'}); toast('API 키를 삭제했습니다.'); await navigate(currentView,false);
    }
    if (action === 'revoke-mcp' && confirm('이 GPT·Claude MCP 연결을 해제할까요?')) {
      await api('/auth/mcp-connections/' + encodeURIComponent(id),{method:'DELETE'}); toast('MCP 연결을 해제했습니다.'); await navigate(currentView,false);
    }
    if (action === 'delete-vault' && confirm(`${name} 비밀값을 영구 삭제할까요?`)) {
      await api('/v1/vault/' + encodeURIComponent(name),{method:'DELETE'}); toast('Vault 비밀값을 삭제했습니다.'); await navigate(currentView,false);
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
window.addEventListener('popstate',() => {
  const view = viewFromLocation();
  if (view !== currentView) navigate(view, true, 'none');
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
    await navigate(viewFromLocation(), true, 'replace');
  } catch (error) { $('#console-error').textContent = error.message; $('#console-error').hidden = false; }
})();
