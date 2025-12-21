"""
DuplicationDetector テストモジュール

duplication_detector.py の単体テストを提供します。
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.duplication_detector import DuplicationDetector
from src.source_adapters.base import PersonCandidate


@pytest.fixture
def sample_master_df() -> pd.DataFrame:
    """テスト用のMASTER DataFrame"""
    return pd.DataFrame(
        [
            {
                "person_name": "山田太郎",
                "category": "政治・経済",
                "birth_year": 1960,
                "person_type": "REAL",
            },
            {
                "person_name": "鈴木花子",
                "category": "芸能・エンタメ",
                "birth_year": 1985,
                "person_type": "REAL",
            },
            {
                "person_name": "田中一郎",
                "category": "スポーツ",
                "birth_year": 1970,
                "person_type": "REAL",
            },
            {
                "person_name": "佐藤次郎",
                "category": "科学・技術",
                "birth_year": 1955,
                "person_type": "REAL",
            },
        ]
    )


@pytest.fixture
def detector(sample_master_df: pd.DataFrame) -> DuplicationDetector:
    """テスト用のDuplicationDetectorインスタンス"""
    return DuplicationDetector(sample_master_df)


class TestDuplicationDetectorInit:
    """初期化テスト"""

    def test_init_with_valid_df(self, sample_master_df: pd.DataFrame) -> None:
        """有効なDataFrameで初期化できる"""
        detector = DuplicationDetector(sample_master_df)
        assert detector.master_df is not None
        assert len(detector.master_names) == 4

    def test_init_raises_on_missing_column(self) -> None:
        """person_name列がない場合は例外"""
        df = pd.DataFrame([{"name": "テスト"}])

        with pytest.raises(ValueError, match="person_name"):
            DuplicationDetector(df)

    def test_init_handles_nan_names(self) -> None:
        """NaN値のperson_nameは除外される"""
        df = pd.DataFrame(
            [
                {"person_name": "テスト太郎"},
                {"person_name": None},
                {"person_name": "テスト次郎"},
            ]
        )
        detector = DuplicationDetector(df)
        assert len(detector.master_names) == 2

    def test_init_handles_duplicate_names(self) -> None:
        """重複する人物名はユニーク化される"""
        df = pd.DataFrame(
            [
                {"person_name": "テスト太郎"},
                {"person_name": "テスト太郎"},  # 重複
                {"person_name": "テスト次郎"},
            ]
        )
        detector = DuplicationDetector(df)
        assert len(detector.master_names) == 2


class TestDetectDuplicateLayer1:
    """Layer 1: 完全一致 のテスト"""

    def test_exact_match_found(self, detector: DuplicationDetector) -> None:
        """完全一致する人物を検出"""
        candidate = PersonCandidate(person_name="山田太郎")
        is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

        assert is_dup is True
        assert matched == "山田太郎"
        assert conf == 1.0
        assert layer == "exact"

    def test_no_exact_match(self, detector: DuplicationDetector) -> None:
        """完全一致しない場合は次の層へ（モックで確認）"""
        candidate = PersonCandidate(person_name="未登録太郎")

        # normalize/aliasをモックして完全一致以外をスキップ
        with patch.object(detector, "_load_normalizer") as mock_load:
            mock_normalizer = MagicMock()
            mock_normalizer.normalize.return_value = None
            detector.normalizer = mock_normalizer
            detector.alias_map = {}

            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

            assert is_dup is False
            assert matched is None
            assert conf == 0.0
            assert layer == "none"


class TestDetectDuplicateLayer2:
    """Layer 2: 正規化一致 のテスト"""

    def test_normalized_match_found(self, detector: DuplicationDetector) -> None:
        """正規化後に一致する人物を検出"""
        candidate = PersonCandidate(person_name="山田 太郎")  # スペースあり

        # モックを設定：正規化結果を名前ごとに異なる値で返す
        mock_normalizer = MagicMock()

        def normalize_side_effect(name):
            mock_result = MagicMock()
            # スペースを除去して正規化
            mock_result.normalized_name = name.replace(" ", "").replace("　", "")
            return mock_result

        mock_normalizer.normalize.side_effect = normalize_side_effect

        with patch.object(detector, "_load_normalizer"):
            detector.normalizer = mock_normalizer
            detector.alias_map = {}

            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

            assert is_dup is True
            assert matched == "山田太郎"  # 正規化一致
            assert layer == "normalized"


class TestDetectDuplicateLayer3:
    """Layer 3: 別名一致 のテスト"""

    def test_alias_match_found(self, detector: DuplicationDetector) -> None:
        """別名で登録されている人物を検出"""
        candidate = PersonCandidate(person_name="山田さん")

        # モック: 正規化は一致しないが、別名が一致
        mock_normalizer = MagicMock()
        mock_normalizer.normalize.return_value = None

        with patch.object(detector, "_load_normalizer"):
            detector.normalizer = mock_normalizer
            detector.alias_map = {"山田さん": "山田太郎"}

            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

            assert is_dup is True
            assert matched == "山田太郎"
            assert conf == 1.0
            assert layer == "alias"


class TestDetectDuplicateLayer4:
    """Layer 4: 類似一致 のテスト

    Note: Layer4の完全なテストは_verify_attributesのテストでカバーされています。
    ここでは、Layer1-3で検出されなかった場合のフォールバック動作をテストします。
    """

    def test_no_match_returns_none_layer(self, detector: DuplicationDetector) -> None:
        """どの層でも一致しない場合はnoneを返す"""
        # 存在しない名前、正規化も別名も類似もなし
        candidate = PersonCandidate(person_name="XXXXXXXXYYYYYYYY")

        # 正規化がNoneを返す（正規化対象外）
        mock_normalizer = MagicMock()
        mock_normalizer.normalize.return_value = None

        with patch.object(detector, "_load_normalizer"):
            detector.normalizer = mock_normalizer
            detector.alias_map = {}

            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

            assert is_dup is False
            assert matched is None
            assert conf == 0.0
            assert layer == "none"


class TestVerifyAttributes:
    """_verify_attributes メソッドのテスト"""

    def test_verify_with_matching_category(self, detector: DuplicationDetector) -> None:
        """カテゴリが一致する場合"""
        candidate = PersonCandidate(
            person_name="テスト",
            category="政治・経済",
            birth_year=1960,
        )
        result = detector._verify_attributes(candidate, "山田太郎")

        # category と birth_year が一致するので True
        assert result is True

    def test_verify_with_mismatching_category(self, detector: DuplicationDetector) -> None:
        """カテゴリが不一致の場合"""
        candidate = PersonCandidate(
            person_name="テスト",
            category="スポーツ",
            birth_year=2000,  # 1960と異なる
        )
        result = detector._verify_attributes(candidate, "山田太郎")

        # category も birth_year も不一致なので False
        assert result is False

    def test_verify_with_birth_year_tolerance(self, detector: DuplicationDetector) -> None:
        """生年が±1年以内なら一致とみなす"""
        candidate = PersonCandidate(
            person_name="テスト",
            category="政治・経済",
            birth_year=1961,  # 1960 + 1
        )
        result = detector._verify_attributes(candidate, "山田太郎")

        # 両方一致扱い
        assert result is True

    def test_verify_with_mismatching_person_type_only(self, detector: DuplicationDetector) -> None:
        """person_typeのみが不一致の場合"""
        # person_typeをFICTIONALに設定（マスターはREAL）
        candidate = PersonCandidate(
            person_name="テスト",
            person_type="FICTIONAL",
        )
        result = detector._verify_attributes(candidate, "山田太郎")

        # 1つの属性しかなく、それが不一致なのでFalse
        assert result is False

    def test_verify_with_nonexistent_master_name(self, detector: DuplicationDetector) -> None:
        """マスターに存在しない名前ではFalse"""
        candidate = PersonCandidate(
            person_name="テスト",
            category="政治・経済",
        )
        result = detector._verify_attributes(candidate, "存在しない人物")

        assert result is False


class TestGetStatistics:
    """get_statistics メソッドのテスト"""

    def test_returns_correct_counts(self, detector: DuplicationDetector) -> None:
        """正しい統計情報を返す"""
        stats = detector.get_statistics()

        assert stats["total_persons"] == 4
        assert stats["total_episodes"] == 4  # 各人物1エピソード

    def test_counts_unique_persons(self) -> None:
        """重複する人物名は1としてカウント"""
        df = pd.DataFrame(
            [
                {"person_name": "テスト太郎"},
                {"person_name": "テスト太郎"},  # 重複
                {"person_name": "テスト次郎"},
            ]
        )
        detector = DuplicationDetector(df)
        stats = detector.get_statistics()

        assert stats["total_persons"] == 2
        assert stats["total_episodes"] == 3


class TestLoadNormalizer:
    """_load_normalizer メソッドのテスト"""

    def test_lazy_loading(self, detector: DuplicationDetector) -> None:
        """初期状態ではnormalizerはNone"""
        assert detector.normalizer is None
        assert detector.alias_map is None

    def test_load_only_once(self, detector: DuplicationDetector) -> None:
        """一度ロードしたら再ロードしない"""
        mock_normalizer = MagicMock()
        detector.normalizer = mock_normalizer
        detector.alias_map = {}

        detector._load_normalizer()

        # 既にセットされているので変更されない
        assert detector.normalizer is mock_normalizer


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_master_df(self) -> None:
        """空のDataFrameでも動作する"""
        df = pd.DataFrame(columns=["person_name"])
        detector = DuplicationDetector(df)

        assert len(detector.master_names) == 0

        candidate = PersonCandidate(person_name="テスト")

        # モックでスキップ
        with patch.object(detector, "_load_normalizer"):
            detector.normalizer = MagicMock()
            detector.normalizer.normalize.return_value = None
            detector.alias_map = {}

            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)

            assert is_dup is False

    def test_candidate_with_special_characters(self, detector: DuplicationDetector) -> None:
        """特殊文字を含む名前でも動作する"""
        candidate = PersonCandidate(person_name="テスト(仮)")

        with patch.object(detector, "_load_normalizer"):
            detector.normalizer = MagicMock()
            detector.normalizer.normalize.return_value = None
            detector.alias_map = {}

            # 例外が発生しないことを確認
            is_dup, matched, conf, layer = detector.detect_duplicate(candidate)
            assert is_dup is False
