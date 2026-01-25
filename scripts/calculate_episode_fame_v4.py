#!/usr/bin/env python3
"""
Episode Fame Score v4 全件計算スクリプト

Usage:
    python scripts/calculate_episode_fame_v4.py --dry-run
    python scripts/calculate_episode_fame_v4.py --execute
    python scripts/calculate_episode_fame_v4.py --sample 100
"""

import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v4.scorer import (
    EpisodeFameSignals,
    calculate_episode_fame_v4,
)

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"


def safe_float(value, default: float = 0.0) -> float:
    """安全にfloatに変換"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def load_csv_data(csv_path: Path) -> tuple[list[str], list[dict]]:
    """CSVを読み込み"""
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []
        rows = list(reader)
    return fieldnames, rows


def build_signals(row: dict) -> EpisodeFameSignals:
    """CSVの行からシグナルを構築"""
    return EpisodeFameSignals(
        # LLM 7軸スコア
        llm_memorability=safe_float(row.get("llm_memorability_score")),
        llm_empathy=safe_float(row.get("llm_empathy_score")),
        llm_surprise=safe_float(row.get("llm_surprise_score")),
        llm_generation_quality=safe_float(row.get("llm_generation_quality_score")),
        llm_educational_value=safe_float(row.get("llm_educational_value")),
        llm_storytelling_quality=safe_float(row.get("llm_storytelling_quality")),
        llm_factual_density=safe_float(row.get("llm_factual_density")),
        # エピソード情報
        episode_text=row.get("episode_text", ""),
        episode_type=row.get("episode_type", ""),
        # 人物知名度（celebrity_score_v2を使用）
        person_fame_score=safe_float(row.get("celebrity_score_v2")),
        # カテゴリ
        category=row.get("category", ""),
    )


def calculate_all(
    rows: list[dict],
    sample_size: int = 0,
) -> tuple[list[dict], dict]:
    """全件計算"""
    if sample_size > 0:
        rows = rows[:sample_size]

    stats = {
        "total": len(rows),
        "by_tier": defaultdict(int),
        "score_distribution": defaultdict(int),
        "samples": {"high": [], "mid": [], "low": []},
    }

    timestamp = datetime.now().isoformat()

    for row in rows:
        signals = build_signals(row)
        episode_id = row.get("episode_id", "")

        result = calculate_episode_fame_v4(signals, episode_id)

        # 結果をrowに追加
        row["episode_fame_score_v4"] = str(result.score)
        row["episode_fame_tier_v4"] = str(result.tier)
        row["episode_fame_v4_updated_at"] = timestamp

        # 統計
        stats["by_tier"][result.tier] += 1
        bucket = int(result.score // 10) * 10
        stats["score_distribution"][bucket] += 1

        # サンプル収集
        sample = {
            "episode_id": episode_id,
            "person_name": row.get("person_name", ""),
            "score": result.score,
            "tier": result.tier,
            "components": result.components,
            "reason": result.reason,
            "text_preview": row.get("episode_text", "")[:60],
        }

        if result.score >= 80 and len(stats["samples"]["high"]) < 10:
            stats["samples"]["high"].append(sample)
        elif 50 <= result.score < 80 and len(stats["samples"]["mid"]) < 10:
            stats["samples"]["mid"].append(sample)
        elif result.score < 50 and len(stats["samples"]["low"]) < 10:
            stats["samples"]["low"].append(sample)

    return rows, stats


def print_stats(stats: dict) -> None:
    """統計を表示"""
    print("\n=== ティア分布 ===")
    for tier in sorted(stats["by_tier"].keys()):
        count = stats["by_tier"][tier]
        pct = count / stats["total"] * 100
        bar = "█" * int(pct / 2)
        print(f"  Tier {tier}: {count:5d}件 ({pct:5.1f}%) {bar}")

    print("\n=== スコア分布 ===")
    for bucket in sorted(stats["score_distribution"].keys()):
        count = stats["score_distribution"][bucket]
        bar = "█" * (count // 100)
        print(f"  {bucket:3d}-{bucket + 9:3d}: {count:5d}件 {bar}")

    print("\n=== 高スコアサンプル (>= 80) ===")
    for s in stats["samples"]["high"][:5]:
        print(f"  {s['episode_id']} | {s['person_name'][:10]} | {s['score']:.1f} | {s['reason'][:40]}")

    print("\n=== 中スコアサンプル (50-79) ===")
    for s in stats["samples"]["mid"][:5]:
        print(f"  {s['episode_id']} | {s['person_name'][:10]} | {s['score']:.1f} | {s['reason'][:40]}")

    print("\n=== 低スコアサンプル (< 50) ===")
    for s in stats["samples"]["low"][:5]:
        print(f"  {s['episode_id']} | {s['person_name'][:10]} | {s['score']:.1f} | {s['reason'][:40]}")


def save_results(
    csv_path: Path,
    fieldnames: list[str],
    rows: list[dict],
    stats: dict,
) -> None:
    """結果を保存"""
    # 新規カラム追加
    new_columns = [
        "episode_fame_score_v4",
        "episode_fame_tier_v4",
        "episode_fame_v4_updated_at",
    ]
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    # バックアップ
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_before_fame_v4_{timestamp}.csv"
    shutil.copy(csv_path, backup_path)
    print(f"\nバックアップ: {backup_path}")

    # CSV書き出し
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV更新: {csv_path}")

    # レポート出力
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"episode_fame_v4_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "total": stats["total"],
                "tier_distribution": dict(stats["by_tier"]),
                "score_distribution": dict(stats["score_distribution"]),
                "samples": stats["samples"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"レポート: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Episode Fame Score v4 計算")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（保存しない）")
    parser.add_argument("--execute", action="store_true", help="実行して保存")
    parser.add_argument("--sample", type=int, default=0, help="サンプル件数（0=全件）")
    args = parser.parse_args()

    if not args.execute and not args.dry_run:
        print("--dry-run または --execute を指定してください")
        sys.exit(1)

    print("=" * 60)
    print("Episode Fame Score v4 計算")
    print("=" * 60)

    if not MASTER_CSV.exists():
        print(f"エラー: {MASTER_CSV} が見つかりません")
        sys.exit(1)

    print(f"\n入力: {MASTER_CSV}")

    # 読み込み
    fieldnames, rows = load_csv_data(MASTER_CSV)
    print(f"総件数: {len(rows)}")

    # 計算
    if args.sample > 0:
        print(f"サンプルモード: {args.sample}件")

    rows, stats = calculate_all(rows, sample_size=args.sample)

    # 統計表示
    print_stats(stats)

    # 保存
    if args.execute and args.sample == 0:
        save_results(MASTER_CSV, fieldnames, rows, stats)
        print("\n完了!")
    else:
        if args.sample > 0:
            print(f"\nサンプルモード（{args.sample}件）: 保存スキップ")
        else:
            print("\n--dry-run: 保存スキップ")


if __name__ == "__main__":
    main()
