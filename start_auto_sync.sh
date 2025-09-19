#!/bin/bash

# ===============================================
# Ultra Think 自動同期監視システム起動スクリプト
# ===============================================

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# バナー表示
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║     🔍 Ultra Think 自動同期監視システム          ║"
echo "║         ファイル変更を検知して自動同期           ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Pythonチェック
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3が見つかりません${NC}"
    exit 1
fi

# watchdogチェック
python3 -c "import watchdog" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️ watchdogがインストールされていません${NC}"
    echo "インストールしますか？ (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        pip install watchdog
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ watchdogのインストールに失敗しました${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ watchdogをインストールしました${NC}"
    else
        echo -e "${RED}監視システムを実行するにはwatchdogが必要です${NC}"
        exit 1
    fi
fi

# 既存のプロセスをチェック
if pgrep -f "auto_sync_watcher.py" > /dev/null; then
    echo -e "${YELLOW}⚠️ 既に監視プロセスが実行中です${NC}"
    echo "既存のプロセスを停止しますか？ (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        pkill -f "auto_sync_watcher.py"
        echo -e "${GREEN}✅ 既存のプロセスを停止しました${NC}"
        sleep 2
    else
        echo -e "${RED}新しい監視プロセスを開始できません${NC}"
        exit 1
    fi
fi

# 環境情報表示
echo -e "${BLUE}📋 環境情報${NC}"
echo "  Python: $(python3 --version)"
echo "  作業ディレクトリ: $(pwd)"
echo "  監視対象: ultra_think_*.csv"
echo ""

# オプション選択
echo -e "${CYAN}実行モードを選択してください:${NC}"
echo "  1) フォアグラウンドで実行（ログを表示）"
echo "  2) バックグラウンドで実行（デーモン化）"
echo "  3) テストモード（1分間だけ実行）"
echo ""
echo -n "選択 (1-3): "
read -r mode

case $mode in
    1)
        echo -e "${GREEN}🚀 フォアグラウンドモードで起動${NC}"
        echo -e "${YELLOW}Ctrl+C で終了できます${NC}"
        echo ""
        python3 auto_sync_watcher.py
        ;;
    
    2)
        echo -e "${GREEN}🚀 バックグラウンドモードで起動${NC}"
        nohup python3 auto_sync_watcher.py > auto_sync_watcher.log 2>&1 &
        PID=$!
        echo -e "${GREEN}✅ プロセスID: $PID${NC}"
        echo ""
        echo "ログを確認: tail -f auto_sync_watcher.log"
        echo "停止: kill $PID または pkill -f auto_sync_watcher.py"
        
        # PIDファイルに保存
        echo $PID > auto_sync_watcher.pid
        ;;
    
    3)
        echo -e "${GREEN}🚀 テストモード（60秒間）${NC}"
        timeout 60 python3 auto_sync_watcher.py
        echo -e "${GREEN}✅ テスト完了${NC}"
        ;;
    
    *)
        echo -e "${RED}無効な選択です${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}ヒント:${NC}"
echo "  • ファイルを編集して保存すると自動的に同期されます"
echo "  • 設定変更: auto_sync_config.json"
echo "  • ログ確認: auto_sync_log.json"
echo "  • バックアップ: backups/ ディレクトリ"

exit 0