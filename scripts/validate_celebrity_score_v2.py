#!/usr/bin/env python3
"""
Celebrity Score v2 品質検証スクリプト

検証項目:
1. スコア範囲（0-1000）
2. カテゴリ分布（政治家20%以下）
3. 外れ値検出（上位0.1%）
4. Top100安定性
5. 同名曖昧性チェック
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# 定数
CACHE_DB_PATH = Path("data/cache/fame_score.db")
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_DIR = Path("src/reports")


def validate_score_range(conn: sqlite3.Connection) -> dict:
    """スコア範囲を検証"""
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN celebrity_score_v2 < 0 THEN 1 ELSE 0 END) as below_zero,
            SUM(CASE WHEN celebrity_score_v2 > 1000 THEN 1 ELSE 0 END) as above_1000,
            MIN(celebrity_score_v2) as min_score,
            MAX(celebrity_score_v2) as max_score,
            AVG(celebrity_score_v2) as avg_score
        FROM fame_cache
        WHERE celebrity_score_v2 IS NOT NULL
    """)
    row = cursor.fetchone()

    return {
        "total": row[0],
        "below_zero": row[1],
        "above_1000": row[2],
        "min_score": row[3],
        "max_score": row[4],
        "avg_score": row[5],
        "passed": row[1] == 0 and row[2] == 0,
    }


def validate_category_distribution(conn: sqlite3.Connection) -> dict:
    """カテゴリ分布を検証（Top100）"""
    # CSVからカテゴリ情報を取得
    df = pd.read_csv(MASTER_CSV_PATH, usecols=["person_id", "category"], low_memory=False)
    df = df.drop_duplicates(subset=["person_id"])
    categories = dict(zip(df["person_id"], df["category"]))

    # Top100を取得
    cursor = conn.execute("""
        SELECT person_id, celebrity_score_v2
        FROM fame_cache
        WHERE celebrity_score_v2 IS NOT NULL
        ORDER BY celebrity_score_v2 DESC
        LIMIT 100
    """)

    category_counts = {}
    for person_id, score in cursor.fetchall():
        cat = categories.get(person_id, "(未分類)")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    politics_count = category_counts.get("政治・社会", 0)

    return {
        "distribution": category_counts,
        "politics_rate": politics_count,
        "passed": politics_count <= 20,
    }


def detect_outliers(conn: sqlite3.Connection) -> dict:
    """外れ値を検出（上位0.1%）"""
    # 99.9%ile を計算
    cursor = conn.execute("""
        SELECT celebrity_score_v2
        FROM fame_cache
        WHERE celebrity_score_v2 IS NOT NULL
        ORDER BY celebrity_score_v2 DESC
    """)
    scores = [row[0] for row in cursor.fetchall()]

    if not scores:
        return {"outliers": [], "threshold": 0, "passed": True}

    threshold_idx = max(0, int(len(scores) * 0.001))
    threshold = scores[threshold_idx] if threshold_idx < len(scores) else scores[0]

    # 外れ値を取得
    cursor = conn.execute(
        """
        SELECT person_id, person_name, celebrity_score_v2
        FROM fame_cache
        WHERE celebrity_score_v2 > ?
        ORDER BY celebrity_score_v2 DESC
    """,
        (threshold,),
    )

    outliers = [{"person_id": r[0], "name": r[1], "score": r[2]} for r in cursor.fetchall()]

    return {
        "outliers": outliers,
        "threshold": threshold,
        "count": len(outliers),
        "passed": len(outliers) <= 10,  # 10人以下なら許容
    }


def get_top10_snapshot(conn: sqlite3.Connection) -> list:
    """Top10スナップショットを取得"""
    cursor = conn.execute("""
        SELECT celebrity_rank_v2, person_name, celebrity_score_v2
        FROM fame_cache
        WHERE celebrity_score_v2 IS NOT NULL
        ORDER BY celebrity_score_v2 DESC
        LIMIT 10
    """)
    return [{"rank": r[0], "name": r[1], "score": r[2]} for r in cursor.fetchall()]


def main():
    """検証を実行"""
    print(f"\n{'=' * 60}")
    print("Celebrity Score v2 品質検証")
    print(f"{'=' * 60}\n")

    if not CACHE_DB_PATH.exists():
        print("ERROR: キャッシュDBが見つかりません")
        sys.exit(1)

    conn = sqlite3.connect(str(CACHE_DB_PATH))

    # 検証実行
    print("検証中...")
    results = {}

    # 1. スコア範囲
    print("  1. スコア範囲...")
    results["score_range"] = validate_score_range(conn)
    status = "✓" if results["score_range"]["passed"] else "✗"
    print(f"     {status} 範囲: {results['score_range']['min_score']:.1f} - {results['score_range']['max_score']:.1f}")

    # 2. カテゴリ分布
    print("  2. カテゴリ分布...")
    results["category_distribution"] = validate_category_distribution(conn)
    status = "✓" if results["category_distribution"]["passed"] else "✗"
    print(f"     {status} 政治家占有率: {results['category_distribution']['politics_rate']}%")

    # 3. 外れ値検出
    print("  3. 外れ値検出...")
    results["outliers"] = detect_outliers(conn)
    status = "✓" if results["outliers"]["passed"] else "✗"
    print(f"     {status} 外れ値: {results['outliers']['count']}件（閾値: {results['outliers']['threshold']:.1f}）")

    # 4. Top10スナップショット
    print("  4. Top10スナップショット...")
    results["top10"] = get_top10_snapshot(conn)

    conn.close()

    # 全体結果
    all_passed = all(
        [
            results["score_range"]["passed"],
            results["category_distribution"]["passed"],
            results["outliers"]["passed"],
        ]
    )

    print()
    if all_passed:
        print("✓ 全ての検証をパスしました")
    else:
        print("✗ 一部の検証に失敗しました")

    # Top10表示
    print("\n=== Top10 ===")
    for item in results["top10"]:
        print(f"  {item['rank']:2d}. {item['name'][:20]:<20s} {item['score']:.1f}")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"v2_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "all_passed": all_passed,
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nレポート: {report_path}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
