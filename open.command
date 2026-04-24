#!/bin/bash
cd "$(dirname "$0")"

# 既に3000番ポートが使われていたら解放
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

echo "========================================="
echo "  サーバー起動中: http://localhost:3000"
echo "  終了するには Ctrl+C を押してください"
echo "========================================="

# 2秒後にブラウザを開く（バックグラウンド）
(sleep 2 && open http://localhost:3000) &

# サーバーをフォアグラウンドで起動（これでターミナルが閉じない）
python3 -m http.server 3000
