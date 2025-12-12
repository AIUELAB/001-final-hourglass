#!/bin/bash
# =============================================================================
# 週次人物名品質チェック
#
# 目的: グループ名+個人名の混入パターンを検出・修正
# 実行タイミング: 毎週月曜日 10:30 (crontab)
# =============================================================================

set -e

# 環境設定
PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
LOG_DIR="${PROJECT_DIR}/logs/name_quality"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/weekly_check_${TIMESTAMP}.log"

# ログディレクトリ確保
mkdir -p "${LOG_DIR}"

# 実行開始
echo "========================================" >> "${LOG_FILE}"
echo "週次人物名品質チェック - ${TIMESTAMP}" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

cd "${PROJECT_DIR}"

# Step 1: ドライラン（検出のみ）
echo "[$(date +%H:%M:%S)] ドライラン実行中..." >> "${LOG_FILE}"
DRYRUN_RESULT=$("${VENV_PYTHON}" scripts/fix_person_group_name_contamination.py --dry-run 2>&1)
echo "${DRYRUN_RESULT}" >> "${LOG_FILE}"

# 問題件数を抽出
ISSUE_COUNT=$(echo "${DRYRUN_RESULT}" | grep -o "検出された問題: [0-9]*件" | grep -o "[0-9]*" || echo "0")

# Step 2: 問題があれば自動修正
if [ "${ISSUE_COUNT}" -gt "0" ]; then
    echo "" >> "${LOG_FILE}"
    echo "[$(date +%H:%M:%S)] ${ISSUE_COUNT}件の問題を検出。自動修正実行中..." >> "${LOG_FILE}"
    "${VENV_PYTHON}" scripts/fix_person_group_name_contamination.py --execute >> "${LOG_FILE}" 2>&1
    echo "[$(date +%H:%M:%S)] 修正完了" >> "${LOG_FILE}"
else
    echo "" >> "${LOG_FILE}"
    echo "[$(date +%H:%M:%S)] 問題なし - 修正不要" >> "${LOG_FILE}"
fi

# Step 3: サマリー
echo "" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"
echo "完了: $(date)" >> "${LOG_FILE}"
echo "検出件数: ${ISSUE_COUNT}" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

# 古いログを削除（30日以上）
find "${LOG_DIR}" -name "weekly_check_*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
