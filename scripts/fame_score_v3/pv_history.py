"""
PV History Analysis - 日本語PVバズ検出モジュール

一時的なPVスパイクを検出し、スコアリングの過大評価を防ぐ。
日本語版Wikipedia PV比率が異常に高い人物を検出し、補正係数を計算。
"""

import json
import sqlite3
from typing import Any


def parse_pv_by_lang(pv_by_lang: str | None) -> dict[str, int]:
    """
    pv_by_lang JSONを解析（多重エスケープ対応）

    Args:
        pv_by_lang: DBから取得したJSON文字列

    Returns:
        dict: {言語コード: PV数}
    """
    if not pv_by_lang:
        return {}

    try:
        # 多重エスケープを解除（最大10回）
        data = pv_by_lang
        for _ in range(10):
            if isinstance(data, str):
                data = json.loads(data)
            else:
                break

        if isinstance(data, dict):
            return {k: int(v) for k, v in data.items() if v}
        return {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def detect_japan_buzz(
    conn: sqlite3.Connection,
    ja_ratio_threshold: float = 0.85,
    min_pv_for_analysis: int = 10000,
    sitelinks_threshold: int = 30,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """
    日本語PV比率が異常に高い人物を検出し、補正係数を計算。

    バズ検出の基準:
    1. 日本語PV比率 > 85%（大部分が日本からのアクセス）
    2. sitelinks < 30（国際的知名度が低い）
    3. 総PV >= 10,000（ノイズ除去）

    これらの条件を満たす人物は、一時的なニュースやイベントで
    PVが急増している可能性が高く、スコアを補正する。

    Args:
        conn: SQLite接続
        ja_ratio_threshold: 日本語PV比率の閾値（デフォルト85%）
        min_pv_for_analysis: 分析対象の最小PV（デフォルト10,000）
        sitelinks_threshold: sitelinks閾値（これ以下だと国際知名度低）

    Returns:
        buzz_adjustments: {person_id: 補正係数(0.5~1.0)}
        buzz_details: [{"person_id", "person_name", "adjustment", "reason", ...}]
    """
    buzz_adjustments: dict[str, float] = {}
    buzz_details: list[dict[str, Any]] = []

    # 分析対象を取得
    cursor = conn.execute(
        """
        SELECT person_id, person_name, multi_lang_pv, sitelinks, pv_by_lang
        FROM fame_cache
        WHERE multi_lang_pv >= ?
        """,
        (min_pv_for_analysis,),
    )

    for row in cursor.fetchall():
        person_id, person_name, multi_lang_pv, sitelinks, pv_by_lang = row

        # PV言語分布を解析
        pv_data = parse_pv_by_lang(pv_by_lang)
        if not pv_data:
            continue

        ja_pv = pv_data.get("ja", 0)
        if ja_pv == 0:
            continue

        # 日本語PV比率を計算
        ja_ratio = ja_pv / multi_lang_pv if multi_lang_pv > 0 else 0

        # バズ判定
        # 1. 日本語比率が非常に高い
        # 2. 国際的知名度が低い（sitelinks < threshold）
        is_buzz = ja_ratio >= ja_ratio_threshold and (sitelinks or 0) < sitelinks_threshold

        if is_buzz:
            # 補正係数を計算
            # ja_ratio 85%→0.8、90%→0.7、95%→0.6、100%→0.5
            adjustment = max(0.5, 1.0 - (ja_ratio - 0.80) * 2)

            buzz_adjustments[person_id] = adjustment
            buzz_details.append(
                {
                    "person_id": person_id,
                    "person_name": person_name,
                    "adjustment": round(adjustment, 2),
                    "reason": f"ja_ratio={ja_ratio:.1%}, sitelinks={sitelinks}",
                    "ja_pv": ja_pv,
                    "total_pv": multi_lang_pv,
                    "ja_ratio": round(ja_ratio, 3),
                    "sitelinks": sitelinks or 0,
                }
            )

    # 詳細をja_ratio降順でソート
    buzz_details.sort(key=lambda x: x["ja_ratio"], reverse=True)

    return buzz_adjustments, buzz_details


def analyze_pv_distribution(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    PV分布の統計情報を取得（デバッグ・分析用）

    Returns:
        dict: 統計情報
    """
    cursor = conn.execute(
        """
        SELECT multi_lang_pv, pv_by_lang, sitelinks
        FROM fame_cache
        WHERE multi_lang_pv > 0
        """
    )

    total_persons = 0
    high_ja_ratio_count = 0
    pv_distribution = {"<1k": 0, "1k-10k": 0, "10k-100k": 0, "100k-1M": 0, ">1M": 0}

    for row in cursor.fetchall():
        multi_lang_pv, pv_by_lang, sitelinks = row
        total_persons += 1

        # PV分布
        if multi_lang_pv < 1000:
            pv_distribution["<1k"] += 1
        elif multi_lang_pv < 10000:
            pv_distribution["1k-10k"] += 1
        elif multi_lang_pv < 100000:
            pv_distribution["10k-100k"] += 1
        elif multi_lang_pv < 1000000:
            pv_distribution["100k-1M"] += 1
        else:
            pv_distribution[">1M"] += 1

        # 日本語比率
        pv_data = parse_pv_by_lang(pv_by_lang)
        ja_pv = pv_data.get("ja", 0)
        if multi_lang_pv > 0 and ja_pv / multi_lang_pv > 0.8:
            high_ja_ratio_count += 1

    return {
        "total_persons": total_persons,
        "pv_distribution": pv_distribution,
        "high_ja_ratio_count": high_ja_ratio_count,
        "high_ja_ratio_pct": (high_ja_ratio_count / total_persons * 100 if total_persons > 0 else 0),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    db_path = Path("data/cache/fame_score.db")
    if not db_path.exists():
        print(f"Error: {db_path} not found")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))

    print("=== PV Distribution Analysis ===\n")
    stats = analyze_pv_distribution(conn)
    print(f"Total persons: {stats['total_persons']:,}")
    print(f"High ja_ratio (>80%): {stats['high_ja_ratio_count']} ({stats['high_ja_ratio_pct']:.1f}%)")
    print("\nPV Distribution:")
    for bucket, count in stats["pv_distribution"].items():
        print(f"  {bucket}: {count:,}")

    print("\n=== Japan Buzz Detection ===\n")
    adjustments, details = detect_japan_buzz(conn)
    print(f"Detected: {len(details)} persons")

    for d in details[:20]:
        print(
            f"  {d['person_name'][:15]:<15s} "
            f"adj={d['adjustment']:.2f} "
            f"ja={d['ja_ratio']:.0%} "
            f"pv={d['total_pv']:,} "
            f"sl={d['sitelinks']}"
        )

    conn.close()
