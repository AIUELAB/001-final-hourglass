#!/usr/bin/env python3
"""Fame Score更新の進捗確認スクリプト"""

import sqlite3
import subprocess
import time


def check_progress():
    try:
        conn = sqlite3.connect("data/cache/fame_score.db")
        count = conn.execute("SELECT COUNT(*) FROM fame_cache WHERE fame_score_v3 IS NOT NULL").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def check_process():
    result = subprocess.run(["pgrep", "-f", "update_fame_scores"], capture_output=True, text=True)
    return bool(result.stdout.strip())


if __name__ == "__main__":
    total = 7393
    count = check_progress()
    running = check_process()

    pct = count / total * 100
    print(f"進捗: {count:,} / {total:,} ({pct:.1f}%)")
    print(f"状態: {'実行中' if running else '停止'}")

    if count > 0:
        # 推定残り時間（1人あたり約2秒と仮定）
        remaining = (total - count) * 2 / 60
        print(f"推定残り時間: 約{remaining:.0f}分")
