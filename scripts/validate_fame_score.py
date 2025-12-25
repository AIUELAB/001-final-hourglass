#!/usr/bin/env python3
"""
有名人度スコア検証スクリプト（再発防止用）

- スコアが想定レンジ（0-1000）内か検証
- 異常値（NaN, inf, 負数, 上限超過）を検出
- 定期監視・CI統合用
"""

import csv
import math
import sys
from pathlib import Path


# 想定レンジ
FAME_SCORE_MIN = 0.0
FAME_SCORE_MAX = 1000.0
EPISODE_FAME_SCORE_MAX = 500.0  # episode_fame_scoreは0-500程度

# CSVパス
DEFAULT_CSV = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def validate_fame_scores(csv_path: Path = DEFAULT_CSV) -> dict:
    """
    有名人度スコアを検証し、異常値を検出する。

    Returns:
        dict: {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "stats": dict
        }
    """
    errors = []
    warnings = []
    stats = {
        "total_rows": 0,
        "fame_score_v3_count": 0,
        "fame_score_v3_max": 0.0,
        "fame_score_v3_min": float("inf"),
        "episode_fame_score_count": 0,
        "episode_fame_score_max": 0.0,
        "out_of_range": [],
        "nan_inf": [],
        "negative": [],
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # ヘッダー=1行目
            stats["total_rows"] += 1
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")

            # fame_score_v3 検証
            fs_v3_str = row.get("fame_score_v3", "")
            if fs_v3_str and fs_v3_str.strip():
                try:
                    fs_v3 = float(fs_v3_str)
                    stats["fame_score_v3_count"] += 1

                    # NaN/inf チェック
                    if math.isnan(fs_v3) or math.isinf(fs_v3):
                        errors.append(f"行{row_num}: {person_id}/{person_name} - fame_score_v3がNaN/inf: {fs_v3_str}")
                        stats["nan_inf"].append(person_id)
                        continue

                    # 負数チェック
                    if fs_v3 < 0:
                        errors.append(f"行{row_num}: {person_id}/{person_name} - fame_score_v3が負数: {fs_v3}")
                        stats["negative"].append(person_id)
                        continue

                    # レンジチェック
                    if fs_v3 > FAME_SCORE_MAX:
                        errors.append(
                            f"行{row_num}: {person_id}/{person_name} - fame_score_v3が上限超過: {fs_v3} > {FAME_SCORE_MAX}"
                        )
                        stats["out_of_range"].append((person_id, fs_v3))

                    # 統計更新
                    stats["fame_score_v3_max"] = max(stats["fame_score_v3_max"], fs_v3)
                    stats["fame_score_v3_min"] = min(stats["fame_score_v3_min"], fs_v3)

                except ValueError as e:
                    errors.append(
                        f"行{row_num}: {person_id}/{person_name} - fame_score_v3のパース失敗: {fs_v3_str} ({e})"
                    )

            # episode_fame_score 検証
            efs_str = row.get("episode_fame_score", "")
            if efs_str and efs_str.strip():
                try:
                    efs = float(efs_str)
                    stats["episode_fame_score_count"] += 1

                    if math.isnan(efs) or math.isinf(efs):
                        errors.append(
                            f"行{row_num}: {person_id}/{person_name} - episode_fame_scoreがNaN/inf: {efs_str}"
                        )
                        continue

                    if efs < 0:
                        errors.append(f"行{row_num}: {person_id}/{person_name} - episode_fame_scoreが負数: {efs}")

                    if efs > EPISODE_FAME_SCORE_MAX:
                        warnings.append(f"行{row_num}: {person_id}/{person_name} - episode_fame_scoreが高め: {efs}")

                    stats["episode_fame_score_max"] = max(stats["episode_fame_score_max"], efs)

                except ValueError:
                    pass  # episode_fame_scoreは必須ではない

    # 最小値がinfのままなら0に
    if stats["fame_score_v3_min"] == float("inf"):
        stats["fame_score_v3_min"] = 0.0

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }


def main():
    """メインエントリポイント"""
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"📋 検証対象: {csv_path}")
    print()

    result = validate_fame_scores(csv_path)

    # 統計表示
    stats = result["stats"]
    print("=== 統計 ===")
    print(f"  総行数: {stats['total_rows']}")
    print(f"  fame_score_v3: {stats['fame_score_v3_count']}件")
    print(f"    最大: {stats['fame_score_v3_max']:.2f}")
    print(f"    最小: {stats['fame_score_v3_min']:.2f}")
    print(f"  episode_fame_score: {stats['episode_fame_score_count']}件")
    print(f"    最大: {stats['episode_fame_score_max']:.2f}")
    print()

    # 警告表示
    if result["warnings"]:
        print(f"⚠️ 警告: {len(result['warnings'])}件")
        for w in result["warnings"][:5]:
            print(f"  {w}")
        if len(result["warnings"]) > 5:
            print(f"  ... 他 {len(result['warnings']) - 5} 件")
        print()

    # エラー表示
    if result["errors"]:
        print(f"❌ エラー: {len(result['errors'])}件")
        for e in result["errors"][:10]:
            print(f"  {e}")
        if len(result["errors"]) > 10:
            print(f"  ... 他 {len(result['errors']) - 10} 件")
        print()
        sys.exit(1)

    print("✅ 検証OK: 異常値なし")
    sys.exit(0)


if __name__ == "__main__":
    main()
