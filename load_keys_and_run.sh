#!/bin/bash
# APIキー自動ロード＆品質優先知名度評価システム実行スクリプト

echo "=================================="
echo "🔑 APIキー自動ロード開始"
echo "=================================="

# APIキーをロード
python3 scripts/load_api_keys.py

# .envファイルを読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ .envファイルから環境変数を設定しました"
fi

# APIキー設定状況確認
echo ""
echo "📊 APIキー設定状況:"
python3 -c "
import os
keys = [
    'SERPAPI_API_KEY',
    'NEWS_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'BRAVE_API_KEY',
    'YOUTUBE_API_KEY'
]
for k in keys:
    status = '✅ 設定済み' if os.getenv(k) else '❌ 未設定'
    print(f'  {k}: {status}')
"

echo ""
echo "=================================="
echo "🚀 品質優先知名度評価システム"
echo "=================================="
echo ""
echo "処理時間: 5-8時間（品質保証付き）"
echo "入力ファイル: ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
echo ""
read -p "実行しますか？ (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 quality_first_recognition_system.py
else
    echo "❌ 実行をキャンセルしました"
fi
