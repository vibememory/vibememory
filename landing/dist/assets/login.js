'use strict';
let mode = 'login';
let otpChallenge = '';
const initialParams = new URLSearchParams(location.search);
const requestedNext = initialParams.get('next') || '';
const recoveryToken = initialParams.get('token') || '';
let destination = '/console';
try {
  const nextUrl = new URL(requestedNext, location.origin);
  const approvedPath = /^\/connect\?code=[A-Fa-f0-9]{10}$/.test(requestedNext)
    || (requestedNext === '/capture' && nextUrl.origin === location.origin)
    || (nextUrl.origin === location.origin && nextUrl.pathname === '/oauth/authorize' && !nextUrl.hash);
  if (approvedPath && requestedNext.length <= 8192) destination = nextUrl.pathname + nextUrl.search;
} catch { /* Keep the console as the safe destination. */ }
const form = document.querySelector('#auth-form');
const errorBox = document.querySelector('#auth-error');
function setActionLabel(button, label) {
  button.innerHTML = `${label} <svg class="svg-icon" aria-hidden="true"><use href="/assets/icons.svg#arrow-right"></use></svg>`;
}
function selectMode(next) {
  mode = next;
  otpChallenge = '';
  errorBox.hidden = true;
  document.querySelector('.auth-tabs').hidden = false;
  document.querySelector('#name-field').hidden = mode !== 'signup';
  document.querySelector('#email-field').hidden = false;
  document.querySelector('#password-field').hidden = false;
  document.querySelector('#forgot-password').hidden = mode !== 'login';
  document.querySelector('#otp-field').hidden = true;
  document.querySelector('#name').required = mode === 'signup';
  document.querySelector('#email').required = true;
  document.querySelector('#password').required = true;
  document.querySelector('#otp-code').required = false;
  document.querySelector('#password').autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
  document.querySelector('#auth-title').textContent = mode === 'signup' ? '나의 기억을 시작해요.' : '다시 만나 반가워요.';
  document.querySelector('#auth-subtitle').textContent = mode === 'signup' ? '계정을 만들고 에이전트에 기억을 연결하세요.' : '로그인하고 나의 기억을 이어가세요.';
  setActionLabel(document.querySelector('#auth-submit'), mode === 'signup' ? '계정 만들고 시작하기' : '로그인');
  document.querySelector('#auth-note').textContent = mode === 'signup' ? '이메일은 로그인 식별자로 사용됩니다. 비밀번호는 10자 이상으로 설정해주세요.' : '내 계정에 저장된 기억만 볼 수 있습니다.';
  form.setAttribute('aria-labelledby', mode + '-tab');
  for (const tab of document.querySelectorAll('[data-mode]')) {
    tab.setAttribute('aria-selected', String(tab.dataset.mode === mode));
    tab.tabIndex = tab.dataset.mode === mode ? 0 : -1;
  }
}
function selectRecoveryMode(next) {
  mode = next; otpChallenge = ''; errorBox.hidden = true;
  document.querySelector('.auth-tabs').hidden = true;
  document.querySelector('#name-field').hidden = true;
  document.querySelector('#otp-field').hidden = true;
  document.querySelector('#forgot-password').hidden = true;
  document.querySelector('#name').required = false;
  document.querySelector('#otp-code').required = false;
  document.querySelector('#email-field').hidden = next !== 'forgot';
  document.querySelector('#email').required = next === 'forgot';
  document.querySelector('#password-field').hidden = next !== 'reset-password';
  document.querySelector('#password').required = next === 'reset-password';
  document.querySelector('#password').autocomplete = 'new-password';
  const copy = {
    forgot:['비밀번호를 다시 설정하세요.','검증된 복구 이메일로 일회용 링크를 보냅니다.','재설정 안내 받기','가입 여부와 복구 수단 유무는 표시하지 않습니다.'],
    'verify-email':['복구 이메일을 확인할게요.','메일을 받은 브라우저에서 아래 버튼을 눌러 확인을 완료하세요.','복구 이메일 확인','링크를 여는 것만으로는 계정이 변경되지 않습니다.'],
    'reset-password':['새 비밀번호를 설정하세요.','재설정 후에는 새 비밀번호로 다시 로그인해야 합니다.','비밀번호 재설정','OTP와 에이전트 연결 권한은 유지되고 브라우저 세션만 종료됩니다.']
  }[next];
  document.querySelector('#auth-title').textContent = copy[0];
  document.querySelector('#auth-subtitle').textContent = copy[1];
  setActionLabel(document.querySelector('#auth-submit'), copy[2]);
  document.querySelector('#auth-note').textContent = copy[3];
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
document.querySelector('#forgot-password').addEventListener('click', () => selectRecoveryMode('forgot'));
form.addEventListener('submit', async event => {
  event.preventDefault(); errorBox.hidden = true;
  const button = document.querySelector('#auth-submit'); button.disabled = true; button.textContent = '잠시만 기다려주세요…';
  const payload = mode === 'verify-email'
    ? {token: recoveryToken}
    : mode === 'reset-password'
      ? {token: recoveryToken, password: document.querySelector('#password').value}
      : mode === 'forgot'
        ? {email: document.querySelector('#email').value}
        : otpChallenge
          ? {challenge_token: otpChallenge, code: document.querySelector('#otp-code').value}
          : {email: document.querySelector('#email').value, password: document.querySelector('#password').value};
  if (!otpChallenge && mode === 'signup') payload.name = document.querySelector('#name').value;
  try {
    const endpoint = mode === 'verify-email' ? '/auth/recovery/email/verify'
      : mode === 'reset-password' ? '/auth/password-reset/complete'
      : mode === 'forgot' ? '/auth/password-reset/request'
      : otpChallenge ? '/auth/login/otp' : '/auth/' + mode;
    const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력한 내용을 다시 확인해주세요.');
    if (data.mfa_required) {
      otpChallenge = data.challenge_token;
      document.querySelector('#password').value = '';
      document.querySelector('.auth-tabs').hidden = true;
      document.querySelector('#name-field').hidden = true;
      document.querySelector('#email-field').hidden = true;
      document.querySelector('#password-field').hidden = true;
      document.querySelector('#email').required = false;
      document.querySelector('#password').required = false;
      document.querySelector('#otp-field').hidden = false;
      document.querySelector('#otp-code').required = true;
      document.querySelector('#auth-title').textContent = '한 단계만 더 확인할게요.';
      document.querySelector('#auth-subtitle').textContent = '인증 앱의 6자리 코드 또는 복구 코드를 입력하세요.';
      document.querySelector('#auth-note').textContent = '인증 코드는 한 번만 사용할 수 있으며 5분 후 로그인이 만료됩니다.';
      button.disabled = false; setActionLabel(button, '인증하고 로그인');
      document.querySelector('#otp-code').focus();
      return;
    }
    if (mode === 'forgot') {
      document.querySelector('#auth-title').textContent = '메일함을 확인해주세요.';
      document.querySelector('#auth-subtitle').textContent = data.message;
      document.querySelector('#auth-submit').hidden = true;
      document.querySelector('#email-field').hidden = true;
      document.querySelector('#auth-note').textContent = '링크는 짧은 시간 동안 한 번만 사용할 수 있습니다.';
      return;
    }
    if (mode === 'verify-email' || mode === 'reset-password') {
      const completed = mode;
      history.replaceState({}, '', '/login');
      selectMode('login');
      document.querySelector('#auth-title').textContent = completed === 'verify-email' ? '복구 이메일을 확인했습니다.' : '비밀번호를 변경했습니다.';
      document.querySelector('#auth-subtitle').textContent = completed === 'verify-email' ? '이제 이 주소로 계정 복구 링크를 받을 수 있습니다.' : '새 비밀번호와 기존 OTP로 다시 로그인해주세요.';
      document.querySelector('#password').value = '';
      button.hidden = false; button.disabled = false; setActionLabel(button, '로그인');
      return;
    }
    document.querySelector('#password').value = '';
    document.querySelector('#otp-code').value = '';
    window.location.replace(destination);
  } catch (error) {
    errorBox.textContent = error instanceof TypeError ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.' : error.message;
    errorBox.hidden = false;
    button.disabled = false; setActionLabel(button, otpChallenge ? '인증하고 로그인' : mode === 'signup' ? '계정 만들고 시작하기' : mode === 'forgot' ? '재설정 안내 받기' : mode === 'verify-email' ? '복구 이메일 확인' : mode === 'reset-password' ? '비밀번호 재설정' : '로그인');
  }
});
if (['verify-email','reset-password'].includes(initialParams.get('mode')) && recoveryToken) selectRecoveryMode(initialParams.get('mode'));
else fetch('/auth/me').then(response => { if (response.ok) window.location.replace(destination); }).catch(() => {});
