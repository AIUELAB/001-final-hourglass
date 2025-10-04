#!/bin/bash
# 統合ルール管理システム - 定期監視セットアップ
# Unified Rule Management System - Periodic Monitoring Setup

set -e

echo "🚀 統合ルール管理システム - 定期監視セットアップ"
echo "============================================================"

# 現在のディレクトリを確認
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "📂 プロジェクトディレクトリ: $PROJECT_DIR"

# 1. cronジョブの設定
echo ""
echo "⏰ cronジョブの設定..."

# crontabエントリ
CRON_ENTRY="0 */6 * * * cd $PROJECT_DIR && /usr/bin/python3 rule_health_monitor.py >> logs/rule_health_cron.log 2>&1"

# 既存のcrontabを取得
crontab -l > /tmp/current_cron 2>/dev/null || echo "# Crontab" > /tmp/current_cron

# 既に登録されているか確認
if grep -q "rule_health_monitor.py" /tmp/current_cron; then
    echo "✅ cronジョブは既に登録済み"
else
    # 追加
    echo "$CRON_ENTRY" >> /tmp/current_cron
    crontab /tmp/current_cron
    echo "✅ cronジョブを登録しました（6時間ごと）"
fi

rm /tmp/current_cron

# 2. ログディレクトリの作成
echo ""
echo "📁 ログディレクトリの作成..."
mkdir -p logs
echo "✅ logs/ ディレクトリ作成完了"

# 3. launchd設定（macOS用）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "🍎 macOS launchd設定の作成..."

    PLIST_FILE="$HOME/Library/LaunchAgents/com.unified-rule-system.health-monitor.plist"

    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.unified-rule-system.health-monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$PROJECT_DIR/rule_health_monitor.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/rule_health_launchd.log</string>

    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/rule_health_launchd.err</string>

    <key>StartInterval</key>
    <integer>21600</integer>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

    # 権限設定
    chmod 644 "$PLIST_FILE"

    # launchdに登録
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"

    echo "✅ launchd設定完了: $PLIST_FILE"
    echo "   起動時に自動実行、その後6時間ごとに実行されます"
fi

# 4. systemd設定（Linux用）
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "🐧 Linux systemd設定の作成..."

    SYSTEMD_SERVICE_FILE="$HOME/.config/systemd/user/unified-rule-health-monitor.service"
    SYSTEMD_TIMER_FILE="$HOME/.config/systemd/user/unified-rule-health-monitor.timer"

    mkdir -p "$HOME/.config/systemd/user"

    # サービスファイル
    cat > "$SYSTEMD_SERVICE_FILE" <<EOF
[Unit]
Description=Unified Rule Management System - Health Monitor
After=network.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/rule_health_monitor.py
StandardOutput=append:$PROJECT_DIR/logs/rule_health_systemd.log
StandardError=append:$PROJECT_DIR/logs/rule_health_systemd.err

[Install]
WantedBy=default.target
EOF

    # タイマーファイル
    cat > "$SYSTEMD_TIMER_FILE" <<EOF
[Unit]
Description=Unified Rule Management System - Health Monitor Timer
Requires=unified-rule-health-monitor.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # systemd再読込と有効化
    systemctl --user daemon-reload
    systemctl --user enable unified-rule-health-monitor.timer
    systemctl --user start unified-rule-health-monitor.timer

    echo "✅ systemd設定完了"
    echo "   起動5分後に初回実行、その後6時間ごとに実行されます"
fi

# 5. 初回ヘルスチェック実行
echo ""
echo "🏥 初回ヘルスチェック実行..."
python3 rule_health_monitor.py

# 6. セットアップ完了レポート
echo ""
echo "============================================================"
echo "✅ セットアップ完了"
echo "============================================================"
echo ""
echo "📋 設定内容:"
echo "  - ヘルスチェック: 6時間ごと"
echo "  - ログディレクトリ: $PROJECT_DIR/logs/"
echo "  - Gitフック: .git/hooks/pre-commit"
echo ""
echo "🔧 手動実行コマンド:"
echo "  ヘルスチェック: python3 rule_health_monitor.py"
echo "  自動同期: python3 rule_sync_automation.py"
echo "  ファイル監視: python3 rule_auto_sync_watcher.py --daemon"
echo ""
echo "📊 ステータス確認:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  launchctl list | grep unified-rule-system"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  systemctl --user status unified-rule-health-monitor.timer"
else
    echo "  crontab -l | grep rule_health"
fi
echo ""
