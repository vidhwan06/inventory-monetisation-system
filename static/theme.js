const THEME_STORAGE_KEY = 'assetflow-theme';

const getSavedTheme = () => localStorage.getItem(THEME_STORAGE_KEY) || localStorage.getItem('theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const getDefaultTheme = () => (prefersDark ? 'dark' : 'light');

const setBodyThemeClass = (theme) => {
  document.body.classList.remove('light-theme', 'dark-theme');
  document.body.classList.add(`${theme}-theme`);
};

const updateThemeButtons = (theme) => {
  const lightBtn = document.getElementById('light-theme-btn');
  const darkBtn = document.getElementById('dark-theme-btn');

  if (lightBtn && darkBtn) {
    if (theme === 'light') {
      lightBtn.classList.add('bg-primary', 'text-white');
      lightBtn.classList.remove('bg-slate-100', 'text-slate-700');
      darkBtn.classList.remove('bg-primary', 'text-white');
      darkBtn.classList.add('bg-slate-100', 'text-slate-700');
    } else {
      darkBtn.classList.add('bg-primary', 'text-white');
      darkBtn.classList.remove('bg-slate-100', 'text-slate-700');
      lightBtn.classList.remove('bg-primary', 'text-white');
      lightBtn.classList.add('bg-slate-100', 'text-slate-700');
    }
  }
};

const updateThemeToggleButton = (theme) => {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;
  toggle.innerHTML = theme === 'dark'
    ? '<span class="material-symbols-outlined">light_mode</span><span class="hidden sm:inline">Light mode</span>'
    : '<span class="material-symbols-outlined">dark_mode</span><span class="hidden sm:inline">Dark mode</span>';
};

const applyTheme = (theme) => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  document.documentElement.classList.toggle('light', theme === 'light');
  setBodyThemeClass(theme);
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  updateThemeButtons(theme);
  updateThemeToggleButton(theme);
};

const initTheme = () => {
  const savedTheme = getSavedTheme();
  const theme = savedTheme || getDefaultTheme();
  applyTheme(theme);
};

window.addEventListener('DOMContentLoaded', () => {
  initTheme();

  const lightBtn = document.getElementById('light-theme-btn');
  const darkBtn = document.getElementById('dark-theme-btn');
  const themeToggle = document.getElementById('themeToggle');

  if (lightBtn) {
    lightBtn.addEventListener('click', () => applyTheme('light'));
  }
  if (darkBtn) {
    darkBtn.addEventListener('click', () => applyTheme('dark'));
  }
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = getSavedTheme() || getDefaultTheme();
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }
});
