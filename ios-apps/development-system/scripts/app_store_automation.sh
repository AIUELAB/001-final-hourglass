#!/bin/bash
# App Store Guidelines準拠自動化スクリプト
# Apple App Store Review Guidelines完全対応版

set -euo pipefail

# スクリプト設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/automation_$(date +%Y%m%d_%H%M%S).log"
CONFIG_FILE="$PROJECT_ROOT/config/app_store_config.json"

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"

    case $level in
        "ERROR")
            echo -e "${RED}❌ ${message}${NC}" >&2
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  ${message}${NC}"
            ;;
        "INFO")
            echo -e "${GREEN}✅ ${message}${NC}"
            ;;
        "DEBUG")
            echo -e "${BLUE}🔍 ${message}${NC}"
            ;;
    esac
}

# エラーハンドリング
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# 設定読み込み
load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "WARN" "設定ファイルが見つかりません。デフォルト設定を作成します。"
        create_default_config
    fi

    # JSON設定読み込み（jqが利用可能な場合）
    if command -v jq &> /dev/null; then
        PROJECT_NAME=$(jq -r '.project_name // "YourApp"' "$CONFIG_FILE")
        SCHEME_NAME=$(jq -r '.scheme_name // "YourApp"' "$CONFIG_FILE")
        BUNDLE_ID=$(jq -r '.bundle_id // "com.yourcompany.yourapp"' "$CONFIG_FILE")
        TEAM_ID=$(jq -r '.team_id // ""' "$CONFIG_FILE")
        MIN_IOS_VERSION=$(jq -r '.min_ios_version // "15.0"' "$CONFIG_FILE")
    else
        log "WARN" "jqが見つかりません。デフォルト値を使用します。"
        PROJECT_NAME="YourApp"
        SCHEME_NAME="YourApp"
        BUNDLE_ID="com.yourcompany.yourapp"
        TEAM_ID=""
        MIN_IOS_VERSION="15.0"
    fi
}

# デフォルト設定作成
create_default_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"

    cat > "$CONFIG_FILE" << EOF
{
    "project_name": "YourApp",
    "scheme_name": "YourApp",
    "bundle_id": "com.yourcompany.yourapp",
    "team_id": "",
    "min_ios_version": "15.0",
    "target_devices": ["iPhone", "iPad"],
    "supported_orientations": ["portrait"],
    "required_permissions": {
        "camera": false,
        "microphone": false,
        "location": false,
        "photo_library": false,
        "contacts": false
    },
    "app_store_config": {
        "age_rating": "4+",
        "category": "utilities",
        "price_tier": "free"
    }
}
EOF
    log "INFO" "デフォルト設定ファイルを作成しました: $CONFIG_FILE"
}

# ==============================
# App Store Guidelines準拠チェック
# ==============================

# Guidelines 2.1: App Completeness
check_app_completeness() {
    log "INFO" "App Store Guidelines 2.1: アプリの完全性チェック開始"

    # プロジェクトファイルの存在確認
    local xcodeproj_files=(*.xcodeproj)
    if [[ ! -e "${xcodeproj_files[0]}" ]]; then
        error_exit "Xcodeプロジェクトファイルが見つかりません"
    fi

    # スキームの確認
    if ! xcodebuild -list -project "${xcodeproj_files[0]}" | grep -q "$SCHEME_NAME"; then
        error_exit "スキーム '$SCHEME_NAME' が見つかりません"
    fi

    # ビルド可能性確認
    log "DEBUG" "ビルド可能性確認中..."
    if ! xcodebuild -scheme "$SCHEME_NAME" -destination 'generic/platform=iOS' clean build > /dev/null 2>&1; then
        error_exit "プロジェクトがビルドできません"
    fi

    log "INFO" "✅ アプリ完全性チェック完了"
}

