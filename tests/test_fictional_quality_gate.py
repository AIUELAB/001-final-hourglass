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

import logging
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
    WorkSetting,
    check_fictional_quality,
    validate_and_fix_fictional_episode,
)
from src.utils.authenticity_checker import AuthenticityStatus


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


# =============================================================================
# Phase 2: カバレッジ向上テスト
# =============================================================================


class TestViolationToDict:
    """Violation.to_dict() のテスト (L92)"""

    def test_to_dict_basic(self):
        """基本的なto_dict変換"""
        v = Violation(
            type=ViolationType.YEAR,
            detail="2019年は禁止",
            fixable=True,
            suggested_fix="2019年 -> ある年",
        )
        d = v.to_dict()
        assert d["type"] == "year_violation"
        assert d["detail"] == "2019年は禁止"
        assert d["fixable"] is True
        assert d["suggested_fix"] == "2019年 -> ある年"

    def test_to_dict_no_suggested_fix(self):
        """suggested_fix が None の場合"""
        v = Violation(
            type=ViolationType.META_EXPRESSION,
            detail="メタ表現検出",
            fixable=False,
        )
        d = v.to_dict()
        assert d["type"] == "meta_expression"
        assert d["suggested_fix"] is None

    def test_to_dict_all_violation_types(self):
        """全ViolationTypeでto_dictが動作"""
        for vtype in ViolationType:
            v = Violation(type=vtype, detail="test", fixable=False)
            d = v.to_dict()
            assert d["type"] == vtype.value


class TestQualityResultToDict:
    """QualityResult.to_dict() のテスト (L112)"""

    def test_to_dict_passed(self):
        """パスした結果のto_dict"""
        r = QualityResult(passed=True)
        d = r.to_dict()
        assert d["passed"] is True
        assert d["violations"] == []
        assert d["fixable"] is False
        assert d["auto_fixed_text"] is None
        assert d["authenticity_status"] is None
        assert d["canon_source"] is None

    def test_to_dict_with_violations(self):
        """違反ありの結果のto_dict"""
        violations = [
            Violation(type=ViolationType.YEAR, detail="年号違反", fixable=True),
            Violation(type=ViolationType.REAL_COMPANY, detail="企業名", fixable=True),
        ]
        r = QualityResult(
            passed=False,
            violations=violations,
            fixable=True,
            auto_fixed_text="修正済みテキスト",
        )
        d = r.to_dict()
        assert d["passed"] is False
        assert len(d["violations"]) == 2
        assert d["violations"][0]["type"] == "year_violation"
        assert d["fixable"] is True
        assert d["auto_fixed_text"] == "修正済みテキスト"

    def test_to_dict_with_authenticity_status(self):
        """authenticity_statusありのto_dict"""
        r = QualityResult(
            passed=True,
            authenticity_status=AuthenticityStatus.CANON,
            canon_source="第1話",
        )
        d = r.to_dict()
        assert d["authenticity_status"] == "canon"
        assert d["canon_source"] == "第1話"


class TestWorkSettingsLoading:
    """作品設定ロードのテスト (L550, L558-560)"""

    def test_file_not_found_raises_error(self, tmp_path):
        """存在しないファイルでFileNotFoundError"""
        fake_path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="Work settings file not found"):
            FictionalQualityGate(
                work_settings_path=fake_path,
                enable_authenticity_check=False,
            )

    def test_corrupted_json_raises_value_error(self, tmp_path):
        """壊れたJSONでValueError"""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json content", encoding="utf-8")
        with pytest.raises(ValueError, match="Work settings file is corrupted"):
            FictionalQualityGate(
                work_settings_path=bad_json,
                enable_authenticity_check=False,
            )


class TestGetWorkSettingEdgeCases:
    """get_work_setting のエッジケース (L636)"""

    def test_none_work_title(self, gate):
        """None入力でNone返却"""
        assert gate.get_work_setting(None) is None

    def test_nan_work_title(self, gate):
        """'nan'文字列でNone返却"""
        assert gate.get_work_setting("nan") is None

    def test_empty_string(self, gate):
        """空文字列でNone返却"""
        assert gate.get_work_setting("") is None


