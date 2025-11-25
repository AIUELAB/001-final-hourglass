#!/bin/bash

#############################################################################
# Auto Fact Updater 起動スクリプト
#############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "🚀 Auto Fact Updater - 自動更新システム起動"
echo "============================================================"
echo ""

# Python環境チェック
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 is not installed"
    exit 1
fi

# 仮想環境の確認と有効化
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Activating virtual environment..."
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 必要なパッケージの確認
echo "📚 Checking dependencies..."
python3 -c "import aiohttp, schedule" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ Installing missing dependencies..."
    pip install aiohttp schedule
fi

# ログディレクトリの作成
mkdir -p "$PROJECT_DIR/logs/update_logs"
mkdir -p "$PROJECT_DIR/logs/schedule_logs"

# オプションの解析
MODE="scheduler"  # デフォルトはスケジューラーモード
PERSONS=10

while [[ $# -gt 0 ]]; do
    case $1 in
        --immediate)
            MODE="immediate"
            shift
            ;;
        --test)
            MODE="test"
            shift
            ;;
        --persons)
            PERSONS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --immediate     即時更新モード（1回実行して終了）"
            echo "  --test          テストモード（3人のみ更新）"
            echo "  --persons N     更新する人物数（デフォルト: 10）"
            echo "  --help          このヘルプを表示"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

# モードに応じて実行
case $MODE in
    scheduler)
        echo "⏰ Starting in scheduler mode..."
        echo "   Daily updates: 03:00 (Sports, Entertainment)"
        echo "   Weekly updates: Sunday 04:00 (Politics, Science, Arts)"
        echo ""
        echo "Press Ctrl+C to stop"
        echo ""

        # スケジューラーを起動
        python3 -c "
import sys
import time
import signal
sys.path.append('.')
from update_scheduler import UpdateScheduler

def signal_handler(sig, frame):
    print('\n⏹️ Stopping scheduler...')
    scheduler.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

scheduler = UpdateScheduler()
scheduler.start()

print('✅ Scheduler is running. Press Ctrl+C to stop.')
while True:
    time.sleep(60)
    # 次回実行予定を表示
    next_runs = scheduler.get_next_runs()
    if next_runs:
        print(f'Next scheduled run: {next_runs[0]}')
"
        ;;

    immediate)
        echo "🚀 Starting immediate update for $PERSONS persons..."
        python3 -c "
import asyncio
import sys
sys.path.append('.')
from auto_fact_updater import AutoFactUpdater

async def main():
    updater = AutoFactUpdater()
    await updater.run_batch_update(max_persons=$PERSONS)

asyncio.run(main())
"
        ;;

    test)
        echo "🧪 Starting test update for 3 persons..."
        python3 auto_fact_updater.py
        ;;
esac

echo ""
echo "✅ Auto Fact Updater completed"
