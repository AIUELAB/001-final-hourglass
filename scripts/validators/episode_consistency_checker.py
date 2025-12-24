#!/usr/bin/env python3
"""
エピソード整合性チェッカー

エピソード生成時およびバッチ処理で以下をチェック：
1. person_name と episode_text 冒頭の整合性
2. グループ名/コンビ名の検出
3. 企業名+個人名パターンの検出
4. 表記揺れの検出

使用例:
    # 単一エピソードをチェック
    python scripts/validators/episode_consistency_checker.py --check "田中太郎" "あなたと同じ30歳のとき、田中太郎は..."

    # 全データベースをスキャン
    python scripts/validators/episode_consistency_checker.py --scan

    # 生成時リアルタイムチェック（API用）
    from episode_consistency_checker import EpisodeConsistencyChecker
    checker = EpisodeConsistencyChecker()
    result = checker.validate_episode(person_name, episode_text)
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

# 同ディレクトリからインポート
sys.path.insert(0, str(Path(__file__).parent))
from group_name_validator import (
    GROUP_PREFIXES,
    HEURISTIC_PATTERNS,
    KNOWN_GROUP_NAMES,
    GroupNameValidator,
)


@dataclass
class ValidationResult:
    """バリデーション結果"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]


class EpisodeConsistencyChecker:
    """エピソード整合性チェッカー"""

    def __init__(self):
        self.group_validator = GroupNameValidator.__new__(GroupNameValidator)
        self.group_validator.df = None

    def validate_episode(self, person_name: str, episode_text: str) -> ValidationResult:
        """
        単一エピソードの整合性をチェック

        Args:
            person_name: 人物名
            episode_text: エピソードテキスト

        Returns:
            ValidationResult: チェック結果
        """
        errors = []
        warnings = []
        suggestions = []

        # 1. グループ名チェック
        is_group, reason = self.group_validator.is_group_name(person_name)
        if is_group:
            errors.append(f"グループ名検出: {reason}")
            suggestion = self.group_validator.suggest_individual_name(person_name)
            if suggestion:
                suggestions.append(f"推奨個人名: {suggestion}")

        # 2. episode_text冒頭との整合性チェック
        text_name = self._extract_name_from_text(episode_text)
        if text_name:
            if text_name != person_name:
                # 完全不一致
                if person_name not in text_name and text_name not in person_name:
                    errors.append(f"名前不整合: person_name='{person_name}' vs text='{text_name}'")
                # 部分一致（許容範囲だが警告）
                elif not text_name.startswith(person_name):
                    warnings.append(f"名前表記差異: person_name='{person_name}' vs text='{text_name}'")

        # 3. ヒューリスティックパターンチェック
        for pattern_name, pattern_info in HEURISTIC_PATTERNS.items():
            if re.match(pattern_info["pattern"], person_name):
                warnings.append(f"ヒューリスティック検出 ({pattern_name}): {pattern_info['description']}")

        # 4. episode_text内のグループ名チェック（主語として使われている場合）
        for group in list(KNOWN_GROUP_NAMES)[:100]:
            if group in episode_text:
                # 「〇〇は」「〇〇が」のパターン（主語）
                if re.search(rf"{re.escape(group)}(は|が|の\w+は)", episode_text):
                    if group != person_name:
                        warnings.append(f"episode_text内にグループ名が主語として存在: '{group}'")

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _extract_name_from_text(self, episode_text: str) -> Optional[str]:
        """episode_textから人物名を抽出"""
        match = re.match(r"あなたと同じ\d+歳のとき、(.+?)(は|が)", episode_text)
        if match:
            return match.group(1)
        return None

    def scan_database(self, csv_path: str = "preserved/data/MASTER_EPISODES_CURRENT.csv") -> dict:
        """
        全データベースをスキャン

        Returns:
            {
                "total": int,
                "errors": list,
                "warnings": list,
                "error_count": int,
                "warning_count": int
            }
        """
        df = pd.read_csv(csv_path, low_memory=False)

        all_errors = []
        all_warnings = []

        for idx, row in df.iterrows():
            person_name = str(row["person_name"])
            episode_text = str(row["episode_text"])
            episode_id = row["episode_id"]

            result = self.validate_episode(person_name, episode_text)

            for error in result.errors:
                all_errors.append({"episode_id": episode_id, "message": error})

            for warning in result.warnings:
                all_warnings.append({"episode_id": episode_id, "message": warning})

        return {
            "total": len(df),
            "errors": all_errors,
            "warnings": all_warnings,
            "error_count": len(all_errors),
            "warning_count": len(all_warnings),
        }


def main():
    parser = argparse.ArgumentParser(description="エピソード整合性チェッカー")
    parser.add_argument("--check", nargs=2, help="単一チェック: person_name episode_text")
    parser.add_argument("--scan", action="store_true", help="全データベースをスキャン")
    parser.add_argument("--strict", action="store_true", help="エラー時に終了コード1")
    args = parser.parse_args()

    checker = EpisodeConsistencyChecker()

    if args.check:
        person_name, episode_text = args.check
        result = checker.validate_episode(person_name, episode_text)

        print(f"\n{'✅ PASS' if result.is_valid else '❌ FAIL'}")
        print(f"person_name: {person_name}")

        if result.errors:
            print("\nエラー:")
            for e in result.errors:
                print(f"  ❌ {e}")

        if result.warnings:
            print("\n警告:")
            for w in result.warnings:
                print(f"  ⚠️ {w}")

        if result.suggestions:
            print("\n提案:")
            for s in result.suggestions:
                print(f"  💡 {s}")

        return 1 if args.strict and not result.is_valid else 0

    if args.scan:
        print("=" * 60)
        print("エピソード整合性スキャン")
        print("=" * 60)

        result = checker.scan_database()

        print(f"\n総エピソード数: {result['total']}")
        print(f"エラー: {result['error_count']}件")
        print(f"警告: {result['warning_count']}件")

        if result["errors"]:
            print("\n【エラー（上位10件）】")
            for e in result["errors"][:10]:
                print(f"  {e['episode_id']}: {e['message']}")

        if args.strict and result["error_count"] > 0:
            return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