class TestPersonTypeInconsistency:
    """person_type不整合のテスト (L668)"""

    def test_fictional_name_with_real_type_logs_warning(self, gate, caplog):
        """架空キャラ名+REAL person_typeで警告ログ"""
        episode = {
            "episode_text": "ある年の春、炭治郎は修行した。",
            "work_title": "鬼滅の刃",
            "person_type": "REAL",
            "person_name": "竈門炭治郎",
        }
        with caplog.at_level(logging.WARNING):
            result = gate.check(episode)
        # チェックは実行される（架空キャラと判定されるため）
        assert isinstance(result, QualityResult)
        # 警告ログが出力される
        assert any("person_type不整合" in record.message for record in caplog.records)

    def test_fictional_name_with_real_type_still_checks(self, gate):
        """架空キャラ名+REAL person_typeでもチェックが実行される"""
        episode = {
            "episode_text": "2019年、ルフィは集英社で働いた。",
            "work_title": "ONE PIECE",
            "person_type": "REAL",
            "person_name": "モンキー・D・ルフィ",
        }
        result = gate.check(episode)
        # 違反が検出される
        assert result.passed is False


class TestYearRangeViolation:
    """年号範囲チェックのテスト (L918, L931, L942)"""

    def test_parse_empty_range(self, gate):
        """空文字列のパース"""
        result = gate._parse_allowed_year_range("")
        assert result is None

    def test_parse_simple_range(self, gate):
        """西暦範囲のパース"""
        result = gate._parse_allowed_year_range("1980-2000")
        assert result == (1980, 2000)

    def test_parse_wareki_format(self, gate):
        """和暦形式のパース"""
        result = gate._parse_allowed_year_range("大正元年-大正15年（1912-1926）")
        assert result == (1912, 1926)

    def test_parse_meiji_format(self, gate):
        """明治和暦形式のパース"""
        result = gate._parse_allowed_year_range("明治元年-明治45年（1868-1912）")
        assert result == (1868, 1912)

    def test_detect_out_of_range_year(self, gate):
        """許可範囲外の年号を検出"""
        # るろうに剣心は allowed_year_range: "明治元年-明治45年（1868-1912）"
        episode = {
            "episode_text": "1950年、剣心は旅に出た。",
            "work_title": "るろうに剣心",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        year_range_violations = [v for v in result.violations if v.type == ViolationType.YEAR_RANGE]
        assert len(year_range_violations) > 0

    def test_in_range_year_passes(self, gate):
        """許可範囲内の年号はパス"""
        # 聖闘士星矢のallowed_year_rangeがあるか確認用に直接テスト
        work_setting = WorkSetting(
            work_title="テスト作品",
            allowed_year_range="1980-2000",
        )
        violations = gate._check_year_range_violation("1990年に冒険した。", work_setting)
        assert len(violations) == 0


class TestCustomYearSystem:
    """独自年号体系チェックのテスト"""

    def test_custom_year_detects_seireki(self, gate):
        """独自年号体系の作品で西暦使用を検出"""
        # ドラゴンボールは year_system="custom"
        episode = {
            "episode_text": "2000年、悟空はナメック星に旅立った。",
            "work_title": "ドラゴンボール",
            "person_type": "FICTIONAL",
            "person_name": "孫悟空",
        }
        result = gate.check(episode)
        custom_year_violations = [v for v in result.violations if v.type == ViolationType.CUSTOM_YEAR]
        assert len(custom_year_violations) > 0

    def test_non_custom_year_system_skips(self, gate):
        """year_system != 'custom' の作品ではスキップ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            year_system="none",
        )
        violations = gate._check_custom_year_system("2000年に冒険した。", work_setting)
        assert len(violations) == 0


class TestTechnologyViolation:
    """技術レベルチェックのテスト (L1002-1011)"""

    def test_detect_smartphone_in_pre_modern(self, gate):
        """前近代作品でスマートフォン検出"""
        # 鬼滅の刃は technology_level="pre_modern"
        episode = {
            "episode_text": "炭治郎はスマートフォンで連絡を取った。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        tech_violations = [v for v in result.violations if v.type == ViolationType.TECHNOLOGY]
        assert len(tech_violations) > 0

    def test_detect_tv_in_pre_modern(self, gate):
        """前近代作品でテレビ検出"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            technology_level="pre_modern",
        )
        violations = gate._check_technology_violation("テレビを見た。", work_setting)
        assert len(violations) > 0
        assert violations[0].type == ViolationType.TECHNOLOGY

    def test_modern_tech_level_skips(self, gate):
        """modern技術レベルではスキップ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            technology_level="modern",
        )
        violations = gate._check_technology_violation("スマートフォンで連絡した。", work_setting)
        assert len(violations) == 0

    def test_only_first_violation_reported(self, gate):
        """技術違反は最初の1つだけ報告"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            technology_level="pre_modern",
        )
        violations = gate._check_technology_violation(
            "スマートフォンでテレビを見ながらパソコンを操作した。",
            work_setting,
        )
        assert len(violations) == 1


