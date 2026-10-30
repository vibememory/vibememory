'use strict';
const statusBox = document.querySelector('#connect-status');
const code = new URLSearchParams(location.search).get('code') || '';
async function start() {
  if (!/^[a-fA-F0-9]{10}$/.test(code)) throw new Error('올바른 연결 링크로 다시 시작해주세요.');
  const me = await fetch('/auth/me', {cache: 'no-store'});
  if (me.status === 401) {
    location.replace('/login?next=' + encodeURIComponent('/connect?code=' + code));
    return;
  }
  if (!me.ok) throw new Error('계정을 확인할 수 없습니다.');
  const account = (await me.json()).user;
  const response = await fetch('/auth/device?code=' + encodeURIComponent(code), {cache: 'no-store'});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || '연결 요청을 확인할 수 없습니다.');
  if (data.state !== 'pending') throw new Error('이미 처리된 연결 요청입니다. 에이전트에서 연결 결과를 확인하세요.');
  document.querySelector('#account').textContent = account.email;
  document.querySelector('#agent-name').textContent = data.name;
  document.querySelector('#user-code').textContent = code.toUpperCase();
  document.querySelector('#vault-scope').hidden = !data.vault_access;
  document.querySelector('#vault-access').checked = Boolean(data.vault_access);
  statusBox.textContent = data.upgrade ? '기존 에이전트의 Vault 권한 변경을 승인할까요?' : '이 에이전트의 연결을 승인할까요?';
  document.querySelector('#approval').hidden = false;
}
async function decide(approved) {
  for (const button of document.querySelectorAll('button')) button.disabled = true;
  try {
    const vaultAccess = approved && !document.querySelector('#vault-scope').hidden && document.querySelector('#vault-access').checked;
    const response = await fetch('/auth/device/approve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({user_code: code, approved, vault_access: vaultAccess})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '연결을 처리할 수 없습니다.');
    document.querySelector('#approval').hidden = true;
    statusBox.textContent = approved ? `승인했습니다. Vault 권한: ${data.vault_access ? '허용' : '허용하지 않음'}. 에이전트가 자동으로 결과를 확인합니다.` : '연결 요청을 거절했습니다.';
  } catch (error) {
    statusBox.textContent = error.message;
    for (const button of document.querySelectorAll('button')) button.disabled = false;
  }
}
document.querySelector('#approve').addEventListener('click', () => decide(true));
document.querySelector('#deny').addEventListener('click', () => decide(false));
start().catch(error => { statusBox.textContent = error.message; });
