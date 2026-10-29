'use strict';
const $ = selector => document.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const utcDate = value => value ? new Date(value).toLocaleString('ko-KR', {timeZone:'UTC',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) + ' UTC' : '—';
const statusInfo = status => ({
  received:['접수됨','received'], reviewing:['검토 중','reviewing'], planned:['계획됨','planned'],
  in_progress:['처리 중','in-progress'], completed:['완료','completed'], declined:['보류','declined']
}[status] || [status,'received']);
const priorityLabel = priority => ({high:'높음',medium:'보통',low:'낮음'}[priority] || priority);
let offset = 0, payload = {items:[],counts:{},total:0}, toastTimer;

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
function editRequest(owner,id) {
  const item = payload.items.find(record => record.owner_id === owner && record.id === id);
  if (!item) return;
  $('#request-title').textContent = item.title;
  $('#requester-name').textContent = item.requester?.name || 'Legacy workspace';
  $('#requester-email').textContent = item.requester?.email || item.owner_id;
  $('#request-priority').textContent = priorityLabel(item.priority);
  $('#request-description').textContent = item.description;
  $('#request-use-case').textContent = item.use_case;
  $('#request-use-case-section').hidden = !item.use_case;
  $('#request-owner-id').value = item.owner_id; $('#request-id').value = item.id;
  $('#request-status').value = item.status; $('#request-result').value = item.result || '';
  $('#request-result-url').value = item.result_url || '';
  $('#request-editor-error').hidden = true; $('#request-editor').showModal();
}

document.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.status !== undefined) {
    $('#status-filter').value = button.dataset.status; offset = 0; load().catch(showError); return;
  }
  if (button.dataset.action === 'edit') editRequest(button.dataset.owner, button.dataset.id);
});
document.querySelectorAll('.admin-dialog-close').forEach(button => button.addEventListener('click',() => $('#request-editor').close()));
$('#request-editor').addEventListener('click',event => { if (event.target === $('#request-editor')) $('#request-editor').close(); });
$('#status-filter').addEventListener('change',() => { offset = 0; load().catch(showError); });
$('#request-search').addEventListener('input',renderRows);
$('#admin-refresh').addEventListener('click',() => load().catch(showError));
$('#admin-previous').addEventListener('click',() => { offset = Math.max(0,offset-50); load().catch(showError); });
$('#admin-next').addEventListener('click',() => { offset += 50; load().catch(showError); });
$('#request-editor-form').addEventListener('submit',async event => {
  event.preventDefault();
  const save = $('#request-save'); save.disabled = true; $('#request-editor-error').hidden = true;
  try {
    const owner = encodeURIComponent($('#request-owner-id').value), id = encodeURIComponent($('#request-id').value);
    await api(`/v1/admin/feature-requests/${owner}/${id}`, {method:'PATCH',body:JSON.stringify({status:$('#request-status').value,result:$('#request-result').value,result_url:$('#request-result-url').value})});
    $('#request-editor').close(); toast('처리 결과를 저장했습니다.'); await load();
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
    await load();
  } catch (error) { showError(error); }
})();
