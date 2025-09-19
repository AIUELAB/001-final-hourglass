#!/bin/bash

# Wikipedia知名度評価システム - バックグラウンド実行スクリプト

echo "================================================"
echo "Wikipedia知名度評価システム"
echo "バックグラウンド実行を開始します"
echo "================================================"

# ログファイル名
LOG_FILE="recognition_$(date +%Y%m%d_%H%M%S).log"

# Python環境の確認
if command -v python3 &> /dev/null; then
    echo "✅ Python3が見つかりました"
else
    echo "❌ Python3が見つかりません"
    exit 1
fi

# 必要なファイルの確認
if [ -f "ultra_think_RANKED_20250907_161756.csv" ]; then
    echo "✅ 入力ファイルが見つかりました"
else
    echo "❌ 入力ファイルが見つかりません"
    exit 1
fi

# 処理モードの選択
echo ""
echo "処理モードを選択してください:"
echo "1) テスト実行（10件）"
echo "2) デモ実行（100件）"
echo "3) 完全実行（4,701件）"
echo -n "選択 (1-3): "
read mode

case $mode in
    1)
        echo "テストモードで実行します（10件）"
        nohup python3 test_integrated_system.py > $LOG_FILE 2>&1 &
        ;;
    2)
        echo "デモモードで実行します（100件）"
        nohup python3 run_full_recognition_auto.py > $LOG_FILE 2>&1 &
        ;;
    3)
        echo "⚠️ 完全実行には2-3時間かかります"
        echo -n "続行しますか？ (y/n): "
        read confirm
        if [ "$confirm" = "y" ]; then
            # run_full_recognition_auto.py を編集して全件処理に変更
            cp run_full_recognition_auto.py run_full_recognition_all.py
            sed -i '' 's/df_sample = df.head(100)/df_sample = df/' run_full_recognition_all.py
            nohup python3 run_full_recognition_all.py > $LOG_FILE 2>&1 &
        else
            echo "キャンセルしました"
            exit 0
        fi
        ;;
    *)
        echo "無効な選択です"
        exit 1
        ;;
esac

# プロセスIDを取得
PID=$!
echo ""
echo "✅ バックグラウンドで処理を開始しました"
echo "   プロセスID: $PID"
echo "   ログファイル: $LOG_FILE"
echo ""
echo "進捗確認コマンド:"
echo "  tail -f $LOG_FILE"
echo ""
echo "プロセス確認コマンド:"
echo "  ps aux | grep $PID"
echo ""
echo "処理停止コマンド:"
echo "  kill $PID"
echo ""
echo "================================================"