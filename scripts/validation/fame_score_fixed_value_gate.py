#!/usr/bin/env python3
"""
fame_score_v3 固定値異常検出ゲート

同一のfame_score_v3が閾値以上の件数で異なるperson_idに存在する場合を検出する。
これはAPIエラー時のフォールバック値やバグによる固定値大量発生を検知するためのゲート。

例外値（デフォルト除外可能）:
- 400.00: 架空キャラクターのデフォルト値
- 500.00: Wikipedia無しのデフォルト値

Usage:
    python scripts/validation/fame_score_fixed_value_gate.py --csv PATH [--threshold N] [--exclude-defaults]

Exit codes:
    0: OK（異常なし）
    1: CRITICAL（固定値異常検出）
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/fame_score_fixed_value_gate_result.json"

# デフォルト閾値
DEFAULT_COUNT_THRESHOLD = 50  # 同一スコアがこの件数以上
DEFAULT_PERSON_THRESHOLD = 10  # 異なる人物がこの人数以上

# 除外可能なデフォルト値
KNOWN_DEFAULT_VALUES = {
    400.00: "架空キャラクター",
    500.00: "Wikipedia無し",
}


@dataclass
class FixedValueAnomaly:
    """固定値異常"""

    fame_score_v3: float
    count: int
    person_count: int
    severity: str
    sample_persons: list  # サンプル人物名（最大5件）
    sample_episode_ids: list  # サンプルエピソードID（最大5件）


def detect_fixed_value_anomaly(
    csv_path: Path,
    count_threshold: int = DEFAULT_COUNT_THRESHOLD,
    person_threshold: int = DEFAULT_PERSON_THRESHOLD,
    exclude_defaults: bool = False,
) -> dict:
    """
    fame_score_v3の固定値異常を検出

    Args:
        csv_path: CSVファイルパス
        count_threshold: 件数閾値（デフォルト50）
        person_threshold: 人物数閾値（デフォルト10）
        exclude_defaults: デフォルト値（400.00, 500.00）を除外するか

    Returns:
        検出結果を含む辞書
    """
    # fame_score_v3 -> [(person_id, person_name, episode_id), ...]
    score_records = defaultdict(list)
    total_records = 0
    missing_score_count = 0

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_records += 1
            fame_score_str = row.get("fame_score_v3", "")

            if not fame_score_str:
                missing_score_count += 1
                continue

            try:
                fame_score = round(float(fame_score_str), 2)
            except (ValueError, TypeError):
                missing_score_count += 1
                continue

            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")

            score_records[fame_score].append(
                {
                    "person_id": person_id,
                    "person_name": person_name,
                    "episode_id": episode_id,
                }
            )

    # 異常検出
    anomalies = []
    excluded_defaults = []

    for score, records in score_records.items():
        count = len(records)
        unique_persons = set(r["person_id"] for r in records)
        person_count = len(unique_persons)

        # 閾値チェック: 件数 >= count_threshold AND 人物数 >= person_threshold
        if count >= count_threshold and person_count >= person_threshold:
            # デフォルト値の除外判定
            if exclude_defaults and score in KNOWN_DEFAULT_VALUES:
                excluded_defaults.append(
                    {
                        "score": score,
                        "reason": KNOWN_DEFAULT_VALUES[score],
                        "count": count,
                        "person_count": person_count,
                    }
                )
                continue

            # 重大度判定
            if count >= 200 and person_count >= 50:
                severity = "critical"
            elif count >= 100 and person_count >= 30:
                severity = "high"
            else:
                severity = "medium"

            # サンプル抽出
            sample_persons = list({r["person_name"] for r in records})[:5]
            sample_episode_ids = [r["episode_id"] for r in records][:5]

            anomalies.append(
                FixedValueAnomaly(
                    fame_score_v3=score,
                    count=count,
                    person_count=person_count,
                    severity=severity,
                    sample_persons=sample_persons,
                    sample_episode_ids=sample_episode_ids,
                )
            )

    # 重大度順にソート
    severity_order = {"critical": 0, "high": 1, "medium": 2}
    anomalies.sort(key=lambda x: (severity_order[x.severity], -x.count))

    # 統計
    severity_counts = {
        "critical": sum(1 for a in anomalies if a.severity == "critical"),
        "high": sum(1 for a in anomalies if a.severity == "high"),
        "medium": sum(1 for a in anomalies if a.severity == "medium"),
    }

    return {
        "scan_date": datetime.now().isoformat(),
        "csv_path": str(csv_path),
        "total_records": total_records,
        "missing_score_count": missing_score_count,
        "unique_scores": len(score_records),
        "count_threshold": count_threshold,
        "person_threshold": person_threshold,
        "exclude_defaults": exclude_defaults,
        "excluded_defaults": excluded_defaults,
        "total_anomalies": len(anomalies),
        "severity_counts": severity_counts,
        "anomalies": [asdict(a) for a in anomalies],
    }


def get_anomaly_summary(result: dict) -> str:
    """異常サマリーを生成"""
    lines = []
    lines.append("=" * 60)
    lines.append("fame_score_v3 固定値異常サマリー")
    lines.append("=" * 60)
    lines.append(f"\n検査日時: {result['scan_date']}")
    lines.append(f"対象CSV: {result['csv_path']}")
    lines.append(f"総レコード数: {result['total_records']}")
    lines.append(f"スコア欠損数: {result['missing_score_count']}")
    lines.append(f"ユニークスコア数: {result['unique_scores']}")
    lines.append("\n閾値設定:")
    lines.append(f"  - 件数閾値: {result['count_threshold']}件以上")
    lines.append(f"  - 人物数閾値: {result['person_threshold']}人以上")
    lines.append(f"  - デフォルト値除外: {result['exclude_defaults']}")

    if result["excluded_defaults"]:
        lines.append("\n--- 除外されたデフォルト値 ---")
        for ed in result["excluded_defaults"]:
            lines.append(f"  {ed['score']:.2f}: {ed['count']}件, {ed['person_count']}人物 ({ed['reason']})")

    lines.append("\n--- 検出結果 ---")
    lines.append(f"総異常数: {result['total_anomalies']}")
    lines.append(f"  CRITICAL (200件+/50人物+): {result['severity_counts']['critical']}")
    lines.append(f"  HIGH (100件+/30人物+): {result['severity_counts']['high']}")
    lines.append(f"  MEDIUM: {result['severity_counts']['medium']}")

    if result["anomalies"]:
        lines.append("\n--- 固定値異常リスト ---")
        for a in result["anomalies"]:
            lines.append(f"\n  [{a['severity'].upper()}] fame_score_v3 = {a['fame_score_v3']:.2f}")
            lines.append(f"    件数: {a['count']}, 影響人物数: {a['person_count']}")
            lines.append(f"    サンプル人物: {', '.join(a['sample_persons'][:3])}...")
            lines.append(f"    サンプルEP: {', '.join(a['sample_episode_ids'][:3])}...")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="fame_score_v3 固定値異常検出ゲート")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_MASTER_CSV,
        help=f"対象CSVパス (デフォルト: {DEFAULT_MASTER_CSV})",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_COUNT_THRESHOLD,
        help=f"件数閾値 (デフォルト: {DEFAULT_COUNT_THRESHOLD})",
    )
    parser.add_argument(
        "--person-threshold",
        type=int,
        default=DEFAULT_PERSON_THRESHOLD,
        help=f"人物数閾値 (デフォルト: {DEFAULT_PERSON_THRESHOLD})",
    )
    parser.add_argument(
        "--exclude-defaults",
        action="store_true",
        help="デフォルト値（400.00, 500.00）を除外する",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="JSON出力のみ（人間可読出力を抑制）",
    )
    args = parser.parse_args()

    # CSVファイル存在チェック
    if not args.csv.exists():
        print(f"❌ エラー: CSVファイルが見つかりません: {args.csv}", file=sys.stderr)
        return 1

    # 検出実行
    result = detect_fixed_value_anomaly(
        csv_path=args.csv,
        count_threshold=args.threshold,
        person_threshold=args.person_threshold,
        exclude_defaults=args.exclude_defaults,
    )

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if args.json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 人間可読サマリー出力
        summary = get_anomaly_summary(result)
        print(summary)
        print(f"\n✅ レポート保存先: {REPORT_PATH}")

    # 終了コード判定
    critical_count = result["severity_counts"]["critical"]
    high_count = result["severity_counts"]["high"]

    if critical_count > 0:
        print(f"\n❌ CRITICAL: {critical_count}件の固定値異常を検出")
        return 1

    if high_count > 0:
        print(f"\n⚠️ HIGH: {high_count}件の固定値異常を検出（ゲート警告）")
        return 1

    if result["total_anomalies"] > 0:
        print(f"\n⚠️ MEDIUM: {result['total_anomalies']}件の固定値異常あり（ゲート通過）")
        return 0

    print("\n✅ OK: 固定値異常なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
