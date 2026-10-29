'use strict';
const descriptions = {
  claude: 'Claude Code가 나의 개발 언어 선호를 참고하는 예시입니다.',
  codex: 'Codex가 이전 작업의 맥락을 이어받는 예시입니다.',
  openclaw: 'OpenClaw가 프로젝트와 연결된 기억을 찾는 예시입니다.',
  hermes: 'Hermes가 다른 에이전트에 남긴 취향을 참고하는 예시입니다.'
};
for (const button of document.querySelectorAll('[data-agent]')) {
  button.addEventListener('click', () => {
    for (const peer of document.querySelectorAll('[data-agent]')) {
      const selected = peer === button;
      peer.classList.toggle('selected', selected);
      peer.setAttribute('aria-pressed', String(selected));
    }
    document.querySelector('#agent-description').textContent = descriptions[button.dataset.agent];
  });
}
const demos = {
  memory: {
    kicker: '에이전트가 추출한 기억',
    message: '“앞으로 개발 예제는 Python으로 보여줘.”',
    explanation: '에이전트가 선호를 이해하고, 저장할 키워드를 구성합니다.',
    keywords: ['Python', '개발 언어', '코드 예제'],
    method: 'POST /v1/memories',
    code: {content: '사용자는 Python 예제를 선호한다', kind: 'preference', keywords: ['Python', '개발 언어', '코드 예제'], source: 'coding-agent'},
    footer: '앱은 keywords만 로컬에서 임베딩합니다.'
  },
  file: {
    kicker: '에이전트가 분석한 파일',
    message: '“프로젝트 문서의 맥락도 기억해줘.”',
    explanation: '원본은 바이트 스트림으로 업로드하고, 분석한 메타정보는 별도 JSON으로 연결합니다.',
    keywords: ['프로젝트', '기억 공유', '그래프 DB'],
    method: 'POST /v1/documents',
    code: {title: 'project.pdf', file_id: 'id-from-byte-stream-upload', keywords: ['프로젝트', '기억 공유', '그래프 DB'], metadata: {summary: '에이전트가 분석한 프로젝트 개요'}},
    footer: '파일 분석은 에이전트가, 원본 보관은 앱이 담당합니다.'
  },
  search: {
    kicker: '에이전트가 추출한 검색 키워드',
    message: '“내가 선호하는 개발 언어가 뭐였지?”',
    explanation: '질문은 에이전트가 이해합니다. 앱에는 추출한 검색 키워드만 전달합니다.',
    keywords: ['개발 언어', '선호'],
    method: 'POST /v1/search',
    code: {keywords: ['개발 언어', '선호'], scope: 'memories', limit: 5},
    footer: '키워드로 검색한 뒤, 에이전트가 근거를 구성합니다.'
  }
};
let activeDemo = 'memory';
function renderCode(data) {
  const target = document.querySelector('#demo-code');
  // Use text nodes: example strings never become executable markup.
  target.replaceChildren();
  const json = JSON.stringify(data, null, 2);
  const tokens = /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")/g;
  let cursor = 0;
  for (const match of json.matchAll(tokens)) {
    target.append(document.createTextNode(json.slice(cursor, match.index)));
    const span = document.createElement('span');
    span.className = match[1] ? 'json-key' : 'json-value';
    span.textContent = match[0];
    target.append(span);
    cursor = match.index + match[0].length;
  }
  target.append(document.createTextNode(json.slice(cursor)));
}
function selectDemo(name) {
  activeDemo = name;
  const demo = demos[name];
  for (const tab of document.querySelectorAll('[data-demo]')) {
    const selected = tab.dataset.demo === name;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  document.querySelector('#demo-panel').setAttribute('aria-labelledby', `tab-${name}`);
  for (const field of ['kicker', 'message', 'explanation']) document.querySelector(`#demo-${field}`).textContent = demo[field];
  document.querySelector('#code-method').textContent = demo.method;
  document.querySelector('#code-footer').textContent = demo.footer;
  document.querySelector('#demo-keywords').replaceChildren(...demo.keywords.map(keyword => {
    const span = document.createElement('span'); span.textContent = keyword; return span;
  }));
  renderCode(demo.code);
}
const tabs = [...document.querySelectorAll('[data-demo]')];
for (const [index, tab] of tabs.entries()) {
  tab.addEventListener('click', () => selectDemo(tab.dataset.demo));
  tab.addEventListener('keydown', event => {
    const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    selectDemo(tabs[next].dataset.demo); tabs[next].focus();
  });
}
let toastTimer;
function notify(message) {
  const toast = document.querySelector('#toast');
  toast.textContent = message; toast.classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove('visible'), 2600);
}
document.querySelector('#copy-example').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(JSON.stringify(demos[activeDemo].code, null, 2));
    notify('요청 JSON을 복사했습니다.');
  } catch {
    const code = document.querySelector('#demo-code');
    const range = document.createRange(); range.selectNodeContents(code);
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    notify('코드를 선택했습니다. 복사 단축키를 사용하세요.');
  }
});
selectDemo('memory');
