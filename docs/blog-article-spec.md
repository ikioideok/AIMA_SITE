# AIMA Blog Article Spec

## Source Of Truth
- Layout/template: [blog-post.html](../blog-post.html)
- Reference implementation: [blog-llmo-taisaku.html](../blog-llmo-taisaku.html)
- Supervisor source: [company.html](../company.html)

If this spec and a specific article differ, update the article to match this spec unless the user explicitly requests an exception.

## New Article Workflow
1. Copy `blog-post.html` to `{slug}.html`.
2. Replace placeholders in title, meta description, canonical URL, OGP/Twitter tags, category, date, article title, image paths, and prev/next links.
3. Keep the shared favicon block (`favicon.ico`, `favicon.svg`, `apple-touch-icon`) in the article head.
4. Keep the shared stylesheet query version aligned with the current site pages.
5. Put article assets under `images/{slug}/`.
6. Update the card in `blog.html` with the new link, title, date, and thumbnail.
7. Update `sitemap.xml` when a new article is added or when an article URL's publish state changes.

## Layout Rules
- The left main column contains everything that belongs to the article itself:
  - breadcrumbs
  - meta/date/tag
  - title
  - eyecatch
  - lead paragraphs
  - collapsed TOC under the lead
  - supervisor block
  - article body
  - CTA
  - prev/next navigation
  - related articles section at the very end
- The right column is reserved for sticky sidebar modules.
- The first sidebar module is the sticky `H2` TOC by default.
- The right sidebar may later include featured posts, banners, or other modules. Keep the sidebar area reusable.
- Use the shared lower-page header/footer pattern with hamburger menu, nav CTA, `site-footer`, and `js/main.js`.

## TOC Rules
- Keep two TOCs:
  - lead TOC: collapsed by default, placed directly under the lead paragraphs
  - sidebar TOC: sticky on desktop, `H2` only
- The sidebar TOC must not appear immediately on page load. It becomes visible from the first `H2` onward.
- Both TOCs are generated from article headings by the inline script. Do not hardcode individual TOC links.

## Supervisor Block
- Always place the supervisor block directly under the lead TOC.
- Use the company profile from `company.html`:
  - name: `水間 雄紀`
  - role: `株式会社AIMA 代表取締役`
  - photo: `images/member-photo.png`
  - bio text: match `company.html`
- Do not add a company profile link inside the supervisor block unless explicitly requested.

## Content Structure
- Use `h2` for major sections and `h3` for subsections.
- Keep the lead to 2-3 short paragraphs before the TOC.
- For long comparison articles, target roughly 10,000 Japanese characters overall unless the user requests a different length.
- Draft long articles section-by-section at the `h2` level, then assemble them after the sections are individually written and checked.
- Give each `h2` block a distinct role so the same explanation does not get repeated across multiple sections.
- For prefecture-specific LLMO company articles, the default `h2` skeleton is:
  - `{都道府県名 or 地域名}でおすすめのLLMO会社10選`
  - `{都道府県名 or 地域名}のLLMO会社を比較する際のポイント`
  - `{都道府県名 or 地域名}のLLMO会社に依頼する費用相場`
  - `{都道府県名 or 地域名}のLLMO会社に関するよくある質問`
  - `まとめ` or a prefecture-specific closing headline
- The default prefecture article skeleton may be slightly adjusted, but only when the article becomes more locally accurate, not just for variation.
- Use `figure` + `figcaption` for inline images and diagrams.
- Use tables only when comparison is clearer in a matrix than in prose.
- Use `<time datetime="YYYY-MM-DD">` for the visible publish date instead of plain text.
- Show both the publish date and the last-modified date in `.post-meta`, each wrapped in its own `<time datetime>` element. Prefix visible text with `公開日` / `更新日`. Use `.post-date` on both, plus `.post-updated` on the modified one.
- When there is no substantive revision, set `更新日` equal to the publish date. Only bump the modified date when the article content actually changes.

## SEO Rules
- Add visible breadcrumbs near the top of the left main column: `トップ > ブログ > 記事タイトル`.
- Add `BreadcrumbList` JSON-LD that matches the visible breadcrumbs.
- Add `Article` JSON-LD with title, description, canonical URL, eyecatch image, publish date, modified date, author, and publisher. Keep `datePublished` and `dateModified` in sync with the visible `公開日` / `更新日` and with the `article:published_time` / `article:modified_time` OGP tags.
- Add 2-4 natural internal links inside the article body, not only in the header or CTA.
- Prioritize links to related published blog articles when available. If the cluster is not published yet, use relevant internal service/tool/company pages instead.
- Never leave `href="#"` in the post navigation. If previous/next articles are unavailable, use real internal fallback links such as `blog.html` and another relevant page.
- Do not add blanket `rel="nofollow"` to editorial reference links. Keep external source links normal unless the user explicitly wants a different policy.

## Quote And Reference Rules
- When quoting a source, keep the source link inside the same `blockquote` using `.quote-source`.
- Do not leave `出典：...` as a separate paragraph under a quote.
- Figure sources go inside `figcaption` using `.figure-source`.
- Regular references at the end of a section use `.post-ref`.

## Asset Rules
- Each article gets its own directory under `images/{slug}/`.
- Expected default files:
  - `eyecatch.jpg`
  - `og.jpg`
- Additional inline figures should live in the same directory with descriptive names.
- Add intrinsic `width` and `height` attributes to every article image using the actual asset dimensions.
- For prefecture-specific LLMO company articles, generate the eyecatch with a fixed `image2` prompt pattern based on the article title:
  - `{都道府県名}でおすすめのLLMO会社10選`
  - `費用相場と選び方もわかりやすく解説`
- Use only these eyecatch colors:
  - `#ffffff`
  - `#000000`
  - `#7759f6`
  - `#d1ed42`
- Export the eyecatch at `1600x900`.
- Render the Japanese title text inside the `image2` output itself.
- Do not add the title later in HTML/CSS or by local post-compositing unless the user explicitly asks for a fallback workflow.

## Style Rules
- Body text uses the stronger gray setting from the current template.
- Reference links are smaller than body text.
- Keep the current CTA and prev/next block structure.
- Add a related articles section after the prev/next navigation as the last block in the left main column.
- Use real internal links in the related article cards. Prefer 2-3 published blog articles; if you want a broader directory link, keep it as a separate text link such as `blog.html`.
- Preserve the responsive two-column behavior from `blog-post.html`.

## Final Checklist
- Visible breadcrumbs exist and match the article path.
- `Article` and `BreadcrumbList` JSON-LD are present and article-specific.
- The visible date uses a `<time>` tag with a machine-readable `datetime`.
- Both `公開日` and `更新日` are shown in `.post-meta`, and match `datePublished` / `dateModified` in JSON-LD and `article:published_time` / `article:modified_time` in OGP.
- Title and eyecatch are in the left main column.
- Lead TOC exists and is collapsed by default.
- Sidebar TOC exists, is `H2` only, and appears from the first `H2`.
- Supervisor block matches `company.html`.
- There are natural internal links inside the article body.
- Quote sources are inside quote boxes.
- Images and OGP files use the article slug directory.
- `blog.html` card is updated.
- `sitemap.xml` includes the article when it should be publicly indexed.
- Run `python3 scripts/check_prefecture_articles.py --strict` when adding a prefecture article to confirm coverage and `blog.html` linkage stay in sync.
- Long comparison articles are written `h2` block by `h2` block and avoid repeating the same point in multiple sections.
- Related articles are present at the very end of the article with real internal links.
