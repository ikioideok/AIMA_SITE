(function () {
  const menuToggle = document.getElementById('corporate-menu-toggle');
  const nav = document.getElementById('corporate-nav');
  if (!menuToggle || !nav) return;

  const setMenuState = (open) => {
    nav.classList.toggle('is-open', open);
    menuToggle.classList.toggle('is-open', open);
    menuToggle.setAttribute('aria-expanded', String(open));
    menuToggle.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
  };

  menuToggle.addEventListener('click', () => {
    setMenuState(!nav.classList.contains('is-open'));
  });

  nav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setMenuState(false));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !nav.classList.contains('is-open')) return;
    setMenuState(false);
    menuToggle.focus();
  });

  const path = window.location.pathname.replace(/\/index\.html$/, '/');
  const currentRoute = path === '/service/' || path.endsWith('/service-redesign-v5.html')
    ? 'service'
    : path.endsWith('/blog.html')
      ? 'blog'
      : path.endsWith('/company.html')
        ? 'company'
        : '';

  if (currentRoute) {
    const currentLink = nav.querySelector(`[data-site-route="${currentRoute}"]`);
    if (currentLink) currentLink.setAttribute('aria-current', 'page');
  }
}());
