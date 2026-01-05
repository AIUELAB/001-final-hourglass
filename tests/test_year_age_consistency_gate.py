#!/usr/bin/env python3
"""年齢×年号 整合性ゲート v2 のテスト

テスト観点:
1. 年号が年齢と整合しないケースが検出される
2. 修正後のマリー・キュリー起点2件が検出されない
3. 年号が複数あっても「主題年が整合」なら過検出しない
4. 回顧型言及パターン（「〜以来」「後に〜」）を除外
5. 架空キャラクター（FICTIONAL）はスキップ
6. 生年データがない場合はスキップ
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts/validation"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from year_age_consistency_gate_v2 import (
    extract_subject_years,
    is_excluded,
    is_retrospective,
    check_episode,
)


class TestExtractSubjectYears:
    """主題年抽出のテスト"""

    def test_extracts_year_from_text(self):
        """基本的な年号抽出"""
        text = "2003年、彼は大きな決断を下した"
        years = extract_subject_years(text)
        assert len(years) == 1
        assert years[0][0] == 2003

    def test_excludes_retrospective_reference_since(self):
        """回顧型「〜以来」を除外"""
        text = "1990年のデビュー以来、第一線で活躍し続けた"
        years = extract_subject_years(text)
        assert len(years) == 0

    def test_excludes_retrospective_reference_from(self):
        """回顧型「〜から」を除外"""
        text = "1985年から続けてきた研究が実を結んだ"
        years = extract_subject_years(text)
        assert len(years) == 0

    def test_excludes_retrospective_reference_later(self):
        """回顧型「後に〜」を除外"""
        text = "この研究が後に2020年のノーベル賞へとつながった"
        years = extract_subject_years(text)
        assert len(years) == 0

    def test_excludes_era_reference(self):
        """年代言及「1990年代」を除外"""
        text = "1990年代に活躍した"
        years = extract_subject_years(text)
        assert len(years) == 0

    def test_excludes_birth_year_reference(self):
        """生年言及を除外"""
        text = "1867年生まれのマリー・キュリーは"
        years = extract_subject_years(text)
        assert len(years) == 0

    def test_multiple_years_mixed_types(self):
        """複数年号の混在（主題年+回顧型）"""
        # 文脈が十分離れている場合、回顧型と主題年を区別できる
        # （50文字以上離す必要あり）
        text = (
            "1990年のデビュー以来、長年にわたり活躍を続けてきた。"
            "様々な困難を乗り越え、多くの経験を積んだ。"
            "そして2003年、彼は大きな決断を下した。"
        )
        years = extract_subject_years(text)
        # 1990年は「〜以来」で除外、2003年は主題年として抽出
        assert len(years) == 1
        assert years[0][0] == 2003


class TestIsRetrospective:
    """回顧型判定のテスト"""

    def test_since_pattern(self):
        """「〜以来」パターン"""
        assert is_retrospective("1990年の成功以来") is True

    def test_from_pattern(self):
        """「〜から」パターン"""
        assert is_retrospective("1990年から") is True

    def test_debut_pattern(self):
        """デビュー年パターン"""
        assert is_retrospective("1990年のデビュー") is True

    def test_later_pattern(self):
        """「後に〜」パターン"""
        assert is_retrospective("後に2020年に達成") is True

    def test_not_retrospective(self):
        """回顧型ではない通常言及"""
        assert is_retrospective("2003年、ノーベル賞を受賞した") is False


class TestCheckEpisode:
    """エピソードチェックのテスト"""

    def test_detects_critical_inconsistency(self):
        """5年以上の乖離をCRITICALとして検出"""
        # 今田耕司（1966年生まれ）、13歳なら1979年が正しい
        # 本文に1970年とあれば9年の乖離でCRITICAL
        row = {
            "episode_id": "TEST-001",
            "person_name": "今田耕司",
            "age": "13",
            "episode_text": "1970年、大阪で活動していた",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is not None
        assert result["severity"] == "CRITICAL"
        assert result["year_diff"] >= 5

    def test_detects_warning_inconsistency(self):
        """3-5年の乖離をWARNINGとして検出"""
        row = {
            "episode_id": "TEST-002",
            "person_name": "今田耕司",
            "age": "13",
            "episode_text": "1975年、大阪で活動していた",  # 1979年が正しい、4年の乖離
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is not None
        assert result["severity"] == "WARNING"
        assert 3 <= result["year_diff"] < 5

    def test_skips_fictional_character(self):
        """架空キャラクターはスキップ"""
        row = {
            "episode_id": "TEST-003",
            "person_name": "ルフィ",
            "age": "20",
            "episode_text": "1999年に冒険を始めた",
            "person_type": "FICTIONAL",
        }
        result = check_episode(row)
        assert result is None

    def test_skips_unknown_birth_year(self):
        """生年データがない人物はスキップ"""
        row = {
            "episode_id": "TEST-004",
            "person_name": "未知の人物XYZ",
            "age": "30",
            "episode_text": "2000年に活動した",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is None

    def test_passes_consistent_episode(self):
        """整合しているエピソードはNoneを返す"""
        # マリー・キュリー（1867年生まれ）、36歳なら1903年が正しい
        row = {
            "episode_id": "EP-000007808",
            "person_name": "マリー・キュリー",
            "age": "36",
            "episode_text": "1903年、ノーベル物理学賞を受賞した",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is None

    def test_excludes_retrospective_in_episode(self):
        """エピソード内の回顧型言及を除外"""
        row = {
            "episode_id": "TEST-005",
            "person_name": "今田耕司",
            "age": "53",  # 1966+53=2019年
            "episode_text": "1990年のデビュー以来、30年以上活躍し続けた",
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 1990年は回顧型として除外されるので、検出されない
        assert result is None


class TestMarieCurieEpisodes:
    """マリー・キュリー起点2件の回帰テスト"""

    def test_ep000004833_consistent(self):
        """EP-000004833（35歳）は整合している"""
        row = {
            "episode_id": "EP-000004833",
            "person_name": "マリー・キュリー",
            "age": "35",
            "episode_text": (
                "あなたと同じ35歳のとき、マリー・キュリーは4年間の過酷な作業の末、"
                "ついに純粋なラジウムの分離に成功した。"
            ),
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 年号が含まれていないので検出されない
        assert result is None

    def test_ep000007808_consistent(self):
        """EP-000007808（36歳）は整合している"""
        row = {
            "episode_id": "EP-000007808",
            "person_name": "マリー・キュリー",
            "age": "36",
            "episode_text": (
                "あなたと同じ36歳のとき、マリー・キュリーは1903年、"
                "ノーベル物理学賞の候補者リストに夫ピエールの名前だけが記載され、"
                "自分の名前が除外されていることを知った。"
            ),
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 36歳=1903年で整合しているので検出されない
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
