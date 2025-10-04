#!/bin/bash
# PDCAガーディアン ルール同期システム - Cron自動化セットアップスクリプト
# 作成日: 2025年9月22日

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH="/usr/bin/python3"
LOG_DIR="$PROJECT_DIR/logs/cron"
SYNC_SCRIPT="$PROJECT_DIR/rule_sync_system.py"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "PDCAガーディアン 自動同期セットアップ"
echo "======================================"

# 1. ログディレクトリの作成
echo -e "\n${GREEN}[1/5]${NC} ログディレクトリを作成..."
mkdir -p "$LOG_DIR"
echo "✅ ログディレクトリ: $LOG_DIR"

# 2. 同期実行ラッパースクリプトの作成
echo -e "\n${GREEN}[2/5]${NC} 実行ラッパースクリプトを作成..."
cat > "$PROJECT_DIR/scripts/run_daily_sync.sh" << 'WRAPPER_EOF'
#!/bin/bash
# PDCAガーディアン 日次同期実行スクリプト

PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
LOG_DIR="$PROJECT_DIR/logs/cron"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sync_$TIMESTAMP.log"
SUMMARY_FILE="$LOG_DIR/sync_summary.log"

# 環境設定
export PATH="/usr/local/bin:/usr/bin:/bin"
cd "$PROJECT_DIR" || exit 1

# ログヘッダー
echo "=====================================" >> "$LOG_FILE"
echo "PDCAガーディアン ルール同期" >> "$LOG_FILE"
echo "実行日時: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

# Python仮想環境のアクティベート（もし存在すれば）
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 同期実行
echo "同期開始..." >> "$LOG_FILE"
python3 "$PROJECT_DIR/rule_sync_system.py" >> "$LOG_FILE" 2>&1
SYNC_EXIT_CODE=$?

# 結果記録
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    echo "✅ 同期成功: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
    echo "同期が正常に完了しました" >> "$LOG_FILE"

    # 成功通知（macOS通知センター）
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "PDCAガーディアンのルール同期が完了しました" with title "同期成功"'
    fi
else
    echo "❌ 同期失敗: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
    echo "エラーが発生しました (Exit Code: $SYNC_EXIT_CODE)" >> "$LOG_FILE"

    # エラー通知（macOS通知センター）
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "PDCAガーディアンのルール同期でエラーが発生しました" with title "同期失敗" sound name "Glass"'
    fi
fi

# 古いログファイルの削除（30日以上前）
find "$LOG_DIR" -name "sync_*.log" -mtime +30 -delete

echo "=====================================" >> "$LOG_FILE"
echo "実行完了: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

exit $SYNC_EXIT_CODE
WRAPPER_EOF

chmod +x "$PROJECT_DIR/scripts/run_daily_sync.sh"
echo "✅ 実行ラッパー作成完了: scripts/run_daily_sync.sh"

# 3. 手動テスト実行スクリプトの作成
echo -e "\n${GREEN}[3/5]${NC} テスト実行スクリプトを作成..."
cat > "$PROJECT_DIR/scripts/test_sync.sh" << 'TEST_EOF'
#!/bin/bash
# 同期テスト実行スクリプト

PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
echo "PDCAガーディアン ルール同期テスト実行"
echo "======================================"

# 同期スクリプトを実行
bash "$PROJECT_DIR/scripts/run_daily_sync.sh"

# 結果確認
if [ $? -eq 0 ]; then
    echo -e "\n✅ テスト成功！"
    echo "最新のログ："
    LATEST_LOG=$(ls -t $PROJECT_DIR/logs/cron/sync_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        tail -n 20 "$LATEST_LOG"
    fi
else
    echo -e "\n❌ テスト失敗"
    echo "エラーログを確認してください："
    LATEST_LOG=$(ls -t $PROJECT_DIR/logs/cron/sync_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        tail -n 50 "$LATEST_LOG"
    fi
fi
TEST_EOF

chmod +x "$PROJECT_DIR/scripts/test_sync.sh"
echo "✅ テストスクリプト作成完了: scripts/test_sync.sh"

# 4. Crontabエントリの準備
echo -e "\n${GREEN}[4/5]${NC} Crontabエントリを準備..."
CRON_ENTRY="0 3 * * * $PROJECT_DIR/scripts/run_daily_sync.sh"
CRON_FILE="$PROJECT_DIR/cron_entry.txt"

cat > "$CRON_FILE" << CRON_EOF
# PDCAガーディアン ルール同期システム
# 毎日午前3時に実行
$CRON_ENTRY

# 別の実行時間オプション：
# 毎日午前9時に実行
# 0 9 * * * $PROJECT_DIR/scripts/run_daily_sync.sh

# 平日のみ午前6時に実行
# 0 6 * * 1-5 $PROJECT_DIR/scripts/run_daily_sync.sh

# 6時間ごとに実行
# 0 */6 * * * $PROJECT_DIR/scripts/run_daily_sync.sh
CRON_EOF

echo "✅ Crontabエントリ準備完了: cron_entry.txt"

# 5. 現在のcrontabを確認
echo -e "\n${GREEN}[5/5]${NC} 現在のcrontab設定を確認..."
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

if echo "$CURRENT_CRON" | grep -q "rule_sync_system\|run_daily_sync"; then
    echo -e "${YELLOW}⚠️  既存の同期設定が検出されました${NC}"
    echo "既存のエントリ："
    echo "$CURRENT_CRON" | grep "rule_sync_system\|run_daily_sync"
else
    echo "✅ 既存の同期設定はありません"
fi

# インストール手順の表示
echo ""
echo "======================================"
echo "セットアップ完了！"
echo "======================================"
echo ""
echo "📝 インストール手順："
echo ""
echo "1. まずテスト実行して動作確認："
echo "   ${GREEN}bash $PROJECT_DIR/scripts/test_sync.sh${NC}"
echo ""
echo "2. 問題なければcrontabに追加："
echo "   ${GREEN}crontab -e${NC}"
echo ""
echo "3. 以下の行を追加（毎日午前3時に実行）："
echo "   ${YELLOW}$CRON_ENTRY${NC}"
echo ""
echo "4. または用意されたエントリを使用："
echo "   ${GREEN}crontab -l > temp_cron.txt${NC}"
echo "   ${GREEN}cat $CRON_FILE >> temp_cron.txt${NC}"
echo "   ${GREEN}crontab temp_cron.txt${NC}"
echo "   ${GREEN}rm temp_cron.txt${NC}"
echo ""
echo "📊 ログファイル："
echo "   - 実行ログ: $LOG_DIR/sync_*.log"
echo "   - サマリー: $LOG_DIR/sync_summary.log"
echo ""
echo "🔧 管理コマンド："
echo "   - 手動実行: bash $PROJECT_DIR/scripts/run_daily_sync.sh"
echo "   - テスト実行: bash $PROJECT_DIR/scripts/test_sync.sh"
echo "   - ログ確認: tail -f $LOG_DIR/sync_summary.log"
echo "   - Cron確認: crontab -l"
echo "   - Cron編集: crontab -e"
echo "   - Cron削除: crontab -r （注意：全削除）"
echo ""
echo "======================================"