#!/bin/bash
# ============================================================
# PDCAガーディアン起動スクリプト（デーモン化）
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# 仮想環境の有効化
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# デーモンとしてバックグラウンド実行
nohup python3 pdca_guardian_daemon.py > logs/pdca_daemon.log 2>&1 &

echo $!
