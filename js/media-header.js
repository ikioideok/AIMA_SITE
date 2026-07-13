(function() {
  const mobileMenuToggle = document.getElementById('menu-toggle');
  const mobileNav = document.getElementById('nav');
  const mobileBreakpoint = window.matchMedia('(max-width: 980px)');
  if (!mobileMenuToggle || !mobileNav) return;

  function setMenuState(isOpen, returnFocus) {
    mobileNav.classList.toggle('is-open', isOpen);
    mobileMenuToggle.setAttribute('aria-expanded', String(isOpen));
    mobileMenuToggle.setAttribute('aria-label', isOpen ? 'メニューを閉じる' : 'メニューを開く');
    const icon = mobileMenuToggle.querySelector('.material-symbols-rounded');
    if (icon) icon.textContent = isOpen ? 'close' : 'menu';
    document.body.classList.toggle('menu-open', isOpen && mobileBreakpoint.matches);
    mobileNav.inert = mobileBreakpoint.matches && !isOpen;
    if (returnFocus) mobileMenuToggle.focus();
  }

  setMenuState(false, false);
  mobileMenuToggle.addEventListener('click', function() {
    setMenuState(!mobileNav.classList.contains('is-open'), false);
  });
  mobileNav.querySelectorAll('a').forEach(function(link) {
    link.addEventListener('click', function() {
      setMenuState(false, false);
    });
  });
  document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape' || !mobileNav.classList.contains('is-open')) return;
    setMenuState(false, true);
  });
  mobileBreakpoint.addEventListener('change', function() {
    setMenuState(false, false);
    mobileNav.inert = false;
  });
})();
