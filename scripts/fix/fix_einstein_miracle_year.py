#!/usr/bin/env python3
"""
Phase 36: アインシュタイン奇跡の年スコア修正

問題:
- EP-3947C4DE（26歳・奇跡の年）の7軸スコアが低すぎる
- surprise=5.0, memorability=6.0 は物理学史上最も革命的な年に対して不適切
- 結果として50歳エピソードより低いepisode_fame_v6になっている

修正:
- 7軸スコアを内容に見合った適切な値に更新
- episode_fame_v6を再計算
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# 修正対象
TARGET_EPISODE_ID = "EP-3947C4DE"

# 修正値（内容に基づく適切なスコア）
# 「奇跡の年」: 特殊相対性理論、E=mc²、光量子仮説、ブラウン運動
# 物理学史上最も革命的な年の一つ
CORRECTED_SCORES = {
    "memorability_score": 9.5,  # 「奇跡の年」は物理学史で最も記憶に残る年の一つ
    "empathy_score": 7.0,  # 特許庁技術者として働きながらの偉業は共感を呼ぶ
    "surprise_score": 9.5,  # ニュートン以来200年の物理学を覆した革命的内容
    "generation_quality_score": 9.0,  # 高品質な文章
    "educational_value": 9.0,  # 特殊相対性理論、E=mc²は教育的価値が極めて高い
    "story_quality": 8.0,  # 良いストーリー構成
    "factual_density": 10.0,  # 4本の論文、複数の理論など事実密度が高い（維持）
}


def fix_miracle_year_scores(dry_run: bool = True) -> dict:
    """奇跡の年エピソードのスコアを修正"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 対象エピソードを探す
    target_row = None
    target_idx = None
    for idx, row in enumerate(rows):
        if row.get("episode_id") == TARGET_EPISODE_ID:
            target_row = row
            target_idx = idx
            break

    if target_row is None:
        return {"error": f"Episode {TARGET_EPISODE_ID} not found"}

    # 修正前のスコア
    old_scores = {field: float(target_row.get(field, 0) or 0) for field in CORRECTED_SCORES.keys()}

    # スコア修正
    changes = []
    for field, new_value in CORRECTED_SCORES.items():
        old_value = old_scores[field]
        if old_value != new_value:
            changes.append({"field": field, "old": old_value, "new": new_value})
            if not dry_run:
                rows[target_idx][field] = str(new_value)

    # CSV保存（7軸スコアのみ更新、episode_fame_v6は後で再計算）
    if not dry_run and changes:
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {
        "episode_id": TARGET_EPISODE_ID,
        "person_name": target_row.get("person_name"),
        "age": target_row.get("age"),
        "changes": changes,
        "dry_run": dry_run,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="アインシュタイン奇跡の年スコア修正")
    parser.add_argument("--execute", action="store_true", help="実際に修正を適用")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 36: アインシュタイン奇跡の年スコア修正")
    print("=" * 60)
    print()

    print("【問題】")
    print("  - EP-3947C4DE（26歳・奇跡の年）の7軸スコアが低すぎる")
    print("  - surprise=5.0, memorability=6.0 は革命的内容に対して不適切")
    print()

    result = fix_miracle_year_scores(dry_run=not args.execute)

    if "error" in result:
        print(f"❌ エラー: {result['error']}")
        return

    print(f"【対象】{result['episode_id']} ({result['person_name']}, {result['age']}歳)")
    print()

    if result["changes"]:
        print("【修正内容】")
        for c in result["changes"]:
            print(f"  {c['field']}: {c['old']:.1f} → {c['new']:.1f}")
        print()

    if result["dry_run"]:
        print("⚠️  ドライランモード: --execute で実際に適用")
    else:
        print("✓ 修正完了")


if __name__ == "__main__":
    main()
