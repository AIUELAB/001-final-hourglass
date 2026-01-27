#!/bin/bash
# Phase 32: iOS Required Status Checks を main ブランチに追加
# Usage: ./configure-branch-protection.sh [--dry-run]
set -euo pipefail

REPO="AIUELAB/001-final-hourglass"
BRANCH="main"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# 追加するiOSチェック（quality-gate.yml のジョブ名）
IOS_CHECKS=(
  "SwiftLint"
  "Periphery (Dead Code Detection)"
  "Build"
  "Privacy Manifest Audit"
)

# 既存チェック（保持）
EXISTING_CHECKS=(
  "Code Quality"
  "Unit Tests (Python 3.11)"
  "Unit Tests (Python 3.12)"
)

# JSON構築
ALL_CHECKS=("${EXISTING_CHECKS[@]}" "${IOS_CHECKS[@]}")
CHECKS_JSON=$(printf '%s\n' "${ALL_CHECKS[@]}" | jq -R '{"context": ., "app_id": 15368}' | jq -s '.')

PAYLOAD=$(jq -n \
  --argjson checks "$CHECKS_JSON" \
  '{
    required_status_checks: {strict: true, checks: $checks},
    enforce_admins: true,
    required_pull_request_reviews: null,
    restrictions: null
  }')

echo "=== Required Status Checks ==="
printf '%s\n' "${ALL_CHECKS[@]}" | nl
echo ""

if $DRY_RUN; then
  echo "[DRY-RUN] 以下のペイロードを適用予定:"
  echo "$PAYLOAD" | jq .
  exit 0
fi

gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
  --input - <<< "$PAYLOAD"

echo "✅ Branch protection updated (${#ALL_CHECKS[@]} required checks)"

# 検証
echo ""
echo "=== 検証 ==="
gh api "repos/$REPO/branches/$BRANCH/protection/required_status_checks" \
  -q '.checks[].context' | nl
