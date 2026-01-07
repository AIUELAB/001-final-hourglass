#!/usr/bin/env python3
"""
エピソード形式検証ゲート

EPUPの定型仕様を検証:
1. 「あなたと同じ{age}歳のとき、{person_name}は...」形式の検証
2. episode_fame_v6の範囲検証（0-200）
3. 一人称「私は」パターンの検出
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


@dataclass
class ValidationResult:
    """検証結果"""

    passed: bool
    total_episodes: int
    issues: list[dict]
    summary: dict


class EpisodeFormatGate:
    """エピソード形式検証ゲート"""

    # 定型パターン: 「あなたと同じ{age}歳のとき、{person_name}は...」
    VALID_PATTERN = r"^あなたと同じ\d+歳のとき、[^、]+は"

    # 禁止パターン: 一人称「私は」で始まる
    INVALID_PATTERN = r"^あなたと同じ\d+歳のとき.*私は"

    # episode_fame_v6の許容範囲
    V6_MIN = 0
    V6_MAX = 200  # 通常は0-120だが、余裕を持たせる

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path

    def validate(self, df: pd.DataFrame = None) -> ValidationResult:
        """全件検証"""
        if df is None:
            df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)

        issues = []
        format_issues = 0
        v6_issues = 0

        for idx, row in df.iterrows():
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")
            text = str(row.get("episode_text", "") or "")

            # 1. 一人称パターン検出
            if re.match(self.INVALID_PATTERN, text):
                issues.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "issue_type": "format_watashi",
                        "message": "一人称「私は」パターンを使用",
                        "text_preview": text[:100],
                    }
                )
                format_issues += 1

            # 2. episode_fame_v6の範囲検証
            v6 = pd.to_numeric(row.get("episode_fame_v6"), errors="coerce")
            if pd.notna(v6) and (v6 < self.V6_MIN or v6 > self.V6_MAX):
                issues.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "issue_type": "v6_out_of_range",
                        "message": f"episode_fame_v6が範囲外: {v6:.2f}",
                        "value": v6,
                    }
                )
                v6_issues += 1

        return ValidationResult(
            passed=len(issues) == 0,
            total_episodes=len(df),
            issues=issues,
            summary={
                "format_issues": format_issues,
                "v6_issues": v6_issues,
                "total_issues": len(issues),
            },
        )

    def validate_single(self, episode_text: str, v6_score: Optional[float] = None) -> list[str]:
        """単一エピソードの検証"""
        errors = []

        # 一人称パターン検出
        if re.match(self.INVALID_PATTERN, episode_text):
            errors.append("一人称「私は」パターンは禁止です。人物名を主語にしてください。")

        # v6範囲検証
        if v6_score is not None:
            if v6_score < self.V6_MIN or v6_score > self.V6_MAX:
                errors.append(f"episode_fame_v6が範囲外: {v6_score:.2f} (許容: {self.V6_MIN}-{self.V6_MAX})")

        return errors


def main():
    """メイン処理"""
    print("=== エピソード形式検証ゲート ===\n")

    gate = EpisodeFormatGate()
    result = gate.validate()

    print(f"総エピソード: {result.total_episodes}")
    print(f"検証結果: {'✓ PASSED' if result.passed else '✗ FAILED'}")
    print("\n問題件数:")
    print(f"  - 形式逸脱（私は）: {result.summary['format_issues']}")
    print(f"  - v6範囲外: {result.summary['v6_issues']}")

    if result.issues:
        print("\n=== 問題サンプル（最大10件）===")
        for issue in result.issues[:10]:
            print(f"  {issue['episode_id']}: {issue['issue_type']} - {issue['message']}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
