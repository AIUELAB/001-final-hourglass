#!/usr/bin/env python3
"""
人物名重複検出バリデーター

新規人物/エピソード追加時に、既存の人物との重複（表記揺れ）を検出する。

使用例:
    # 全体スキャン
    python scripts/validators/person_name_duplicate_validator.py

    # 特定の人物名をチェック
    python scripts/validators/person_name_duplicate_validator.py --check "エルビス・プレスリー"

    # CI/pre-commit用（重複があればexit 1）
    python scripts/validators/person_name_duplicate_validator.py --strict
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


class PersonNameNormalizer:
    """人物名正規化クラス"""

    # 表記揺れパターン（正規化ルール）
    NORMALIZATION_RULES = [
        # ヴ行 → ブ行
        (r"ヴァ", "バ"),
        (r"ヴィ", "ビ"),
        (r"ヴェ", "ベ"),
        (r"ヴォ", "ボ"),
        (r"ヴ", "ブ"),
        # 長音記号の揺れ
        (r"ー+", "ー"),
        # 中点・スペースの統一
        (r"[・\s　]+", ""),
        # 全角英数→半角
        (r"[Ａ-Ｚａ-ｚ０-９]", lambda m: chr(ord(m.group(0)) - 0xFEE0)),
    ]

    # 同一人物とみなすべきパターン（手動定義）
    KNOWN_ALIASES = {
        "北野武": ["ビートたけし", "たけし"],
        "イチロー": ["鈴木一朗"],
        "ASKA": ["飛鳥涼"],
    }

    @classmethod
    def normalize(cls, name: str) -> str:
        """人物名を正規化"""
        if pd.isna(name):
            return ""
        name = str(name).strip()

        for pattern, replacement in cls.NORMALIZATION_RULES:
            if callable(replacement):
                name = re.sub(pattern, replacement, name)
            else:
                name = re.sub(pattern, replacement, name)

        return name.lower()

    @classmethod
    def get_known_canonical(cls, name: str) -> Optional[str]:
        """既知のエイリアスから正式名を取得"""
        for canonical, aliases in cls.KNOWN_ALIASES.items():
            if name in aliases or name == canonical:
                return canonical
        return None


class PersonNameDuplicateValidator:
    """人物名重複検出バリデーター"""

    def __init__(self, csv_path: str = "preserved/data/MASTER_EPISODES_CURRENT.csv"):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path, low_memory=False)
        self.normalizer = PersonNameNormalizer()
        self._build_index()

    def _build_index(self):
        """正規化名インデックスを構築"""
        self.name_index = defaultdict(list)
        persons = self.df.groupby("person_id").agg({"person_name": "first", "episode_id": "count"}).reset_index()

        for _, row in persons.iterrows():
            norm = self.normalizer.normalize(row["person_name"])
            if norm:
                self.name_index[norm].append(
                    {
                        "person_id": row["person_id"],
                        "person_name": row["person_name"],
                        "count": row["episode_id"],
                    }
                )

    def find_duplicates(self) -> list:
        """重複候補を検出"""
        duplicates = []
        for norm, persons in self.name_index.items():
            if len(persons) > 1:
                duplicates.append(
                    {
                        "normalized": norm,
                        "persons": persons,
                        "severity": "ERROR",
                        "message": f"表記揺れ重複: {[p['person_name'] for p in persons]}",
                    }
                )
        return duplicates

    def check_new_name(self, name: str) -> list:
        """新規人物名が既存と重複しないかチェック"""
        norm = self.normalizer.normalize(name)
        conflicts = []

        # 正規化名での完全一致
        if norm in self.name_index:
            existing = self.name_index[norm]
            conflicts.append(
                {
                    "type": "exact_match",
                    "input_name": name,
                    "existing": existing,
                    "message": f"既存人物と重複: {[p['person_name'] for p in existing]}",
                }
            )

        # 既知のエイリアスチェック
        canonical = self.normalizer.get_known_canonical(name)
        if canonical and canonical != name:
            conflicts.append(
                {
                    "type": "known_alias",
                    "input_name": name,
                    "canonical": canonical,
                    "message": f"既知のエイリアス: {name} → {canonical}",
                }
            )

        return conflicts

    def validate(self) -> dict:
        """全体バリデーション"""
        duplicates = self.find_duplicates()
        return {
            "timestamp": datetime.now().isoformat(),
            "total_persons": len(self.name_index),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
            "status": "FAIL" if duplicates else "PASS",
        }


def main():
    parser = argparse.ArgumentParser(description="人物名重複検出バリデーター")
    parser.add_argument("--check", type=str, help="特定の人物名をチェック")
    parser.add_argument("--strict", action="store_true", help="重複があればexit 1")
    parser.add_argument("--report", action="store_true", help="詳細レポートを保存")
    args = parser.parse_args()

    validator = PersonNameDuplicateValidator()

    if args.check:
        # 特定の名前をチェック
        conflicts = validator.check_new_name(args.check)
        if conflicts:
            print(f"❌ 重複検出: {args.check}")
            for c in conflicts:
                print(f"  {c['message']}")
            return 1
        else:
            print(f"✅ 重複なし: {args.check}")
            return 0

    # 全体スキャン
    result = validator.validate()

    print("=" * 60)
    print("人物名重複チェック")
    print("=" * 60)
    print(f"総人物数: {result['total_persons']}")
    print(f"重複候補: {result['duplicate_count']}件")
    print(f"ステータス: {result['status']}")

    if result["duplicates"]:
        print("\n【重複候補】")
        for dup in result["duplicates"][:10]:
            print(f"  {dup['message']}")

    if args.report:
        report_path = Path("src/reports/logs/person_duplicates.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n詳細: {report_path}")

    if args.strict and result["duplicate_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
