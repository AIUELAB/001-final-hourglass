#!/usr/bin/env python3
"""
全スコアフィールド包括検証スクリプト（再発防止用）

各スコアフィールドの想定スケールを定義し、
範囲外・NaN・inf・負数を検出する。
"""

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScoreSpec:
    """スコアフィールドの仕様"""

    name: str
    min_val: float
    max_val: float
    scale_name: str
    required: bool = False


# 全スコアフィールドのスケール定義
SCORE_SPECS = [
    # 0-5 Tier
    ScoreSpec("fame_tier", 0, 5, "0-5 (Tier)"),
    ScoreSpec("episode_fame_tier", 0, 5, "0-5 (Tier)"),
    # 0-10 スケール
    ScoreSpec("composite_score", 0, 10, "0-10"),
    ScoreSpec("composite_score_5axis", 0, 10, "0-10"),
    ScoreSpec("surprise_score", 0, 10, "0-10"),
    ScoreSpec("memorability_score", 0, 10, "0-10"),
    ScoreSpec("empathy_score", 0, 10, "0-10"),
    ScoreSpec("surprise_score", 0, 10, "0-10"),
    ScoreSpec("generation_quality_score", 0, 10, "0-10"),
    ScoreSpec("educational_value", 0, 10, "0-10"),
    ScoreSpec("story_quality", 0, 10, "0-10"),
    ScoreSpec("factual_density", 0, 10, "0-10"),
    ScoreSpec("llm_memorability_score", 0, 10, "0-10"),
    ScoreSpec("llm_empathy_score", 0, 10, "0-10"),
    ScoreSpec("llm_surprise_score", 0, 10, "0-10"),
    ScoreSpec("llm_generation_quality_score", 0, 10, "0-10"),
    # 0-100 スケール (fame_scoreはv3と同期のため0-1000)
    ScoreSpec("fame_score", 0, 1000, "0-1000"),  # v3と同期済み
    ScoreSpec("fame_score_v2", 0, 100, "0-100"),
    ScoreSpec("impressiveness_score", 0, 100, "0-100"),
    # 0-500 スケール
    ScoreSpec("episode_fame_score", 0, 500, "0-500"),
    # 0-1000 スケール
    ScoreSpec("fame_score_v3", 0, 1000, "0-1000", required=True),
    ScoreSpec("quality_score", 0, 1000, "0-1000"),
    ScoreSpec("priority_score", 0, 1000, "0-1000"),
    ScoreSpec("episode_importance_score", 0, 1000, "0-1000"),
]

DEFAULT_CSV = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def validate_all_scores(csv_path: Path = DEFAULT_CSV) -> dict:
    """
    全スコアフィールドを検証。

    Returns:
        dict: 検証結果
    """
    errors = []
    warnings = []
    stats = {
        spec.name: {"count": 0, "min": float("inf"), "max": float("-inf"), "out_of_range": 0} for spec in SCORE_SPECS
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            person_id = row.get("person_id", "")

            for spec in SCORE_SPECS:
                val_str = row.get(spec.name, "")
                if not val_str or not val_str.strip() or val_str.lower() in ("nan", "none", ""):
                    continue

                try:
                    val = float(val_str)

                    # NaN/inf チェック
                    if math.isnan(val) or math.isinf(val):
                        errors.append(f"行{row_num}: {person_id} - {spec.name}がNaN/inf: {val_str}")
                        continue

                    stats[spec.name]["count"] += 1
                    stats[spec.name]["min"] = min(stats[spec.name]["min"], val)
                    stats[spec.name]["max"] = max(stats[spec.name]["max"], val)

                    # 範囲チェック
                    if val < spec.min_val:
                        errors.append(f"行{row_num}: {person_id} - {spec.name}が下限未満: {val} < {spec.min_val}")
                        stats[spec.name]["out_of_range"] += 1
                    elif val > spec.max_val:
                        # 10%のマージンを許容（警告扱い）
                        margin = spec.max_val * 0.1
                        if val > spec.max_val + margin:
                            errors.append(f"行{row_num}: {person_id} - {spec.name}が上限超過: {val} > {spec.max_val}")
                        else:
                            warnings.append(
                                f"行{row_num}: {person_id} - {spec.name}が上限付近: {val} (上限{spec.max_val})"
                            )
                        stats[spec.name]["out_of_range"] += 1

                except ValueError as e:
                    errors.append(f"行{row_num}: {person_id} - {spec.name}のパース失敗: {val_str}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "specs": SCORE_SPECS,
    }


def main():
    """メインエントリポイント"""
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"📋 全スコアフィールド検証: {csv_path}")
    print()

    result = validate_all_scores(csv_path)

    # スケール定義表示
    print("=== スコアフィールド定義 ===")
    print(f"{'フィールド':<35} {'スケール':>12} {'件数':>8} {'最大':>10}")
    print("-" * 70)

    for spec in SCORE_SPECS:
        s = result["stats"][spec.name]
        count = s["count"]
        max_v = s["max"] if s["max"] != float("-inf") else 0
        status = "✅" if s["out_of_range"] == 0 else f"⚠️({s['out_of_range']})"
        print(f"{spec.name:<35} {spec.scale_name:>12} {count:>8} {max_v:>10.2f} {status}")

    print()

    # 警告表示
    if result["warnings"]:
        print(f"⚠️ 警告: {len(result['warnings'])}件")
        for w in result["warnings"][:3]:
            print(f"  {w}")
        if len(result["warnings"]) > 3:
            print(f"  ... 他 {len(result['warnings']) - 3} 件")
        print()

    # エラー表示
    if result["errors"]:
        print(f"❌ エラー: {len(result['errors'])}件")
        for e in result["errors"][:5]:
            print(f"  {e}")
        if len(result["errors"]) > 5:
            print(f"  ... 他 {len(result['errors']) - 5} 件")
        print()
        sys.exit(1)

    print("✅ 全スコアフィールド検証OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
