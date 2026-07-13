(function () {
  const mount = document.querySelector('[data-redesign-v6-header]');
  if (!mount) return;

  const isHome = mount.dataset.headerHome === 'true';
  const sectionHref = (id) => `${isHome ? '' : '/'}#${id}`;
  const serviceHref = mount.dataset.headerService === 'local' ? '#service' : sectionHref('flow');
  const pricingHref = mount.dataset.headerPricing === 'local' ? '#pricing' : sectionHref('pricing');
  const contactHref = mount.dataset.headerContact === 'local' ? '#contact' : sectionHref('contact');

  mount.outerHTML = `
<header>
  <div class="header-inner">
    <a href="/" class="logo"><img src="/images/index-redesign-v6-logo/aima-wordmark.png" alt="AIMA" width="1122" height="317"></a>
    <nav class="nav" id="nav" aria-label="メインメニュー">
      <a href="${sectionHref('llmo')}">LLMOとは</a>
      <a href="${serviceHref}">サービス</a>
      <a href="${sectionHref('case')}">実績</a>
      <a href="${pricingHref}">料金</a>
      <a href="/blog.html">ブログ</a>
      <a href="/company.html">会社概要</a>
      <a href="/llmo-shindan.html" class="btn btn-diagnosis">無料診断<span class="ar">→</span></a>
      <a href="${contactHref}" class="btn btn-contact">相談する<span class="ar">→</span></a>
    </nav>
    <button class="menu-toggle" id="menu-toggle" type="button" aria-label="メニューを開く" aria-controls="nav" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
`;

  const menuToggle = document.getElementById('menu-toggle');
  const nav = document.getElementById('nav');
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

  nav.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => {
    setMenuState(false);
  }));

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !nav.classList.contains('is-open')) return;
    setMenuState(false);
    menuToggle.focus();
  });
})();
