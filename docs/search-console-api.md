# Search Console API

`Search Analytics API` で検索クエリとページ別データを取得するためのスクリプトです。

ファイル:

- `scripts/search_console_search_analytics.py`

Google 公式:

- `searchanalytics.query`: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- Python quickstart: https://developers.google.com/webmaster-tools/v1/quickstart/quickstart-python
- Search Analytics how-to: https://developers.google.com/webmaster-tools/v1/how-tos/search_analytics

## 依存パッケージ

```bash
python3 -m pip install --upgrade google-api-python-client google-auth google-auth-oauthlib
```

## 認証方法

このスクリプトは次の3パターンに対応しています。

### 1. 既存トークン

このワークスペースには、すでに使える Search Console トークンがあります。まずは canonical token map を確認してください。通常は combined token を既定ルートとして使うのが最短です。

```bash
python3 scripts/google_token_locator.py --purpose search-console
python3 scripts/google_token_locator.py --purpose search-analytics-combined
```

既存トークンでそのまま確認する例:

```bash
python3 scripts/search_console_search_analytics.py --list-sites

python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query \
  --last-days 28
```

### 2. OAuth クライアント

普段使っている Google アカウントで Search Console を読むときの標準ルートです。

1. Google Cloud で `Search Console API` を有効化
2. `OAuth client ID` を `Desktop app` で作成
3. JSON を保存
4. 初回実行時にブラウザで認証

実行例:

```bash
python3 scripts/search_console_search_analytics.py \
  --client-secrets /path/to/oauth-client.json \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query \
  --last-days 28
```

初回認証後のトークンは `.tokens/search-console-token.json` に保存されます。

### 3. Service Account

定期実行やサーバー実行向けです。`service account` を Search Console 側の対象プロパティにユーザー追加してから使います。

実行例:

```bash
python3 scripts/search_console_search_analytics.py \
  --service-account /path/to/service-account.json \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query \
  --last-days 28
```

環境変数でも渡せます。

```bash
export SEARCH_CONSOLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
python3 scripts/search_console_search_analytics.py --site-url sc-domain:ai-and-marketing.jp
```

既存の `GOOGLE_CREDENTIALS_JSON` に service account JSON が入っている場合も利用できます。

## よく使う例

### アクセス可能なプロパティ一覧

```bash
python3 scripts/search_console_search_analytics.py --list-sites
```

### 上位クエリを取る

```bash
python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query \
  --last-days 28 \
  --row-limit 100
```

### クエリとページの組み合わせを見る

```bash
python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query,page \
  --last-days 28 \
  --row-limit 500
```

### まず日別でデータ有無を確認する

Google の how-to でも、先に `date` でデータ存在確認する流れが推奨されています。

```bash
python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions date \
  --last-days 14
```

### 特定ページ配下だけ見る

```bash
python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query,page \
  --filter page contains /blog/ \
  --last-days 28
```

### CSV に書き出す

```bash
python3 scripts/search_console_search_analytics.py \
  --site-url sc-domain:ai-and-marketing.jp \
  --dimensions query,page \
  --last-days 90 \
  --row-limit 1000 \
  --output-format csv \
  --output output/search-console/query-page-90d.csv
```

## 引数メモ

- `--site-url`
  Search Console のプロパティID。URL prefix なら `https://example.com/`、ドメインプロパティなら `sc-domain:example.com`
- `--dimensions`
  `query`, `page`, `date`, `country`, `device`, `searchAppearance` をカンマ区切り
- `--search-type`
  `web`, `image`, `video`, `news`, `discover`, `googleNews`
- `--aggregation`
  `auto`, `byPage`, `byProperty`, `byNewsShowcasePanel`
- `--data-state`
  `final`, `all`, `hourly_all`
- `--filter`
  `DIMENSION OPERATOR VALUE` 形式。演算子は `contains`, `equals`, `notContains`, `notEquals`, `includingRegex`, `excludingRegex`

## 注意

- 既定の `--token-file` は `.tokens/google-readonly-combined-token.json` です。既存トークンだけで読み取りできます。新しい OAuth client を探す前に、まず token map を確認してください。
- Search Console データは通常少し遅れて反映されます。デフォルトでは `今日から3日前` までを対象にしています。
- `rowLimit` の上限は `25,000` です。大量取得時は `--start-row` を増やしてページングしてください。
- `query` や `page` で細かく切ると、API は上位行中心で返します。全量運用が必要なら BigQuery export の方が向いています。
