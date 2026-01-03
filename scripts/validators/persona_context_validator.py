#!/usr/bin/env python3
"""
ペルソナ・文脈整合性バリデーター

北野武/ビートたけしのような「複数ペルソナを持つ人物」の
エピソード文脈とグループ名の整合性を検証する。

使用例:
    python scripts/validators/persona_context_validator.py
    python scripts/validators/persona_context_validator.py --fix
"""

import argparse
import json
from pathlib import Path

import pandas as pd

# ペルソナ定義: {person_id: {persona_name: context_keywords}}
PERSONA_DEFINITIONS = {
    "P34EA398": {
        "person_name": "北野武",
        "director_context": ["監督", "映画", "作品", "カンヌ", "ベネチア", "ヴェネツィア", "撮影", "脚本"],
        "comedian_context": ["漫才", "ツービート", "お笑い", "芸人", "コント", "たけし軍団", "ひょうきん族"],
        "group_name": "ツービート",
        "rule": "映画監督文脈ではグループ名を付与しない",
    },
}

# 混在禁止ルール
CONTAMINATION_RULES = [
    {
        "pattern": r"北野武（ツービート）",
        "message": "映画監督文脈で「北野武（ツービート）」は使用禁止",
        "severity": "ERROR",
    },
]


def validate_persona_context(df: pd.DataFrame) -> list:
    """ペルソナ・文脈整合性を検証"""
    violations = []

    for rule in CONTAMINATION_RULES:
        pattern = rule["pattern"]
        matches = df[df["episode_text"].str.contains(pattern, na=False, regex=True)]
        for _, row in matches.iterrows():
            violations.append(
                {
                    "episode_id": row["episode_id"],
                    "person_id": row["person_id"],
                    "person_name": row["person_name"],
                    "pattern": pattern,
                    "message": rule["message"],
                    "severity": rule["severity"],
                    "text_preview": str(row["episode_text"])[:100],
                }
            )

    return violations


def main():
    parser = argparse.ArgumentParser(description="ペルソナ・文脈整合性バリデーター")
    parser.add_argument("--fix", action="store_true", help="検出した問題を自動修正")
    args = parser.parse_args()

    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, low_memory=False)

    print("=" * 60)
    print("ペルソナ・文脈整合性チェック")
    print("=" * 60)

    violations = validate_persona_context(df)

    if not violations:
        print("✅ 問題なし")
        return 0

    print(f"❌ {len(violations)}件の問題を検出")
    for v in violations[:10]:
        print(f"  {v['episode_id']}: {v['message']}")

    # レポート保存
    report_path = Path("src/reports/logs/persona_violations.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(violations, f, ensure_ascii=False, indent=2)
    print(f"\n詳細: {report_path}")

    return 1 if violations else 0


if __name__ == "__main__":
    exit(main())
