#!/usr/bin/env python3
"""
エピソード年齢検証モジュール

エピソード生成時に未来のエピソードを拒否するための検証ロジック
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.birth_year_database import (
    CURRENT_YEAR,
    get_birth_year,
    get_max_valid_age,
    is_future_episode,
    validate_episode_age,
)


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""

    is_valid: bool
    error_code: Optional[str]
    message: str
    suggested_age: Optional[int] = None
    birth_year: Optional[int] = None
    episode_year: Optional[int] = None


class EpisodeAgeValidator:
    """エピソード年齢検証クラス"""

    # エラーコード
    ERROR_FUTURE_EPISODE = "FUTURE_EPISODE"
    ERROR_AGE_NEGATIVE = "AGE_NEGATIVE"
    ERROR_AGE_TOO_HIGH = "AGE_TOO_HIGH"
    ERROR_BIRTH_YEAR_UNKNOWN = "BIRTH_YEAR_UNKNOWN"

    def __init__(self, current_year: int = None, strict_mode: bool = True):
        """
        初期化

        Args:
            current_year: 現在の年（デフォルトは実際の年）
            strict_mode: 厳格モード（生年不明でもエラーにする）
        """
        self.current_year = current_year or CURRENT_YEAR
        self.strict_mode = strict_mode

    def validate(self, person_name: str, age: int, person_type: str = "REAL") -> ValidationResult:
        """
        エピソード年齢を検証

        Args:
            person_name: 人物名
            age: エピソードの年齢
            person_type: 人物タイプ（REAL/FICTIONAL）

        Returns:
            ValidationResult: 検証結果
        """
        # 架空キャラクターはスキップ
        if person_type != "REAL":
            return ValidationResult(is_valid=True, error_code=None, message="架空キャラクターのため検証スキップ")

        # 基本的な年齢チェック
        if age < 0:
            return ValidationResult(
                is_valid=False, error_code=self.ERROR_AGE_NEGATIVE, message=f"年齢が負の値です: {age}"
            )

        if age > 130:
            return ValidationResult(
                is_valid=False, error_code=self.ERROR_AGE_TOO_HIGH, message=f"年齢が130歳を超えています: {age}"
            )

        # 生年データベースでチェック
        birth_year = get_birth_year(person_name)

        if birth_year is None:
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    error_code=self.ERROR_BIRTH_YEAR_UNKNOWN,
                    message=f"生年データなし: {person_name}（厳格モード）",
                )
            else:
                return ValidationResult(
                    is_valid=True, error_code=None, message=f"警告: 生年データなし（{person_name}）"
                )

        episode_year = birth_year + age
        max_age = self.current_year - birth_year

        if episode_year > self.current_year:
            return ValidationResult(
                is_valid=False,
                error_code=self.ERROR_FUTURE_EPISODE,
                message=f"未来のエピソード: {person_name}の{age}歳は{episode_year}年（現在{self.current_year}年）",
                suggested_age=max_age,
                birth_year=birth_year,
                episode_year=episode_year,
            )

        return ValidationResult(
            is_valid=True, error_code=None, message="OK", birth_year=birth_year, episode_year=episode_year
        )

    def get_valid_age_range(self, person_name: str) -> tuple[int, int]:
        """
        有効な年齢範囲を取得

        Args:
            person_name: 人物名

        Returns:
            (最小年齢, 最大年齢)
        """
        birth_year = get_birth_year(person_name)
        if birth_year is None:
            return (0, 100)  # デフォルト範囲

        max_age = self.current_year - birth_year
        return (0, max(0, max_age))

    def suggest_valid_age(self, person_name: str, requested_age: int) -> int:
        """
        有効な年齢を提案

        Args:
            person_name: 人物名
            requested_age: 要求された年齢

        Returns:
            有効な年齢（最大でmax_age）
        """
        _, max_age = self.get_valid_age_range(person_name)
        return min(requested_age, max_age)


def validate_episode_before_generation(
    person_name: str, age: int, person_type: str = "REAL", current_year: int = None, strict_mode: bool = False
) -> tuple[bool, str, Optional[int]]:
    """
    エピソード生成前の検証（シンプルなインターフェース）

    Args:
        person_name: 人物名
        age: エピソードの年齢
        person_type: 人物タイプ
        current_year: 現在の年
        strict_mode: 厳格モード

    Returns:
        (有効かどうか, メッセージ, 推奨年齢)
    """
    validator = EpisodeAgeValidator(current_year=current_year, strict_mode=strict_mode)
    result = validator.validate(person_name, age, person_type)

    return result.is_valid, result.message, result.suggested_age


def generate_episode_with_validation(generate_func, person_name: str, age: int, person_type: str = "REAL", **kwargs):
    """
    検証付きでエピソードを生成するラッパー

    Args:
        generate_func: 実際の生成関数
        person_name: 人物名
        age: エピソードの年齢
        person_type: 人物タイプ
        **kwargs: 生成関数に渡す追加引数

    Returns:
        生成されたエピソード、または None（検証失敗時）

    Raises:
        ValueError: 未来のエピソードを生成しようとした場合
    """
    is_valid, message, suggested_age = validate_episode_before_generation(person_name, age, person_type)

    if not is_valid:
        if suggested_age is not None:
            raise ValueError(f"{message}\n推奨: {suggested_age}歳以下のエピソードを生成してください")
        else:
            raise ValueError(message)

    return generate_func(person_name=person_name, age=age, person_type=person_type, **kwargs)


if __name__ == "__main__":
    # テスト実行
    print("=" * 60)
    print("エピソード年齢検証テスト")
    print("=" * 60)

    validator = EpisodeAgeValidator(strict_mode=False)

    test_cases = [
        ("堺雅人", 40, "REAL"),  # OK: 2013年
        ("堺雅人", 51, "REAL"),  # OK: 2024年
        ("堺雅人", 52, "REAL"),  # NG: 2025年（未来）
        ("堺雅人", 53, "REAL"),  # NG: 2026年（未来）
        ("綾瀬はるか", 39, "REAL"),  # OK: 2024年
        ("綾瀬はるか", 40, "REAL"),  # NG: 2025年（未来）
        ("大谷翔平", 30, "REAL"),  # OK: 2024年
        ("大谷翔平", 31, "REAL"),  # NG: 2025年（未来）
        ("ドラえもん", 100, "FICTIONAL"),  # OK: 架空
        ("未知の人物", 50, "REAL"),  # WARN: データなし
    ]

    print("\n検証結果:")
    for name, age, ptype in test_cases:
        result = validator.validate(name, age, ptype)
        status = "✅" if result.is_valid else "❌"

        print(f"\n{status} {name} {age}歳 ({ptype})")
        print(f"   メッセージ: {result.message}")

        if result.birth_year:
            print(f"   生年: {result.birth_year}年")
        if result.episode_year:
            print(f"   エピソード年: {result.episode_year}年")
        if result.suggested_age is not None:
            print(f"   推奨年齢: {result.suggested_age}歳以下")

    # 年齢範囲のテスト
    print("\n" + "=" * 60)
    print("有効年齢範囲:")
    for name in ["堺雅人", "大谷翔平", "広瀬すず"]:
        min_age, max_age = validator.get_valid_age_range(name)
        birth_year = get_birth_year(name)
        print(f"  {name}（{birth_year}年生）: {min_age}〜{max_age}歳")
