#!/usr/bin/env python3
"""
年齢-本文整合性テスト

テスト観点表:
- 等価分割:
  - 正常: field_age == text_age
  - 異常: field_age != text_age
  - 境界: 年齢なし、本文なし、パターンなし
- 境界値:
  - age=0, age=1, age=150
  - 「同じ0歳」「同じ1歳」「同じ100歳」
"""

import pytest

pytestmark = pytest.mark.integration
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.age_text_consistency_gate import (
    validate_age_text_consistency,
    check_all_episodes,
)


class TestAgeTextConsistency:
    """年齢-本文整合性テスト"""

    def test_matching_age(self):
        """正常: フィールドと本文の年齢が一致"""
        episode = {"age": "25.0", "episode_text": "あなたと同じ25歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True
        assert result["error"] is None

    def test_mismatching_age(self):
        """異常: フィールドと本文の年齢が不一致"""
        episode = {"age": "35.0", "episode_text": "あなたと同じ25歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is False
        assert "field_age=35" in result["error"]
        assert "text_age=25" in result["error"]

    def test_no_age_field(self):
        """境界: ageフィールドなし"""
        episode = {"episode_text": "あなたと同じ25歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True

    def test_no_text(self):
        """境界: episode_textなし"""
        episode = {
            "age": "25.0",
        }
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True

    def test_no_age_pattern_in_text(self):
        """境界: 本文に「同じX歳」パターンなし"""
        episode = {"age": "25.0", "episode_text": "これは年齢パターンのないテキストです。"}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True

    def test_boundary_age_zero(self):
        """境界値: 0歳"""
        episode = {"age": "0", "episode_text": "あなたと同じ0歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True

    def test_boundary_age_one(self):
        """境界値: 1歳"""
        episode = {"age": "1.0", "episode_text": "あなたと同じ1歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True

    def test_boundary_age_hundred(self):
        """境界値: 100歳"""
        episode = {"age": "100", "episode_text": "あなたと同じ100歳のとき、田中太郎は..."}
        result = validate_age_text_consistency(episode)
        assert result["valid"] is True


class TestRegressionTanakaMinami:
    """田中みな実問題の回帰テスト"""

    def test_tanaka_minami_ep000009352_fixed(self):
        """EP-000009352: 田中みな実のage=25が正しく設定されていること"""
        import csv

        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSVファイルが存在しません")

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("episode_id") == "EP-000009352":
                    age = float(row.get("age", 0))
                    assert abs(age - 25.0) < 0.1, f"EP-000009352の年齢が不正: {age}"

                    # 本文との整合性も確認
                    result = validate_age_text_consistency(row)
                    assert result["valid"], f"年齢-本文不整合: {result['error']}"
                    return

        pytest.fail("EP-000009352が見つかりません")


class TestFullDatasetConsistency:
    """全データセットの整合性テスト"""

    def test_no_age_text_mismatches_in_dataset(self):
        """全エピソードで年齢-本文不整合がないこと"""
        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSVファイルが存在しません")

        issues = check_all_episodes(str(csv_path))
        assert len(issues) == 0, f"年齢-本文不整合が{len(issues)}件あります:\n" + "\n".join(
            f"  - {i['episode_id']} ({i['person_name']}): {i['error']}" for i in issues[:5]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
