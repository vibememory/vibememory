'use strict';
(() => {
  const storageKey = 'vm-theme';
  const media = window.matchMedia?.('(prefers-color-scheme: dark)');
  const valid = new Set(['light', 'dark']);

  function readPreference() {
    try {
      const stored = localStorage.getItem(storageKey);
      return valid.has(stored) ? stored : null;
    } catch {
      return null;
    }
  }

  function systemTheme() {
    return media?.matches ? 'dark' : 'light';
  }

  function currentTheme() {
    const active = document.documentElement.dataset.theme;
    return valid.has(active) ? active : (readPreference() || systemTheme());
  }

  function updateControls(theme) {
    const next = theme === 'dark' ? 'light' : 'dark';
    const label = next === 'dark' ? '다크 모드로 전환' : '라이트 모드로 전환';
    document.querySelectorAll('[data-vm-theme]').forEach(button => {
      button.dataset.theme = theme;
      button.setAttribute('aria-label', label);
      button.setAttribute('title', label);
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      const use = button.querySelector('use');
      if (use) use.setAttribute('href', `/assets/icons.svg#${next === 'dark' ? 'moon' : 'sun'}`);
    });
  }

  function applyTheme(theme, {emit = true} = {}) {
    const next = valid.has(theme) ? theme : systemTheme();
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;
    document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
      meta.setAttribute('content', next === 'dark' ? '#0b1020' : '#f8f9fc');
    });
    updateControls(next);
    if (emit) window.dispatchEvent(new CustomEvent('vm-theme-change', {detail:{theme:next}}));
    return next;
  }

  function setTheme(theme, persist = true) {
    if (!valid.has(theme)) return false;
    if (persist) {
      try { localStorage.setItem(storageKey, theme); } catch { /* Theme switching still works. */ }
    }
    applyTheme(theme);
    return true;
  }

  function mountToggle() {
    if (document.querySelector('[data-vm-theme]')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'vm-theme-toggle';
    button.dataset.vmTheme = '';
    button.innerHTML = '<svg aria-hidden="true"><use href="/assets/icons.svg#moon"></use></svg>';
    button.addEventListener('click', () => setTheme(currentTheme() === 'dark' ? 'light' : 'dark'));
    const mount = document.querySelector('.header-actions') || document.querySelector('.console-header .topbar-actions') || document.querySelector('.admin-header nav');
    if (mount) mount.prepend(button);
    else {
      button.classList.add('vm-theme-floating');
      document.body.append(button);
    }
    updateControls(currentTheme());
  }

  function handleSystemChange() {
    if (!readPreference()) applyTheme(systemTheme());
  }

  window.vmTheme = {current: currentTheme, set: setTheme, useSystem() {
    try { localStorage.removeItem(storageKey); } catch { /* Keep the current theme when storage is blocked. */ }
    return applyTheme(systemTheme());
  }};

  applyTheme(readPreference() || systemTheme(), {emit:false});
  media?.addEventListener?.('change', handleSystemChange);
  window.addEventListener('storage', event => {
    if (event.key === storageKey) applyTheme(valid.has(event.newValue) ? event.newValue : systemTheme());
  });
  document.addEventListener('DOMContentLoaded', mountToggle);
})();
