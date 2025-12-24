#!/usr/bin/env python3
"""
Google検索キャッシュ監視スクリプト。

重複検索・キャッシュ未参照を検知してレポートする。
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.google_search import get_stats, reset_stats

CACHE_DB_PATH = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports/logs")


def analyze_cache_status() -> dict:
    """キャッシュ状況を分析"""
    if not CACHE_DB_PATH.exists():
        return {"error": "Cache DB not found"}

    conn = sqlite3.connect(str(CACHE_DB_PATH))

    # 統計取得
    total = conn.execute("SELECT COUNT(*) FROM fame_cache").fetchone()[0]
    with_google = conn.execute("SELECT COUNT(*) FROM fame_cache WHERE google_hits IS NOT NULL").fetchone()[0]
    without_google = total - with_google

    # 上位未取得（優先度高）
    top_missing = conn.execute("""
        SELECT person_name, fame_score_v3
        FROM fame_cache
        WHERE google_hits IS NULL AND fame_score_v3 IS NOT NULL
        ORDER BY fame_score_v3 DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total_persons": total,
        "with_google_hits": with_google,
        "without_google_hits": without_google,
        "coverage_pct": round(with_google / total * 100, 1) if total > 0 else 0,
        "top_missing": [{"name": n, "score": s} for n, s in top_missing],
    }


def check_session_stats() -> dict:
    """セッション内の検索統計を確認"""
    stats = get_stats()
    issues = []

    # 異常検知
    if stats["api_calls"] > 0 and stats["cache_hits"] == 0:
        issues.append("WARNING: API呼び出しがあるがキャッシュヒットなし（キャッシュ未参照の可能性）")

    if stats["api_errors"] > stats["api_calls"] * 0.1:
        issues.append(f"WARNING: エラー率が10%超過 ({stats['api_errors']}/{stats['api_calls']})")

    return {
        "stats": stats,
        "issues": issues,
    }


def generate_report() -> dict:
    """監視レポートを生成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "cache_status": analyze_cache_status(),
        "session_stats": check_session_stats(),
    }
    return report


def save_report(report: dict) -> Path:
    """レポートを保存"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"cache_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report_path


def main():
    print("=== Google検索キャッシュ監視 ===\n")

    report = generate_report()

    # キャッシュ状況
    cs = report["cache_status"]
    if "error" not in cs:
        print(f"キャッシュカバレッジ: {cs['with_google_hits']}/{cs['total_persons']} ({cs['coverage_pct']}%)")
        print(f"未取得: {cs['without_google_hits']}人")
        if cs["top_missing"]:
            print("\n未取得トップ5:")
            for i, p in enumerate(cs["top_missing"][:5], 1):
                print(f"  {i}. {p['name']} (スコア: {p['score']:.2f})")
    else:
        print(f"ERROR: {cs['error']}")

    # セッション統計
    ss = report["session_stats"]
    stats = ss["stats"]
    print("\nセッション統計:")
    print(f"  キャッシュヒット: {stats['cache_hits']}")
    print(f"  API呼び出し: {stats['api_calls']}")
    print(f"  APIエラー: {stats['api_errors']}")

    # 問題検知
    if ss["issues"]:
        print("\n⚠️ 検知された問題:")
        for issue in ss["issues"]:
            print(f"  - {issue}")

    # レポート保存
    report_path = save_report(report)
    print(f"\nレポート保存: {report_path}")


if __name__ == "__main__":
    main()
