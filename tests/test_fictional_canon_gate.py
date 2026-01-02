#!/usr/bin/env python3
"""
EPUP: 架空キャラ カノン検証ゲート 回帰テスト

テスト観点:
1. 一般的キャリア文の検出
2. 不自然な年齢設定の検出
3. 肩書プレフィックスの検出
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validators.fictional_canon_validator import (
    check_career_templates,
    check_title_prefix,
    check_unnatural_age,
    validate_episode,
)


class TestCareerTemplateDetection:
    """一般的キャリア文の検出テスト"""

    def test_detects_specialization(self):
        """専門性確立の検出"""
        text = "ジジは魔女の宅急便業における専門性の確立に取り組んでいました。"
        violations = check_career_templates(text)
        assert len(violations) >= 1
        assert any("専門性確立" in v[0] for v in violations)

    def test_detects_leadership(self):
        """指導者表現の検出"""
        text = "後進の魔女たちへの指導者としての役割を担い始めた時期です。"
        violations = check_career_templates(text)
        assert len(violations) >= 1
        assert any("指導者表現" in v[0] for v in violations)

    def test_detects_communication(self):
        """コミュニケーション表現の検出"""
        text = "コミュニケーションの重要性を若い魔女たちに伝えることに情熱を注ぎました。"
        violations = check_career_templates(text)
        assert len(violations) >= 1
        assert any("コミュニケーション" in v[0] for v in violations)

    def test_detects_career_balance(self):
        """キャリアバランス表現の検出"""
        text = "キャリアと個人生活のバランスを取りながら、成長を遂げた。"
        violations = check_career_templates(text)
        assert len(violations) >= 1
        assert any("キャリアバランス" in v[0] for v in violations)

    def test_no_violation_for_normal_text(self):
        """通常のテキストでは違反なし"""
        text = "キキと共にコリコの街で宅急便を始めました。"
        violations = check_career_templates(text)
        assert len(violations) == 0


class TestUnnaturalAgeDetection:
    """不自然な年齢設定の検出テスト"""

    def test_detects_cat_with_adult_age(self):
        """猫キャラに成人年齢"""
        assert check_unnatural_age("ジジ", 30) is True

    def test_detects_dog_with_adult_age(self):
        """犬キャラに成人年齢"""
        assert check_unnatural_age("スヌーピー", 30) is True

    def test_detects_toy_with_adult_age(self):
        """おもちゃキャラに成人年齢"""
        assert check_unnatural_age("ウッディ", 30) is True
        assert check_unnatural_age("バズ・ライトイヤー", 35) is True

    def test_no_violation_for_child_age(self):
        """子供の年齢は違反なし"""
        assert check_unnatural_age("ジジ", 10) is False

    def test_no_violation_for_human_character(self):
        """人間キャラは成人年齢でも違反なし"""
        assert check_unnatural_age("キキ", 30) is False


class TestTitlePrefixDetection:
    """肩書プレフィックスの検出テスト"""

    def test_detects_city_mayor(self):
        """地名+市長の検出"""
        violations = check_title_prefix("ニューヨーク市長マイケル・ブルームバーグ")
        assert len(violations) >= 1
        assert any("地名+役職" in v[0] for v in violations)

    def test_detects_sport_prefix(self):
        """スポーツ名プレフィックスの検出"""
        violations = check_title_prefix("バスケ・ルカ・ドンチッチ")
        assert len(violations) >= 1
        assert any("スポーツ名" in v[0] for v in violations)

    def test_detects_org_prefix(self):
        """組織名プレフィックスの検出"""
        violations = check_title_prefix("マンチェスター・シティ・ハーランド")
        assert len(violations) >= 1
        assert any("組織名" in v[0] for v in violations)

    def test_no_violation_for_normal_name(self):
        """通常の名前では違反なし"""
        violations = check_title_prefix("マイケル・ブルームバーグ")
        assert len(violations) == 0


class TestValidateEpisode:
    """エピソード検証の統合テスト"""

    def test_jiji_episode_is_invalid(self):
        """ジジのエピソード（削除済み）は無効"""
        row = {
            "episode_id": "E441CD69E",
            "person_name": "ジジ",
            "person_type": "FICTIONAL",
            "age": 30,
            "episode_text": "あなたと同じ30歳のとき、ジジは魔女の宅急便業における専門性の確立に取り組んでいました。",
        }
        result = validate_episode(row)
        assert result["is_valid"] is False
        assert len(result["violations"]) >= 1

    def test_valid_episode(self):
        """正常なエピソードは有効"""
        row = {
            "episode_id": "TEST001",
            "person_name": "キキ",
            "person_type": "FICTIONAL",
            "age": 13,
            "episode_text": "あなたと同じ13歳のとき、キキは魔女の修行のために故郷を旅立ちました。",
        }
        result = validate_episode(row)
        assert result["is_valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
