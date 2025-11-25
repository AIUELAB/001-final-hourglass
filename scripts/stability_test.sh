#!/bin/bash

# MCP管理システム - 30分間安定性テスト
# 実行時刻: $(date '+%Y-%m-%d %H:%M:%S')

set -e

TEST_DURATION=1800  # 30分 = 1800秒
CHECK_INTERVAL=60   # 60秒ごとにチェック
LOG_FILE="stability_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================" | tee -a "$LOG_FILE"
echo "📊 MCP管理システム - 長期安定性テスト" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📅 開始時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "⏱️ テスト時間: 30分間" | tee -a "$LOG_FILE"
echo "🔄 チェック間隔: 60秒" | tee -a "$LOG_FILE"
echo "📝 ログファイル: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# カウンター初期化
TOTAL_CHECKS=0
SERENA_FAILURES=0
CODEX_FAILURES=0
MEMORY_FAILURES=0
SEQUENTIAL_FAILURES=0
RESTARTS=0

# 開始時刻を記録
START_TIME=$(date +%s)

# 初期状態を記録
echo "🚀 初期状態確認..." | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"

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
        echo "  ❌ Memory: 停止" | tee -a "$LOG_FILE"
        MEMORY_FAILURES=$((MEMORY_FAILURES + 1))
    fi

    # Sequential Thinking
    if pgrep -f "@modelcontextprotocol/server-sequential-thinking" > /dev/null 2>&1; then
        echo "  ✅ Sequential: 稼働中" | tee -a "$LOG_FILE"
    else
        echo "  ❌ Sequential: 停止" | tee -a "$LOG_FILE"
        SEQUENTIAL_FAILURES=$((SEQUENTIAL_FAILURES + 1))
    fi

    # ポート状態
    echo "" | tee -a "$LOG_FILE"
    echo "  ポート状態:" | tee -a "$LOG_FILE"
    if lsof -i:8000 > /dev/null 2>&1; then
        echo "    • Port 8000 (Serena): 使用中" | tee -a "$LOG_FILE"
    else
        echo "    • Port 8000 (Serena): 未使用" | tee -a "$LOG_FILE"
    fi

    if lsof -i:8765 > /dev/null 2>&1; then
        echo "    • Port 8765 (Codex): 使用中" | tee -a "$LOG_FILE"
    else
        echo "    • Port 8765 (Codex): 未使用" | tee -a "$LOG_FILE"
    fi

    # メモリ使用量
    echo "" | tee -a "$LOG_FILE"
    echo "  システム状態:" | tee -a "$LOG_FILE"
    echo "    • メモリ使用量: $(ps aux | grep -E 'mcp|serena|codex' | grep -v grep | awk '{sum+=$4} END {printf "%.1f%%", sum}')" | tee -a "$LOG_FILE"
    echo "    • CPU使用量: $(ps aux | grep -E 'mcp|serena|codex' | grep -v grep | awk '{sum+=$3} END {printf "%.1f%%", sum}')" | tee -a "$LOG_FILE"
}

# ヘルスチェック関数
health_check() {
    local timestamp=$(date '+%H:%M:%S')

    echo "" | tee -a "$LOG_FILE"
    echo "  ヘルスチェック:" | tee -a "$LOG_FILE"

    # Codex health check
    if curl -s http://localhost:8765/health > /dev/null 2>&1; then
        echo "    • Codex API: 応答あり" | tee -a "$LOG_FILE"
    else
        echo "    • Codex API: 応答なし" | tee -a "$LOG_FILE"
    fi

    # Serena dashboard check
    if curl -s http://127.0.0.1:24282/dashboard/index.html > /dev/null 2>&1; then
        echo "    • Serena Dashboard: アクセス可能" | tee -a "$LOG_FILE"
    else
        echo "    • Serena Dashboard: アクセス不可" | tee -a "$LOG_FILE"
    fi
}

# メインループ
echo "" | tee -a "$LOG_FILE"
echo "🔄 安定性テスト開始..." | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    # 30分経過したら終了
    if [ $ELAPSED -ge $TEST_DURATION ]; then
        break
    fi

    # 残り時間を計算
    REMAINING=$((TEST_DURATION - ELAPSED))
    MINUTES=$((REMAINING / 60))
    SECONDS=$((REMAINING % 60))

    # ステータスチェック
    check_processes

    # 5分ごとにヘルスチェック
    if [ $((TOTAL_CHECKS % 5)) -eq 0 ]; then
        health_check
    fi

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
echo "⏱️ テスト時間: 30分間" | tee -a "$LOG_FILE"
echo "🔍 総チェック回数: $TOTAL_CHECKS" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📈 稼働率統計:" | tee -a "$LOG_FILE"

# 稼働率計算
calculate_uptime() {
    local failures=$1
    local uptime=$(echo "scale=2; (($TOTAL_CHECKS - $failures) * 100) / $TOTAL_CHECKS" | bc)
    echo "$uptime"
}

SERENA_UPTIME=$(calculate_uptime $SERENA_FAILURES)
CODEX_UPTIME=$(calculate_uptime $CODEX_FAILURES)
MEMORY_UPTIME=$(calculate_uptime $MEMORY_FAILURES)
SEQUENTIAL_UPTIME=$(calculate_uptime $SEQUENTIAL_FAILURES)

echo "  • Serena: ${SERENA_UPTIME}% (失敗: $SERENA_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
echo "  • Codex: ${CODEX_UPTIME}% (失敗: $CODEX_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
echo "  • Memory: ${MEMORY_UPTIME}% (失敗: $MEMORY_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
echo "  • Sequential: ${SEQUENTIAL_UPTIME}% (失敗: $SEQUENTIAL_FAILURES/$TOTAL_CHECKS)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 総合評価
TOTAL_FAILURES=$((SERENA_FAILURES + CODEX_FAILURES + MEMORY_FAILURES + SEQUENTIAL_FAILURES))
if [ $TOTAL_FAILURES -eq 0 ]; then
    echo "✅ 結果: 完全安定 - すべてのサーバーが30分間正常稼働" | tee -a "$LOG_FILE"
elif [ $TOTAL_FAILURES -le 2 ]; then
    echo "⚠️ 結果: 概ね安定 - 軽微な問題あり" | tee -a "$LOG_FILE"
else
    echo "❌ 結果: 不安定 - 改善が必要" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "📝 詳細ログは $LOG_FILE に保存されました" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
