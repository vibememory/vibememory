'use strict';
(() => {
  let theme = null;
  try { theme = localStorage.getItem('vm-theme'); } catch { /* Use the system preference. */ }
  if (theme !== 'light' && theme !== 'dark') {
    theme = window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
})();
