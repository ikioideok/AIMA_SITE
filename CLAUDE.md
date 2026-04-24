# Blog Article Rules

- For any new blog article, start from `blog-post.html`.
- Follow `docs/blog-article-spec.md`.
- Do not invent a different blog layout unless explicitly requested.
- Keep title, eyecatch, lead, lead TOC, supervisor block, article body, CTA, and prev/next navigation in the left main column.
- Keep the right sidebar for sticky modules. The default first module is the `H2` TOC.
- Use the supervisor profile from `company.html`.
- Put quote source links inside the same `blockquote`.
- After creating an article, update the article card in `blog.html`.
- Deploy notes are in `docs/deploy.md`.

# Google API Auth

- Do not scan the whole home directory to find Google OAuth tokens.
- Check the canonical token map in `docs/google-api-auth.md` first.
- For a quick lookup, run `python3 scripts/google_token_locator.py`.
- For Google Sheets write operations such as `spreadsheets.batchUpdate` or `addSheet`, use the `sheets-write` token entry first.
- Never copy token contents into this repo. Refer to token files by absolute path only.

# Search Console And GA4

- Prefer local API scripts over browser scraping when Claude needs Search Console or GA4 data.
- For Search Console, use `scripts/search_console_search_analytics.py` and read `docs/search-console-api.md`.
- For GA4, use `scripts/ga4_run_report.py` and read `docs/google-analytics-api.md`.
- Before any Google API task, check `docs/google-api-auth.md` or run `python3 scripts/google_token_locator.py`.
- For Search Console reads, prefer the `search-analytics-combined` token as the default route. Use the dedicated `search-console` token only if the task explicitly depends on it.
- For GA4 reads, use the `analytics-read` token entry first.
- If a required GA4 property ID is unknown, list accessible properties with `python3 scripts/ga4_run_report.py --list-properties` before asking the user.
- Do not invent GA4 property IDs, Search Console property IDs, dimensions, or metrics. If the API rejects a combination, reduce the query and retry with a smaller set.
- If canonical tokens are missing or insufficient, stop and ask for the needed credential path instead of searching broadly.
