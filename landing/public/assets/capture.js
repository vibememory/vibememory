'use strict';
const tokenFromHash = new URLSearchParams(location.hash.slice(1)).get('token') || '';
if (/^[A-Za-z0-9_-]{40,60}$/.test(tokenFromHash)) {
  sessionStorage.setItem('vibe-memory-vault-capture', tokenFromHash);
  history.replaceState(null, '', '/capture');
}
const captureToken = tokenFromHash || sessionStorage.getItem('vibe-memory-vault-capture') || '';
const statusText = document.querySelector('#capture-status');
const requestBox = document.querySelector('#capture-request');
const captureForm = document.querySelector('#capture-form');
const errorBox = document.querySelector('#capture-error');
const successBox = document.querySelector('#capture-success');

function showError(message) {
  statusText.textContent = message;
  errorBox.textContent = message;
  errorBox.hidden = false;
}

async function responseData(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '요청을 처리할 수 없습니다.');
  return data;
}

async function loadCapture() {
  if (!/^[A-Za-z0-9_-]{40,60}$/.test(captureToken)) {
    sessionStorage.removeItem('vibe-memory-vault-capture');
    showError('올바르지 않은 Vault 입력 링크입니다.');
    return;
  }
  const response = await fetch('/v1/vault/captures/' + encodeURIComponent(captureToken), {
    headers: {'Accept': 'application/json', 'Cache-Control': 'no-store'},
    cache: 'no-store'
  });
  if (response.status === 401) {
    location.replace('/login?next=' + encodeURIComponent('/capture'));
    return;
  }
  const data = await responseData(response);
  document.querySelector('#capture-agent').textContent = data.requester_agent_name;
  document.querySelector('#capture-name').textContent = data.name;
  document.querySelector('#capture-expiry').textContent = new Date(data.expires_at * 1000).toISOString().replace('.000Z', 'Z') + ' (UTC)';
  if (data.description) {
    const description = document.querySelector('#capture-description');
    description.textContent = data.description;
    description.hidden = false;
  }
  statusText.textContent = '요청 내용과 저장 위치를 확인한 뒤 값을 입력하세요.';
  requestBox.hidden = false;
  captureForm.hidden = false;
  document.querySelector('#capture-value').focus();
}

captureForm.addEventListener('submit', async event => {
  event.preventDefault();
  errorBox.hidden = true;
  const input = document.querySelector('#capture-value');
  const value = input.value;
  const button = document.querySelector('#capture-submit');
  button.disabled = true;
  button.textContent = '암호화하여 저장 중…';
  try {
    const response = await fetch('/v1/vault/captures/' + encodeURIComponent(captureToken), {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({value})
    });
    input.value = '';
    await responseData(response);
    sessionStorage.removeItem('vibe-memory-vault-capture');
    captureForm.hidden = true;
    requestBox.hidden = true;
    statusText.hidden = true;
    successBox.hidden = false;
  } catch (error) {
    input.value = '';
    errorBox.textContent = error instanceof TypeError ? '서버에 연결할 수 없습니다.' : error.message;
    errorBox.hidden = false;
    button.disabled = false;
    button.textContent = 'Vault에 안전하게 저장 ↗';
  }
});

loadCapture().catch(error => showError(error instanceof TypeError ? '서버에 연결할 수 없습니다.' : error.message));
