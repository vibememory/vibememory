'use strict';
let mode = 'login';
const form = document.querySelector('#auth-form');
const errorBox = document.querySelector('#auth-error');
function selectMode(next) {
  mode = next;
  errorBox.hidden = true;
  document.querySelector('#name-field').hidden = mode !== 'signup';
  document.querySelector('#name').required = mode === 'signup';
  document.querySelector('#password').autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
  document.querySelector('#auth-title').textContent = mode === 'signup' ? '나의 기억을 시작해요.' : '다시 만나 반가워요.';
  document.querySelector('#auth-subtitle').textContent = mode === 'signup' ? '계정을 만들고 에이전트에 기억을 연결하세요.' : '로그인하고 나의 기억을 이어가세요.';
  document.querySelector('#auth-submit').textContent = mode === 'signup' ? '계정 만들고 시작하기 ↗' : '로그인 ↗';
  document.querySelector('#auth-note').textContent = mode === 'signup' ? '이메일은 로그인 식별자로 사용됩니다. 비밀번호는 10자 이상으로 설정해주세요.' : '내 계정에 저장된 기억만 볼 수 있습니다.';
  form.setAttribute('aria-labelledby', mode + '-tab');
  for (const tab of document.querySelectorAll('[data-mode]')) {
    tab.setAttribute('aria-selected', String(tab.dataset.mode === mode));
    tab.tabIndex = tab.dataset.mode === mode ? 0 : -1;
  }
}
for (const tab of document.querySelectorAll('[data-mode]')) {
  tab.addEventListener('click', () => selectMode(tab.dataset.mode));
  tab.addEventListener('keydown', event => {
    if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault(); selectMode(mode === 'login' ? 'signup' : 'login');
      document.querySelector(`[data-mode="${mode}"]`).focus();
    }
  });
}
document.querySelector('#show-password').addEventListener('click', event => {
  const input = document.querySelector('#password');
  input.type = input.type === 'password' ? 'text' : 'password';
  event.target.textContent = input.type === 'password' ? '보기' : '숨기기';
  event.target.setAttribute('aria-label', input.type === 'password' ? '비밀번호 표시' : '비밀번호 숨기기');
});
form.addEventListener('submit', async event => {
  event.preventDefault(); errorBox.hidden = true;
  const button = document.querySelector('#auth-submit'); button.disabled = true; button.textContent = '잠시만 기다려주세요…';
  const payload = {email: document.querySelector('#email').value, password: document.querySelector('#password').value};
  if (mode === 'signup') payload.name = document.querySelector('#name').value;
  try {
    const response = await fetch('/auth/' + mode, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력한 내용을 다시 확인해주세요.');
    document.querySelector('#password').value = '';
    window.location.replace('/console');
  } catch (error) {
    errorBox.textContent = error instanceof TypeError ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.' : error.message;
    errorBox.hidden = false;
    button.disabled = false; button.textContent = mode === 'signup' ? '계정 만들고 시작하기 ↗' : '로그인 ↗';
  }
});
fetch('/auth/me').then(response => { if (response.ok) window.location.replace('/console'); }).catch(() => {});
