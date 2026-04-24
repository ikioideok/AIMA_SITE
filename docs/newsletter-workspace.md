# Google Workspace で動かすメルマガ最小構成

このサイトでは、`Google Workspace + Apps Script + Google Sheets` で `LLMO内製化マガジン` を無料に近い構成で回せるようにしています。

## 前提

- 送信元は `newsletter@自社ドメイン` のような専用アドレスを使う
- `SPF / DKIM / DMARC` は Google Workspace 側で設定する
- 配信は `double opt-in` 前提
- 購読停止はメール末尾とヘッダの両方から行えるようにする

## このメルマガの目的

- 一次の狙いは、`LLMOをまずは内製で試したい層` を集めること
- 本文はあくまで `内製化` に関する設計・運用・改善の実務知見を届ける
- 本文中では、強引に発注へ誘導するような流れは作らない
- 読者が `まずは自分たちで試せる` と感じられる内容を優先する
- 相談導線は、本文の最後にある自然な `ご相談はこちら` のCTAで受ける

本文を作るときは、売り込みよりも `内製で試せるヒント` を優先し、必要な相談導線は末尾CTAだけで補う。

## 使うファイル

- GAS 本体: [gas/unified-gas.js](../gas/unified-gas.js)
- フロント送信処理: [js/main.js](../js/main.js)
- ブログ導線: [blog.html](../blog.html), [blog-post.html](../blog-post.html)

## Apps Script 側の設定

1. `gas/unified-gas.js` を新しい Apps Script プロジェクトに貼り付ける
2. `SPREADSHEET_ID` を運用するスプレッドシートIDに変える
3. `NEWSLETTER_FROM_EMAIL` を実際の送信アドレスに変える
4. 必要なら `WEB_APP_URL` に公開URLを固定で入れる
5. `Gmail API` の高度なサービスを有効化する
6. Web App としてデプロイする
7. `sendDailyNewsletter` に時間トリガーをつける

`Gmail API` を有効化しておくと、`List-Unsubscribe` ヘッダ付きで送れます。無効でも `MailApp` にフォールバックして配信はできます。

## 自動作成されるシート

### `メルマガ購読者`

- `email`
- `status`
- `source`
- `confirm_token`
- `unsubscribe_token`
- `created_at`
- `confirmed_at`
- `unsubscribed_at`
- `last_sent_at`

`status` は `pending / active / unsubscribed` を使います。

### `メルマガ配信`

- `send_date`
- `subject`
- `preheader`
- `html_body`
- `text_body`
- `status`
- `sent_at`
- `sent_count`

配信前は `status` を `ready` にしておきます。`sendDailyNewsletter` は、当日以前で `ready / pending / draft` の最初の1行を拾って送ります。

### `メルマガ送信ログ`

- `timestamp`
- `send_date`
- `email`
- `subject`
- `result`
- `detail`

## ブログ側の導線

- `blog.html` に一覧ページ用の登録フォームを置く
- `blog-post.html` に記事末尾CTAとサイドバー導線を置く
- 既存の記事ページにも同じフォームを差し込む

フロントは `formType=newsletter` を同じ Web App に `POST` します。

## 運用フロー

1. 読者がブログからメールアドレスを登録する
2. Apps Script が `pending` で保存し、確認メールを送る
3. 確認リンクを押したら `active` になり、登録直後のウェルカムメールを1通送る
4. 毎朝のトリガーで当日の配信原稿を送る
5. 停止リンクを押したら `unsubscribed` になる

## 最初の運用ルール

- まずは `平日毎朝` か `週3回` で始める
- 本文は `300〜500字 + 1リンク` 程度に固定する
- `subject` は短く具体的にする
- 配信前に `自分宛てテスト送信` を1回行う

## デプロイ順

1. Apps Script を更新して Web App を再デプロイ
2. フロント側のHTML/JSを公開
3. 自分のメールアドレスで登録 → 確認 → 停止まで通す
4. `メルマガ配信` に1行入れて `sendDailyNewsletter` を手動実行する
