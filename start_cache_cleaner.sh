#!/bin/bash

# IDEキャッシュクリアツール起動スクリプト

echo "🚀 IDEキャッシュクリアツールを起動中..."

# スクリプトディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境の確認と作成
if [ ! -d "ide_cache_env" ]; then
    echo "📦 仮想環境を作成中..."
    python3 -m venv ide_cache_env
fi

# 仮想環境をアクティベート
source ide_cache_env/bin/activate

# 依存関係のインストール
echo "📦 依存関係をインストール中..."
pip install -q watchdog

# 引数の確認
if [ "$1" = "--monitor" ]; then
    echo "🔍 ファイル削除監視モードを開始"
    if [ "$2" = "--auto-restart" ]; then
        echo "🔄 自動再起動モードを有効化"
        python scripts/auto_cache_cleaner.py --monitor --auto-restart
    else
        python scripts/auto_cache_cleaner.py --monitor
    fi
else
    echo "🧹 手動キャッシュクリアを実行"
    python scripts/auto_cache_cleaner.py
fi

# 仮想環境を非アクティベート
deactivate

echo "✨ 完了！"
