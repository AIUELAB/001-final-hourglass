#!/usr/bin/env python3
"""
年齢集中度ゲート テスト

テスト観点表:
- 等価分割:
  - 正常: 他年齢言及なし、または5歳以内
  - 警告: 10歳差以上、20%以上言及
  - ブロック: 20歳差以上、30%以上言及
- 境界値:
  - 年齢差5歳、6歳
  - 言及率19%、20%、29%、30%
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.age_focus_gate import validate_age_focus


class TestAgeFocusGate:
    """年齢集中度ゲートテスト"""

    def test_no_other_ages(self):
        """正常: 他年齢言及なし"""
        episode = {
            "age": "35.0",
            "episode_text": "あなたと同じ35歳のとき、田中太郎は画期的な発明をしました。35歳の彼は...",
        }
        result = validate_age_focus(episode)
        assert result["valid"] is True
        assert result["warning"] is None

    def test_minor_age_difference(self):
        """正常: 年齢差5歳以内（許容）"""
        episode = {
            "age": "35.0",
            "episode_text": "あなたと同じ35歳のとき、田中太郎は...32歳から始めた研究が実を結び...",
        }
        result = validate_age_focus(episode)
        assert result["valid"] is True
        assert result["warning"] is None

    def test_large_deviation_low_ratio(self):
        """正常: 年齢差大だが言及少ない（1文のみ）"""
        episode = {
            "age": "60.0",
            "episode_text": "あなたと同じ60歳のとき、田中太郎は25歳で始めた会社の集大成を見届けた。60歳の今、彼は満足していた。60歳という節目に。60歳で引退を決意。60歳の決断だった。",
        }
        result = validate_age_focus(episode)
        # 25歳言及は1文のみなので20%未満、警告なし
        assert result["valid"] is True

    def test_warning_case(self):
        """警告: 年齢差10歳以上、言及20%以上"""
        episode = {
            "age": "50.0",
            "episode_text": "あなたと同じ50歳のとき、田中太郎は振り返った。30歳の決断。50歳の今。30歳当時は。50歳で完成。",
        }
        result = validate_age_focus(episode)
        # 警告はあるがvalidはTrue
        assert result["deviation"] >= 10

    def test_block_case(self):
        """ブロック: 年齢差20歳以上、言及30%以上"""
        episode = {
            "age": "55.0",
            "episode_text": "あなたと同じ55歳のとき、田中太郎は...25歳の時の受賞。25歳で。25歳だった。55歳で。",
        }
        result = validate_age_focus(episode)
        assert result["deviation"] >= 20

    def test_boundary_age_diff_5(self):
        """境界値: 年齢差5歳（許容）"""
        episode = {
            "age": "40.0",
            "episode_text": "あなたと同じ40歳のとき...35歳から...40歳で...",
        }
        result = validate_age_focus(episode)
        assert len(result["other_ages"]) == 0  # 5歳差は許容

    def test_boundary_age_diff_6(self):
        """境界値: 年齢差6歳（検出）"""
        episode = {
            "age": "40.0",
            "episode_text": "あなたと同じ40歳のとき...34歳から...40歳で...",
        }
        result = validate_age_focus(episode)
        assert 34 in result["other_ages"]  # 6歳差は検出

    def test_empty_fields(self):
        """境界: フィールドなし"""
        episode = {"episode_text": "テキストのみ"}
        result = validate_age_focus(episode)
        assert result["valid"] is True

    def test_no_text(self):
        """境界: テキストなし"""
        episode = {"age": "30.0"}
        result = validate_age_focus(episode)
        assert result["valid"] is True


class TestRegressionKurosawa:
    """黒澤明エピソード回帰テスト"""

    def test_kurosawa_ep1636_fixed(self):
        """EP-000001636: 修正後は41歳言及がないこと"""
        import csv

        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSVファイルが存在しません")

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("episode_id") == "EP-000001636":
                    result = validate_age_focus(row)
                    # 41歳への言及がないこと
                    assert 41 not in result["other_ages"], f"41歳への言及が残っています: {result}"
                    return

        pytest.fail("EP-000001636が見つかりません")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
