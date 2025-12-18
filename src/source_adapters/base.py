"""
Source Adapter Base - 候補ソースアダプタの抽象基底クラス

このモジュールは人物候補を収集するための共通インターフェースを定義します。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PersonCandidate:
    """
    候補人物の共通スキーマ

    Attributes:
        person_name: 人物名（必須）
        category: カテゴリ（例: 音楽、スポーツ、etc）
        sub_category: サブカテゴリ（オプション）
        person_type: 人物タイプ（REAL, FICTIONAL, etc）
        description: 人物の説明
        birth_year: 生年
        death_year: 没年（存命の場合はNone）
        preferred_age: 優先年齢（指定された場合、この年齢のみでエピソード生成）
        tier: 重要度ティア（S+, S, A, B）
        source_name: ソース名（例: manual, nhk_asadora, wikipedia_ja）
        source_url: ソースURL
        status: 処理ステータス（pending, active, etc）

        # メタデータ（処理中に追加）
        validation_errors: 検証エラーのリスト
        skip_reason: スキップ理由（重複、検証エラー等）
        confidence_score: 信頼度スコア（0.0-1.0）

    Example:
        >>> candidate = PersonCandidate(
        ...     person_name="山中伸弥",
        ...     category="科学・技術",
        ...     person_type="REAL",
        ...     birth_year=1962,
        ...     preferred_age=47,  # 47歳のエピソードのみ生成
        ...     tier="S+",
        ...     source_name="manual"
        ... )
    """

    person_name: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    person_type: str = "REAL"
    description: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    preferred_age: Optional[int] = None
    tier: Optional[str] = None  # S+, S, A, B
    source_name: str = ""
    source_url: Optional[str] = None
    status: str = "pending"

    # メタデータ（処理中に追加）
    validation_errors: List[str] = field(default_factory=list)
    skip_reason: Optional[str] = None
    confidence_score: float = 1.0

    def __post_init__(self):
        """データクラス初期化後の検証"""
        if not self.person_name:
            raise ValueError("person_name is required")

        if self.birth_year and not isinstance(self.birth_year, int):
            raise ValueError(f"birth_year must be int, got {type(self.birth_year)}")

        if self.death_year and not isinstance(self.death_year, int):
            raise ValueError(f"death_year must be int, got {type(self.death_year)}")

        if self.preferred_age is not None:
            if not isinstance(self.preferred_age, int):
                raise ValueError(f"preferred_age must be int, got {type(self.preferred_age)}")
            if self.preferred_age < 0:
                raise ValueError(f"preferred_age must be non-negative, got {self.preferred_age}")

    def to_dict(self) -> dict:
        """辞書形式に変換（JSON出力用）"""
        return {
            "person_name": self.person_name,
            "category": self.category,
            "sub_category": self.sub_category,
            "person_type": self.person_type,
            "description": self.description,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "preferred_age": self.preferred_age,
            "tier": self.tier,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "status": self.status,
            "validation_errors": self.validation_errors,
            "skip_reason": self.skip_reason,
            "confidence_score": self.confidence_score,
        }


class SourceAdapter(ABC):
    """
    候補ソースアダプタの抽象基底クラス

    すべてのSource Adapterはこのクラスを継承し、
    fetch_candidates()とget_source_name()を実装する必要があります。

    Example:
        >>> class MyAdapter(SourceAdapter):
        ...     def fetch_candidates(self, limit=None):
        ...         return [PersonCandidate(person_name="太郎", source_name="my_source")]
        ...     def get_source_name(self):
        ...         return "my_source"
    """

    @abstractmethod
    def fetch_candidates(self, limit: Optional[int] = None) -> List[PersonCandidate]:
        """
        候補人物を取得

        Args:
            limit: 取得する候補数の上限（Noneの場合は全件）

        Returns:
            PersonCandidateのリスト

        Raises:
            FileNotFoundError: ソースファイルが存在しない
            ValueError: データ形式が不正
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        ソース名を返す

        Returns:
            ソース名（例: "manual", "nhk_asadora", "wikipedia_ja"）
        """
        pass

    def validate_candidate(self, candidate: PersonCandidate) -> bool:
        """
        候補の基本検証

        Args:
            candidate: 検証対象の候補

        Returns:
            検証OK: True, 検証NG: False
        """
        # 必須フィールドのチェック
        if not candidate.person_name:
            candidate.validation_errors.append("person_name is required")
            return False

        # person_typeの検証
        valid_types = ["REAL", "FICTIONAL", "GROUP", "ANIMAL", "OTHER"]
        if candidate.person_type not in valid_types:
            candidate.validation_errors.append(f"Invalid person_type: {candidate.person_type}")
            return False

        # tierの検証（指定されている場合）
        if candidate.tier:
            valid_tiers = ["S+", "S", "A", "B", "C"]
            if candidate.tier not in valid_tiers:
                candidate.validation_errors.append(f"Invalid tier: {candidate.tier}")
                return False

        return True
