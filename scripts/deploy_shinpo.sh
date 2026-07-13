#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_HOST="${SHINPO_REMOTE_HOST:-violetsheep5.sakura.ne.jp}"
REMOTE_ROOT="${SHINPO_REMOTE_ROOT:-www}"
MODE="dry-run"

if [[ "${1:-}" == "--apply" ]]; then
  MODE="apply"
elif [[ -n "${1:-}" && "${1:-}" != "--dry-run" ]]; then
  echo "使い方: scripts/deploy_shinpo.sh [--dry-run|--apply]" >&2
  exit 2
fi

cd "$ROOT_DIR"

required_files=(
  "shinpo/index.html"
  "shinpo/shinpo.css"
  "shinpo/shinpo.js"
  "shinpo/feed.xml"
  "shinpo/editorial-policy.html"
  "shinpo/images/ai-shinpo-logo.webp"
  "sitemap.xml"
  "news-sitemap.xml"
  "llms.txt"
  "images/favicon.svg"
  "images/apple-touch-icon.png"
  "images/member-photo.webp"
  "images/shinpo/managed-agents-hero.webp"
  "images/shinpo/ogp.png"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "エラー: 公開に必要なファイルがありません: $file" >&2
    exit 1
  fi
done

if ! compgen -G "shinpo/20??-??-??-*.html" >/dev/null; then
  echo "エラー: 公開記事が1件も見つかりません" >&2
  exit 1
fi

rsync_options=(
  -avz
  --itemize-changes
  --prune-empty-dirs
)

if [[ "$MODE" == "dry-run" ]]; then
  rsync_options+=(--dry-run)
  echo "確認モード: サーバーは変更しません"
else
  echo "公開モード: AI深報の許可済みファイルだけを更新します"
  ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_ROOT/shinpo/images' '$REMOTE_ROOT/images/shinpo'"
fi

# AI深報ディレクトリでは、明示した公開ファイルだけを転送する。
# drafts、テンプレート、Markdown、tmp、.DS_Storeなどは対象外。
rsync "${rsync_options[@]}" \
  --include='/index.html' \
  --include='/shinpo.css' \
  --include='/shinpo.js' \
  --include='/20??-??-??-*.html' \
  --include='/category-*.html' \
  --include='/feed.xml' \
  --include='/editorial-policy.html' \
  --include='/images/' \
  --include='/images/ai-shinpo-logo.webp' \
  --exclude='*' \
  shinpo/ \
  "$REMOTE_HOST:$REMOTE_ROOT/shinpo/"

# AI深報が参照する、サイト共通側の画像だけを個別転送する。
rsync "${rsync_options[@]}" \
  images/favicon.svg \
  images/apple-touch-icon.png \
  images/member-photo.webp \
  "$REMOTE_HOST:$REMOTE_ROOT/images/"

rsync "${rsync_options[@]}" \
  images/shinpo/managed-agents-hero.webp \
  images/shinpo/ogp.png \
  images/shinpo/articles \
  "$REMOTE_HOST:$REMOTE_ROOT/images/shinpo/"

rsync "${rsync_options[@]}" \
  .htaccess robots.txt sitemap.xml news-sitemap.xml llms.txt \
  "$REMOTE_HOST:$REMOTE_ROOT/"

if [[ "$MODE" == "dry-run" ]]; then
  echo "確認完了。実際に公開する場合だけ --apply を付けて実行してください。"
  exit 0
fi

base_url="https://ai-and-marketing.jp/shinpo"
check_urls=(
  "$base_url/"
  "$base_url/shinpo.css"
  "$base_url/shinpo.js"
  "$base_url/images/ai-shinpo-logo.webp"
  "https://ai-and-marketing.jp/images/shinpo/managed-agents-hero.webp"
  "https://ai-and-marketing.jp/images/shinpo/ogp.png"
  "https://ai-and-marketing.jp/sitemap.xml"
  "https://ai-and-marketing.jp/news-sitemap.xml"
  "$base_url/feed.xml"
)

for article in shinpo/20??-??-??-*.html; do
  check_urls+=("$base_url/${article#shinpo/}")
done

failed=0
for url in "${check_urls[@]}"; do
  if curl --fail --silent --show-error --location --output /dev/null "$url"; then
    echo "OK: $url"
  else
    echo "NG: $url" >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "エラー: 公開後のURL確認で失敗しました" >&2
  exit 1
fi

echo "AI深報の公開とURL確認が完了しました。"
