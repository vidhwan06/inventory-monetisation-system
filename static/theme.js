const THEME_STORAGE_KEY = 'assetflow-theme';
const THEME_TOGGLE_ID = 'themeToggle';

const getSavedTheme = () => localStorage.getItem(THEME_STORAGE_KEY);
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const getDefaultTheme = () => (prefersDark ? 'dark' : 'light');

const updateToggleButton = (theme) => {
  const toggle = document.getElementById(THEME_TOGGLE_ID);
  if (!toggle) return;

  const icon = theme === 'dark' ? 'light_mode' : 'dark_mode';
  const label = theme === 'dark' ? 'Light mode' : 'Dark mode';
  toggle.innerHTML = `<span class="material-symbols-outlined">${icon}</span><span class="hidden sm:inline">${label}</span>`;
  toggle.setAttribute('aria-label', `${label} toggle`);
};

const applyTheme = (theme) => {
  document.documentElement.classList.remove('dark', 'light');
  document.documentElement.classList.add(theme === 'dark' ? 'dark' : 'light');
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  updateToggleButton(theme);
};

const initTheme = () => {
  const savedTheme = getSavedTheme();
  const theme = savedTheme || getDefaultTheme();
  applyTheme(theme);
};

window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const toggle = document.getElementById(THEME_TOGGLE_ID);
  if (!toggle) return;

  toggle.addEventListener('click', () => {
    const isDark = document.documentElement.classList.contains('dark');
    applyTheme(isDark ? 'light' : 'dark');
  });
});
