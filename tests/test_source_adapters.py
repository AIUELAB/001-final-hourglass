"""
Source Adapters のテスト

PersonCandidate dataclass, SourceAdapter ABC,
ManualSourceAdapter, NHKAsadoraAdapter の動作を検証します。
"""

import pytest
from pathlib import Path

from src.source_adapters.base import PersonCandidate, SourceAdapter
from src.source_adapters.manual_adapter import ManualSourceAdapter
from src.source_adapters.nhk_asadora_adapter import NHKAsadoraAdapter


class TestPersonCandidate:
    """PersonCandidate dataclass のテスト"""

    def test_create_minimal(self):
        """最小構成で作成"""
        candidate = PersonCandidate(person_name="テスト太郎")
        assert candidate.person_name == "テスト太郎"
        assert candidate.person_type == "REAL"
        assert candidate.status == "pending"
        assert candidate.confidence_score == 1.0

    def test_create_full(self):
        """全フィールド指定で作成"""
        candidate = PersonCandidate(
            person_name="山中伸弥",
            category="科学・技術",
            sub_category="医学",
            person_type="REAL",
            description="iPS細胞研究でノーベル賞",
            birth_year=1962,
            death_year=None,
            tier="S+",
            source_name="manual",
            source_url="https://example.com",
            status="active",
        )
        assert candidate.person_name == "山中伸弥"
        assert candidate.category == "科学・技術"
        assert candidate.birth_year == 1962
        assert candidate.tier == "S+"

    def test_validation_empty_name(self):
        """空の人物名でエラー"""
        with pytest.raises(ValueError, match="person_name is required"):
            PersonCandidate(person_name="")

    def test_validation_invalid_birth_year(self):
        """無効な生年でエラー"""
        with pytest.raises(ValueError, match="birth_year must be int"):
            PersonCandidate(person_name="テスト太郎", birth_year="1990")  # type: ignore

    def test_to_dict(self):
        """辞書形式に変換"""
        candidate = PersonCandidate(person_name="テスト太郎", category="テスト", birth_year=1990)
        data = candidate.to_dict()

        assert data["person_name"] == "テスト太郎"
        assert data["category"] == "テスト"
        assert data["birth_year"] == 1990
        assert "validation_errors" in data
        assert "confidence_score" in data


class TestManualSourceAdapter:
    """ManualSourceAdapter のテスト"""

    def test_fetch_candidates_with_limit(self):
        """候補取得（limit指定）"""
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")
        candidates = adapter.fetch_candidates(limit=5)

        assert len(candidates) <= 5
        assert all(isinstance(c, PersonCandidate) for c in candidates)

    def test_fetch_candidates_all(self):
        """候補取得（全件）"""
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")
        candidates = adapter.fetch_candidates()

        assert len(candidates) > 0
        assert all(isinstance(c, PersonCandidate) for c in candidates)

    def test_source_name(self):
        """ソース名が正しい"""
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")
        assert adapter.get_source_name() == "manual_manual_list"

    def test_candidates_have_source_name(self):
        """全候補にsource_nameが設定されている"""
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")
        candidates = adapter.fetch_candidates(limit=3)

        for candidate in candidates:
            assert candidate.source_name == "manual_manual_list"

    def test_file_not_found(self):
        """存在しないファイルでエラー"""
        with pytest.raises(FileNotFoundError):
            ManualSourceAdapter("config/person_sources/nonexistent.csv")

    def test_skip_empty_rows(self):
        """空行をスキップ"""
        # manual_list.csv の実際のデータを使用
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")
        candidates = adapter.fetch_candidates()

        # すべての候補はperson_nameが空でない
        assert all(candidate.person_name for candidate in candidates)

    def test_candidate_validation(self):
        """候補の基本検証が動作する"""
        adapter = ManualSourceAdapter("config/person_sources/80s_celebrities.csv")
        candidates = adapter.fetch_candidates(limit=10)

        # 検証エラーがある候補はskip_reasonが設定されている
        for candidate in candidates:
            if candidate.validation_errors:
                assert candidate.skip_reason == "validation_error"


