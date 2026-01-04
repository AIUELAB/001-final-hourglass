#!/usr/bin/env python3
"""
年齢×年号 整合性チェックのテスト

テスト観点表:
| # | テストケース | 入力 | 期待結果 | 目的 |
|---|---|---|---|---|
| 1 | 年号が年齢と整合しないケースが検出される | 35歳EP + 本文「1911年受賞」(想定1902年) | CRITICAL検出 | 矛盾検出の動作確認 |
| 2 | 修正後のマリー・キュリー(EP-000004833)が検出されない | 修正済みエピソード | 検出なし | 修正の検証 |
| 3 | 年号が複数あっても主題年が整合していれば過検出しない | 整合EPで過去言及あり | 検出なし | 過検出抑制 |
| 4 | 架空キャラクターはスキップ | FICTIONAL + 不整合年号 | 検出なし | スキップ動作 |
| 5 | 生年データなしの場合はNone返却 | 未登録人物 | None | フェイルセーフ |
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts/validation"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from year_age_consistency_gate import check_episode, extract_years_from_text
from birth_year_database import get_birth_year


class TestYearExtraction:
    """年号抽出のテスト"""

    def test_single_year_extraction(self):
        """単一年号の抽出"""
        text = "1903年にノーベル賞を受賞した"
        years = extract_years_from_text(text)
        assert years == [1903]

    def test_multiple_years_extraction(self):
        """複数年号の抽出"""
        text = "1867年に生まれ、1911年に2度目のノーベル賞を受賞"
        years = extract_years_from_text(text)
        assert 1867 in years
        assert 1911 in years

    def test_no_year_in_text(self):
        """年号がない場合は空リスト"""
        text = "研究に没頭した日々"
        years = extract_years_from_text(text)
        assert years == []

    def test_invalid_year_filtered(self):
        """無効な年号（範囲外）はフィルタリング"""
        text = "西暦500年や3000年は除外される"
        years = extract_years_from_text(text)
        assert 500 not in years
        assert 3000 not in years


class TestCheckEpisode:
    """エピソードチェックのテスト"""

    def test_detects_year_age_mismatch_critical(self):
        """テスト1: 年号が年齢と整合しないケース（CRITICAL）が検出される"""
        # マリー・キュリー (1867年生) の35歳 = 1902年
        # 本文に1911年（9年の乖離）→ CRITICAL
        row = {
            "episode_id": "TEST-001",
            "person_name": "マリー・キュリー",
            "age": "35",
            "episode_text": "1911年に化学分野でノーベル賞を受賞した",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is not None
        assert result["severity"] == "CRITICAL"
        assert result["year_diff"] >= 5

    def test_marie_curie_fixed_episode_not_detected(self):
        """テスト2: 修正後のマリー・キュリー起点エピソードが検出されない"""
        # 修正後: 35歳(1902年)のエピソードに年号断定なし
        row = {
            "episode_id": "EP-000004833",
            "person_name": "マリー・キュリー",
            "age": "35",
            "episode_text": "あなたと同じ35歳のとき、マリー・キュリーは4年間の過酷な作業の末、ついに純粋なラジウムの分離に成功した。",
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 年号がないので検出されない
        assert result is None

    def test_no_false_positive_when_year_matches(self):
        """テスト3: 年号が複数あっても主題年が整合していれば過検出しない"""
        # マリー・キュリー 36歳 = 1903年、本文に1903年 → OK
        row = {
            "episode_id": "EP-000007808",
            "person_name": "マリー・キュリー",
            "age": "36",
            "episode_text": "1903年、ノーベル物理学賞の候補者リストに夫ピエールの名前だけが記載され",
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 年号が整合しているので検出されない
        assert result is None

    def test_fictional_character_skipped(self):
        """テスト4: 架空キャラクターはスキップ"""
        row = {
            "episode_id": "TEST-FICTIONAL",
            "person_name": "ドラえもん",
            "age": "100",
            "episode_text": "2112年に誕生した猫型ロボット",
            "person_type": "FICTIONAL",
        }
        result = check_episode(row)
        assert result is None

    def test_unknown_person_returns_none(self):
        """テスト5: 生年データなしの場合はNone返却"""
        row = {
            "episode_id": "TEST-UNKNOWN",
            "person_name": "架空の人物A",
            "age": "30",
            "episode_text": "2020年に活躍した",
            "person_type": "REAL",
        }
        result = check_episode(row)
        # 生年データがないのでチェック不可 → None
        assert result is None


class TestBirthYearDatabase:
    """生年データベースのテスト"""

    def test_marie_curie_birth_year(self):
        """マリー・キュリーの生年が正しく登録されている"""
        birth_year = get_birth_year("マリー・キュリー")
        assert birth_year == 1867

    def test_pierre_curie_birth_year(self):
        """ピエール・キュリーの生年が正しく登録されている"""
        birth_year = get_birth_year("ピエール・キュリー")
        assert birth_year == 1859

    def test_unknown_person_returns_none(self):
        """未登録人物はNoneを返す"""
        birth_year = get_birth_year("存在しない人物XYZ")
        assert birth_year is None


class TestRealWorldCases:
    """実際のデータに基づくテスト"""

    def test_consistent_episode_passes(self):
        """整合するエピソードはチェックをパス"""
        # 大谷翔平 (1994年生) の26歳 = 2020年
        row = {
            "episode_id": "TEST-OHTANI",
            "person_name": "大谷翔平",
            "age": "26",
            "episode_text": "2020年シーズンでの活躍",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is None

    def test_minor_difference_warning(self):
        """3-4年の差はWARNING"""
        # 大谷翔平 (1994年生) の26歳 = 2020年
        # 本文に2024年（4年の乖離）→ WARNING
        row = {
            "episode_id": "TEST-WARN",
            "person_name": "大谷翔平",
            "age": "26",
            "episode_text": "2024年に記録を達成",
            "person_type": "REAL",
        }
        result = check_episode(row)
        assert result is not None
        assert result["severity"] == "WARNING"
        assert result["year_diff"] == 4
