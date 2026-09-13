// ============================================================
// theme.js — Light / Dark theme switcher
// UI-only: reads/writes data-theme on <html>, persists to
// localStorage, and respects prefers-color-scheme on first visit.
// ============================================================

(function () {
  var STORAGE_KEY = 'wgpt-theme';
  var htmlEl = document.documentElement;

  function getPreferred() {
    // 1. Stored user choice
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    // 2. System preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark'; // default
  }

  function applyTheme(theme) {
    htmlEl.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }

  // Apply on load (before paint to avoid flash)
  applyTheme(getPreferred());

  // Wire the toggle button once DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var current = htmlEl.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  });
})();
