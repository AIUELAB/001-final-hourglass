#!/usr/bin/env python3
"""
Phase8関連エピソードの問題検出スクリプト

誤指令F-001/F-002により生成された問題エピソードを検出する：
- 「すでにこの世を去って」などのメタ表現
- 「未来のこと」「到達していない」などの拒否表現
- 「代わりに」「別の年齢」などの回避表現
"""

import csv
import re
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 問題を示唆するパターン
PROBLEMATIC_PATTERNS = [
    # メタ表現
    (r"すでにこの世を去って", "META_DEATH"),
    (r"亡くなった後", "META_DEATH"),
    (r"死去した後", "META_DEATH"),
    # 未来/未到達
    (r"未来のこと", "FUTURE"),
    (r"まだ到達していない", "NOT_REACHED"),
    (r"まだ到来していない", "NOT_REACHED"),
    (r"\d+歳になるのは\d+年", "FUTURE_YEAR"),
    # 拒否/回避
    (r"代わりに.*歳.*のエピソード", "ALTERNATIVE"),
    (r"別の年齢.*生成", "ALTERNATIVE"),
    (r"年齢設定.*変更", "ALTERNATIVE"),
    (r"申し訳.*ません.*が", "REFUSAL"),
    (r"生成.*できません", "REFUSAL"),
]


def detect_problematic_episodes(csv_path: Path) -> List[Dict]:
    """問題エピソードを検出"""
    problematic = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            milestone_tag = row.get("人生の節目タグ", "")
            episode_text = row.get("episode_text", "")
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")
            age = row.get("age", "")

            # phase8関連のみチェック
            if milestone_tag not in ["晩年の挑戦", "若き挑戦"]:
                continue

            # 問題パターンをチェック
            issues = []
            for pattern, issue_type in PROBLEMATIC_PATTERNS:
                if re.search(pattern, episode_text):
                    issues.append(issue_type)

            if issues:
                problematic.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "age": age,
                        "milestone_tag": milestone_tag,
                        "issues": issues,
                        "text_preview": episode_text[:150] + "...",
                    }
                )

    return problematic


def main():
    print("=" * 70)
    print("🔍 Phase8エピソード問題検出")
    print("=" * 70)
    print(f"対象: {MASTER_CSV}")
    print()

    problematic = detect_problematic_episodes(MASTER_CSV)

    if not problematic:
        print("✅ 問題エピソードは検出されませんでした")
        return

    print(f"❌ 問題エピソード: {len(problematic)}件\n")

    # 問題タイプ別カウント
    issue_counts = {}
    for ep in problematic:
        for issue in ep["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    print("📊 問題タイプ別カウント:")
    for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue_type}: {count}件")

    print("\n" + "=" * 70)
    print("📋 問題エピソード一覧（上位20件）")
    print("=" * 70)

    for i, ep in enumerate(problematic[:20], 1):
        print(f"\n[{i}] {ep['episode_id']}")
        print(f"    人物: {ep['person_name']} ({ep['age']}歳)")
        print(f"    タグ: {ep['milestone_tag']}")
        print(f"    問題: {', '.join(ep['issues'])}")
        print(f"    本文: {ep['text_preview']}")

    if len(problematic) > 20:
        print(f"\n... 他 {len(problematic) - 20}件")

    print("\n" + "=" * 70)
    print("💡 推奨アクション")
    print("=" * 70)
    print("1. 上記のエピソードを確認")
    print("2. 問題エピソードを削除または修正")
    print("3. テンプレートにbirth_year/death_yearを追加して再生成")


if __name__ == "__main__":
    main()
