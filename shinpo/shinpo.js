(() => {
  "use strict";

  const masthead = document.querySelector(".sh-masthead");
  const tagline = masthead?.querySelector(".sh-tagline");
  const aimaLink = masthead?.querySelector(".sh-aima-link");
  if (masthead && tagline && aimaLink) {
    const brandCopy = document.createElement("div");
    brandCopy.className = "sh-brand-copy";
    tagline.before(brandCopy);
    brandCopy.append(tagline, aimaLink);
    aimaLink.textContent = "運営：株式会社AIMA";
  }

  const article = document.querySelector(".sh-article");
  const backLink = article?.querySelector(".sh-back");
  if (article && backLink && !article.querySelector(".sh-supervisor")) {
    const supervisor = document.createElement("section");
    supervisor.className = "sh-supervisor";
    supervisor.setAttribute("aria-labelledby", "sh-supervisor-title");
    supervisor.innerHTML = `
      <p class="sh-supervisor-label">SUPERVISOR</p>
      <div class="sh-supervisor-card">
        <img src="../images/member-photo.webp" alt="監修者 水間 雄紀" width="320" height="320" loading="lazy" decoding="async">
        <div>
          <h2 id="sh-supervisor-title">監修者：水間 雄紀</h2>
          <p class="sh-supervisor-role">株式会社AIMA 代表取締役</p>
          <p class="sh-supervisor-profile">1986年和歌山県生まれ、近畿大学卒。金融機関、経営コンサルティング会社を経て、2018年にコンテンツ制作会社を創業。2024年に事業譲渡し、現在は株式会社AIMAでAI×マーケティング事業に従事。</p>
          <a href="../company.html">株式会社AIMA公式サイト・代表プロフィールを見る <span aria-hidden="true">›</span></a>
        </div>
      </div>`;

    const body = article.querySelector(".sh-body");
    if (body) {
      const ctaHeading = document.createElement("h2");
      ctaHeading.textContent = "月額5万円でできる、AI対策。";

      const ctaText = document.createElement("p");
      ctaText.innerHTML = "株式会社AIMAは、AIに選ばれるための質問設計・記事制作・引用チェックを月額5万円で支援しています。相談回数に制限はなく、記事制作・修正も範囲内で無制限。最低契約期間もありません。まずは<a href=\"../llmo-shindan.html\">無料のAI診断</a>、または<a href=\"../service.html\">AIMAのAI対策サービス</a>をご覧ください。";

      body.append(ctaHeading, ctaText);
      body.after(supervisor);
    }
  }

  const menuButton = document.querySelector(".sh-menu-toggle");
  const primaryNav = document.querySelector(".sh-nav");

  if (menuButton && primaryNav) {
    menuButton.addEventListener("click", () => {
      const isOpen = primaryNav.classList.toggle("is-open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
      const icon = menuButton.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = isOpen ? "close" : "menu";
    });

    primaryNav.addEventListener("click", () => {
      primaryNav.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
      const icon = menuButton.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = "menu";
    });
  }

  const params = new URLSearchParams(window.location.search);
  const requestedCategory = params.get("category") || "all";
  const categoryLinks = [...document.querySelectorAll("[data-category-link]")];
  const activeLink =
    categoryLinks.find((link) => link.dataset.categoryLink === requestedCategory) ||
    categoryLinks.find((link) => link.dataset.categoryLink === "all");
  const activeCategory = activeLink?.dataset.categoryLink || "all";
  const activeCategoryLabel = activeLink?.textContent?.trim() || "トップ";

  categoryLinks.forEach((link) => {
    const isActive = link === activeLink;
    link.classList.toggle("is-active", isActive);
    if (isActive) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });

  const newsRows = [...document.querySelectorAll(".sh-list .sh-item[data-news-card]")];
  const filterStatus = document.querySelector("[data-filter-status]");
  const filterEmpty = document.querySelector("[data-filter-empty]");
  const latestNewsTitle = document.querySelector("#latest-news-title");
  const topGrid = document.querySelector(".sh-top-grid");
  const contentGrid = document.querySelector(".sh-content-grid");
  const isFilteredView = activeCategory !== "all";

  if (topGrid) topGrid.hidden = isFilteredView;
  if (contentGrid) contentGrid.classList.toggle("is-filtered", isFilteredView);
  if (latestNewsTitle) {
    latestNewsTitle.textContent = isFilteredView
      ? `${activeCategoryLabel}のニュース`
      : "最新ニュース";
  }

  if (newsRows.length) {
    let visibleCount = 0;
    newsRows.forEach((row) => {
      const matches =
        activeCategory === "all" ||
        (row.dataset.category || "").includes(activeCategory);
      row.hidden = !matches;
      if (matches) visibleCount += 1;
    });

    if (filterStatus) {
      filterStatus.textContent =
        activeCategory === "all" ? "新着順" : `${visibleCount}件`;
    }
    if (filterEmpty) filterEmpty.hidden = visibleCount !== 0;
  }

  function readCards(root) {
    return [...root.querySelectorAll("[data-news-card]")]
      .map((card) => {
        const titleNode = card.querySelector(".sh-lead-title, .sh-item-copy strong");
        const dateTime = card.dataset.datetime || card.querySelector("time")?.dateTime || "";
        return {
          href: card.getAttribute("href") || "#",
          title: titleNode?.textContent.replace(/\s+/g, " ").trim() || "",
          dateTime,
        };
      })
      .filter((item) => item.title && item.dateTime)
      .sort((a, b) => b.dateTime.localeCompare(a.dateTime));
  }

  function renderLatest(container, items) {
    const fragment = document.createDocumentFragment();
    items.slice(0, 5).forEach((item) => {
      const link = document.createElement("a");
      link.className = "sh-latest-entry";
      link.href = item.href;

      const time = document.createElement("time");
      time.dateTime = item.dateTime;
      time.textContent = item.dateTime.slice(11, 16);

      const title = document.createElement("strong");
      title.textContent = item.title;

      link.append(time, title);
      fragment.append(link);
    });
    container.replaceChildren(fragment);
  }

  async function hydrateLatestLists() {
    const containers = [...document.querySelectorAll("[data-latest-list]")];
    if (!containers.length) return;

    let items = readCards(document);
    if (!items.length) {
      try {
        const response = await fetch("index.html", { credentials: "same-origin" });
        if (!response.ok) return;
        const html = await response.text();
        const parsed = new DOMParser().parseFromString(html, "text/html");
        items = readCards(parsed);
      } catch (_) {
        return;
      }
    }

    containers.forEach((container) => renderLatest(container, items));
  }

  hydrateLatestLists();
})();
