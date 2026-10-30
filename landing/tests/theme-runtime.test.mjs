import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const stored = new Map();
const documentListeners = new Map();
const windowListeners = new Map();
const controls = [];
const themeMeta = {content:'#f8f9fc', setAttribute(name, value) { this[name] = value; }};
const media = {
  matches:true,
  listener:null,
  addEventListener(type, listener) { if (type === 'change') this.listener = listener; },
};

function createButton() {
  const attributes = new Map();
  const listeners = new Map();
  const use = {href:'', setAttribute(name, value) { this[name] = value; }};
  return {
    dataset:{},
    className:'',
    classList:{add(name) { this.value = name; }},
    set innerHTML(value) { this.markup = value; },
    querySelector(selector) { return selector === 'use' ? use : null; },
    setAttribute(name, value) { attributes.set(name, value); },
    getAttribute(name) { return attributes.get(name); },
    addEventListener(type, listener) { listeners.set(type, listener); },
    click() { listeners.get('click')?.(); },
    use,
  };
}

globalThis.window = globalThis;
window.matchMedia = () => media;
window.addEventListener = (type, listener) => windowListeners.set(type, listener);
window.dispatchEvent = event => { window.lastEvent = event; return true; };
globalThis.CustomEvent = class CustomEvent {
  constructor(type, init) { this.type = type; this.detail = init?.detail; }
};
Object.defineProperty(globalThis, 'localStorage', {value:{
  getItem:key => stored.get(key) ?? null,
  setItem:(key, value) => stored.set(key, value),
  removeItem:key => stored.delete(key),
}});
globalThis.document = {
  documentElement:{dataset:{}, style:{}},
  body:{append(button) { controls.push(button); }},
  querySelector(selector) {
    if (selector === 'meta[name="theme-color"]') return themeMeta;
    if (selector === '[data-vm-theme]') return controls[0] || null;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === '[data-vm-theme]') return controls;
    if (selector === 'meta[name="theme-color"]') return [themeMeta];
    return [];
  },
  createElement(tag) { assert.equal(tag, 'button'); return createButton(); },
  addEventListener(type, listener) { documentListeners.set(type, listener); },
};

const initSource = fs.readFileSync(new URL('../public/assets/theme-init.js', import.meta.url), 'utf8');
eval(initSource);
const source = fs.readFileSync(new URL('../public/assets/theme.js', import.meta.url), 'utf8');
eval(source);
documentListeners.get('DOMContentLoaded')();

test('the blocking initializer follows the system theme before mounting a toggle', () => {
  assert.equal(document.documentElement.dataset.theme, 'dark');
  assert.equal(document.documentElement.style.colorScheme, 'dark');
  assert.equal(themeMeta.content, '#0b1020');
  assert.equal(controls.length, 1);
  assert.equal(controls[0].getAttribute('aria-label'), '라이트 모드로 전환');
  assert.equal(controls[0].getAttribute('aria-pressed'), 'true');
  assert.equal(controls[0].use.href, '/assets/icons.svg#sun');
});

test('manual switching persists and updates the browser chrome color', () => {
  controls[0].click();
  assert.equal(stored.get('vm-theme'), 'light');
  assert.equal(window.vmTheme.current(), 'light');
  assert.equal(document.documentElement.dataset.theme, 'light');
  assert.equal(themeMeta.content, '#f8f9fc');
  assert.equal(controls[0].getAttribute('aria-label'), '다크 모드로 전환');
  assert.equal(controls[0].use.href, '/assets/icons.svg#moon');
  assert.equal(window.lastEvent.type, 'vm-theme-change');
  assert.deepEqual(window.lastEvent.detail, {theme:'light'});
});

test('system mode can be restored and follows preference changes', () => {
  media.matches = true;
  assert.equal(window.vmTheme.useSystem(), 'dark');
  assert.equal(stored.has('vm-theme'), false);
  media.matches = false;
  media.listener();
  assert.equal(window.vmTheme.current(), 'light');
});

test('invalid explicit themes are rejected', () => {
  assert.equal(window.vmTheme.set('sepia'), false);
  assert.equal(window.vmTheme.current(), 'light');
});
