#!/bin/bash
# CTR改善＆kakuyasu-daiko集約のデプロイスクリプト（2026-05-02）
# curlでFTPアップロード。lftp不要。
# 実行: bash scripts/deploy_ctr_fix.sh

set -euo pipefail
cd "$(dirname "$0")/.."

FTP_USER="violetsheep5"
FTP_HOST="violetsheep5.sakura.ne.jp"
FTP_BASE="ftp://${FTP_HOST}"

read -s -r -p "FTPパスワード: " FTP_PASSWORD
echo
if [ -z "$FTP_PASSWORD" ]; then
  echo "パスワードが入力されませんでした。中断します。" >&2
  exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

NETRC="$TMPDIR/netrc"
umask 077
cat > "$NETRC" <<EOF
machine $FTP_HOST
login $FTP_USER
password $FTP_PASSWORD
EOF
chmod 600 "$NETRC"

CURL_OPTS=(--silent --show-error --fail --netrc-file "$NETRC" --ftp-pasv)

echo
echo "[1/3] サーバーの既存 .htaccess を確認中..."
HTTP_STATUS=$(curl --netrc-file "$NETRC" --ftp-pasv -o "$TMPDIR/server_htaccess" -w "%{http_code}" --silent "$FTP_BASE/.htaccess" || echo "ERROR")

NEEDS_HTACCESS_UPLOAD=1
if [ -s "$TMPDIR/server_htaccess" ]; then
  if grep -q "kakuyasu-llmo-daiko" "$TMPDIR/server_htaccess"; then
    echo "  → 既存に301設定あり。.htaccess は変更なし"
    NEEDS_HTACCESS_UPLOAD=0
  else
    echo "  → 既存あり。301行を追記してマージ"
    cp "$TMPDIR/server_htaccess" .htaccess.merged
    {
      echo ""
      echo "# 301 redirect: kakuyasu-llmo-daiko → kakuyasu-llmo-taisaku-kaisha (consolidated 2026-05-02)"
      echo "Redirect 301 /blog-kakuyasu-llmo-daiko.html /blog-kakuyasu-llmo-taisaku-kaisha.html"
    } >> .htaccess.merged
    mv .htaccess.merged .htaccess
  fi
else
  echo "  → サーバーに既存なし。新規アップロード"
fi

FILES=(
  blog-aichi-llmo-kaisha.html
  blog-akita-llmo-kaisha.html
  blog-aomori-llmo-kaisha.html
  blog-btob-llmo-kaisha.html
  blog-fukuoka-llmo-kaisha.html
  blog-gunma-llmo-kaisha.html
  blog-hokkaido-llmo-kaisha.html
  blog-ibaraki-llmo-kaisha.html
  blog-iwate-llmo-kaisha.html
  blog-kakuyasu-llmo-daiko.html
  blog-kakuyasu-llmo-taisaku-kaisha.html
  blog-kanagawa-llmo-kaisha.html
  blog-llmo-taisaku.html
  blog-miyagi-llmo-kaisha.html
  blog-osaka-llmo-kaisha.html
  blog-saitama-llmo-kaisha.html
  blog-tochigi-llmo-kaisha.html
  blog-tokyo-llmo-kaisha.html
  blog.html
  sitemap.xml
)

if [ "$NEEDS_HTACCESS_UPLOAD" = "1" ]; then
  FILES+=(.htaccess)
fi

echo
echo "[2/3] ${#FILES[@]} ファイルをアップロード中..."

FAIL_COUNT=0
for f in "${FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  ⚠️  スキップ: $f"
    continue
  fi
  if curl "${CURL_OPTS[@]}" -T "$f" "$FTP_BASE/$f"; then
    printf "  ✓ %s\n" "$f"
  else
    printf "  ✗ %s (失敗)\n" "$f" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

echo
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "[3/3] $FAIL_COUNT 件のアップロード失敗あり" >&2
  exit 1
fi

echo "[3/3] デプロイ完了"
echo
echo "動作確認:"
echo "  curl -I https://ai-and-marketing.jp/blog-kakuyasu-llmo-daiko.html"
echo "  → 301 Moved Permanently が返れば成功"
