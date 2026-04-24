# Prefecture Article Automation

## Purpose

Generate the remaining prefecture-specific `blog-*-llmo-kaisha.html` articles one at a time while keeping `blog.html` and article coverage checks in sync.

## Helper Commands

Show the current coverage report:

```bash
python3 scripts/check_prefecture_articles.py
```

Get the next missing prefecture in machine-readable form:

```bash
python3 scripts/check_prefecture_articles.py --next-missing --json
```

Fail the run when `blog.html` linkage is inconsistent:

```bash
python3 scripts/check_prefecture_articles.py --strict
```

## Automation Rules

- Process at most one missing prefecture per run.
- Start from `blog-post.html`.
- Follow `docs/blog-article-spec.md`.
- Target roughly 10,000 Japanese characters for each prefecture article unless the user changes the requirement.
- Update `blog.html` after creating a new article.
- Update `sitemap.xml` for each newly published prefecture article.
- Keep article assets under `images/{slug}/`.
- Use a fixed eyecatch prompt pattern for prefecture articles:
  - `{都道府県名}でおすすめのLLMO会社10選`
  - `費用相場と選び方もわかりやすく解説`
- Use only `#ffffff`, `#000000`, `#7759f6`, and `#d1ed42` in the eyecatch.
- Export the eyecatch at `1600x900`.
- Render the Japanese title text inside the `image2` output itself.
- Do not switch to a local text-overlay workflow unless the user explicitly asks for that fallback.
- Use current web sources for company facts, services, and local statistics because these can change.
- Review existing prefecture articles first and keep the same high-level article pattern unless a local reason justifies a change.
- When the article lists company sections under `h3`, use the screenshot workflow from [$blog-company-homepage-screenshots](/Users/mizumayuuki/.codex/skills/blog-company-homepage-screenshots/SKILL.md).
- Write the article one `h2` block at a time instead of generating the whole body in one pass.
- Before drafting, decide the final `h2` outline and assign a unique purpose to each block.
- After drafting each `h2` block, keep a short covered-points note so later blocks do not repeat the same explanation.
- Assemble the final article only after all `h2` blocks have been drafted and checked for overlap.
- End each run by executing `python3 scripts/check_prefecture_articles.py --strict`.
- After the content checks pass, deploy the changed public files according to `docs/deploy.md`, syncing only the files and asset directories that changed.
- Verify the live article, `blog.html`, and `sitemap.xml` with `curl` after deploy.

## Default H2 Outline For Prefecture Articles

Keep this outline by default:

1. `{都道府県名 or 地域名}でおすすめのLLMO会社10選`
2. `{都道府県名 or 地域名}のLLMO会社を比較する際のポイント`
3. `{都道府県名 or 地域名}のLLMO会社に依頼する費用相場`
4. `{都道府県名 or 地域名}のLLMO会社に関するよくある質問`
5. `まとめ` or a short prefecture-specific closing headline

The heading labels can be adjusted slightly, but the article should still cover these five roles in this order.

## Locality Rules By H2

- `おすすめのLLMO会社10選`:
  - Introduce the prefecture through its actual business geography before listing companies.
  - Prefer companies with a real office, strong service page, or clear support relevance to that prefecture.
  - In each company description, explain fit in local terms such as prefectural cities, industrial clusters, tourism areas, or local business types.
- `比較する際のポイント`:
  - Base each `h3` on that prefecture's real market structure.
  - Use prefecture-specific information such as major cities, manufacturing clusters, tourism areas, healthcare concentration, startup ecosystem, logistics hubs, or population distribution.
  - Avoid generic bullets that could be pasted into another prefecture article unchanged.
- `費用相場`:
  - Explain the price bands, then tie them back to local business reality.
  - Example framing: urban competition, broad-area support, manufacturing complexity, tourism demand, local SMB budgets, or multi-location operations.
- `FAQ`:
  - Keep the common core questions, but customize at least some questions or answers to that prefecture's context.
  - Example: Tokyo may emphasize BtoB and multi-location companies, Aichi may emphasize manufacturing, Fukuoka may emphasize tourism and logistics.
- `まとめ`:
  - Close with the prefecture's actual choosing logic, not a generic recap.
  - Summarize which local market differences should drive company selection.