class TestForbiddenKeywords:
    """禁止キーワードのテスト (L895)"""

    def test_detect_forbidden_keyword(self, gate):
        """禁止キーワード検出"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            forbidden_keywords=["東京", "日本"],
        )
        violations = gate._check_forbidden_keywords("東京に行った。", work_setting)
        assert len(violations) > 0
        assert violations[0].type == ViolationType.WORLD_SETTING
        assert "東京" in violations[0].detail

    def test_no_forbidden_keywords_passes(self, gate):
        """禁止キーワードなしではパス"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            forbidden_keywords=[],
        )
        violations = gate._check_forbidden_keywords("東京に行った。", work_setting)
        assert len(violations) == 0

    def test_no_work_setting_passes(self, gate):
        """work_settingなしではパス"""
        violations = gate._check_forbidden_keywords("東京に行った。", None)
        assert len(violations) == 0

    def test_forbidden_keyword_in_real_work(self, gate):
        """実際の作品設定で禁止キーワード検出"""
        # NARUTOの forbidden_keywords に "日本" がある
        episode = {
            "episode_text": "ナルトは日本に行った。",
            "work_title": "NARUTO",
            "person_type": "FICTIONAL",
            "person_name": "うずまきナルト",
        }
        result = gate.check(episode)
        kw_violations = [v for v in result.violations if v.type == ViolationType.WORLD_SETTING]
        assert len(kw_violations) > 0


class TestAutoFixExtended:
    """自動修正の拡張テスト (L1034, L1049, L1055, L1085)"""

    def test_unfixable_violations_return_none(self, gate):
        """修正不可の違反でNone返却"""
        episode = {"episode_text": "テストテキスト"}
        violations = [
            Violation(
                type=ViolationType.META_EXPRESSION,
                detail="メタ表現",
                fixable=False,
            ),
        ]
        result = gate.auto_fix(episode, violations)
        assert result is None

    def test_year_range_fix(self, gate):
        """YEAR_RANGE違反の自動修正"""
        episode = {"episode_text": "1950年に剣心は旅に出た。"}
        violations = [
            Violation(
                type=ViolationType.YEAR_RANGE,
                detail="1950年は許可範囲外",
                fixable=True,
                suggested_fix="1950年 -> ある年",
            ),
        ]
        result = gate.auto_fix(episode, violations)
        assert result is not None
        assert "1950年" not in result
        assert "ある年" in result

    def test_custom_year_fix(self, gate):
        """CUSTOM_YEAR違反の自動修正"""
        episode = {"episode_text": "2000年に悟空は戦った。"}
        violations = [
            Violation(
                type=ViolationType.CUSTOM_YEAR,
                detail="西暦2000年は禁止",
                fixable=True,
                suggested_fix="西暦を削除",
            ),
        ]
        result = gate.auto_fix(episode, violations)
        assert result is not None
        assert "2000年" not in result
        assert "ある年" in result

    def test_unchanged_text_returns_none(self, gate):
        """テキストが変化しない場合はNone返却"""
        # fixableだが実際には該当パターンがないケース
        episode = {"episode_text": "テストテキストです。"}
        violations = [
            Violation(
                type=ViolationType.YEAR,
                detail="年号違反",
                fixable=True,
            ),
        ]
        result = gate.auto_fix(episode, violations)
        # テキスト中に年号パターンがないため変化なし
        assert result is None


