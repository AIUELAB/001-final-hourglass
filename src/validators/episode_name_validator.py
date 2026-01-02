#!/usr/bin/env python3
"""
エピソード人物名整合性バリデーター（品質ゲート）

保存前にperson_nameとepisode_text冒頭の人物名が一致することを検証する。
不一致の場合は例外を発生させ、保存をブロックする。
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ValidationResult(Enum):
    """バリデーション結果"""

    VALID = "valid"
    MISMATCH = "mismatch"
    NO_PATTERN = "no_pattern"


@dataclass
class NameValidationResult:
    """バリデーション結果"""

    result: ValidationResult
    person_name: str
    text_name: Optional[str]
    message: str


def extract_lead_name(episode_text: str, person_name: str = "") -> Optional[str]:
    """
    リード文から人物名を抽出

    Args:
        episode_text: エピソードテキスト
        person_name: 期待される人物名（最適化用）

    Returns:
        抽出された人物名、または None
    """
    if not episode_text:
        return None

    # person_nameが指定されている場合は優先チェック
    if person_name:
        # 架空キャラ『作品名』形式
        fictional_pattern = rf"^あなたと同じ[\d.]+歳のとき、{re.escape(person_name)}『.+?』は"
        if re.match(fictional_pattern, episode_text):
            return person_name

        # 通常形式
        normal_pattern = rf"^あなたと同じ[\d.]+歳のとき、{re.escape(person_name)}は"
        if re.match(normal_pattern, episode_text):
            return person_name

    # フォールバック: パターンマッチで抽出
    # 架空キャラ形式
    fictional_match = re.match(r"^あなたと同じ[\d.]+歳のとき、(.+?)『.+?』は", episode_text)
    if fictional_match:
        return fictional_match.group(1)

    # 通常形式
    match = re.match(r"^あなたと同じ[\d.]+歳のとき、(.+?)は", episode_text)
    if match:
        return match.group(1)

    return None


def validate_episode_name(person_name: str, episode_text: str, strict: bool = True) -> NameValidationResult:
    """
    エピソードの人物名整合性を検証

    Args:
        person_name: CSVのperson_nameフィールド
        episode_text: エピソードテキスト
        strict: 厳密モード（True: 不一致で例外、False: 警告のみ）

    Returns:
        NameValidationResult

    Raises:
        ValueError: 厳密モードで不一致の場合
    """
    text_name = extract_lead_name(episode_text, person_name)

    if text_name is None:
        return NameValidationResult(
            result=ValidationResult.NO_PATTERN,
            person_name=person_name,
            text_name=None,
            message=f"リード文パターンが見つかりません: {episode_text[:50]}...",
        )

    # 架空キャラ『作品名』形式の場合は作品名を除去して比較
    text_name_clean = re.sub(r"『.+?』$", "", text_name)

    if text_name_clean == person_name:
        return NameValidationResult(
            result=ValidationResult.VALID, person_name=person_name, text_name=text_name, message="OK"
        )

    # 不一致
    result = NameValidationResult(
        result=ValidationResult.MISMATCH,
        person_name=person_name,
        text_name=text_name,
        message=f"人物名不一致: CSVは'{person_name}'、本文は'{text_name}'",
    )

    if strict:
        raise ValueError(result.message)

    return result


class EpisodeNameValidator:
    """
    エピソード人物名バリデーター（クラス版）

    Usage:
        validator = EpisodeNameValidator(strict=True)
        validator.validate(person_name, episode_text)  # 不一致で例外
    """

    def __init__(self, strict: bool = True):
        self.strict = strict
        self.validation_count = 0
        self.mismatch_count = 0

    def validate(self, person_name: str, episode_text: str) -> NameValidationResult:
        """エピソードを検証"""
        self.validation_count += 1
        result = validate_episode_name(person_name, episode_text, self.strict)
        if result.result == ValidationResult.MISMATCH:
            self.mismatch_count += 1
        return result

    def get_stats(self) -> dict:
        """統計を取得"""
        return {
            "validation_count": self.validation_count,
            "mismatch_count": self.mismatch_count,
            "mismatch_rate": self.mismatch_count / max(1, self.validation_count),
        }


if __name__ == "__main__":
    # テスト
    print("=== エピソード人物名バリデーター テスト ===\n")

    test_cases = [
        # (person_name, episode_text, expected_result)
        ("山田太郎", "あなたと同じ30歳のとき、山田太郎は起業した。", ValidationResult.VALID),
        ("毛利蘭", "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。", ValidationResult.VALID),
        ("エイダ・ラヴレース", "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。", ValidationResult.MISMATCH),
        ("田中一郎", "これは不正なフォーマットです。", ValidationResult.NO_PATTERN),
    ]

    validator = EpisodeNameValidator(strict=False)

    for person_name, episode_text, expected in test_cases:
        result = validator.validate(person_name, episode_text)
        status = "✅" if result.result == expected else "❌"
        print(f"{status} {person_name}: {result.result.value}")
        if result.result != ValidationResult.VALID:
            print(f"   {result.message}")
        print()

    print(f"統計: {validator.get_stats()}")
