# Blog Article Rules

- This is a static site. Public files live at the repository root and are deployed to `~/www/`.
- Main public pages are `index.html`, `service.html`, `company.html`, `privacy.html`, `blog.html`, and `blog-*.html`.
- Blog article assets live in `images/{article-slug}/`. Keep article image paths matched to the article slug.
- `blog-post.html` is the article template. Do not deploy it as a real article.
- `docs/`, `scripts/`, `samples/`, `output/`, `.playwright-*`, `.tokens/`, and `tmp*` are local work areas unless a task explicitly says otherwise.
- Do not reorganize public file paths just to make the repository look cleaner. Moving public HTML or image paths can break SEO, links, images, sitemap entries, and redirects.
- If public paths must change, update all internal links, image paths, canonical tags, OGP tags, `sitemap.xml`, and redirects together.
- The shared blog header/footer source is `blog-post.html`. Do not edit those blocks in `blog.html` or individual articles. After changing the shared layout, run `python3 scripts/sync_blog_layout.py`.
- The shared corporate-site shell sources are `partials/site-shell-head.html`, `partials/site-header.html`, and `partials/site-footer.html`. Do not edit generated `SITE_SHELL_HEAD`, `SITE_HEADER`, or `SITE_FOOTER` blocks in individual pages. After changing a shared shell source, run `python3 scripts/sync_site_shell.py`.
- New corporate pages must include all three shared-shell marker blocks so `scripts/sync_site_shell.py` can discover and update them.
- Before deploy, run `python3 scripts/sync_site_shell.py --check`, `python3 scripts/sync_blog_layout.py --check`, `python3 scripts/check_prefecture_articles.py --strict`, and `git diff --check`.
- For any new blog article, start from `blog-post.html`.
- Follow `docs/blog-article-spec.md`.
- For new articles, do not cap the number of `h3` sections. Normal non-FAQ `h3` sections should be substantial, roughly 300-400 Japanese characters each.
- New articles should include 2-3 primary/official source quotes where possible. Put `出典：...` inside the same `blockquote`; do not label quoted sources as `参考`.
- AIMA blog articles should naturally lead back to AIMA's strengths: LLMO specialization, unlimited consultation, monthly 50,000 yen pricing, unlimited article creation/revision within scope, and no minimum contract period.
- For any new blog article, run the visual polish step before finishing: generate the eyecatch/OGP with `imagegen`, add one short `<mark><strong>` highlight inside every `h3` section, and add or propose 3-6 infographic insertion points.
- When the article is intended to be published, do not stop at infographic text proposals. Generate the infographic image assets and insert them as `figure` blocks unless the user explicitly asks for proposal-only work.
- For new article eyecatch images, use `imagegen` by default. Do not replace it with local SVG/HTML/CSS compositing unless the user explicitly approves a fallback.
- For every new AIMA blog eyecatch, use only this fixed `imagegen` brief unless the user explicitly overrides it. Do not add subtitles, composition instructions, extra scene details, extra text, or alternate wording:
  - 用途：AIMAブログ用アイキャッチ
  - 形式：16:9 横長
  - 雰囲気：BtoB向け、清潔、レポート表紙風
  - 色：黒、#7759f6、#d1ed42、薄いグレー
  - 入れる文字：タイトル
  - 文字も画像生成すること
- Do not invent a different blog layout unless explicitly requested.
- Keep title, eyecatch, lead, lead TOC, supervisor block, article body, CTA, and prev/next navigation in the left main column.
- Keep the right sidebar for sticky modules. The default first module is the `H2` TOC.
- Use the supervisor profile from `company.html`.
- Put quote source links inside the same `blockquote`.
- If an article has a visible FAQ section, add matching `FAQPage` JSON-LD for those questions.
- For external company/vendor/competitor links in comparison articles, use `rel="nofollow noopener"`; keep government, municipality, public institution, and official primary-source documentation links follow unless there is a specific reason not to.
- Keep `<mark><strong>` highlights sparse in normal edits. For new articles, the required default is one short marker inside every `h3` section.
- For area or prefecture articles, add natural internal links to related cluster articles when they are published.
- After creating an article, update the article card in `blog.html`.
- Deploy notes are in `docs/deploy.md`.

# Google API Auth

- Do not scan the whole home directory to find Google OAuth tokens.
- Check the canonical token map in `docs/google-api-auth.md` first.
- For a quick lookup, run `python3 scripts/google_token_locator.py`.
- For Google Sheets write operations such as `spreadsheets.batchUpdate` or `addSheet`, use the `sheets-write` token entry first.
- Never copy token contents into this repo. Refer to token files by absolute path only.
