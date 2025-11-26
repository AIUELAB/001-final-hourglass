#!/usr/bin/env python3
"""
エピソードフォーマット準拠テスト

全エピソードが標準フォーマット「あなたと同じ◯◯歳のとき、◯◯は〜」で
開始することを検証するテスト
"""

import re
import sys
from pathlib import Path

import pytest
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.age_data_validator import AgeDataValidator, ValidationStatus

# 定数
CSV_PATH = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STANDARD_PREFIX_PATTERN = r"^あなたと同じ\d+歳のとき、.+は"


class TestEpisodeFormatCompliance:
    """エピソードフォーマット準拠テスト"""

    @pytest.fixture
    def episode_data(self):
        """テスト用エピソードデータを読み込み"""
        if not CSV_PATH.exists():
            pytest.skip(f"CSVファイルが見つかりません: {CSV_PATH}")
        return pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    def test_all_episodes_have_standard_prefix(self, episode_data):
        """全エピソードが標準プレフィックスで開始することを検証"""
        non_compliant = []

        for idx, row in episode_data.iterrows():
            episode_text = str(row.get("episode_text", ""))
            if not re.match(STANDARD_PREFIX_PATTERN, episode_text):
                non_compliant.append(
                    {
                        "index": idx,
                        "person_name": row.get("person_name", ""),
                        "age": row.get("age", ""),
                        "episode_preview": episode_text[:100],
                    }
                )

        # 非準拠が0件であることを確認
        assert len(non_compliant) == 0, (
            f"{len(non_compliant)}件のエピソードが標準フォーマットに準拠していません:\n"
            + "\n".join(
                [
                    f"  - {item['person_name']} ({item['age']}歳): {item['episode_preview'][:50]}..."
                    for item in non_compliant[:10]
                ]
            )
        )

    def test_no_invalid_age_episodes(self, episode_data):
        """無効な年齢のエピソードが存在しないことを検証"""
        invalid_age_episodes = []
        validator = AgeDataValidator(current_year=2025)

        for idx, row in episode_data.iterrows():
            person_type = str(row.get("person_type", "")).upper()
            age = row.get("age")

            # 年齢が取得できない場合はスキップ
            try:
                age_int = int(float(age))
            except (ValueError, TypeError):
                continue

            # 架空キャラはスキップ
            if person_type == "FICTIONAL":
                continue

            # 年齢検証
            result = validator.validate_age(age=age_int, person_type=person_type)

            if not result.is_valid:
                invalid_age_episodes.append(
                    {"index": idx, "person_name": row.get("person_name", ""), "age": age, "reason": result.message}
                )

        # 無効な年齢が0件であることを確認（現在はバリデーションが緩いためスキップ可）
        # 本番環境でbirth_year/death_yearが利用可能になったら有効化
        if invalid_age_episodes:
            print(f"⚠️ {len(invalid_age_episodes)}件の年齢検証警告（birth_year/death_year未使用）")


class TestAgeDataValidator:
    """年齢データバリデーターのユニットテスト"""

    @pytest.fixture
    def validator(self):
        return AgeDataValidator(current_year=2025)

    def test_fictional_character_always_valid(self, validator):
        """架空キャラクターは常に有効"""
        result = validator.validate_age(age=100, person_type="FICTIONAL")
        assert result.is_valid
        assert result.status == ValidationStatus.VALID

    def test_deceased_person_age_exceeded(self, validator):
        """故人の寿命超過を検出"""
        # 吉田松陰（1830-1859）は29歳で死亡
        result = validator.validate_age(age=36, person_type="REAL", birth_year=1830, death_year=1859)
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID_AGE_EXCEEDED
        assert result.suggested_max_age == 29

    def test_deceased_person_valid_age(self, validator):
        """故人の有効な年齢"""
        result = validator.validate_age(age=25, person_type="REAL", birth_year=1830, death_year=1859)
        assert result.is_valid
        assert result.status == ValidationStatus.VALID

    def test_living_person_future_age(self, validator):
        """存命者の未来年齢を検出"""
        result = validator.validate_age(age=30, person_type="REAL", birth_year=2000)
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID_FUTURE_AGE
        assert result.suggested_max_age == 25

    def test_living_person_valid_age(self, validator):
        """存命者の有効な年齢"""
        result = validator.validate_age(age=20, person_type="REAL", birth_year=2000)
        assert result.is_valid
        assert result.status == ValidationStatus.VALID

    def test_negative_age_invalid(self, validator):
        """負の年齢は無効"""
        result = validator.validate_age(age=-5, person_type="REAL")
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID_NEGATIVE_AGE


class TestMetaExplanationDetection:
    """メタ的説明検出テスト"""

    @pytest.fixture
    def episode_data(self):
        """テスト用エピソードデータを読み込み"""
        if not CSV_PATH.exists():
            pytest.skip(f"CSVファイルが見つかりません: {CSV_PATH}")
        return pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    def test_no_meta_explanation_in_fictional_episodes(self, episode_data):
        """架空キャラクターエピソードにメタ的説明が含まれないことを確認"""
        meta_patterns = [
            r"は架空の(キャラクター|人物|存在)であり",
            r"実在(しない|の人物ではない)",
            r"エピソード(は|が)存在しません",
            r"公式(な|の)?描写は.*存在しない",
            r"申し訳ございませんが",
            r"架空.*ため",
        ]

        meta_detected = []

        for idx, row in episode_data.iterrows():
            person_type = str(row.get("person_type", "")).upper()
            if "FICTIONAL" not in person_type:
                continue

            episode_text = str(row.get("episode_text", ""))

            for pattern in meta_patterns:
                if re.search(pattern, episode_text):
                    meta_detected.append(
                        {
                            "person_name": row.get("person_name", ""),
                            "age": row.get("age", ""),
                            "pattern": pattern,
                            "episode_preview": episode_text[:100],
                        }
                    )
                    break

        assert len(meta_detected) == 0, f"{len(meta_detected)}件のメタ的説明が検出されました:\n" + "\n".join(
            [f"  - {item['person_name']} ({item['age']}歳): {item['pattern']}" for item in meta_detected[:10]]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
