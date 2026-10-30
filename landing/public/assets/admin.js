'use strict';
const $ = selector => document.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const utcDate = value => value ? new Date(value).toLocaleString('ko-KR', {timeZone:'UTC',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) + ' UTC' : '—';
const statusInfo = status => ({
  received:['접수됨','received'], reviewing:['검토 중','reviewing'], planned:['계획됨','planned'],
  in_progress:['처리 중','in-progress'], completed:['완료','completed'], declined:['보류','declined']
}[status] || [status,'received']);
const priorityLabel = priority => ({high:'높음',medium:'보통',low:'낮음'}[priority] || priority);
let offset = 0, payload = {items:[],counts:{},total:0}, userOffset = 0;
let usersPayload = {items:[],total:0}, operatorPayload = {items:[]}, toastTimer, userSearchTimer;

async function api(path, options = {}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json'}, credentials:'same-origin', ...options});
  let data = null;
  if (response.status !== 204) {
    try { data = await response.json(); } catch { throw new Error('서버 응답을 확인할 수 없습니다.'); }
  }
  if (!response.ok) {
    if (response.status === 401) { location.replace('/login?next=%2Fadmin'); throw new Error('로그인이 필요합니다.'); }
    if (response.status === 403) { location.replace('/console'); throw new Error('관리자 권한이 필요합니다.'); }
    throw new Error(typeof data?.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.');
  }
  return data;
}
function toast(message) {
  $('#admin-toast').textContent = message; $('#admin-toast').classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#admin-toast').classList.remove('visible'), 2600);
}
function statusBadge(status) {
  const [label,style] = statusInfo(status);
  return `<span class="admin-status ${style}">${h(label)}</span>`;
}
function bytes(value) {
  const size = Number(value || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 ** 2) return `${(size / 1024).toFixed(1)} KiB`;
  if (size < 1024 ** 3) return `${(size / 1024 ** 2).toFixed(1)} MiB`;
  return `${(size / 1024 ** 3).toFixed(1)} GiB`;
}
function renderStats() {
  const cards = [
    ['', '전체', payload.total],
    ['received', '접수됨', payload.counts.received || 0],
    ['reviewing', '검토 중', payload.counts.reviewing || 0],
    ['in_progress', '처리 중', payload.counts.in_progress || 0],
    ['completed', '완료', payload.counts.completed || 0],
  ];
  const selected = $('#status-filter').value;
  $('#admin-stats').innerHTML = cards.map(([value,label,count]) => `<button type="button" data-status="${value}" class="${selected === value ? 'selected' : ''}"><span>${h(label)}</span><strong>${count}</strong><small>${value ? 'STATUS' : 'ALL REQUESTS'}</small></button>`).join('');
}
function visibleItems() {
  const query = $('#request-search').value.trim().toLowerCase();
  if (!query) return payload.items;
  return payload.items.filter(item => [item.title,item.description,item.result,item.requester?.name,item.requester?.email,item.agent_name].some(value => String(value || '').toLowerCase().includes(query)));
}
function renderRows() {
  const items = visibleItems();
  $('#queue-description').textContent = `${payload.total}개 요청 중 ${items.length}개를 표시합니다.`;
  $('#request-rows').innerHTML = items.length ? items.map(item => `<tr><td><button class="admin-request-title" type="button" data-action="edit" data-owner="${h(item.owner_id)}" data-id="${h(item.id)}">${h(item.title)}</button><span>${h(item.description.slice(0,110))}</span></td><td><strong>${h(item.requester?.name || 'Legacy workspace')}</strong><small>${h(item.requester?.email || item.owner_id)}</small></td><td><span class="admin-priority ${h(item.priority)}">${h(priorityLabel(item.priority))}</span></td><td>${statusBadge(item.status)}</td><td><p class="admin-result ${item.result ? '' : 'empty'}">${h(item.result || '결과 대기 중')}</p></td><td><time>${h(utcDate(item.updated_at))}</time></td><td><button class="admin-edit" type="button" data-action="edit" data-owner="${h(item.owner_id)}" data-id="${h(item.id)}">처리</button></td></tr>`).join('') : '<tr><td colspan="7" class="admin-empty">조건에 맞는 기능 요청이 없습니다.</td></tr>';
  $('#admin-previous').disabled = offset === 0;
  $('#admin-next').disabled = payload.items.length < 50;
  $('#admin-page-number').textContent = `${Math.floor(offset / 50) + 1} 페이지`;
}
async function load() {
  $('#request-rows').innerHTML = '<tr><td colspan="7" class="admin-loading">불러오는 중…</td></tr>';
  const status = $('#status-filter').value;
  payload = await api(`/v1/admin/feature-requests?limit=50&offset=${offset}${status ? `&status=${encodeURIComponent(status)}` : ''}`);
  renderStats(); renderRows();
}
function renderUsers() {
  $('#user-description').textContent = `${usersPayload.total}명의 사용자 중 ${usersPayload.items.length}명을 표시합니다.`;
  $('#user-rows').innerHTML = usersPayload.items.length ? usersPayload.items.map(user => `<tr><td><strong>${h(user.name)}</strong><small>${h(user.email)}</small><code>${h(user.id)}</code></td><td><span class="admin-role ${user.is_admin ? 'administrator' : ''}">${user.is_admin ? '관리자' : '사용자'}</span></td><td><span class="admin-role ${user.totp_enabled ? 'otp-enabled' : ''}">${user.totp_enabled ? 'OTP 사용' : '비밀번호'}</span></td><td><time>${h(utcDate(new Date(user.created_at * 1000).toISOString()))}</time></td><td><strong>${h(user.api_key_count + user.mcp_connection_count)}</strong><small>API 키 ${h(user.api_key_count)} · MCP ${h(user.mcp_connection_count)} · 세션 ${h(user.active_session_count)}</small></td><td><strong>${h(user.record_count)}</strong><small>관계 ${h(user.relation_count)} · Vault ${h(user.vault_entry_count)}</small></td><td><strong>${h(bytes(user.storage_bytes))}</strong><small>기억 ${h(bytes(user.memory_bytes))} · 파일 ${h(bytes(user.file_bytes))}</small></td></tr>`).join('') : '<tr><td colspan="7" class="admin-empty">조건에 맞는 사용자가 없습니다.</td></tr>';
  $('#users-previous').disabled = userOffset === 0;
  $('#users-next').disabled = usersPayload.items.length < 50;
  $('#users-page-number').textContent = `${Math.floor(userOffset / 50) + 1} 페이지`;
}
async function loadUsers() {
  $('#user-rows').innerHTML = '<tr><td colspan="7" class="admin-loading">불러오는 중…</td></tr>';
  const query = $('#user-search').value.trim();
  usersPayload = await api(`/v1/admin/users?limit=50&offset=${userOffset}${query ? `&q=${encodeURIComponent(query)}` : ''}`);
  renderUsers();
}
function renderOperators() {
  const target = $('#operator-agent-list');
  target.innerHTML = operatorPayload.items.length ? operatorPayload.items.map(agent => `<article class="admin-operator-card"><div><span class="admin-operator-status ${agent.feature_request_operator ? 'enabled' : ''}">${agent.feature_request_operator ? '운영 권한 활성' : '일반 에이전트'}</span><strong>${h(agent.name)}</strong><small>${h(agent.prefix)} · 연결 ${h(utcDate(new Date(agent.created_at * 1000).toISOString()))}</small></div><dl><div><dt>기능 요청 전체 조회</dt><dd>${agent.feature_request_operator ? '허용' : '차단'}</dd></div><div><dt>기능 요청 처리·수정</dt><dd>${agent.feature_request_operator ? '허용' : '차단'}</dd></div><div><dt>Vault</dt><dd>${agent.vault_access ? '별도 허용됨' : '차단'}</dd></div></dl><button type="button" data-action="toggle-operator" data-id="${h(agent.id)}" data-enabled="${agent.feature_request_operator ? 'true' : 'false'}" class="${agent.feature_request_operator ? 'danger' : 'primary'}">${agent.feature_request_operator ? '운영 권한 회수' : '운영 에이전트로 승인'}</button></article>`).join('') : '<p class="admin-empty">연결된 에이전트가 없습니다. 콘솔에서 에이전트를 먼저 연결하세요.</p>';
}
async function loadOperators() {
  $('#operator-agent-list').innerHTML = '<p class="admin-loading">에이전트 연결을 불러오는 중…</p>';
  operatorPayload = await api('/v1/admin/operator-agents');
  renderOperators();
}
function editRequest(owner,id) {
  const item = payload.items.find(record => record.owner_id === owner && record.id === id);
  if (!item) return;
  $('#request-heading').textContent = item.title;
  $('#requester-name').textContent = item.requester?.name || 'Legacy workspace';
  $('#requester-email').textContent = item.requester?.email || item.owner_id;
  $('#request-agent-name').textContent = item.agent_name;
  $('#request-source').textContent = item.source || '출처 미지정';
  $('#request-owner-id').value = item.owner_id; $('#request-id').value = item.id;
  $('#request-edit-title').value = item.title;
  $('#request-edit-description').value = item.description;
  $('#request-edit-use-case').value = item.use_case || '';
  $('#request-edit-priority').value = item.priority;
  $('#request-status').value = item.status; $('#request-result').value = item.result || '';
  $('#request-result-url').value = item.result_url || '';
  $('#request-editor-error').hidden = true; window.VMUI.openModal($('#request-editor'));
}

document.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.status !== undefined) {
    $('#status-filter').value = button.dataset.status; offset = 0; load().catch(showError); return;
  }
  if (button.dataset.action === 'edit') editRequest(button.dataset.owner, button.dataset.id);
  if (button.dataset.action === 'toggle-operator') {
    const enabled = button.dataset.enabled === 'true';
    const accepted = await window.VMUI.confirm({
      title: enabled ? '운영 권한을 회수할까요?' : '운영 에이전트로 승인할까요?',
      message: enabled
        ? '이 에이전트는 즉시 모든 사용자의 기능 요청 조회와 처리를 할 수 없게 됩니다.'
        : '이 에이전트는 모든 사용자의 기능 요청 내용을 조회하고 처리 상태와 공개 결과를 수정할 수 있습니다. 기억·사용자·Vault 권한은 부여되지 않습니다.',
      confirmLabel: enabled ? '권한 회수' : '운영 에이전트로 승인',
      tone: enabled ? 'danger' : 'default'
    });
    if (!accepted) return;
    button.disabled = true;
    try {
      await api('/v1/admin/operator-agents/' + encodeURIComponent(button.dataset.id), {method:'PATCH',body:JSON.stringify({feature_request_operator:!enabled})});
      toast(enabled ? '운영 에이전트 권한을 회수했습니다.' : '운영 에이전트 권한을 승인했습니다.');
      await loadOperators();
    } catch (error) { showError(error); button.disabled = false; }
  }
});
document.querySelectorAll('.admin-dialog-close').forEach(button => button.addEventListener('click',() => window.VMUI.closeModal($('#request-editor'))));
$('#request-editor').addEventListener('click',event => { if (event.target === $('#request-editor')) window.VMUI.closeModal($('#request-editor')); });
$('#status-filter').addEventListener('change',() => { offset = 0; load().catch(showError); });
$('#request-search').addEventListener('input',renderRows);
$('#admin-refresh').addEventListener('click',() => load().catch(showError));
$('#admin-previous').addEventListener('click',() => { offset = Math.max(0,offset-50); load().catch(showError); });
$('#admin-next').addEventListener('click',() => { offset += 50; load().catch(showError); });
$('#users-refresh').addEventListener('click',() => loadUsers().catch(showError));
$('#operators-refresh').addEventListener('click',() => loadOperators().catch(showError));
$('#users-previous').addEventListener('click',() => { userOffset = Math.max(0,userOffset-50); loadUsers().catch(showError); });
$('#users-next').addEventListener('click',() => { userOffset += 50; loadUsers().catch(showError); });
$('#user-search').addEventListener('input',() => {
  clearTimeout(userSearchTimer);
  userSearchTimer = setTimeout(() => { userOffset = 0; loadUsers().catch(showError); }, 250);
});
$('#request-editor-form').addEventListener('submit',async event => {
  event.preventDefault();
  const save = $('#request-save'); save.disabled = true; $('#request-editor-error').hidden = true;
  try {
    const owner = encodeURIComponent($('#request-owner-id').value), id = encodeURIComponent($('#request-id').value);
    await api(`/v1/admin/feature-requests/${owner}/${id}`, {method:'PATCH',body:JSON.stringify({title:$('#request-edit-title').value,description:$('#request-edit-description').value,use_case:$('#request-edit-use-case').value,priority:$('#request-edit-priority').value,status:$('#request-status').value,result:$('#request-result').value,result_url:$('#request-result-url').value})});
    window.VMUI.closeModal($('#request-editor')); toast('요청과 처리 결과를 저장했습니다.'); await load();
  } catch (error) { $('#request-editor-error').textContent = error.message; $('#request-editor-error').hidden = false; }
  finally { save.disabled = false; }
});
$('#admin-logout').addEventListener('click',async () => { try { await api('/auth/logout',{method:'POST'}); location.replace('/login'); } catch (error) { showError(error); } });
function showError(error) { $('#admin-error').textContent = error.message; $('#admin-error').hidden = false; }

(async () => {
  try {
    const account = await api('/auth/me');
    if (!account.is_admin) { location.replace('/console'); return; }
    $('#admin-name').textContent = account.user.name; $('#admin-email').textContent = account.user.email;
    await Promise.all([load(), loadUsers(), loadOperators()]);
  } catch (error) { showError(error); }
})();
