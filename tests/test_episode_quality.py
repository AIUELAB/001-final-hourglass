#!/usr/bin/env python3
"""
エピソード品質修正のテスト

テスト対象:
1. 1文目年号検出・修正
2. 定型パターン修正
3. 丁寧語検出
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.gates.post_processor import (
    EpisodePostProcessor,
    apply_post_processing,
)


class TestYearInFirstSentence:
    """1文目年号修正のテスト"""

    def test_no_year_no_change(self):
        """年号がない場合は変更なし"""
        text = "あなたと同じ33歳のとき、坂本龍馬は薩長同盟を仲介しました。"
        result, changes = apply_post_processing(text, "坂本龍馬", 33)
        assert result == text
        assert len(changes) == 0

    def test_year_comma_pattern(self):
        """「は{年}年、」パターンの修正（年号削除）"""
        text = "あなたと同じ40歳のとき、蛍原徹は2008年、相方と活動していました。"
        result, changes = apply_post_processing(text, "蛍原徹", 40)

        # 年号が1文目から消えている
        assert "は2008年、" not in result
        # 年号は削除される（括弧追加なし）
        assert "（2008年）" not in result
        # 変更が記録されている
        assert any("年号削除" in c for c in changes)

    def test_year_ni_pattern(self):
        """「は{年}年に」パターンの修正（年号削除）"""
        text = "あなたと同じ65歳のとき、細川たかしは2015年に歌手生活40周年を迎えました。"
        result, changes = apply_post_processing(text, "細川たかし", 65)

        assert "は2015年に" not in result
        # 年号は削除される（括弧追加なし）
        assert "（2015年）" not in result

    def test_year_no_pattern(self):
        """「は{年}年の」パターンの修正（年号削除、「その」に置換）"""
        text = "あなたと同じ80歳のとき、武者小路実篤は1965年の春、自宅で執筆していました。"
        result, changes = apply_post_processing(text, "武者小路実篤", 80)

        assert "は1965年の" not in result
        assert "はその春" in result
        # 年号は削除される（括弧追加なし）
        assert "（1965年）" not in result

    def test_year_deleted_after_fix(self):
        """修正後、年号は1文目から完全に削除される"""
        text = "あなたと同じ29歳のとき、大谷翔平は2023年、MVPを獲得しました。"
        result, changes = apply_post_processing(text, "大谷翔平", 29)

        # 1文目（最初の句点まで）に年号がないことを確認
        first_period = result.find("。")
        first_sentence = result[:first_period] if first_period > 0 else result
        assert "2023年" not in first_sentence


class TestFormatPattern:
    """定型パターン修正のテスト"""

    def test_valid_pattern_no_change(self):
        """正しい定型パターンは変更なし"""
        text = "あなたと同じ33歳のとき、坂本龍馬は薩長同盟を仲介しました。"
        result, changes = apply_post_processing(text, "坂本龍馬", 33)
        assert result.startswith("あなたと同じ33歳のとき、坂本龍馬は")

    def test_age_mismatch_fixed(self):
        """年齢不一致の修正"""
        text = "あなたと同じ30歳のとき、坂本龍馬は薩長同盟を仲介しました。"
        result, changes = apply_post_processing(text, "坂本龍馬", 33)
        assert "33歳" in result
        assert any("年齢修正" in c for c in changes)

    def test_markdown_header_removed(self):
        """Markdownヘッダーの除去"""
        text = "**坂本龍馬 - 33歳**\n薩長同盟を仲介しました。"
        result, changes = apply_post_processing(text, "坂本龍馬", 33)
        assert not result.startswith("**")
        assert "あなたと同じ33歳のとき、坂本龍馬は" in result


class TestDuplicateName:
    """重複人物名修正のテスト"""

    def test_duplicate_name_removed(self):
        """重複した人物名の除去"""
        text = "あなたと同じ33歳のとき、坂本龍馬は坂本龍馬は薩長同盟を仲介しました。"
        result, changes = apply_post_processing(text, "坂本龍馬", 33)

        # 「坂本龍馬は」が1回だけになる
        assert result.count("坂本龍馬は") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
