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
8. Run the visual polish step before final verification:
   - Generate `eyecatch.jpg` and `og.jpg` with `imagegen`.
   - Add one short `<mark><strong>` highlight inside every `h3` section.
   - Choose 3-6 infographic insertion points.
   - For publish-ready articles, generate the infographic assets and insert them as `figure` blocks.

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
- Use the shared AIMA MEDIA header/footer pattern: `media-site-header` (logo, search form pointing to `blog.html`, consult CTA, category nav), `blog-footer`, plus `css/blog-media.css`, `js/main.js`, and `js/media-header.js`. The body tag needs `class="media-article"`.
- The single source of truth for the shared header/footer is `blog-post.html`. Never edit these blocks in individual articles or `blog.html` directly. Edit them in `blog-post.html`, then run `python3 scripts/sync_blog_layout.py` to propagate to every blog page (use `--check` to preview).

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
- Do not set a maximum number of `h3` sections. Use as many `h3` sections as needed to answer the search intent clearly without padding or repetition.
- For normal body sections, target roughly 300-400 Japanese characters under each `h3`. FAQ `h3` sections may be shorter when a concise answer is more useful.
- Keep the lead to 2-3 short paragraphs before the TOC.
- For long comparison articles, target roughly 10,000 Japanese characters overall unless the user requests a different length.
- Draft long articles section-by-section at the `h2` level, then assemble them after the sections are individually written and checked.
- Give each `h2` block a distinct role so the same explanation does not get repeated across multiple sections.
- The purpose of AIMA blog articles is to generate interest in AIMA, not to be a neutral encyclopedia article. Each article should naturally return to AIMA's current strengths where relevant:
  - LLMO-specialized company
  - unlimited consultation, anytime and for as long as needed, including broader Web marketing questions when related
  - monthly 50,000 yen pricing, positioned as about one-third of the industry average
  - unlimited article creation, article revision, and related implementation work within the service scope
  - no minimum contract period
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
- If the article has a visible FAQ section, add `FAQPage` JSON-LD. The `Question` entries must match the visible FAQ questions, and the answer text should summarize the visible answer without inventing extra claims.
- Add 2-4 natural internal links inside the article body, not only in the header or CTA.
- Prioritize links to related published blog articles when available. If the cluster is not published yet, use relevant internal service/tool/company pages instead.
- For area, prefecture, or comparison articles, add natural links to nearby cluster articles when they exist, such as same-region prefecture articles, major city comparison articles, or the relevant general comparison article. Do not force links to unpublished or weakly related pages.
- Never leave `href="#"` in the post navigation. If previous/next articles are unavailable, use real internal fallback links such as `blog.html` and another relevant page.
- External link rel policy:
  - Company, vendor, agency, tool, and competitor links in comparison articles use `rel="nofollow noopener"` when they open in a new tab.
  - Government, municipality, university, public institution, standards body, and official documentation links can stay follow by default, but still use `noopener` with `target="_blank"`.
  - Do not blindly add `nofollow` to every external source link. Classify the link first.

## Quote And Reference Rules
- When quoting a source, keep the source link inside the same `blockquote` using `.quote-source`.
- Add 2-3 source-backed quotes from primary or official information in each new article when possible. Use quotes to support important claims, definitions, pricing logic, or platform guidance.
- Quote labels must say `出典：...`, not `参考：...`. Regular non-quoted links may still use reference-style wording.
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
- For every new article, generate the eyecatch and OGP source with `imagegen` by default. Do not use local SVG/HTML/CSS text composition as the default substitute.
- For every new AIMA blog eyecatch, use only this fixed `imagegen` brief unless the user explicitly overrides it. Do not add subtitles, composition instructions, extra scene details, extra text, or alternate wording:
  - 用途：AIMAブログ用アイキャッチ
  - 形式：16:9 横長
  - 雰囲気：BtoB向け、清潔、レポート表紙風
  - 色：黒、#7759f6、#d1ed42、薄いグレー
  - 入れる文字：タイトル
  - 文字も画像生成すること
- For every new publish-ready article, add infographic assets under `images/{slug}/` when the article has dense explanations, comparisons, flows, or checklists. Use descriptive names such as `infographic-role-comparison.jpg`.
- For prefecture-specific LLMO company articles, generate the eyecatch with a fixed `image2` prompt pattern based on the article title:
  - `{都道府県名}でおすすめのLLMO会社10選`
  - `費用相場と選び方もわかりやすく解説`
- Use only the fixed eyecatch colors above, with white allowed as the base canvas when needed for the clean report-cover look.
- Export the eyecatch at `1600x900`.
- Render the Japanese title text inside the `image2` output itself.
- Do not add the title later in HTML/CSS or by local post-compositing unless the user explicitly asks for a fallback workflow.

## Style Rules
- Body text uses the stronger gray setting from the current template.
- Reference links are smaller than body text.
- Use `<mark><strong>` only for the most important phrases. Target 10 or fewer occurrences per article unless the user explicitly approves a denser style.
- New articles are the default exception: add one short `<mark><strong>` phrase inside each `h3` section. Keep each marker short; do not mark the heading itself.
- When a phrase needs light emphasis but is not a top-priority takeaway, use `<strong>` only or leave it as plain text.
- Keep the current CTA and prev/next block structure.
- Add a related articles section after the prev/next navigation as the last block in the left main column.
- Use real internal links in the related article cards. Prefer 2-3 published blog articles; if you want a broader directory link, keep it as a separate text link such as `blog.html`.
- Preserve the responsive two-column behavior from `blog-post.html`.

## Final Checklist
- Visible breadcrumbs exist and match the article path.
- `Article` and `BreadcrumbList` JSON-LD are present and article-specific.
- If a visible FAQ section exists, `FAQPage` JSON-LD is present and the number of `Question` entries matches the visible FAQ questions.
- The visible date uses a `<time>` tag with a machine-readable `datetime`.
- Both `公開日` and `更新日` are shown in `.post-meta`, and match `datePublished` / `dateModified` in JSON-LD and `article:published_time` / `article:modified_time` in OGP.
- Title and eyecatch are in the left main column.
- Lead TOC exists and is collapsed by default.
- Sidebar TOC exists, is `H2` only, and appears from the first `H2`.
- Supervisor block matches `company.html`.
- There are natural internal links inside the article body.
- Area or comparison articles link to related cluster articles when relevant articles are already published.
- External company/vendor/competitor links use `rel="nofollow noopener"`; public primary-source links are not blindly nofollowed.
- `<mark><strong>` usage is 10 or fewer occurrences unless deliberately approved for that article.
- Quote sources are inside quote boxes.
- New articles include 2-3 primary-source quotes with `出典：...` inside the same quote boxes when possible.
- Images and OGP files use the article slug directory.
- New article eyecatch/OGP files were generated with `imagegen`, not only local SVG/HTML/CSS composition.
- Each `h3` section has one short `<mark><strong>` highlight when the article is newly created.
- Infographic insertion points were proposed, and publish-ready articles include the generated infographic figures.
- `blog.html` card is updated.
- `sitemap.xml` includes the article when it should be publicly indexed.
- Run `python3 scripts/check_prefecture_articles.py --strict` when adding a prefecture article to confirm coverage and `blog.html` linkage stay in sync.
- Long comparison articles are written `h2` block by `h2` block and avoid repeating the same point in multiple sections.
- Related articles are present at the very end of the article with real internal links.
