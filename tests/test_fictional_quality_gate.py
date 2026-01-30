#!/usr/bin/env python3
"""
test_fictional_quality_gate.py

FictionalQualityGate のユニットテスト

検証項目:
1. 年号違反検出
2. 現実人物検出
3. 現実企業検出
4. 現実地名検出
5. メタ表現検出
6. 自動修正機能
7. 作品設定に基づく検証

Author: EPUP Validation Team
Date: 2026-01-15
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.fictional_quality_gate import (
    FictionalQualityGate,
    QualityResult,
    Violation,
    ViolationType,
    QualityViolationError,
    check_fictional_quality,
    validate_and_fix_fictional_episode,
)


# =============================================================================
# テストフィクスチャ
# =============================================================================


@pytest.fixture
def gate():
    """FictionalQualityGate インスタンス（真正性検証無効）"""
    # 既存のテストとの互換性のため、真正性検証は無効化
    return FictionalQualityGate(enable_authenticity_check=False)


@pytest.fixture
def gate_with_authenticity():
    """FictionalQualityGate インスタンス（真正性検証有効）"""
    return FictionalQualityGate(enable_authenticity_check=True)


@pytest.fixture
def kimetsu_episode():
    """鬼滅の刃エピソードサンプル"""
    return {
        "episode_id": "EP-TEST001",
        "person_name": "竈門炭治郎",
        "work_title": "鬼滅の刃",
        "person_type": "FICTIONAL",
        "episode_text": "ある年の春、炭治郎は師匠の鱗滝左近次のもとで修行を積んでいた。厳しい訓練の中で、水の呼吸の基本を習得し始めた。",
    }


@pytest.fixture
def one_piece_episode():
    """ONE PIECEエピソードサンプル"""
    return {
        "episode_id": "EP-TEST002",
        "person_name": "モンキー・D・ルフィ",
        "work_title": "ONE PIECE",
        "person_type": "FICTIONAL",
        "episode_text": "大海賊時代の幕開けから数年後、ルフィは東の海のフーシャ村で海賊への夢を育んでいた。",
    }


# =============================================================================
# 基本機能テスト
# =============================================================================


class TestBasicFunctionality:
    """基本機能のテスト"""

    def test_gate_initialization(self, gate):
        """ゲートの初期化"""
        assert gate is not None
        assert gate.work_settings_path.exists()

    def test_work_setting_lookup(self, gate):
        """作品設定の検索"""
        setting = gate.get_work_setting("鬼滅の刃")
        assert setting is not None
        assert setting.era_setting == "大正時代"

        setting_variant = gate.get_work_setting("Demon Slayer")
        assert setting_variant is not None

    def test_valid_episode_passes(self, gate, kimetsu_episode):
        """正常なエピソードはパス"""
        result = gate.check(kimetsu_episode)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_non_fictional_skipped(self, gate):
        """非FICTIONALはスキップ"""
        episode = {
            "episode_text": "2019年に集英社で働いた。",
            "work_title": "テスト",
            "person_type": "REAL",
        }
        result = gate.check(episode)
        assert result.passed is True


# =============================================================================
# 年号違反検出テスト
# =============================================================================


class TestYearViolation:
    """年号違反検出のテスト"""

    def test_detect_modern_year_in_historical(self, gate):
        """歴史設定作品での現代年号検出"""
        episode = {
            "episode_text": "2019年、炭治郎は鬼殺隊の任務に就いた。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.YEAR for v in result.violations)

    def test_detect_year_in_one_piece(self, gate):
        """架空世界作品での西暦年号検出"""
        episode = {
            "episode_text": "1999年、ルフィは海に出た。",
            "work_title": "ONE PIECE",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.YEAR for v in result.violations)

    def test_allowed_year_in_conan(self, gate):
        """現代設定作品では年号OK"""
        episode = {
            "episode_text": "2020年、コナンは新しい事件に挑んだ。",
            "work_title": "名探偵コナン",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        # 名探偵コナンは現代設定なので年号は許可される
        year_violations = [v for v in result.violations if v.type == ViolationType.YEAR]
        assert len(year_violations) == 0


# =============================================================================
# 現実人物検出テスト
# =============================================================================


class TestRealPersonDetection:
    """現実人物検出のテスト"""

    def test_detect_author_reference(self, gate):
        """作者への言及検出"""
        episode = {
            "episode_text": "炭治郎は吾峠呼世晴先生に感謝した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.REAL_PERSON for v in result.violations)

    def test_detect_voice_actor_reference(self, gate):
        """声優への言及検出"""
        episode = {
            "episode_text": "炭治郎の声は花江夏樹が担当した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.REAL_PERSON for v in result.violations)


# =============================================================================
# 現実企業検出テスト
# =============================================================================


class TestRealCompanyDetection:
    """現実企業検出のテスト"""

    def test_detect_publisher_reference(self, gate):
        """出版社への言及検出"""
        episode = {
            "episode_text": "炭治郎の物語は集英社から出版された。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.REAL_COMPANY for v in result.violations)

    def test_detect_studio_reference(self, gate):
        """スタジオへの言及検出"""
        episode = {
            "episode_text": "炭治郎のアニメはufotableで制作された。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.REAL_COMPANY for v in result.violations)


# =============================================================================
# 現実地名検出テスト
# =============================================================================


class TestRealLocationDetection:
    """現実地名検出のテスト"""

    def test_detect_real_city_in_fictional_world(self, gate):
        """架空世界作品での現実地名検出"""
        episode = {
            "episode_text": "ルフィは東京に到着した。",
            "work_title": "ONE PIECE",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.REAL_LOCATION for v in result.violations)

    def test_allow_real_location_in_jujutsu(self, gate):
        """現代日本設定作品では現実地名OK"""
        episode = {
            "episode_text": "虎杖は渋谷で戦った。",
            "work_title": "呪術廻戦",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        # 呪術廻戦は現代日本設定なので地名は許可される
        location_violations = [v for v in result.violations if v.type == ViolationType.REAL_LOCATION]
        assert len(location_violations) == 0


# =============================================================================
# メタ表現検出テスト
# =============================================================================


class TestMetaExpressionDetection:
    """メタ表現検出のテスト"""

    def test_detect_meta_reference(self, gate):
        """メタ表現検出"""
        episode = {
            "episode_text": "この作品では炭治郎が主人公として活躍する。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.META_EXPRESSION for v in result.violations)

    def test_detect_original_reference(self, gate):
        """原作言及検出"""
        episode = {
            "episode_text": "原作では炭治郎は最終的に勝利した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert any(v.type == ViolationType.META_EXPRESSION for v in result.violations)


# =============================================================================
# 自動修正機能テスト
# =============================================================================


class TestAutoFix:
    """自動修正機能のテスト"""

    def test_auto_fix_year(self, gate):
        """年号の自動修正"""
        episode = {
            "episode_text": "2019年、炭治郎は修行を始めた。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.fixable is True
        assert result.auto_fixed_text is not None
        assert "2019年" not in result.auto_fixed_text
        assert "ある年" in result.auto_fixed_text

    def test_auto_fix_company(self, gate):
        """企業名の自動修正"""
        episode = {
            "episode_text": "炭治郎は集英社に感謝した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.fixable is True
        assert result.auto_fixed_text is not None
        assert "集英社" not in result.auto_fixed_text

    def test_unfixable_meta_expression(self, gate):
        """メタ表現は修正不可"""
        episode = {
            "episode_text": "この作品では炭治郎が主人公だ。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.fixable is False
        assert result.auto_fixed_text is None


# =============================================================================
# ユーティリティ関数テスト
# =============================================================================


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    def test_check_fictional_quality(self, kimetsu_episode):
        """check_fictional_quality関数"""
        # 既存のテストとの互換性のため、真正性検証は無効化
        result = check_fictional_quality(kimetsu_episode, enable_authenticity_check=False)
        assert isinstance(result, QualityResult)
        assert result.passed is True

    def test_validate_and_fix_fictional_episode_pass(self, kimetsu_episode):
        """validate_and_fix_fictional_episode関数（パス）"""
        # 既存のテストとの互換性のため、真正性検証は無効化
        passed, text = validate_and_fix_fictional_episode(kimetsu_episode, enable_authenticity_check=False)
        assert passed is True
        assert len(text) > 0

    def test_validate_and_fix_fictional_episode_fix(self):
        """validate_and_fix_fictional_episode関数（修正）"""
        episode = {
            "episode_text": "2019年、炭治郎は修行した。これは100文字以上のテキストである必要があるので、追加のテキストを入れる。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        # 既存のテストとの互換性のため、真正性検証は無効化
        passed, text = validate_and_fix_fictional_episode(episode, enable_authenticity_check=False)
        assert passed is True
        assert "2019年" not in text


# =============================================================================
# 例外テスト
# =============================================================================


class TestExceptions:
    """例外のテスト"""

    def test_quality_violation_error(self):
        """QualityViolationError"""
        violations = [
            Violation(
                type=ViolationType.YEAR,
                detail="2019年は禁止",
                fixable=False,
            ),
            Violation(
                type=ViolationType.META_EXPRESSION,
                detail="メタ表現検出",
                fixable=False,
            ),
        ]
        error = QualityViolationError(violations)
        assert len(error.violations) == 2
        assert "year_violation" in str(error)
        assert "meta_expression" in str(error)


# =============================================================================
# 複合違反テスト
# =============================================================================


class TestMultipleViolations:
    """複合違反のテスト"""

    def test_multiple_violations(self, gate):
        """複数の違反を同時に検出"""
        episode = {
            "episode_text": "2019年、炭治郎は集英社で吾峠呼世晴先生と会った。この作品では重要なシーンだ。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        assert len(result.violations) >= 3

        violation_types = [v.type for v in result.violations]
        assert ViolationType.YEAR in violation_types
        assert ViolationType.REAL_COMPANY in violation_types
        assert ViolationType.REAL_PERSON in violation_types

    def test_partial_fixable(self, gate):
        """一部のみ修正可能"""
        episode = {
            "episode_text": "2019年、炭治郎はこの作品では重要な存在だ。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert result.passed is False
        # 年号は修正可能だがメタ表現は修正不可なので全体として修正不可
        assert result.fixable is False


# =============================================================================
# エッジケーステスト
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_episode_text(self, gate):
        """空のエピソードテキスト"""
        episode = {
            "episode_text": "",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        # 空テキストは違反なし（別のバリデーションで処理）
        assert result.passed is True

    def test_unknown_work_title(self, gate):
        """不明な作品タイトル"""
        episode = {
            "episode_text": "キャラクターは冒険した。",
            "work_title": "存在しない作品",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        # 作品設定がなくてもチェックは実行される
        assert isinstance(result, QualityResult)

    def test_missing_work_title(self, gate):
        """作品タイトルなし"""
        episode = {
            "episode_text": "キャラクターは冒険した。",
            "work_title": "",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        assert isinstance(result, QualityResult)


# =============================================================================
# RCA-20260130 回帰テスト
# =============================================================================


class TestRCA20260130Regression:
    """
    RCA-20260130: トトロ（EP-260113172800511）メタ要素問題の回帰テスト

    根本原因:
    - detect_meta_element_violations.py が独自のFICTIONAL_CHARACTERSセットを
      定義しており、src/utils/fictional_characters.py のリストと同期していなかった
    - 「トトロ」が独自セットに含まれていなかったため、検出がバイパスされた
    """

    def test_totoro_detected_as_fictional(self):
        """トトロがFICTIONAL_CHARACTERSリストに含まれていること"""
        from src.utils.fictional_characters import is_fictional_character

        assert is_fictional_character("トトロ") is True

    def test_ghibli_characters_detected(self):
        """主要ジブリキャラクターがFICTIONAL_CHARACTERSリストに含まれていること"""
        from src.utils.fictional_characters import is_fictional_character

        ghibli_characters = [
            "トトロ",
            "ナウシカ",
            "アシタカ",
            "サン",
            "千尋",
            "ハク",
            "ハウル",
            "ソフィー",
            "ポニョ",
        ]

        for char in ghibli_characters:
            assert is_fictional_character(char) is True, f"{char} should be detected as fictional"

    def test_totoro_episode_meta_detection(self, gate):
        """トトロのメタ要素違反エピソードが検出されること"""
        # EP-260113172800511 と同様のメタ違反パターン
        episode = {
            "episode_text": "スタジオジブリでの40年間で、1,200万人以上が作品に魅了され、"
            "2001年の「千と千尋の神隠し」では日本アカデミー賞を受賞。",
            "work_title": "となりのトトロ",
            "person_type": "FICTIONAL",
            "person_name": "トトロ",
        }
        result = gate.check(episode)

        # メタ要素違反が検出されること
        assert not result.passed or len(result.violations) > 0


# =============================================================================
# 真正性検証テスト（AuthenticityChecker 統合）
# =============================================================================


class TestAuthenticityIntegration:
    """AuthenticityChecker 統合のテスト"""

    def test_authenticity_check_enabled(self, gate_with_authenticity):
        """真正性検証が有効な場合、canon_source がないエピソードは失敗"""
        episode = {
            "episode_text": "炭治郎は修行を積んでいた。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
            "person_name": "竈門炭治郎",
            # canon_source がない
        }
        result = gate_with_authenticity.check(episode)
        # 真正性違反が検出されること
        assert any(v.type == ViolationType.AUTHENTICITY for v in result.violations)

    def test_authenticity_check_disabled(self, gate):
        """真正性検証が無効な場合、canon_source がなくてもパス可能"""
        episode = {
            "episode_text": "炭治郎は修行を積んでいた。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
            "person_name": "竈門炭治郎",
            # canon_source がない
        }
        result = gate.check(episode)
        # 真正性違反は検出されない
        assert not any(v.type == ViolationType.AUTHENTICITY for v in result.violations)
        assert result.passed is True

    def test_authenticity_result_fields(self, gate_with_authenticity):
        """QualityResult に authenticity_status と canon_source が含まれる"""
        episode = {
            "episode_text": "炭治郎は家族を鬼に殺された。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
            "person_name": "竈門炭治郎",
            "age": 13,
            "canon_source": "第1話「残酷」",
        }
        result = gate_with_authenticity.check(episode)
        # authenticity_status フィールドが存在すること
        assert hasattr(result, "authenticity_status")
        # canon_source フィールドが存在すること
        assert hasattr(result, "canon_source")

    def test_violation_type_authenticity_exists(self):
        """ViolationType.AUTHENTICITY が定義されていること"""
        assert hasattr(ViolationType, "AUTHENTICITY")
        assert ViolationType.AUTHENTICITY.value == "authenticity"

    def test_authenticity_violation_not_fixable(self, gate_with_authenticity):
        """真正性違反は fixable=False であること"""
        episode = {
            "episode_text": "炭治郎は修行した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
            "person_name": "竈門炭治郎",
            # canon_source がない
        }
        result = gate_with_authenticity.check(episode)
        auth_violations = [v for v in result.violations if v.type == ViolationType.AUTHENTICITY]
        # 真正性違反は全て fixable=False
        for v in auth_violations:
            assert v.fixable is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
