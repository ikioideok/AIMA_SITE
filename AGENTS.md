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
