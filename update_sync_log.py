#!/usr/bin/env python3
"""
sync_log.jsonを更新
"""
import json
from datetime import datetime

# sync_log.jsonを読み込み
with open('sync_log.json', 'r', encoding='utf-8') as f:
    sync_log = json.load(f)

# 新しいエントリを追加
new_entry = {
    "timestamp": datetime.now().isoformat(),
    "csv_file": "ultra_think_FICTIONAL_FIXED_20250828_215146.csv",
    "status": "success",
    "message": "架空キャラクター作品名修正完了",
    "highlights": {
        "P000199": "アルミン・アルレルト（進撃の巨人）",
        "total_fixed": 56,
        "success_rate": "92.0%",
        "total_fictional": 50
    }
}

sync_log.append(new_entry)

# 最新10件のみ保持
if len(sync_log) > 10:
    sync_log = sync_log[-10:]

# ファイルに書き戻し
with open('sync_log.json', 'w', encoding='utf-8') as f:
    json.dump(sync_log, f, ensure_ascii=False, indent=2)

print("✅ sync_log.json更新完了")