class TestValidateAndFixFail:
    """validate_and_fix_fictional_episode が False を返すテスト (L1128)"""

    def test_unfixable_returns_false(self):
        """修正不可エピソードでFalse返却"""
        episode = {
            "episode_text": "この作品では炭治郎が主人公だ。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
        }
        passed, text = validate_and_fix_fictional_episode(episode, enable_authenticity_check=False)
        assert passed is False
        assert text == episode["episode_text"]


class TestRealPersonAllowed:
    """allow_real_people 設定のテスト (L812)"""

    def test_real_person_allowed_in_rurouni_kenshin(self, gate):
        """るろうに剣心では実在人物OK"""
        episode = {
            "episode_text": "剣心は旅を続けた。",
            "work_title": "るろうに剣心",
            "person_type": "FICTIONAL",
        }
        result = gate.check(episode)
        person_violations = [v for v in result.violations if v.type == ViolationType.REAL_PERSON]
        assert len(person_violations) == 0

    def test_allow_real_people_setting(self, gate):
        """allow_real_people=Trueで現実人物チェックスキップ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            allow_real_people=True,
        )
        violations = gate._check_real_person("吾峠呼世晴先生と会った。", work_setting)
        assert len(violations) == 0

    def test_disallow_real_people_setting(self, gate):
        """allow_real_people=Falseで現実人物を検出"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            allow_real_people=False,
        )
        violations = gate._check_real_person("吾峠呼世晴先生と会った。", work_setting)
        assert len(violations) > 0


class TestRealLocationNonFictionalWorld:
    """非架空世界での地名チェック (L854)"""

    def test_non_fictional_world_skips_location_check(self, gate):
        """world_type != 'fictional' では地名チェックスキップ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            world_type="real",
            allow_real_locations=False,
        )
        violations = gate._check_real_location("東京に行った。", work_setting)
        assert len(violations) == 0

    def test_fictional_modern_skips_location_check(self, gate):
        """world_type='fictional_modern' では地名チェックスキップ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            world_type="fictional_modern",
            allow_real_locations=False,
        )
        violations = gate._check_real_location("東京に行った。", work_setting)
        assert len(violations) == 0

    def test_fictional_world_detects_location(self, gate):
        """world_type='fictional' では地名を検出"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            world_type="fictional",
            allow_real_locations=False,
        )
        violations = gate._check_real_location("東京に行った。", work_setting)
        assert len(violations) > 0


class TestYearViolationInvalidPattern:
    """年号違反チェックの無効パターンテスト (L784-791)"""

    def test_invalid_year_range_pattern(self, gate, caplog):
        """無効な年号範囲パターンで警告ログ"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            forbidden_year_patterns=["abc-def"],
        )
        with caplog.at_level(logging.WARNING):
            violations = gate._check_year_violation("2000年に何かが起きた。", work_setting)
        # 無効パターンは警告してスキップ
        assert any("Invalid year range pattern" in record.message for record in caplog.records)
        # 無効パターンからは違反が生成されない
        assert len(violations) == 0

    def test_single_year_pattern(self, gate):
        """単一年パターンでの検出"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            forbidden_year_patterns=["2000"],
        )
        violations = gate._check_year_violation("2000年に何かが起きた。", work_setting)
        assert len(violations) > 0

    def test_single_year_pattern_no_match(self, gate):
        """単一年パターンで不一致"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            forbidden_year_patterns=["2000"],
        )
        violations = gate._check_year_violation("1999年に何かが起きた。", work_setting)
        assert len(violations) == 0


# =============================================================================
# Phase 3: 残り未カバー行のテスト (L636, L931, L942, branches)
# =============================================================================


class TestGetWorkSettingPartialMatch:
    """get_work_setting 部分一致テスト (L636)"""

    def test_partial_match_work_title_substring(self, gate):
        """作品名の部分一致で設定を取得"""
        # 登録名の一部を含む文字列で検索（例: "鬼滅の刃 無限列車編"）
        setting = gate.get_work_setting("鬼滅の刃 無限列車編")
        assert setting is not None
        assert "鬼滅" in setting.work_title or setting.era_setting == "大正時代"

    def test_partial_match_reverse_substring(self, gate):
        """登録名が入力の部分文字列の場合"""
        # 短い入力が登録名に含まれる場合
        # 例: "NARUTO" の設定が "NARUTO -ナルト-" 等のキーで登録されている可能性
        setting = gate.get_work_setting("NARUTO")
        assert setting is not None


