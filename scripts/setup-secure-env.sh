#!/bin/bash

# ===============================================
# 🔒 Ultra Think セキュリティ環境設定スクリプト
# ===============================================
# 環境変数を安全に設定し、認証情報を保護します

set -e  # エラー時に停止

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔒 Ultra Think セキュリティ環境設定            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

# プロジェクトディレクトリ
PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
cd "$PROJECT_DIR"

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .envファイルが存在しません。テンプレートから作成します...${NC}"
    cp .env.example .env 2>/dev/null || touch .env
fi

# 環境変数の設定関数
set_env_var() {
    local var_name=$1
    local var_value=$2
    local description=$3

    if [ -z "$var_value" ] || [ "$var_value" = "your_*" ]; then
        echo -e "${YELLOW}⚠️ $description ($var_name) が未設定です${NC}"
        return 1
    else
        export "$var_name=$var_value"
        echo -e "${GREEN}✅ $description 設定完了${NC}"
        return 0
    fi
}

# .envファイルの読み込み
echo -e "\n${BLUE}📋 環境変数を読み込み中...${NC}"
source .env 2>/dev/null || true

# 必須環境変数の設定
echo -e "\n${BLUE}🔐 必須環境変数の設定:${NC}"

# Google認証
if [ -f "$PROJECT_DIR/key/credentials.json" ]; then
    set_env_var "GOOGLE_APPLICATION_CREDENTIALS" \
                "$PROJECT_DIR/key/credentials.json" \
                "Google認証情報"
else
    echo -e "${RED}❌ Google認証ファイルが見つかりません${NC}"
fi

# GitHub Token（.env.mcpからも試す）
if [ -z "$GITHUB_TOKEN" ] && [ -f ".env.mcp" ]; then
    GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" .env.mcp | cut -d'=' -f2)
fi
set_env_var "GITHUB_TOKEN" "$GITHUB_TOKEN" "GitHub Token"

# API Keys
set_env_var "OPENAI_API_KEY" "$OPENAI_API_KEY" "OpenAI API Key"
set_env_var "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY" "Anthropic API Key"
set_env_var "YOUTUBE_API_KEY" "$YOUTUBE_API_KEY" "YouTube API Key"
set_env_var "BRAVE_API_KEY" "$BRAVE_API_KEY" "Brave Search API Key"

# Firebase設定
if [ -f "/Users/admin/Documents/key/final-hourglass-claude-firebase-adminsdk-fbsvc-61b72fdd53.json" ]; then
    set_env_var "FIREBASE_CONFIG_PATH" \
                "/Users/admin/Documents/key/final-hourglass-claude-firebase-adminsdk-fbsvc-61b72fdd53.json" \
                "Firebase設定"
fi

# セキュリティチェック
echo -e "\n${BLUE}🛡️ セキュリティチェック:${NC}"

# .gitignore確認
if grep -q "key/" .gitignore && grep -q ".env" .gitignore; then
    echo -e "${GREEN}✅ .gitignore: 認証情報は保護されています${NC}"
else
    echo -e "${YELLOW}⚠️ .gitignore: 認証情報の保護を確認してください${NC}"
fi

# secure_config.py確認
if [ -f "src/secure_config.py" ]; then
    echo -e "${GREEN}✅ セキュア設定クラス: 実装済み${NC}"
else
    echo -e "${YELLOW}⚠️ セキュア設定クラス: 未実装${NC}"
fi

# 環境変数のサマリー
echo -e "\n${BLUE}📊 環境変数設定サマリー:${NC}"
echo "================================"

# チェック関数
check_var() {
    local var_name=$1
    local var_value="${!var_name}"
    if [ -n "$var_value" ] && [ "$var_value" != "your_"* ]; then
        echo -e "${GREEN}✅${NC} $var_name: 設定済み"
        return 0
    else
        echo -e "${RED}❌${NC} $var_name: 未設定"
        return 1
    fi
}

# 各環境変数をチェック
total=0
configured=0

for var in GOOGLE_APPLICATION_CREDENTIALS GITHUB_TOKEN OPENAI_API_KEY \
           ANTHROPIC_API_KEY YOUTUBE_API_KEY BRAVE_API_KEY FIREBASE_CONFIG_PATH; do
    ((total++))
    if check_var "$var"; then
        ((configured++))
    fi
done

# スコア計算
score=$((configured * 100 / total))
echo "================================"
echo -e "${BLUE}セキュリティスコア: ${configured}/${total} (${score}%)${NC}"

if [ $score -ge 80 ]; then
    echo -e "${GREEN}✅ Production Ready${NC}"
elif [ $score -ge 60 ]; then
    echo -e "${YELLOW}⚠️ 部分的に設定済み - 追加設定推奨${NC}"
else
    echo -e "${RED}❌ セキュリティリスク - 環境変数の設定が必要${NC}"
fi

# シェル設定への永続化オプション
echo -e "\n${BLUE}💡 永続化オプション:${NC}"
echo "以下を ~/.zshrc または ~/.bashrc に追加することで永続化できます:"
echo ""
echo "# Ultra Think Environment Variables"
echo "export GOOGLE_APPLICATION_CREDENTIALS=\"$GOOGLE_APPLICATION_CREDENTIALS\""
echo "export FIREBASE_CONFIG_PATH=\"$FIREBASE_CONFIG_PATH\""
echo ""

# 完了メッセージ
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ セキュリティ環境設定スクリプト完了          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"

# 環境変数をエクスポート（現在のシェルセッション用）
export GOOGLE_APPLICATION_CREDENTIALS
export GITHUB_TOKEN
export OPENAI_API_KEY
export ANTHROPIC_API_KEY
export YOUTUBE_API_KEY
export BRAVE_API_KEY
export FIREBASE_CONFIG_PATH
