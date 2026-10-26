// Presentation and native window controls only; sync operations stay in app.js.
window.applyChromePlatform = function (platform) {
  const supported = ['macos', 'windows', 'other'];
  document.documentElement.classList.remove(...supported.map(p => `platform-${p}`));
  document.documentElement.classList.add(`platform-${supported.includes(platform) ? platform : 'other'}`);
};
window.applyChromePlatform(/Mac/.test(navigator.platform) ? 'macos' : /Win/.test(navigator.platform) ? 'windows' : 'other');
document.addEventListener('DOMContentLoaded', () => {
  const menus = [...document.querySelectorAll('.windows-menu details')];
  const closeMenus = () => menus.forEach(menu => menu.open = false);
  document.querySelectorAll('[data-click-target]').forEach(button => {
    button.addEventListener('click', () => {
      closeMenus();
      document.getElementById(button.dataset.clickTarget)?.click();
    });
  });
  menus.forEach(menu => menu.addEventListener('toggle', () => {
    if (menu.open) menus.filter(other => other !== menu).forEach(other => other.open = false);
  }));
  document.addEventListener('click', event => {
    if (!event.target.closest('.windows-menu')) closeMenus();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeMenus();
      if (document.activeElement.closest('.dropdown-container')) document.activeElement.blur();
    }
  });
  document.querySelectorAll('[data-window-action]').forEach(button => {
    button.addEventListener('click', async () => {
      if (!window.pywebview?.api) return;
      try {
        const result = await window.pywebview.api.window_action(button.dataset.windowAction);
        if (!result.success) console.error(result.error);
      } catch (error) { console.error('Điều khiển cửa sổ:', error); }
    });
  });
});
