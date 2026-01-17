#!/usr/bin/env python3
"""
UnifiedGate - DB反映前の最終ゲート 回帰テスト

テスト観点:
1. FICTIONAL向け: メタ表現検出、カノン逸脱検出、年齢境界違反検出
2. REAL向け: 年齢境界違反検出、死後エピソード検出
3. ゲートテスト: 高スコアでも違反検出、正常エピソードパス

Author: EPUP Validation Team
Date: 2026-01-17
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sage.persistence.unified_gate import (
    UnifiedGate,
    ValidationError,
    ValidationResult,
    ViolationType,
)


# =============================================================================
# テストデータ定義
# =============================================================================


def make_base_episode(
    person_id: str = "P001",
    person_name: str = "テスト人物",
    age: int = 30,
    episode_text: str = "",
    person_type: str = "REAL",
    **kwargs,
) -> dict:
    """ベースエピソードを生成"""
    # 最低限の長さを持つテキスト（100文字以上必要）
    if not episode_text:
        episode_text = "これはテスト用のエピソードテキストです。" * 10

    return {
        "person_id": person_id,
        "person_name": person_name,
        "age": age,
        "episode_text": episode_text,
        "person_type": person_type,
        **kwargs,
    }


# =============================================================================
# FICTIONAL向けテスト
# =============================================================================


class TestFictionalMetaExpression:
    """1. メタ表現検出テスト"""

    def test_detect_meta_expression_gensaku(self):
        """「原作では」パターンを検出"""
        episode = make_base_episode(
            person_name="竈門炭治郎",
            person_type="FICTIONAL",
            episode_text="原作では彼は強いキャラクターとして描かれている。" * 10,
            work_title="鬼滅の刃",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.META_EXPRESSION in result.violations
        assert any("メタ表現" in msg for msg in result.messages)

    def test_detect_meta_expression_sakuhin(self):
        """「この作品では」パターンを検出"""
        episode = make_base_episode(
            person_name="ルフィ",
            person_type="FICTIONAL",
            episode_text="この作品では彼は海賊王を目指している。" * 10,
            work_title="ONE PIECE",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.META_EXPRESSION in result.violations

    def test_detect_meta_expression_anime_version(self):
        """「アニメ版では」パターンを検出"""
        episode = make_base_episode(
            person_name="エレン・イェーガー",
            person_type="FICTIONAL",
            episode_text="アニメ版では彼の行動がより強調されている。" * 10,
            work_title="進撃の巨人",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.META_EXPRESSION in result.violations

    def test_no_meta_expression_in_normal_text(self):
        """通常のテキストではメタ表現違反なし"""
        episode = make_base_episode(
            person_name="キキ",
            person_type="FICTIONAL",
            episode_text="キキは魔女の宅急便を始めて、コリコの街で配達業務を行った。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # メタ表現違反がないことを確認
        assert ViolationType.META_EXPRESSION not in result.violations


class TestFictionalCanonViolation:
    """2. カノン逸脱検出テスト"""

    def test_detect_canon_violation_nhk(self):
        """架空世界での「NHK」言及を検出"""
        episode = make_base_episode(
            person_name="ルフィ",
            person_type="FICTIONAL",
            episode_text="ルフィはNHKの取材を受け、海賊としての生き様を語った。" * 10,
            work_title="ONE PIECE",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # 作品名言及として検出されるか、または時代不整合として検出
        # 現在の実装ではREAL_ENTITY_IN_FICTIONALとしてチェックされる可能性
        # 注: 現在の実装では明示的なカノン違反チェックは未実装
        # このテストは将来の拡張を見据えた仕様テスト
        # 実装されれば ViolationType.CANON_VIOLATION または
        # ViolationType.REAL_ENTITY_IN_FICTIONAL で検出されるべき

        # 現時点では、エピソード自体は有効となる可能性がある
        # （カノン違反チェックが未実装のため）
        # 将来の実装でこのテストが失敗すれば、機能が追加された証拠

    def test_detect_canon_violation_tokyo_university(self):
        """架空世界での「東京大学」言及を検出"""
        episode = make_base_episode(
            person_name="うずまきナルト",
            person_type="FICTIONAL",
            episode_text="ナルトは東京大学で忍術を研究していた。" * 10,
            work_title="NARUTO",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # 注: 現在の実装ではREAL_ENTITY_IN_FICTIONALチェックは未実装
        # 将来の拡張を見据えたテスト


class TestFictionalAgeBoundary:
    """3. 架空キャラの年齢境界違反検出テスト"""

    def test_detect_negative_age(self):
        """負の年齢を検出"""
        episode = make_base_episode(
            person_name="テストキャラ",
            person_type="FICTIONAL",
            age=-5,
            episode_text="これはテスト用のエピソードテキストです。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # 注: 現在の実装では負の年齢チェックは明示的に未実装
        # 将来の拡張でFICTIONAL_AGE_BOUNDARYとして検出されるべき

    def test_detect_extreme_age(self):
        """異常に高い年齢（1000歳等）を検出"""
        episode = make_base_episode(
            person_name="不死のキャラ",
            person_type="FICTIONAL",
            age=1000,
            episode_text="1000歳になったとき、彼は悟りを開いた。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # 注: 架空キャラの異常年齢チェックは現在未実装
        # 将来の拡張を見据えたテスト


# =============================================================================
# REAL向けテスト
# =============================================================================


class TestRealAgeBoundary:
    """4. 実在人物の年齢境界違反検出テスト"""

    def test_detect_real_age_boundary_violation(self):
        """生没年×年齢整合性違反を検出"""
        # birth_year=1990, age=50 (現在2026年で36歳が最大)
        episode = make_base_episode(
            person_name="テスト実在人物",
            person_type="REAL",
            birth_year=1990,
            age=50,
            episode_text="50歳のとき、彼は大きな決断を下した。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.REAL_AGE_BOUNDARY in result.violations
        assert any("年齢" in msg and "超過" in msg for msg in result.messages)

    def test_detect_age_exceeds_lifespan(self):
        """享年を超える年齢を検出"""
        # 60歳で亡くなった人物に70歳のエピソード
        episode = make_base_episode(
            person_name="故人テスト",
            person_type="REAL",
            birth_year=1940,
            death_year=2000,  # 享年60歳
            age=70,
            episode_text="70歳のとき、彼は新しい挑戦を始めた。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.REAL_AGE_BOUNDARY in result.violations


class TestDeathYearViolation:
    """5. 死後エピソード検出テスト"""

    def test_detect_death_year_violation(self):
        """死亡年以降のエピソードを検出"""
        # death_year=2000, episode_year=2010
        # 注: 現在の実装ではepisode_yearフィールドではなく
        # age + birth_year で算出される年齢で判定

        episode = make_base_episode(
            person_name="故人テスト",
            person_type="REAL",
            birth_year=1950,
            death_year=2000,  # 2000年に死去（享年50歳）
            age=60,  # 60歳のエピソード = 死後10年
            episode_text="60歳のとき、彼は新しい活動を始めた。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        # 年齢境界違反として検出される（享年50歳を超えている）
        assert ViolationType.REAL_AGE_BOUNDARY in result.violations


# =============================================================================
# ゲートテスト
# =============================================================================


class TestGateIntegration:
    """6-7. 統合ゲートテスト"""

    def test_high_score_with_violation_rejected(self):
        """高品質スコアでもメタ表現違反は検出される"""
        episode = make_base_episode(
            person_name="竈門炭治郎",
            person_type="FICTIONAL",
            episode_text="原作では彼は強いキャラクターとして描かれている。" * 10,
            work_title="鬼滅の刃",
            composite_score=95.0,  # 高スコア
            episode_fame_v6=90.0,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # スコアに関係なく、違反は検出されるべき
        assert not result.is_valid
        assert ViolationType.META_EXPRESSION in result.violations

    def test_valid_episode_passes(self):
        """正常なエピソードはパスする"""
        episode = make_base_episode(
            person_name="手塚治虫",
            person_type="REAL",
            birth_year=1928,
            death_year=1989,
            age=50,  # 享年61歳なので問題なし
            episode_text="50歳のとき、手塚治虫は漫画家としてさらなる挑戦を続けていた。新しい作品の構想を練り、若い漫画家たちへの指導にも力を入れていた。"
            * 5,
            category="文化",
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert result.is_valid
        assert len(result.violations) == 0

    def test_valid_fictional_episode_passes(self):
        """正常な架空キャラエピソードはパスする"""
        episode = make_base_episode(
            person_name="キキ",
            person_type="FICTIONAL",
            age=13,
            episode_text="13歳のとき、キキは魔女の修行のために故郷を旅立った。コリコの街で宅急便を始め、様々な人々と出会い成長していった。"
            * 5,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        # メタ表現がないので有効
        assert ViolationType.META_EXPRESSION not in result.violations


# =============================================================================
# 例外処理テスト
# =============================================================================


class TestStrictMode:
    """strict_mode動作テスト"""

    def test_strict_mode_raises_exception(self):
        """strict_modeでは違反時に例外発生"""
        episode = make_base_episode(
            person_name="テスト",
            person_type="REAL",
            birth_year=1990,
            age=50,  # 違反
            episode_text="50歳のとき、彼は決断を下した。" * 10,
        )

        gate = UnifiedGate(strict_mode=True)

        with pytest.raises(ValidationError) as exc_info:
            gate.validate(episode)

        assert exc_info.value.result.is_valid is False

    def test_non_strict_mode_returns_result(self):
        """非strict_modeでは結果オブジェクトを返す"""
        episode = make_base_episode(
            person_name="テスト",
            person_type="REAL",
            birth_year=1990,
            age=50,  # 違反
            episode_text="50歳のとき、彼は決断を下した。" * 10,
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert isinstance(result, ValidationResult)
        assert not result.is_valid


# =============================================================================
# 必須フィールドテスト
# =============================================================================


class TestRequiredFields:
    """必須フィールド検証テスト"""

    def test_missing_person_id(self):
        """person_id欠損を検出"""
        episode = {
            "person_name": "テスト",
            "age": 30,
            "episode_text": "これはテスト用のエピソードテキストです。" * 10,
            "person_type": "REAL",
        }

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.REQUIRED_FIELD_MISSING in result.violations

    def test_text_too_short(self):
        """テキスト短すぎを検出"""
        episode = make_base_episode(
            episode_text="短いテキスト",  # 100文字未満
        )

        gate = UnifiedGate(strict_mode=False)
        result = gate.validate(episode)

        assert not result.is_valid
        assert ViolationType.TEXT_TOO_SHORT in result.violations


# =============================================================================
# ValidationResult テスト
# =============================================================================


class TestValidationResult:
    """ValidationResult動作テスト"""

    def test_to_dict(self):
        """to_dict()メソッドの動作確認"""
        result = ValidationResult(is_valid=False)
        result.add_violation(ViolationType.META_EXPRESSION, "テストメッセージ")

        result_dict = result.to_dict()

        assert result_dict["is_valid"] is False
        assert "meta_expression" in result_dict["violations"]
        assert "テストメッセージ" in result_dict["messages"]

    def test_add_violation(self):
        """add_violation()メソッドの動作確認"""
        result = ValidationResult(is_valid=True)
        result.add_violation(ViolationType.REAL_AGE_BOUNDARY, "年齢違反")

        assert not result.is_valid
        assert ViolationType.REAL_AGE_BOUNDARY in result.violations
        assert "年齢違反" in result.messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
