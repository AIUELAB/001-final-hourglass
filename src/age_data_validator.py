#!/usr/bin/env python3
"""
年齢データ検証モジュール

エピソード生成パイプラインで使用する年齢データの検証を行う。
- 故人: death_age を超える年齢を拒否
- 存命者: 現在年齢を超える年齢を拒否
- 架空キャラ: 基本的に許容
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PersonType(Enum):
    """人物タイプ"""

    REAL = "REAL"
    FICTIONAL = "FICTIONAL"
    UNKNOWN = "UNKNOWN"


class ValidationStatus(Enum):
    """検証ステータス"""

    VALID = "VALID"
    INVALID_AGE_EXCEEDED = "INVALID_AGE_EXCEEDED"
    INVALID_FUTURE_AGE = "INVALID_FUTURE_AGE"
    INVALID_NEGATIVE_AGE = "INVALID_NEGATIVE_AGE"
    INVALID_DATA = "INVALID_DATA"
    SKIPPED = "SKIPPED"


@dataclass
class ValidationResult:
    """検証結果"""

    is_valid: bool
    status: ValidationStatus
    message: str
    suggested_max_age: Optional[int] = None


class AgeDataValidator:
    """
    年齢データ検証クラス

    エピソード生成前に年齢データの妥当性を検証する。
    """

    def __init__(self, current_year: int = None):
        """
        Args:
            current_year: 現在年（デフォルト: システム年）
        """
        self.current_year = current_year or datetime.now().year

    def validate_age(
        self,
        age: int,
        person_type: str,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        death_age: Optional[int] = None,
    ) -> ValidationResult:
        """
        年齢データを検証

        Args:
            age: 検証対象の年齢
            person_type: 人物タイプ (REAL, FICTIONAL)
            birth_year: 生年（オプション）
            death_year: 没年（オプション）
            death_age: 死亡年齢（オプション）

        Returns:
            ValidationResult: 検証結果
        """
        # 基本チェック: 負の年齢
        if age < 0:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_NEGATIVE_AGE,
                message=f"年齢が負の値です: {age}",
            )

        # 架空キャラクターは基本的に許容
        person_type_upper = person_type.upper() if person_type else "UNKNOWN"
        if person_type_upper == "FICTIONAL":
            return ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                message="架空キャラクターのため年齢制限なし",
            )

        # 実在人物の検証
        if person_type_upper == "REAL":
            # 故人の場合: 死亡年齢チェック
            if death_age is not None and age > death_age:
                return ValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID_AGE_EXCEEDED,
                    message=f"死亡年齢({death_age}歳)を超えています: {age}歳",
                    suggested_max_age=death_age,
                )

            # 没年と生年から計算
            if death_year is not None and birth_year is not None:
                max_age = death_year - birth_year
                if age > max_age:
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.INVALID_AGE_EXCEEDED,
                        message=f"寿命({max_age}歳)を超えています: {age}歳",
                        suggested_max_age=max_age,
                    )

            # 存命者の場合: 現在年齢チェック
            if death_year is None and birth_year is not None:
                current_age = self.current_year - birth_year
                if age > current_age:
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.INVALID_FUTURE_AGE,
                        message=f"現在年齢({current_age}歳)を超えています: {age}歳",
                        suggested_max_age=current_age,
                    )

        return ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            message="年齢データは有効です",
        )

    def validate_episode_age(
        self,
        episode_text: str,
        person_name: str,
        person_type: str,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        death_age: Optional[int] = None,
    ) -> ValidationResult:
        """
        エピソードテキストから年齢を抽出して検証

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            person_type: 人物タイプ
            birth_year: 生年
            death_year: 没年
            death_age: 死亡年齢

        Returns:
            ValidationResult: 検証結果
        """
        # 標準フォーマットから年齢を抽出
        match = re.match(r"あなたと同じ(\d+)歳のとき", episode_text)
        if not match:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_DATA,
                message="標準フォーマットから年齢を抽出できません",
            )

        age = int(match.group(1))
        return self.validate_age(
            age=age,
            person_type=person_type,
            birth_year=birth_year,
            death_year=death_year,
            death_age=death_age,
        )


def validate_age_for_generation(
    age: int,
    person_type: str,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
) -> tuple[bool, str]:
    """
    エピソード生成前の年齢検証（シンプルなインターフェース）

    Args:
        age: 生成対象の年齢
        person_type: 人物タイプ
        birth_year: 生年
        death_year: 没年

    Returns:
        (is_valid, message): 検証結果とメッセージ
    """
    validator = AgeDataValidator()
    death_age = None
    if death_year and birth_year:
        death_age = death_year - birth_year

    result = validator.validate_age(
        age=age,
        person_type=person_type,
        birth_year=birth_year,
        death_year=death_year,
        death_age=death_age,
    )

    return result.is_valid, result.message


if __name__ == "__main__":
    # テスト
    validator = AgeDataValidator(current_year=2025)

    # 架空キャラ: 許容
    result = validator.validate_age(100, "FICTIONAL")
    print(f"架空キャラ 100歳: {result}")

    # 故人（吉田松陰: 1830-1859）
    result = validator.validate_age(36, "REAL", birth_year=1830, death_year=1859)
    print(f"吉田松陰 36歳: {result}")

    result = validator.validate_age(29, "REAL", birth_year=1830, death_year=1859)
    print(f"吉田松陰 29歳: {result}")

    # 存命者（2000年生まれ）
    result = validator.validate_age(30, "REAL", birth_year=2000)
    print(f"2000年生まれ 30歳: {result}")

    result = validator.validate_age(25, "REAL", birth_year=2000)
    print(f"2000年生まれ 25歳: {result}")
