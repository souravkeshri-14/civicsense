(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem('civicsense-theme') || 'light';
  root.dataset.theme = saved;
  const button = document.getElementById('themeToggle');
  if (!button) return;
  const sync = () => {
    const dark = root.dataset.theme === 'dark';
    button.textContent = dark ? '☀️' : '🌙';
    button.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
  };
  sync();
  button.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('civicsense-theme', root.dataset.theme);
    sync();
  });
})();
