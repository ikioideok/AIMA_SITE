(function () {
  const mount = document.querySelector('[data-redesign-v5-header]');
  if (!mount) return;

  const isHome = mount.dataset.headerHome === 'true';
  const sectionHref = (id) => `${isHome ? '' : 'index-redesign-v5.html'}#${id}`;
  const serviceHref = mount.dataset.headerService === 'local' ? '#service' : 'service-redesign-v5.html';
  const pricingHref = mount.dataset.headerPricing === 'local' ? '#pricing' : sectionHref('pricing');
  const contactHref = mount.dataset.headerContact === 'local' ? '#contact' : sectionHref('contact');

  mount.outerHTML = `
<header>
  <div class="header-inner">
    <a href="index-redesign-v5.html" class="logo"><img src="images/index-redesign-v5-logo/aima-wordmark.png" alt="AIMA"></a>
    <nav class="nav" id="nav">
      <a href="${serviceHref}">サービス</a>
      <a href="${sectionHref('case')}">実績</a>
      <a href="${pricingHref}">料金</a>
      <a href="blog.html">ブログ</a>
      <a href="company-redesign-v5.html">会社概要</a>
      <a href="llmo-shindan.html" class="btn btn-diagnosis">無料診断<span class="ar">→</span></a>
      <a href="${contactHref}" class="btn btn-contact">相談する<span class="ar">→</span></a>
    </nav>
    <button class="menu-toggle" id="menu-toggle" aria-label="メニューを開く" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
`;

  const menuToggle = document.getElementById('menu-toggle');
  const nav = document.getElementById('nav');
  if (!menuToggle || !nav) return;

  menuToggle.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    menuToggle.classList.toggle('is-open', open);
    menuToggle.setAttribute('aria-expanded', open);
  });

  nav.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => {
    nav.classList.remove('is-open');
    menuToggle.classList.remove('is-open');
    menuToggle.setAttribute('aria-expanded', 'false');
  }));
})();
