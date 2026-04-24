# Google API Auth Map

This workspace already has known Google OAuth token locations. Check these paths first before searching elsewhere.

## Canonical entries

### `analytics-read`

- Purpose: Google Analytics 4 read access for the local GA4 reporting script
- Token file: `.tokens/google-readonly-combined-token.json`
- Expected scope: `https://www.googleapis.com/auth/analytics.readonly`
- Notes: Use this first for GA4 reporting and property discovery.

### `sheets-write`

- Purpose: Google Sheets write access, including `spreadsheets.values.update` and `spreadsheets.batchUpdate` such as `addSheet`
- Token file: `/Users/mizumayuuki/Downloads/llmo_diagnoser/data/google-oauth-token.json`
- Expected scope: `https://www.googleapis.com/auth/spreadsheets`
- Notes: This is the first token to try when a task needs to create tabs, update headers, or write sheet data through the Sheets API.

### `docs-read`

- Purpose: Google Docs access plus Drive read-only access used by the local docs MCP tooling
- Token file: `/Users/mizumayuuki/.codex/tools/google-docs-mcp/token.json`
- Expected scopes:
  - `https://www.googleapis.com/auth/documents`
  - `https://www.googleapis.com/auth/drive.readonly`
  - `https://www.googleapis.com/auth/spreadsheets.readonly`
- Notes: Useful for reading Docs or Sheets metadata, but not sufficient for Sheets write calls.

### `search-console`

- Purpose: Search Console API cache used by local reporting scripts
- Token file: `.tokens/search-console-token.json`
- Expected scope: `https://www.googleapis.com/auth/webmasters.readonly`
- Notes: This token is workspace-local and unrelated to Sheets write access. Prefer the combined token first when Claude needs a default path that also works for GA4.

### `search-analytics-combined`

- Purpose: Combined Search Console + GA4 read access for local reporting scripts
- Token file: `.tokens/google-readonly-combined-token.json`
- Expected scopes:
  - `https://www.googleapis.com/auth/webmasters.readonly`
  - `https://www.googleapis.com/auth/analytics.readonly`
- Notes: This is the preferred default token for Claude when one token needs to cover both Search Console and GA4 without a second lookup.

## Fast lookup

Run:

```bash
python3 scripts/google_token_locator.py
```

Examples:

```bash
python3 scripts/google_token_locator.py --purpose sheets-write
python3 scripts/google_token_locator.py --purpose sheets-write --path-only
python3 scripts/google_token_locator.py --json
```

## Operational rule

- If a Google API task fails because a token is missing, check this map and the helper script output before doing any broader filesystem search.
- Refresh expired access tokens with the stored `refresh_token`; do not replace token locations unless the source system changes.
