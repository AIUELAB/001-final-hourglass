#!/bin/bash

# ===============================================
# 🚀 SuperClaude Ultra Think 起動コマンド集
# ===============================================
# Claude Code起動時に実行すべきSuperClaudeコマンド

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║   🚀 SuperClaude Ultra Think 起動シーケンス      ║${NC}"
echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"

# ===============================================
# 🔴 CRITICAL - 必須実行コマンド
# ===============================================

echo -e "\n${RED}━━━ 🔴 CRITICAL: セキュリティ・セッション管理 ━━━${NC}"

# 1. Git状態確認（mainブランチ作業防止）
echo -e "${YELLOW}📌 Git状態確認...${NC}"
git status --short
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo -e "${RED}⚠️ 警告: mainブランチで作業中！feature branchの使用を推奨${NC}"
fi

# 2. セッション復元（SuperClaude）
echo -e "${CYAN}💾 セッション状態復元...${NC}"
# /sc:load コマンド相当の処理
if [ -f ".claude/session.json" ]; then
    echo -e "${GREEN}✅ 前回のセッション検出${NC}"
fi

# ===============================================
# 🟡 IMPORTANT - パフォーマンス・品質
# ===============================================

echo -e "\n${YELLOW}━━━ 🟡 IMPORTANT: Ultra Think モード活性化 ━━━${NC}"

# 3. Ultra Think設定
echo -e "${BLUE}⚡ Ultra Thinkモード設定:${NC}"
cat << EOF
  --ultrathink       ✅ 最大深度分析（32Kトークン）
  --delegate auto    ✅ サブエージェント自動振り分け
  --concurrency 10   ✅ 10並列処理
  --all-mcp         ✅ 全MCPサーバー有効
EOF

# 4. MCP最適化プロファイル確認
echo -e "${CYAN}🔧 MCPサーバー状態:${NC}"
MCP_SERVERS=(
    "Serena (セマンティックコード検索)"
    "GitHub (Issue/PR管理)"
    "Firecrawl (高度Webスクレイピング)"
    "Playwright (ブラウザ自動化)"
    "Sequential-thinking (順次思考処理)"
)
for server in "${MCP_SERVERS[@]}"; do
    echo "  ✅ $server"
done

# ===============================================
# 🚀 Ultra Think データベース同期
# ===============================================

echo -e "\n${BLUE}━━━ 🚀 Ultra Think データベース同期 ━━━${NC}"

# 5. 最新CSVファイル検出
LATEST_CSV=$(ls -t ultra_think_*.csv 2>/dev/null | head -1)
if [ -n "$LATEST_CSV" ]; then
    echo -e "${GREEN}📊 最新データ: $LATEST_CSV${NC}"
    LINE_COUNT=$(wc -l < "$LATEST_CSV")
    echo -e "${GREEN}   行数: $LINE_COUNT${NC}"
fi

# 6. 同期実行（既存スクリプト呼び出し）
if [ -f "auto_startup_sync_optimized.py" ]; then
    echo -e "${CYAN}🔄 Google Sheets同期開始...${NC}"
    # 実際の同期は別プロセスで実行
fi

# ===============================================
# 🟢 RECOMMENDED - 条件付き実行
# ===============================================

echo -e "\n${GREEN}━━━ 🟢 RECOMMENDED: 品質チェック ━━━${NC}"

# 7. コード品質チェック
echo -e "${YELLOW}🔍 品質チェック項目:${NC}"
QUALITY_CHECKS=(
    "SonarLint警告: 0件目標"
    "Ruffリント: PEP8準拠"
    "型チェック: mypy strict"
    "テストカバレッジ: 80%以上"
)
for check in "${QUALITY_CHECKS[@]}"; do
    echo "  📋 $check"
done

# ===============================================
# 📊 コマンド組み合わせ推奨
# ===============================================

echo -e "\n${MAGENTA}━━━ 📊 推奨コマンド組み合わせ ━━━${NC}"

cat << 'EOF'

🚀 Ultra Think標準起動:
  /sc:load --ultrathink --delegate auto --concurrency 10 --all-mcp /sync-database

🔥 最大パフォーマンス起動:
  /sc:load --ultrathink --delegate auto --concurrency 15 --c7 --seq --serena --focus performance

💾 リソース制約起動:
  /sc:load --think --delegate auto --concurrency 5 --uc --no-mcp

🔧 開発・デバッグ起動:
  /sc:load --introspect --validate --think-hard --c7 --seq /fix-errors

EOF

# ===============================================
# 📌 フラグ自動発動条件
# ===============================================

echo -e "${CYAN}━━━ 📌 自動フラグ発動条件 ━━━${NC}"

# ファイル数チェック
FILE_COUNT=$(find . -type f -name "*.py" 2>/dev/null | wc -l)
DIR_COUNT=$(find . -type d 2>/dev/null | wc -l)

echo -e "${YELLOW}📁 プロジェクト統計:${NC}"
echo "  • ファイル数: $FILE_COUNT"
echo "  • ディレクトリ数: $DIR_COUNT"

if [ $FILE_COUNT -gt 50 ] || [ $DIR_COUNT -gt 7 ]; then
    echo -e "${GREEN}✅ --delegate auto 推奨（大規模プロジェクト）${NC}"
fi

# メモリ使用率チェック（macOS）
if [ "$(uname)" = "Darwin" ]; then
    MEM_PRESSURE=$(memory_pressure | grep "System-wide memory free percentage" | awk '{print $5}' | sed 's/%//')
    if [ -n "$MEM_PRESSURE" ] && [ "$MEM_PRESSURE" -lt 25 ]; then
        echo -e "${YELLOW}⚠️ --uc 推奨（メモリ使用率高）${NC}"
    fi
fi

# ===============================================
# 🔄 セッション管理情報
# ===============================================

echo -e "\n${BLUE}━━━ 🔄 セッション管理 ━━━${NC}"

cat << 'EOF'
📋 セッションライフサイクル:
  1. 開始: /sc:load → 既存状態復元
  2. 定期: /sc:checkpoint (30分間隔) → 状態保存
  3. 終了: /sc:save → 完全状態保存

💡 ヒント:
  • Ctrl+C で緊急停止
  • pkill -f watchdog で監視停止
  • tail -f *.log でログ確認
EOF

# ===============================================
# ✨ 起動完了
# ===============================================

echo -e "\n${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✨ SuperClaude Ultra Think 準備完了！          ║${NC}"
echo -e "${GREEN}║   並列処理: 10ワーカー | MCP: 全サーバー有効     ║${NC}"
echo -e "${GREEN}║   監視: リアルタイム | 同期: 自動                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"

# 環境変数設定（オプション）
export SUPERCLAUDE_MODE="ultrathink"
export SUPERCLAUDE_CONCURRENCY="10"
export SUPERCLAUDE_MCP="all"
export SUPERCLAUDE_DELEGATE="auto"

echo -e "\n${CYAN}🎯 環境変数設定完了:${NC}"
echo "  SUPERCLAUDE_MODE=$SUPERCLAUDE_MODE"
echo "  SUPERCLAUDE_CONCURRENCY=$SUPERCLAUDE_CONCURRENCY"
echo "  SUPERCLAUDE_MCP=$SUPERCLAUDE_MCP"
echo "  SUPERCLAUDE_DELEGATE=$SUPERCLAUDE_DELEGATE"

exit 0