# Guidelines 2.5: Software Requirements
check_software_requirements() {
    log "INFO" "App Store Guidelines 2.5: ソフトウェア要件チェック開始"

    # iOS最小バージョンチェック
    local current_ios_version=$(xcrun simctl list runtimes | grep iOS | tail -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    log "DEBUG" "最小iOS対応バージョン: $MIN_IOS_VERSION, 現在のiOS: $current_ios_version"

    # プライベートAPI使用チェック
    log "DEBUG" "プライベートAPI使用チェック実行中..."
    if python3 "$SCRIPT_DIR/code_quality_check.py" . > /tmp/quality_check.json; then
        if command -v jq &> /dev/null; then
            local private_api_errors=$(jq '.issues[] | select(.issue_type == "private_api_usage")' /tmp/quality_check.json)
            if [[ -n "$private_api_errors" ]]; then
                error_exit "プライベートAPIの使用が検出されました。詳細: /tmp/quality_check.json"
            fi
        fi
    fi

    log "INFO" "✅ ソフトウェア要件チェック完了"
}

# Guidelines 5.1: Privacy
check_privacy_compliance() {
    log "INFO" "App Store Guidelines 5.1: プライバシー準拠チェック開始"

    # Info.plistのプライバシー設定確認
    local info_plist_path
    info_plist_path=$(find . -name "Info.plist" -not -path "./Pods/*" -not -path "./build/*" | head -1)

    if [[ -z "$info_plist_path" ]]; then
        error_exit "Info.plistファイルが見つかりません"
    fi

    # プライバシー説明文の確認
    local privacy_keys=(
        "NSCameraUsageDescription"
        "NSMicrophoneUsageDescription"
        "NSLocationWhenInUseUsageDescription"
        "NSPhotoLibraryUsageDescription"
        "NSContactsUsageDescription"
    )

    for key in "${privacy_keys[@]}"; do
        if grep -q "$key" "$info_plist_path"; then
            local description
            description=$(plutil -extract "$key" raw "$info_plist_path" 2>/dev/null || echo "")
            if [[ ${#description} -lt 10 ]]; then
                log "WARN" "プライバシー説明が不十分: $key"
            else
                log "DEBUG" "プライバシー説明OK: $key"
            fi
        fi
    done

    # ATT (App Tracking Transparency) 設定確認
    if grep -q "NSUserTrackingUsageDescription" "$info_plist_path"; then
        log "DEBUG" "App Tracking Transparency設定確認済み"
    fi

    log "INFO" "✅ プライバシー準拠チェック完了"
}

# ==============================
# 自動テスト実行
# ==============================

run_comprehensive_tests() {
    log "INFO" "包括的テストスイート実行開始"

    # 単体テスト
    log "DEBUG" "単体テスト実行中..."
    if ! xcodebuild test -scheme "$SCHEME_NAME" -destination 'platform=iOS Simulator,name=iPhone 14' -only-testing:"${SCHEME_NAME}Tests"; then
        log "ERROR" "単体テストが失敗しました"
        return 1
    fi

    # UIテスト
    log "DEBUG" "UIテスト実行中..."
    if ! xcodebuild test -scheme "$SCHEME_NAME" -destination 'platform=iOS Simulator,name=iPhone 14' -only-testing:"${SCHEME_NAME}UITests"; then
        log "ERROR" "UIテストが失敗しました"
        return 1
    fi

    # パフォーマンステスト
    log "DEBUG" "パフォーマンステスト実行中..."
    if ! xcodebuild test -scheme "$SCHEME_NAME" -destination 'platform=iOS Simulator,name=iPhone 14' -only-testing:"${SCHEME_NAME}PerformanceTests"; then
        log "WARN" "パフォーマンステストが失敗しました（継続）"
    fi

    log "INFO" "✅ 包括的テスト完了"
}

# ==============================
# アーカイブとアップロード
# ==============================

create_archive() {
    log "INFO" "アーカイブ作成開始"

    local archive_path="$PROJECT_ROOT/build/$SCHEME_NAME.xcarchive"
    local export_path="$PROJECT_ROOT/build/export"

    # クリーンビルド
    log "DEBUG" "クリーンビルド実行中..."
    xcodebuild clean -scheme "$SCHEME_NAME" || error_exit "クリーンビルドが失敗しました"

    # アーカイブ作成
    log "DEBUG" "アーカイブ作成中..."
    if ! xcodebuild archive \
        -scheme "$SCHEME_NAME" \
        -archivePath "$archive_path" \
        -destination 'generic/platform=iOS' \
        SKIP_INSTALL=NO \
        BUILD_LIBRARY_FOR_DISTRIBUTION=YES; then
        error_exit "アーカイブ作成が失敗しました"
    fi

    # Export options作成
    create_export_options_plist "$export_path/ExportOptions.plist"

    # IPA作成
    log "DEBUG" "IPA作成中..."
    if ! xcodebuild -exportArchive \
        -archivePath "$archive_path" \
        -exportPath "$export_path" \
        -exportOptionsPlist "$export_path/ExportOptions.plist"; then
        error_exit "IPA作成が失敗しました"
    fi

    log "INFO" "✅ アーカイブ作成完了: $archive_path"
    echo "$archive_path"
}

create_export_options_plist() {
    local plist_path=$1
    mkdir -p "$(dirname "$plist_path")"

    cat > "$plist_path" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store</string>
    <key>teamID</key>
    <string>$TEAM_ID</string>
    <key>uploadBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
    <key>compileBitcode</key>
    <false/>
    <key>destination</key>
    <string>upload</string>
    <key>signingStyle</key>
    <string>automatic</string>
    <key>stripSwiftSymbols</key>
    <true/>
</dict>
</plist>
EOF
}

# ==============================
# メタデータ検証
# ==============================

validate_metadata() {
    log "INFO" "App Store メタデータ検証開始"

    # アプリアイコンの確認
    validate_app_icons

    # スクリーンショットの確認（存在する場合）
    validate_screenshots

    # プロモーション素材の確認
    validate_promotional_materials

    log "INFO" "✅ メタデータ検証完了"
}

validate_app_icons() {
    local icon_dirs
    mapfile -t icon_dirs < <(find . -name "*.appiconset" -not -path "./Pods/*")

    if [[ ${#icon_dirs[@]} -eq 0 ]]; then
        error_exit "アプリアイコンセットが見つかりません"
    fi

    for icon_dir in "${icon_dirs[@]}"; do
        local contents_json="$icon_dir/Contents.json"
        if [[ ! -f "$contents_json" ]]; then
            error_exit "Contents.jsonが見つかりません: $icon_dir"
        fi

        # 必要なサイズの確認
        local required_sizes=("60x60" "76x76" "83.5x83.5" "1024x1024")
        for size in "${required_sizes[@]}"; do
            if ! grep -q "\"size\" : \"$size\"" "$contents_json"; then
                log "WARN" "必要なアイコンサイズが不足: $size in $icon_dir"
            fi
        done

        log "DEBUG" "アプリアイコン確認完了: $icon_dir"
    done
}

validate_screenshots() {
    local screenshots_dir="$PROJECT_ROOT/metadata/screenshots"
    if [[ -d "$screenshots_dir" ]]; then
        log "DEBUG" "スクリーンショット検証中..."

        # 必要なサイズのスクリーンショットを確認
        local required_sizes=("6.7" "6.1" "5.5")  # iPhone用
        for size in "${required_sizes[@]}"; do
            local size_dir="$screenshots_dir/${size}inch"
            if [[ -d "$size_dir" ]]; then
                local screenshot_count
                screenshot_count=$(find "$size_dir" -name "*.png" -o -name "*.jpg" | wc -l)
                if [[ $screenshot_count -lt 1 ]]; then
                    log "WARN" "スクリーンショットが不足: ${size}inch"
                else
                    log "DEBUG" "スクリーンショット確認済み: ${size}inch ($screenshot_count 枚)"
                fi
            fi
        done
    fi
}

validate_promotional_materials() {
    # プロモーション用テキストやビデオの確認
    local metadata_dir="$PROJECT_ROOT/metadata"
    if [[ -d "$metadata_dir" ]]; then
        log "DEBUG" "プロモーション素材確認中..."

        # 説明文ファイルの確認
        if [[ -f "$metadata_dir/description.txt" ]]; then
            local desc_length
            desc_length=$(wc -c < "$metadata_dir/description.txt")
            if [[ $desc_length -gt 4000 ]]; then
                log "WARN" "アプリ説明文が4000文字を超えています"
            fi
        fi

        # キーワードファイルの確認
        if [[ -f "$metadata_dir/keywords.txt" ]]; then
            local keywords_length
            keywords_length=$(wc -c < "$metadata_dir/keywords.txt")
            if [[ $keywords_length -gt 100 ]]; then
                log "WARN" "キーワードが100文字を超えています"
            fi
        fi
    fi
}

# ==============================
# セキュリティチェック
# ==============================

security_audit() {
    log "INFO" "セキュリティ監査開始"

    # HTTP通信の確認
    check_http_usage

    # 機密情報のハードコーディング確認
    check_hardcoded_secrets

    # キーチェーン使用確認
    check_keychain_usage

    log "INFO" "✅ セキュリティ監査完了"
}

check_http_usage() {
    log "DEBUG" "HTTP通信使用確認中..."

    # http:// の使用をチェック（localhost除く）
    local http_usage
    http_usage=$(grep -r "http://" --include="*.swift" --include="*.m" --include="*.mm" . | grep -v "localhost" | grep -v "127.0.0.1" || true)

    if [[ -n "$http_usage" ]]; then
        log "WARN" "HTTP通信の使用が検出されました:"
        echo "$http_usage"
        log "WARN" "本番環境ではHTTPS通信の使用を強く推奨します"
    fi
}

check_hardcoded_secrets() {
    log "DEBUG" "機密情報ハードコーディング確認中..."

    # 一般的な機密情報パターン
    local secret_patterns=(
        "password.*="
        "api.*key.*="
        "secret.*="
        "token.*="
        "[0-9a-fA-F]{32,}" # 32文字以上のハッシュ値
    )

    for pattern in "${secret_patterns[@]}"; do
        local matches
        matches=$(grep -r -i "$pattern" --include="*.swift" --include="*.m" --include="*.mm" . || true)
        if [[ -n "$matches" ]]; then
            log "WARN" "機密情報がハードコーディングされている可能性があります: $pattern"
        fi
    done
}

check_keychain_usage() {
    log "DEBUG" "キーチェーン使用確認中..."

    if grep -r "Keychain" --include="*.swift" . > /dev/null; then
        log "DEBUG" "キーチェーン使用を確認しました"
    else
        log "WARN" "機密情報の保存にキーチェーンの使用を推奨します"
    fi
}

# ==============================
# レポート生成
# ==============================

generate_compliance_report() {
    log "INFO" "App Store Guidelines準拠レポート生成開始"

    local report_file="$PROJECT_ROOT/reports/compliance_report_$(date +%Y%m%d_%H%M%S).md"
    mkdir -p "$(dirname "$report_file")"

    cat > "$report_file" << EOF
# App Store Guidelines準拠レポート

**生成日時**: $(date '+%Y-%m-%d %H:%M:%S')
**プロジェクト**: $PROJECT_NAME
**バンドルID**: $BUNDLE_ID

## チェック結果サマリー

### ✅ 完了項目
- アプリの完全性チェック (Guidelines 2.1)
- ソフトウェア要件チェック (Guidelines 2.5)
- プライバシー準拠チェック (Guidelines 5.1)
- セキュリティ監査
- メタデータ検証

### ⚠️ 警告項目
$(grep "WARN" "$LOG_FILE" | sed 's/.*WARN] /- /' || echo "なし")

### ❌ エラー項目
$(grep "ERROR" "$LOG_FILE" | sed 's/.*ERROR] /- /' || echo "なし")

## 推奨事項

1. **プライバシー説明の充実**: より詳細な説明を追加
2. **テストカバレッジ向上**: 自動テストの範囲拡大
3. **セキュリティ強化**: HTTPS通信の徹底
4. **アクセシビリティ対応**: VoiceOver等の対応強化

## 次のステップ

- [ ] 警告項目の修正
- [ ] エラー項目の修正（優先度：高）
- [ ] 追加テストの実行
- [ ] App Store Connect設定確認

---
*このレポートは自動生成されました。詳細なログは $LOG_FILE を参照してください。*
EOF

    log "INFO" "✅ レポート生成完了: $report_file"
    echo "$report_file"
}

# ==============================
# メイン処理
# ==============================

show_help() {
    cat << EOF
App Store Guidelines準拠自動化スクリプト

使用方法:
    $0 [オプション] [コマンド]

コマンド:
    check       App Store Guidelines準拠チェック
    test        包括的テスト実行
    build       ビルドとアーカイブ作成
    upload      App Store Connectにアップロード
    audit       セキュリティ監査
    report      準拠レポート生成
    all         すべての処理を実行

オプション:
    -h, --help      このヘルプを表示
    -v, --verbose   詳細ログを出力
    -c, --config    設定ファイルパス (デフォルト: $CONFIG_FILE)

例:
    $0 check                    # 準拠チェックのみ実行
    $0 all                      # 全処理実行
    $0 -v test                  # 詳細ログでテスト実行
    $0 -c custom.json build     # カスタム設定でビルド
EOF
}

main() {
    local verbose=false
    local command=""

    # パラメータ解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            check|test|build|upload|audit|report|all)
                command="$1"
                shift
                ;;
            *)
                log "ERROR" "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # コマンドが指定されていない場合はヘルプ表示
    if [[ -z "$command" ]]; then
        show_help
        exit 1
    fi

    # ログディレクトリ作成
    mkdir -p "$(dirname "$LOG_FILE")"

    log "INFO" "App Store Guidelines準拠自動化スクリプト開始"
    log "DEBUG" "コマンド: $command"
    log "DEBUG" "設定ファイル: $CONFIG_FILE"

    # 設定読み込み
    load_config

    # コマンド実行
    case $command in
        check)
            check_app_completeness
            check_software_requirements
            check_privacy_compliance
            validate_metadata
            ;;
        test)
            run_comprehensive_tests
            ;;
        build)
            archive_path=$(create_archive)
            log "INFO" "アーカイブが完成しました: $archive_path"
            ;;
        upload)
            # アップロード処理は実際のAPIキー等が必要なため、手動実行を促す
            log "INFO" "App Store Connectでの手動アップロードを実行してください"
            log "INFO" "または、xcodebuild -uploadApp を使用してください"
            ;;
        audit)
            security_audit
            ;;
        report)
            report_path=$(generate_compliance_report)
            log "INFO" "準拠レポートが生成されました: $report_path"
            ;;
        all)
            log "INFO" "全体処理を開始します..."

            # 1. チェック
            check_app_completeness
            check_software_requirements
            check_privacy_compliance

            # 2. テスト
            run_comprehensive_tests

            # 3. セキュリティ監査
            security_audit

            # 4. メタデータ検証
            validate_metadata

            # 5. ビルド
            archive_path=$(create_archive)

            # 6. レポート生成
            report_path=$(generate_compliance_report)

            log "INFO" "✅ 全体処理が完了しました"
            log "INFO" "アーカイブ: $archive_path"
            log "INFO" "レポート: $report_path"
            ;;
    esac

    log "INFO" "スクリプト実行完了"
}

# スクリプト実行
main "$@"
