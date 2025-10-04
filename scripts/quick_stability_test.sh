#!/bin/bash

# MCP管理システム - 5分間クイック安定性テスト（最適化版 v2.0）
# 2025年10月1日更新

set -e

TEST_DURATION=300  # 5分 = 300秒
CHECK_INTERVAL=30  # 30秒ごとにチェック
LOG_FILE="quick_stability_test_$(date +%Y%m%d_%H%M%S).log"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================" | tee -a "$LOG_FILE"
echo "📊 MCP管理システム - クイック安定性テスト" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📅 開始時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "⏱️ テスト時間: 5分間" | tee -a "$LOG_FILE"
echo "🔄 チェック間隔: 30秒" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# カウンター初期化
TOTAL_CHECKS=0
SERENA_FAILURES=0
CODEX_FAILURES=0
MEMORY_FAILURES=0
SEQUENTIAL_FAILURES=0

# 開始時刻を記録
START_TIME=$(date +%s)

# プロセス状態チェック関数
check_processes() {
    local timestamp=$(date '+%H:%M:%S')
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo "" | tee -a "$LOG_FILE"
    echo "[$timestamp] チェック #$TOTAL_CHECKS" | tee -a "$LOG_FILE"
    echo "----------------------------------------" | tee -a "$LOG_FILE"

    # Serena
    if pgrep -f "serena-mcp-server" > /dev/null 2>&1; then
        echo "  ✅ Serena: 稼働中" | tee -a "$LOG_FILE"
    else
        echo "  ❌ Serena: 停止" | tee -a "$LOG_FILE"
        SERENA_FAILURES=$((SERENA_FAILURES + 1))
    fi

    # Codex
    if pgrep -f "codex_mcp_server" > /dev/null 2>&1; then
        echo "  ✅ Codex: 稼働中" | tee -a "$LOG_FILE"
    else
        echo "  ❌ Codex: 停止" | tee -a "$LOG_FILE"
        CODEX_FAILURES=$((CODEX_FAILURES + 1))
    fi

    # Memory
    if pgrep -f "@modelcontextprotocol/server-memory" > /dev/null 2>&1; then
        echo "  ✅ Memory: 稼働中" | tee -a "$LOG_FILE"
    else
        echo "  ⚠️ Memory: 停止（NPXサーバー）" | tee -a "$LOG_FILE"
        MEMORY_FAILURES=$((MEMORY_FAILURES + 1))
    fi

    # Sequential Thinking
    if pgrep -f "@modelcontextprotocol/server-sequential-thinking" > /dev/null 2>&1; then
        echo "  ✅ Sequential: 稼働中" | tee -a "$LOG_FILE"
    else
        echo "  ⚠️ Sequential: 停止（NPXサーバー）" | tee -a "$LOG_FILE"
        SEQUENTIAL_FAILURES=$((SEQUENTIAL_FAILURES + 1))
    fi

    # ポート状態
    echo "" | tee -a "$LOG_FILE"
    echo "  ポート状態:" | tee -a "$LOG_FILE"
    if lsof -i:8000 > /dev/null 2>&1; then
        echo "    • Port 8000 (Serena): ✅ 使用中" | tee -a "$LOG_FILE"
    fi

    if lsof -i:8765 > /dev/null 2>&1; then
        echo "    • Port 8765 (Codex): ✅ 使用中" | tee -a "$LOG_FILE"
    fi
}

# メインループ
echo "" | tee -a "$LOG_FILE"
echo "🔄 安定性テスト開始..." | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    # 5分経過したら終了
    if [ $ELAPSED -ge $TEST_DURATION ]; then
        break
    fi

    # 残り時間を計算
    REMAINING=$((TEST_DURATION - ELAPSED))
    MINUTES=$((REMAINING / 60))
    SECONDS=$((REMAINING % 60))

    # ステータスチェック
    check_processes

    echo "" | tee -a "$LOG_FILE"
    echo "  ⏳ 残り時間: ${MINUTES}分${SECONDS}秒" | tee -a "$LOG_FILE"

    # 次のチェックまで待機
    sleep $CHECK_INTERVAL
done

# 最終レポート生成
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "📊 安定性テスト結果" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📅 終了時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "⏱️ テスト時間: 5分間" | tee -a "$LOG_FILE"
echo "🔍 総チェック回数: $TOTAL_CHECKS" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📈 稼働率統計:" | tee -a "$LOG_FILE"

# 稼働率計算
if [ $TOTAL_CHECKS -gt 0 ]; then
    SERENA_UPTIME=$((100 * (TOTAL_CHECKS - SERENA_FAILURES) / TOTAL_CHECKS))
    CODEX_UPTIME=$((100 * (TOTAL_CHECKS - CODEX_FAILURES) / TOTAL_CHECKS))
    MEMORY_UPTIME=$((100 * (TOTAL_CHECKS - MEMORY_FAILURES) / TOTAL_CHECKS))
    SEQUENTIAL_UPTIME=$((100 * (TOTAL_CHECKS - SEQUENTIAL_FAILURES) / TOTAL_CHECKS))

    echo "  • Serena: ${SERENA_UPTIME}% (失敗: $SERENA_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
    echo "  • Codex: ${CODEX_UPTIME}% (失敗: $CODEX_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
    echo "  • Memory: ${MEMORY_UPTIME}% (失敗: $MEMORY_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
    echo "  • Sequential: ${SEQUENTIAL_UPTIME}% (失敗: $SEQUENTIAL_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

# 総合評価
TOTAL_FAILURES=$((SERENA_FAILURES + CODEX_FAILURES))
if [ $TOTAL_FAILURES -eq 0 ]; then
    echo "✅ 結果: 主要サーバー安定 - Serena/Codexが5分間正常稼働" | tee -a "$LOG_FILE"
else
    echo "⚠️ 結果: 一部不安定 - 詳細ログ確認推奨" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "📝 詳細ログは $LOG_FILE に保存されました" | tee -a "$LOG_FILE"