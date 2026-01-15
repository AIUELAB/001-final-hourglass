#!/usr/bin/env python3
"""
FICTIONAL文頭フォーマットゲートのテスト

fictional_lead_gate.py の単体テストを提供します。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.fictional_lead_gate import (
    FICTIONAL_LEAD_PATTERN,
    INVALID_WORK_TITLES,
    check_fictional_lead,
    check_fictional_lead_row,
)


class TestFictionalLeadPattern:
    """FICTIONALリードパターンのテスト"""

    def test_valid_fictional_format(self):
        """有効なFICTIONAL形式"""
        text = "あなたと同じ17歳のとき、竈門炭治郎『鬼滅の刃』は鬼殺隊に入隊した。"
        assert FICTIONAL_LEAD_PATTERN.match(text) is not None

    def test_invalid_no_work_title(self):
        """無効: 作品名がない"""
        text = "あなたと同じ17歳のとき、竈門炭治郎は鬼殺隊に入隊した。"
        assert FICTIONAL_LEAD_PATTERN.match(text) is None

    def test_invalid_no_lead(self):
        """無効: あなたと同じで始まらない"""
        text = "17歳のとき、竈門炭治郎『鬼滅の刃』は鬼殺隊に入隊した。"
        assert FICTIONAL_LEAD_PATTERN.match(text) is None

    def test_valid_with_brackets(self):
        """有効: 括弧付きの名前"""
        text = "あなたと同じ45歳のとき、マリオ『スーパーマリオブラザーズ』は新しい冒険に出た。"
        assert FICTIONAL_LEAD_PATTERN.match(text) is not None


class TestCheckFictionalLead:
    """check_fictional_lead関数のテスト"""

    def test_valid_fictional(self):
        """有効なFICTIONAL"""
        is_valid, msg = check_fictional_lead(
            episode_text="あなたと同じ17歳のとき、竈門炭治郎『鬼滅の刃』は鬼殺隊に入隊した。",
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        assert is_valid is True
        assert "OK" in msg

    def test_invalid_no_work_title_in_text(self):
        """無効: テキストに作品名がない"""
        is_valid, msg = check_fictional_lead(
            episode_text="あなたと同じ17歳のとき、竈門炭治郎は鬼殺隊に入隊した。",
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        assert is_valid is False
        assert "文頭に『作品名』がありません" in msg

    def test_real_person_skipped(self):
        """REALはスキップ"""
        is_valid, msg = check_fictional_lead(
            episode_text="あなたと同じ45歳のとき、イチローは引退した。",
            person_type="REAL",
            work_title=None,
        )
        assert is_valid is True
        assert "スキップ" in msg

    def test_invalid_category_work_title(self):
        """無効: カテゴリ名がwork_title"""
        is_valid, msg = check_fictional_lead(
            episode_text="あなたと同じ17歳のとき、キャラ『ディズニー』は冒険した。",
            person_type="FICTIONAL",
            work_title="ディズニー",
        )
        assert is_valid is False
        assert "カテゴリ名" in msg

    def test_empty_text(self):
        """無効: テキストが空"""
        is_valid, msg = check_fictional_lead(episode_text="", person_type="FICTIONAL", work_title="鬼滅の刃")
        assert is_valid is False
        assert "空" in msg

    def test_none_person_type_treated_as_real(self):
        """person_typeがNoneはREAL扱い"""
        is_valid, msg = check_fictional_lead(
            episode_text="あなたと同じ30歳のとき、テストは何かした。",
            person_type=None,
            work_title=None,
        )
        assert is_valid is True


class TestCheckFictionalLeadRow:
    """check_fictional_lead_row関数のテスト"""

    def test_valid_row(self):
        """有効な行データ"""
        row = {
            "episode_text": "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会に出場した。",
            "person_type": "FICTIONAL",
            "work_title": "名探偵コナン",
            "person_name": "毛利蘭",
        }
        is_valid, msg = check_fictional_lead_row(row)
        assert is_valid is True

    def test_invalid_row_no_work_title(self):
        """無効: 作品名なし"""
        row = {
            "episode_text": "あなたと同じ17歳のとき、毛利蘭は空手大会に出場した。",
            "person_type": "FICTIONAL",
            "work_title": "名探偵コナン",
            "person_name": "毛利蘭",
        }
        is_valid, msg = check_fictional_lead_row(row)
        assert is_valid is False

    def test_real_row_passes(self):
        """REAL行は通過"""
        row = {
            "episode_text": "あなたと同じ45歳のとき、イチローは引退した。",
            "person_type": "REAL",
            "work_title": None,
            "person_name": "イチロー",
        }
        is_valid, msg = check_fictional_lead_row(row)
        assert is_valid is True


class TestInvalidWorkTitles:
    """無効なwork_titleリストのテスト"""

    def test_category_names_invalid(self):
        """カテゴリ名は無効"""
        invalid_examples = ["少年漫画", "ディズニー", "アニメ", "ゲーム"]
        for title in invalid_examples:
            assert title in INVALID_WORK_TITLES, f"{title} should be invalid"

    def test_valid_work_titles(self):
        """有効な作品名は含まれない"""
        valid_examples = ["鬼滅の刃", "NARUTO", "ONE PIECE", "名探偵コナン"]
        for title in valid_examples:
            assert title not in INVALID_WORK_TITLES, f"{title} should be valid"


class TestHighQualityScoreViolation:
    """高品質スコアでも違反は落ちるテスト（回帰防止）"""

    def test_high_score_but_invalid_format(self):
        """高スコアでも形式違反は不合格"""
        row = {
            "episode_text": "あなたと同じ17歳のとき、竈門炭治郎は鬼殺隊に入隊した。",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "person_name": "竈門炭治郎",
            "composite_score": 95.0,  # 高スコア
            "generation_quality_score": 9.5,  # 高品質
        }
        is_valid, msg = check_fictional_lead_row(row)
        assert is_valid is False, "高スコアでも形式違反は不合格にすべき"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
