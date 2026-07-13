# AI深報 運用マニュアル

「どこよりも早く、AIの重要ニュースが紹介されるメディア」。
運営：株式会社AIMA。

## 構成ファイル

| パス | 役割 |
|---|---|
| `shinpo/index.html` | メディアトップ。`<!-- SHINPO:LIST -->` の直後に新記事カードが挿入される |
| `shinpo/post-template.html` | 記事テンプレート（`{{TITLE}}` などのプレースホルダー入り） |
| `shinpo/shinpo.css` | 共通スタイル（index-redesign-v5 のデザイン言語を継承） |
| `shinpo/drafts/*.json` | 記事の原稿JSON（掲載後も履歴として残す） |
| `shinpo/YYYY-MM-DD-slug.html` | 公開記事 |
| `scripts/shinpo_watch.py` | 情報収集（RSS・Hacker News・Hermes X検索） |
| `scripts/shinpo_x_watch.py` | HermesのX検索結果から、引用URLがある公式投稿だけを候補化 |
| `scripts/shinpo_queue.py` | 候補を `new` / `drafted` / `dismissed` / `published` で管理 |
| `scripts/shinpo_publish.py` | 記事JSON → HTML生成＋トップページ・サイトマップ更新 |
| `data/shinpo_seen.json` | 既読URL（自動生成） |
| `data/shinpo_queue.json` | 新着キュー（自動生成） |

## 運用フロー（1記事あたり15分目安）

1. **収集**：`python3 scripts/shinpo_watch.py`
   - 新着がスコア順で表示され、`data/shinpo_queue.json` に書き出される
   - 一度見つけた候補も、処理するまで最大7日間キューに残る
   - Hermesが引用URLを返さない場合は、X候補を安全のため採用しない
2. **選定・執筆**：Codexがキュー上位を確認して記事JSONを作る
   - 元Xポストだけで断定せず、公式ブログなどの一次情報も確認する
   - 確認できた場合だけ `shinpo/drafts/` に記事JSONを作成する
   - `python3 scripts/shinpo_publish.py --check <draft.json>` で形式を検査する
   - 下書き完成後、候補を `drafted` に変更する
   - **事実確認が取れない項目は書かない**（下記の記事ルール参照）
3. **掲載**：`python3 scripts/shinpo_publish.py shinpo/drafts/<file>.json`
   - 記事HTMLが生成され、トップページの先頭にカードが入り、`sitemap.xml`にも記事URLが追加される
   - 記事にはAIMAのCTAと監修者情報がテンプレートから自動で入る
4. **デプロイ前確認**：公開対象を確認する（サーバーは変更しない）
   ```bash
   scripts/deploy_shinpo.sh --dry-run
   ```
5. **デプロイ**：確認後、許可済みのHTML・CSS・JS・画像だけをSSH経由で公開する
   ```bash
   scripts/deploy_shinpo.sh --apply
   ```

`shinpo/` 全体のFTPミラーは禁止。`drafts/`、`post-template.html`、
`design-qa.md`、`tmp*`、`.DS_Store` などの作業物が公開されるため、
必ず `scripts/deploy_shinpo.sh` を使う。スクリプトは公開後にトップ、
CSS、JS、ロゴ、ヒーロー画像、全記事がHTTP 200か確認する。

Codexオートメーション `ai-4`（AI深報 ニュース作成・公開・URL登録）が、毎日8:00〜22:00の
2時間おきに「収集 → 一次情報確認 → 最大1本の記事作成 → 品質検査 → 公開 →
Search ConsoleのURL検査・登録申請 → サイトマップ再送信」まで実行する。
一次情報を確認できない場合や検査に失敗した場合は公開しない。

### キュー操作

```bash
# 未処理候補をJSONで5件表示
python3 scripts/shinpo_queue.py list --status new --limit 5 --json

# 下書き化した候補を更新
python3 scripts/shinpo_queue.py mark '<候補URL>' drafted --draft-path shinpo/drafts/<file>.json

# 掲載しない候補を却下
python3 scripts/shinpo_queue.py mark '<候補URL>' dismissed
```

記事JSONに `candidate_url` が入っていれば、掲載時にキューは自動で `published` になる。

## 記事ルール

- **事実のみ**。出典（一次情報）に書かれていることだけを書く。推測・未確認情報は「〜とされる」「未確認」と明記
- **出典必須**。`sources` に一次情報を必ず入れる。二次報道（ITmediaなど）を使った場合は両方入れる
- **引用の出典リンクは同じ blockquote 内に入れる**（サイト共通ルール）
- **3行要約（lead3）は必ず3行**。忙しい読者はここだけ読む前提で書く
- **記事タイトルは20〜64文字**。読みやすさの推奨は30〜50文字。英数字・記号も1文字として数える
- 見出し構成の目安：「何が発表されたか」→「特徴・詳細」→「なぜ重要か」
- カテゴリ：`企業動向` / `プロダクト` / `生成AI` / `セキュリティ` / `お知らせ`。
  旧原稿の `企業` / `製品` / `モデル` は公開時に自動変換される。速報性が高いものは `"breaking": true`
- 記事JSONの形式は `scripts/shinpo_publish.py` の docstring 参照

## 情報源と「最速」の現実解

### 現在監視しているもの（無料・安定）

- 公式ブログRSS：OpenAI / Google AI / Hugging Face / ITmedia AI+ / Publickey
- Hacker News（Algoliaフロントページ、AIキーワードで絞り込み）
- フィードの追加・削除は `scripts/shinpo_watch.py` 冒頭の `FEEDS` を編集

### 既知の制約

- **Reddit は 403 でブロックされる**（データセンター/ボットUA対策）。コードは残してあるが期待しない
- **OpenAI のサイト本文はボットアクセス不可**（RSSは取れる）。記事執筆時は二次報道か手動確認で補う
- 初回実行はフィードの過去記事が全部「新着」になる（2回目以降は差分のみ）

### X（Twitter）について

X検索には、設定済みのHermes `x_search_tool` を使う。

- 場所：`/Users/mizumayuuki/.hermes/hermes-agent`
- 認証：xAI OAuth（SuperGrok契約）
- 対象：OpenAI、Anthropic、Google、xAI、Metaなどの公式アカウント
- 安全策：Hermesが実在する元ポストURLを引用として返した候補だけ採用する
- 記事化前：X投稿にリンクされた公式発表、企業ブログ、IRなどをもう一度確認する

Hermesがログアウトした場合は、次で再認証する。

```bash
/Users/mizumayuuki/.hermes/hermes-agent/venv/bin/hermes auth add xai-oauth
```

記事作成から公開まで自動化するが、一次情報の確認と公開前検査に通らない記事は公開しない。

## 公開前チェックリスト

- [ ] 出典リンクが生きているか
- [ ] 数値・固有名詞が出典と一致しているか
- [ ] Hermesの検索結果だけで断定せず、一次情報本文を確認したか
- [ ] `candidate_url` が元キュー候補と一致しているか
- [ ] CTA（無料相談・サービス詳細）と監修者情報が各1つ入っているか
- [ ] canonical、meta description、NewsArticle構造化データが入っているか
- [ ] `noindex` が入っていないか
- [ ] 公開後にSearch ConsoleのURL検査・登録申請とサイトマップ再送信を完了したか
