#!/usr/bin/env python3
"""
Phase 2 Google検索ステータス確認スクリプト

クォータ状況、キャッシュ状況、進捗を表示する。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.quota_manager import GoogleQuotaManager, CACHE_DB_PATH


def main():
    """ステータスを表示"""
    if not CACHE_DB_PATH.exists():
        print(f"エラー: DBが見つかりません: {CACHE_DB_PATH}")
        sys.exit(1)

    quota_mgr = GoogleQuotaManager(CACHE_DB_PATH)

    # 今日のクォータ状態
    status = quota_mgr.get_status()

    print(f"日付: {status.date}")
    print()

    # クォータ状況
    print("=== クォータ状況 ===")
    print(f"  使用済み: {status.total_queries}/{status.quota_limit}")
    print(f"  残り: {status.remaining}")
    print(f"  ステータス: {status.status}")
    if status.last_updated:
        print(f"  最終更新: {status.last_updated}")
    print()

    # 日次統計
    stats = quota_mgr.get_daily_stats()

    print("=== 今日の検索統計 ===")
    print(f"  検索総数: {stats['searches']['total']}")
    print(f"  成功: {stats['searches']['success']}")
    print(f"  エラー: {stats['searches']['error']}")
    print(f"  キャッシュヒット: {stats['searches']['cached']}")
    if stats["searches"]["avg_time_ms"] > 0:
        print(f"  平均処理時間: {stats['searches']['avg_time_ms']:.0f}ms")
    print()

    # キャッシュ状況
    import sqlite3

    conn = sqlite3.connect(CACHE_DB_PATH)

    total = conn.execute("SELECT COUNT(*) FROM fame_cache").fetchone()[0]
    with_google = conn.execute("SELECT COUNT(*) FROM fame_cache WHERE google_hits IS NOT NULL").fetchone()[0]
    without_google = total - with_google

    coverage = (with_google / total * 100) if total > 0 else 0
    estimated_days = (without_google + 99) // 100  # 切り上げ

    print("=== キャッシュ状況 ===")
    print(f"  総人物数: {total:,}")
    print(f"  Google検索済み: {with_google:,} ({coverage:.1f}%)")
    print(f"  未検索: {without_google:,}")
    print(f"  完了予定: 約{estimated_days}日後")
    print()

    # 未検索トップ5
    cursor = conn.execute("""
        SELECT person_name, fame_score_v3
        FROM fame_cache
        WHERE google_hits IS NULL AND fame_score_v3 IS NOT NULL
        ORDER BY fame_score_v3 DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()

    if rows:
        print("=== 未検索トップ5（次回処理対象） ===")
        for i, (name, score) in enumerate(rows, 1):
            print(f"  {i}. {name} (スコア: {score:.2f})")

    conn.close()


if __name__ == "__main__":
    main()
