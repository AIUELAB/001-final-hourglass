#!/bin/bash
#
# EPUP品質修正・検証・Supabase同期 統合スクリプト
#
# 用途: 修正→検証→Supabase同期を1コマンドで実行
#
# 使用方法:
#   ./scripts/epup_quality_fix_and_sync.sh          # dry-run（確認のみ）
#   ./scripts/epup_quality_fix_and_sync.sh --execute # 実際に修正・同期を実行
#
# フェーズA運用化: 2026-01-23
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ヘルプ表示
show_help() {
    cat << EOF
╔══════════════════════════════════════════════════════════════════╗
║      EPUP品質修正・検証・Supabase同期 統合スクリプト             ║
╚══════════════════════════════════════════════════════════════════╝

使用方法:
  $0              dry-run（確認のみ、変更なし）
  $0 --execute    実際に修正・同期を実行
  $0 --help       このヘルプを表示

処理フロー:
  1. 文章品質チェック（text_quality_dryrun_v2.py）
  2. [--execute時] 自動修正（fix_text_quality.py）
  3. 修正後の再検証
  4. [--execute時] Supabase同期（migrate_csv_to_supabase.py）
  5. 件数確認

EOF
}

# メイン処理
main() {
    local execute_mode=false

    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --execute)
                execute_mode=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "不明な引数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    cd "$PROJECT_ROOT"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║      EPUP品質修正・検証・Supabase同期                            ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    if [ "$execute_mode" = true ]; then
        log_warn "実行モード: 変更が適用されます"
    else
        log_info "dry-runモード: 変更は適用されません"
    fi
    echo ""

    # ステップ1: 文章品質チェック
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "ステップ1: 文章品質チェック"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    output=$(python scripts/validation/text_quality_dryrun_v2.py 2>&1)
    echo "$output"

    # 合計件数を抽出
    total=$(echo "$output" | grep "合計:" | sed 's/.*合計: \([0-9]*\)件.*/\1/')

    if [ -z "$total" ]; then
        total=0
    fi

    echo ""
    if [ "$total" = "0" ]; then
        log_success "文章品質チェック通過: 違反0件"
    else
        log_warn "文章品質違反: ${total}件検出"
    fi
    echo ""

    # ステップ2: 自動修正（execute モードのみ）
    if [ "$execute_mode" = true ] && [ "$total" != "0" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "ステップ2: 自動修正実行"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        python scripts/fix/fix_text_quality.py --execute
        echo ""

        # 修正後の再検証
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "ステップ3: 修正後の再検証"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        output=$(python scripts/validation/text_quality_dryrun_v2.py 2>&1)
        echo "$output"

        total_after=$(echo "$output" | grep "合計:" | sed 's/.*合計: \([0-9]*\)件.*/\1/')

        echo ""
        if [ "$total_after" = "0" ]; then
            log_success "修正後検証通過: 違反0件"
        else
            log_error "修正後も違反が残存: ${total_after}件"
            exit 1
        fi
        echo ""
    fi

    # ステップ4: Supabase同期（execute モードのみ）
    if [ "$execute_mode" = true ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "ステップ4: Supabase同期"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # dry-runで件数確認
        log_info "同期前の件数確認（dry-run）..."
        python scripts/supabase/migrate_csv_to_supabase.py --dry-run 2>&1 | head -20

        echo ""
        read -p "Supabase同期を実行しますか？ (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            log_info "Supabase同期を実行中..."
            python scripts/supabase/migrate_csv_to_supabase.py
            log_success "Supabase同期完了"
        else
            log_warn "Supabase同期をスキップしました"
        fi
        echo ""
    fi

    # 完了
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ "$execute_mode" = true ]; then
        log_success "全処理完了（実行モード）"
    else
        log_success "全処理完了（dry-runモード）"
        echo ""
        log_info "実際に修正・同期するには: $0 --execute"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main "$@"
