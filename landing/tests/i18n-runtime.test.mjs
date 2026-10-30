import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const body = {nodeType: 1, hasAttribute: () => false};
const stored = new Map([['vm-language', 'ko']]);
const guideElements = new Map();

globalThis.window = globalThis;
window.confirm = () => true;
window.dispatchEvent = () => true;
Object.defineProperty(globalThis, 'navigator', {value: {language: 'ko-KR'}});
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: key => stored.get(key) ?? null,
    setItem: (key, value) => stored.set(key, value),
  },
});
globalThis.location = {pathname: '/'};
globalThis.Node = {TEXT_NODE: 3, ELEMENT_NODE: 1};
globalThis.NodeFilter = {SHOW_ELEMENT: 1, SHOW_TEXT: 4};
globalThis.CustomEvent = class CustomEvent {
  constructor(type, init) { this.type = type; this.detail = init?.detail; }
};
globalThis.MutationObserver = class MutationObserver { observe() {} };
globalThis.document = {
  body,
  documentElement: {lang: 'ko'},
  title: '',
  addEventListener() {},
  querySelector: selector => guideElements.get(selector) ?? null,
  querySelectorAll: () => [],
  createTreeWalker: () => ({nextNode: () => null}),
};

const source = fs.readFileSync(new URL('../public/assets/i18n.js', import.meta.url), 'utf8');
eval(source);

test('all seven locales translate core and newly added UI labels', () => {
  const expected = {
    ko: '지원됨',
    en: 'Supported',
    zh: '支持',
    ja: '対応',
    es: 'Compatible',
    vi: 'Được hỗ trợ',
    th: 'รองรับ',
  };
  for (const [locale, translated] of Object.entries(expected)) {
    assert.equal(window.vmSetLocale(locale), true);
    assert.equal(window.vmTranslateText('지원됨'), translated);
  }
  assert.equal(window.vmSetLocale('unsupported'), false);
});

test('a reused text node adopts application updates instead of stale Korean', () => {
  window.vmSetLocale('en');
  const node = {nodeType: 3, nodeValue: '로그인', parentElement: null};
  window.vmApplyTranslations(node);
  assert.equal(node.nodeValue, 'Log in');

  node.nodeValue = '저장';
  window.vmApplyTranslations(node);
  assert.equal(node.nodeValue, 'Save');

  window.vmSetLocale('ja');
  window.vmApplyTranslations(node);
  assert.equal(node.nodeValue, '保存');
});

test('a reused element adopts updated translatable attributes', () => {
  window.vmSetLocale('en');
  const attributes = new Map([['placeholder', '검색']]);
  const element = {
    nodeType: 1,
    hasAttribute: name => attributes.has(name),
    getAttribute: name => attributes.get(name),
    setAttribute: (name, value) => attributes.set(name, value),
  };
  window.vmApplyTranslations(element);
  assert.equal(attributes.get('placeholder'), 'Search');

  attributes.set('placeholder', '이름');
  window.vmApplyTranslations(element);
  assert.equal(attributes.get('placeholder'), 'Name');
});

test('dynamic counts and owner workspace names are localized', () => {
  window.vmSetLocale('en');
  assert.equal(window.vmTranslateText('12개 요청 중 5개를 표시합니다.'), 'Showing 5 of 12 requests.');
  assert.equal(window.vmTranslateText('민수의 기억'), "민수's memory");
  assert.equal(window.vmTranslateText('2개의 비밀값이 저장되어 있습니다.'), '2 secrets stored.');
  assert.equal(
    window.vmTranslateText('승인했습니다. Vault 권한: 허용하지 않음. 에이전트가 자동으로 결과를 확인합니다.'),
    'Approved. Vault access: not allowed. The agent will automatically check the result.',
  );
  window.vmSetLocale('vi');
  assert.equal(window.vmTranslateText('3개 노드와 2개 관계를 표시합니다.'), 'Hiển thị 3 nút và 2 quan hệ.');
});

test('language switching remains available when storage is blocked', () => {
  const original = localStorage.setItem;
  localStorage.setItem = () => { throw new Error('blocked'); };
  assert.equal(window.vmSetLocale('th'), true);
  assert.equal(window.vmCurrentLocale(), 'th');
  localStorage.setItem = original;
});

test('guide paragraphs preserve inline code while switching languages', () => {
  const selector = '#files p:nth-of-type(1)';
  const original = '원본 파일은 multipart form이 아닌 <code>application/octet-stream</code> 요청 본문으로 전송합니다.';
  const element = {innerHTML: original};
  guideElements.set(selector, element);

  window.vmSetLocale('en');
  assert.match(element.innerHTML, /Send the original file/);
  assert.match(element.innerHTML, /<code>application\/octet-stream<\/code>/);

  window.vmSetLocale('zh');
  assert.match(element.innerHTML, /原文件应作为/);

  window.vmSetLocale('ko');
  assert.equal(element.innerHTML, original);
  guideElements.delete(selector);
});
