# Google Analytics 4 API

`Analytics Admin API` でアクセス可能なプロパティ一覧を取得し、`Analytics Data API` で GA4 レポートを引くためのスクリプトです。

ファイル:

- `scripts/ga4_run_report.py`

Google 公式:

- Analytics Admin API overview: https://developers.google.com/analytics/devguides/config/admin/v1
- Analytics Data API basics: https://developers.google.com/analytics/devguides/reporting/data/v1
- `properties.runReport`: https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport

## 依存パッケージ

```bash
python3 -m pip install --upgrade google-auth requests
```

## 認証方法

このワークスペースには、GA4 読み取り用の canonical token があります。まずは token map を確認してください。

```bash
python3 scripts/google_token_locator.py --purpose analytics-read
python3 scripts/google_token_locator.py --purpose search-analytics-combined
```

デフォルトでは `.tokens/google-readonly-combined-token.json` を使います。`analytics.readonly` を含むので、追加の client secret なしで使えます。

## よく使う例

### アクセス可能な GA4 プロパティ一覧

```bash
python3 scripts/ga4_run_report.py --list-properties
```

### 直近 28 日の流入元別セッション

```bash
python3 scripts/ga4_run_report.py \
  --property-id 523694776 \
  --dimensions sessionSource \
  --metrics sessions \
  --order-by sessions \
  --desc \
  --last-days 28
```

### ChatGPT 経由の流入だけ見る

```bash
python3 scripts/ga4_run_report.py \
  --property-id 523694776 \
  --dimensions pagePath,sessionSource \
  --metrics sessions,screenPageViews \
  --filter sessionSource exact chatgpt.com \
  --order-by sessions \
  --desc \
  --last-days 90
```

### 特定ディレクトリ配下のページを見る

```bash
python3 scripts/ga4_run_report.py \
  --property-id 523694776 \
  --dimensions pagePath \
  --metrics sessions,screenPageViews,totalUsers \
  --filter pagePath contains /blog/ \
  --order-by screenPageViews \
  --desc \
  --last-days 28
```

### CSV に書き出す

```bash
python3 scripts/ga4_run_report.py \
  --property-id 523694776 \
  --dimensions sessionSource,pagePath \
  --metrics sessions,screenPageViews,totalUsers \
  --order-by sessions \
  --desc \
  --last-days 90 \
  --output-format csv \
  --output output/analytics/session-source-page-90d.csv
```

## 引数メモ

- `--list-properties`
  GA4 Admin API で見える account / property 一覧を出します
- `--property-id`
  `properties/523694776` の末尾の数値部分
- `--dimensions`
  `sessionSource`, `sessionMedium`, `pagePath`, `landingPage`, `date` などをカンマ区切り
- `--metrics`
  `sessions`, `screenPageViews`, `totalUsers`, `engagedSessions` などをカンマ区切り
- `--filter`
  `FIELD OPERATOR VALUE` 形式。演算子は `exact`, `contains`, `beginsWith`, `endsWith`, `fullRegexp`, `partialRegexp`
- `--order-by`
  `--dimensions` または `--metrics` に含めた項目名

## 運用メモ

- まず `--list-properties` で property ID を確定してからレポートを引くと無駄が少ないです。
- Search Console は検索面の変化、GA4 は流入後のページ閲覧を追う用途に分けると解釈が安定します。
- `utm_source=chatgpt.com` の流入確認では、`sessionSource` を起点に見ると扱いやすいです。
- GA4 のディメンションとメトリクスには互換性制約があります。API が `400` を返したら組み合わせを減らして切り分けてください。