class TestNHKAsadoraAdapter:
    """NHKAsadoraAdapter のテスト"""

    @pytest.fixture
    def adapter(self):
        """テスト用アダプタ"""
        return NHKAsadoraAdapter()

    def test_fetch_candidates_with_limit(self, adapter):
        """候補取得（limit指定）"""
        candidates = adapter.fetch_candidates(limit=5)

        assert len(candidates) <= 5
        assert all(isinstance(c, PersonCandidate) for c in candidates)

    def test_fetch_candidates_all(self, adapter):
        """候補取得（全件）"""
        candidates = adapter.fetch_candidates()

        assert len(candidates) > 0
        assert all(isinstance(c, PersonCandidate) for c in candidates)

    def test_source_name(self, adapter):
        """ソース名が正しい"""
        assert adapter.get_source_name() == "nhk_asadora"

    def test_candidates_are_real(self, adapter):
        """全候補がREAL（実在人物）"""
        candidates = adapter.fetch_candidates(limit=5)

        for candidate in candidates:
            assert candidate.person_type == "REAL"

    def test_description_generation(self, adapter):
        """descriptionが自動生成される"""
        candidates = adapter.fetch_candidates(limit=5)

        for candidate in candidates:
            # descriptionに「朝ドラ」が含まれる
            if candidate.description:
                assert "朝ドラ" in candidate.description

    def test_default_tier(self, adapter):
        """tierが指定されていない場合デフォルトS"""
        candidates = adapter.fetch_candidates(limit=5)

        # 少なくとも1件はtierが設定されている
        assert all(candidate.tier for candidate in candidates)

    def test_candidates_have_source_name(self, adapter):
        """全候補にsource_nameが設定されている"""
        candidates = adapter.fetch_candidates(limit=3)

        for candidate in candidates:
            assert candidate.source_name == "nhk_asadora"


class TestSourceAdapterInterface:
    """SourceAdapter ABC のインターフェーステスト"""

    def test_cannot_instantiate_abstract_class(self):
        """抽象基底クラスは直接インスタンス化できない"""
        with pytest.raises(TypeError):
            SourceAdapter()  # type: ignore

    def test_manual_adapter_implements_interface(self):
        """ManualSourceAdapterが正しくインターフェースを実装"""
        adapter = ManualSourceAdapter("config/person_sources/manual_list.csv")

        assert hasattr(adapter, "fetch_candidates")
        assert hasattr(adapter, "get_source_name")
        assert callable(adapter.fetch_candidates)
        assert callable(adapter.get_source_name)

    def test_nhk_adapter_implements_interface(self):
        """NHKAsadoraAdapterが正しくインターフェースを実装"""
        adapter = NHKAsadoraAdapter()

        assert hasattr(adapter, "fetch_candidates")
        assert hasattr(adapter, "get_source_name")
        assert callable(adapter.fetch_candidates)
        assert callable(adapter.get_source_name)


class TestValidation:
    """validate_candidate()メソッドのテスト"""

    @pytest.fixture
    def adapter(self):
        """テスト用アダプタ"""
        return ManualSourceAdapter("config/person_sources/manual_list.csv")

    def test_valid_candidate(self, adapter):
        """正常な候補の検証"""
        candidate = PersonCandidate(person_name="テスト太郎", person_type="REAL", tier="S")
        assert adapter.validate_candidate(candidate) is True
        assert len(candidate.validation_errors) == 0

    def test_invalid_person_type(self, adapter):
        """無効なperson_type"""
        candidate = PersonCandidate(
            person_name="テスト太郎",
            person_type="INVALID",  # type: ignore
        )
        assert adapter.validate_candidate(candidate) is False
        assert len(candidate.validation_errors) > 0

    def test_invalid_tier(self, adapter):
        """無効なtier"""
        candidate = PersonCandidate(
            person_name="テスト太郎",
            person_type="REAL",
            tier="Z",  # type: ignore
        )
        assert adapter.validate_candidate(candidate) is False
        assert "Invalid tier" in candidate.validation_errors[0]


if __name__ == "__main__":
    # pytestを直接実行
    pytest.main([__file__, "-v"])