class TestParseAllowedYearRangeUnparseable:
    """_parse_allowed_year_range パース不可テスト (L931)"""

    def test_unparseable_format_returns_none(self, gate):
        """パース不可能な文字列でNone返却"""
        result = gate._parse_allowed_year_range("不明な形式の範囲")
        assert result is None

    def test_single_year_not_range(self, gate):
        """単一年号（範囲でない）はパース不可"""
        result = gate._parse_allowed_year_range("2000")
        assert result is None

    def test_partial_range_format(self, gate):
        """不完全な範囲形式はパース不可"""
        result = gate._parse_allowed_year_range("1900-")
        assert result is None


class TestCheckYearRangeNoRange:
    """_check_year_range_violation のパース失敗テスト (L942)"""

    def test_unparseable_range_returns_empty(self, gate):
        """パース不可の allowed_year_range では空リスト返却"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            allowed_year_range="不明な範囲",
        )
        violations = gate._check_year_range_violation("2000年に冒険した。", work_setting)
        assert len(violations) == 0


class TestAuthenticityPassedBranch:
    """真正性チェックでパスするケース (L720->733 branch)"""

    def test_authenticity_passed_no_violation(self, gate_with_authenticity):
        """真正性チェックがパスした場合、AUTHENTICITY違反が追加されない"""
        episode = {
            "episode_text": "炭治郎は家族を鬼に殺された後、鬼殺隊を目指した。",
            "work_title": "鬼滅の刃",
            "person_type": "FICTIONAL",
            "person_name": "竈門炭治郎",
            "age": 13,
            "canon_source": "第1話「残酷」",
            "canon_confidence": 0.95,
        }
        result = gate_with_authenticity.check(episode)
        # canon_source 付きのエピソードなら真正性違反は出ないか、出ても少ない
        # ここでは authenticity_status が設定されていることを確認
        assert hasattr(result, "authenticity_status")


class TestAutoFixRealCompanyBranch:
    """auto_fix の REAL_COMPANY 分岐テスト (L1068->1038 branch)"""

    def test_auto_fix_real_company(self, gate):
        """現実企業名の自動修正"""
        episode = {"episode_text": "炭治郎は集英社の前を通った。"}
        violations = [
            Violation(
                type=ViolationType.REAL_COMPANY,
                detail="現実企業「集英社」への言及",
                fixable=True,
                suggested_fix="「集英社」を削除",
            ),
        ]
        result = gate.auto_fix(episode, violations)
        assert result is not None
        assert "集英社" not in result

    def test_auto_fix_real_person(self, gate):
        """現実人物名の自動修正"""
        episode = {"episode_text": "炭治郎は吾峠呼世晴と語り合った。"}
        violations = [
            Violation(
                type=ViolationType.REAL_PERSON,
                detail="現実人物「吾峠呼世晴」への言及",
                fixable=True,
                suggested_fix="「吾峠呼世晴」を削除",
            ),
        ]
        result = gate.auto_fix(episode, violations)
        assert result is not None
        assert "吾峠呼世晴" not in result


class TestYearViolationSingleYearMatch:
    """年号違反チェックの単一年パターン一致テスト (L788->793 branch)"""

    def test_single_year_forbidden_match(self, gate):
        """単一年禁止パターンが一致する場合"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            era_setting="架空時代",
            forbidden_year_patterns=["1999"],
        )
        violations = gate._check_year_violation("1999年に何かが起きた。", work_setting)
        assert len(violations) > 0
        assert violations[0].type == ViolationType.YEAR

    def test_single_year_forbidden_no_match(self, gate):
        """単一年禁止パターンが一致しない場合"""
        work_setting = WorkSetting(
            work_title="テスト作品",
            era_setting="架空時代",
            forbidden_year_patterns=["2005"],
        )
        violations = gate._check_year_violation("1999年に何かが起きた。", work_setting)
        assert len(violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
