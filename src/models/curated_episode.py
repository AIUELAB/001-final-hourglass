"""
CuratedEpisode - 生成済みエピソードデータモデル

curated_episodes.csvの行を表現するデータクラス。
EPUP形式に変換された未マージエピソードを管理します。
MASTER_EPISODES_CURRENT.csvとの互換性を保証します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class CuratedEpisode:
    """
    生成済みエピソードデータモデル

    Attributes:
        episode_id: エピソードID（未採番は空、マージ時に正式採番）
        person_id: 人物ID
        person_name: 正規化済み人物名
        age: 年齢
        episode_text: エピソード本文（EPUP形式）
        source_id: 根拠ソースID（EpisodeSourceのsource_id）
        source_url: 根拠URL
        evidence_quality: 根拠品質（A/B/C）
        validation_status: バリデーション結果（pending/passed/failed/review）
        validation_issues: 検出された問題（JSON形式）
        generated_at: 生成日時
        person_type: 人物タイプ（REAL/FICTIONAL）
        category: カテゴリ（オプション）
        episode_type: エピソードタイプ（オプション）
    """

    person_id: str
    person_name: str
    age: int
    episode_text: str
    source_id: str
    source_url: str
    evidence_quality: str
    episode_id: str = ""  # マージ時に採番
    validation_status: str = "pending"
    validation_issues: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)
    person_type: str = "REAL"
    category: Optional[str] = None
    episode_type: Optional[str] = None

    def __post_init__(self):
        """初期化後処理：バリデーション"""
        self.validate()

    def validate(self):
        """
        データバリデーション

        Raises:
            ValueError: バリデーション失敗時

        チェック項目:
        - 必須フィールド存在確認
        - age範囲検証（0-150）
        - evidence_quality値検証（A/B/C）
        - validation_status値検証
        - person_type値検証（REAL/FICTIONAL）
        - episode_text基本フォーマット検証（「あなたと同じ」形式）
        """
        # 必須フィールド
        if not self.person_id:
            raise ValueError("person_id is required")
        if not self.person_name:
            raise ValueError("person_name is required")
        if not self.episode_text:
            raise ValueError("episode_text is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.source_url:
            raise ValueError("source_url is required")

        # age範囲検証
        if not isinstance(self.age, int) or self.age < 0 or self.age > 150:
            raise ValueError(f"Invalid age: {self.age}. Must be 0-150")

        # evidence_quality検証
        valid_qualities = ["A", "B", "C"]
        if self.evidence_quality not in valid_qualities:
            raise ValueError(f"Invalid evidence_quality: {self.evidence_quality}. Must be one of {valid_qualities}")

        # validation_status検証
        valid_statuses = ["pending", "passed", "failed", "review"]
        if self.validation_status not in valid_statuses:
            raise ValueError(f"Invalid validation_status: {self.validation_status}. Must be one of {valid_statuses}")

        # person_type検証
        valid_person_types = ["REAL", "FICTIONAL"]
        if self.person_type not in valid_person_types:
            raise ValueError(f"Invalid person_type: {self.person_type}. Must be one of {valid_person_types}")

        # episode_text基本フォーマット検証（「あなたと同じ」形式）
        if not self.episode_text.startswith("あなたと同じ"):
            import logging

            logging.warning(f"episode_text does not start with 'あなたと同じ': {self.episode_text[:50]}")

    def mark_passed(self):
        """バリデーション合格としてマーク"""
        self.validation_status = "passed"
        self.validation_issues = None

    def mark_failed(self, issues: str):
        """
        バリデーション不合格としてマーク

        Args:
            issues: 検出された問題（JSON形式）
        """
        self.validation_status = "failed"
        self.validation_issues = issues

    def mark_review(self, reason: str):
        """
        レビュー必要としてマーク

        Args:
            reason: レビュー理由
        """
        self.validation_status = "review"
        self.validation_issues = reason

    def to_dict(self) -> dict:
        """
        辞書形式に変換

        Returns:
            辞書形式のデータ

        Example:
            >>> episode = CuratedEpisode(...)
            >>> data = episode.to_dict()
        """
        return {
            "episode_id": self.episode_id,
            "person_id": self.person_id,
            "person_name": self.person_name,
            "age": self.age,
            "episode_text": self.episode_text,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "evidence_quality": self.evidence_quality,
            "validation_status": self.validation_status,
            "validation_issues": self.validation_issues or "",
            "generated_at": self.generated_at.isoformat(),
            "person_type": self.person_type,
            "category": self.category or "",
            "episode_type": self.episode_type or "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CuratedEpisode":
        """
        辞書からインスタンス生成

        Args:
            data: 辞書データ

        Returns:
            CuratedEpisodeインスタンス

        Example:
            >>> data = {"person_id": "...", ...}
            >>> episode = CuratedEpisode.from_dict(data)
        """
        # datetimeフィールド変換
        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        elif generated_at is None:
            generated_at = datetime.now()

        return cls(
            episode_id=data.get("episode_id", ""),
            person_id=data["person_id"],
            person_name=data["person_name"],
            age=int(data["age"]),
            episode_text=data["episode_text"],
            source_id=data["source_id"],
            source_url=data["source_url"],
            evidence_quality=data["evidence_quality"],
            validation_status=data.get("validation_status", "pending"),
            validation_issues=data.get("validation_issues"),
            generated_at=generated_at,
            person_type=data.get("person_type", "REAL"),
            category=data.get("category"),
            episode_type=data.get("episode_type"),
        )

    def to_master_format(self) -> dict:
        """
        MASTER_EPISODES_CURRENT.csv互換形式に変換

        Returns:
            マスターCSV互換の辞書

        Note:
            以下のフィールドを追加（デフォルト値）:
            - fact_check_result: evidence_qualityから推定
            - source: "COLLECTION_PIPELINE"
            - generation_timestamp: generated_at
            - その他のフィールドは空/デフォルト値
        """
        # fact_check_resultの推定
        fact_check_result = "確認済み" if self.evidence_quality in ["A", "B"] else "未確認"

        return {
            "episode_id": self.episode_id,
            "person_id": self.person_id,
            "person_name": self.person_name,
            "age": self.age,
            "episode_text": self.episode_text,
            "category": self.category or "",
            "person_type": self.person_type,
            "episode_type": self.episode_type or "",
            "fact_check_result": fact_check_result,
            "source": "COLLECTION_PIPELINE",
            "generation_timestamp": self.generated_at.isoformat(),
            "source_url": self.source_url,
            "verification_status": "verified" if self.evidence_quality in ["A", "B"] else "unverified",
            "evidence_quality": self.evidence_quality,
            # 以下はデフォルト値
            "episode_count": 0.0,
            "char_count": float(len(self.episode_text)),
            "quality_score": 0.0,
            "slot": 0.0,
            "tier": 0.0,
            "week": 0.0,
            "work_title": "",
            "fame_tier": 0.0,
            "wikipedia_ja": False,
            "textbook": False,
            "award_level": 0.0,
            "notoriety": False,
            "fame_score": 0.0,
            "composite_score": 0.0,
            "fame_score_updated_at": "",
            "episode_fame_tier": 0.0,
            "episode_fame_score": 0.0,
            "episode_fame_score_updated_at": "",
            "人生の節目タグ": "",
            "記憶性スコア": 0.0,
            "共感性スコア": 0.0,
            "意外性スコア": 0.0,
            "生成品質スコア": 0.0,
            "教育的価値": 0.0,
            "ストーリー品質": 0.0,
            "事実密度": 0.0,
            "category_original": self.category or "",
            "episode_importance_score": 0.0,
            "is_highlight": 0.0,
            "highlight_rank": 0.0,
            "highlight_selection_method": "",
            "事実密度_float": 0.0,
            "priority_score": 0.0,
            "impressiveness_score": 0.0,
            "年代": "",
            "episode_fame_score_original": 0.0,
            "教育的価値_original": 0.0,
            "ストーリー品質_original": 0.0,
            "事実密度_original": 0.0,
            "episode_id_original": "",
            "surprise_score": 0.0,
            "name_raw": "",
            "title": "",
            "affiliation": "",
            "display_name_original": "",
            "generated_at": self.generated_at.isoformat(),
            "last_modified": "",
            "group_name": "",
            "is_group_member": False,
        }

    @staticmethod
    def save_to_csv(episodes: List["CuratedEpisode"], csv_path: Path, append: bool = False):
        """
        CSV保存（UTF-8 BOM、Excel対応）

        Args:
            episodes: 保存するエピソードリスト
            csv_path: 保存先CSVパス
            append: True=追記、False=上書き

        Example:
            >>> episodes = [CuratedEpisode(...), ...]
            >>> CuratedEpisode.save_to_csv(episodes, Path("curated_episodes.csv"))
        """
        if not episodes:
            return

        # 辞書リストに変換
        data = [episode.to_dict() for episode in episodes]
        df = pd.DataFrame(data)

        # 追記モード
        if append and csv_path.exists():
            existing_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            df = pd.concat([existing_df, df], ignore_index=True)

        # 親ディレクトリ作成
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # CSV保存（UTF-8 BOM）
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def load_from_csv(csv_path: Path) -> List["CuratedEpisode"]:
        """
        CSV読み込み

        Args:
            csv_path: 読み込み元CSVパス

        Returns:
            CuratedEpisodeリスト

        Example:
            >>> episodes = CuratedEpisode.load_from_csv(Path("curated_episodes.csv"))
        """
        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # NaN処理
        df = df.fillna("")

        episodes = []
        for _, row in df.iterrows():
            try:
                episode = CuratedEpisode.from_dict(row.to_dict())
                episodes.append(episode)
            except Exception as e:
                import logging

                logging.error(f"Failed to load row: {e}")
                continue

        return episodes

    @staticmethod
    def filter_by_status(episodes: List["CuratedEpisode"], status: str) -> List["CuratedEpisode"]:
        """
        バリデーションステータスでフィルタリング

        Args:
            episodes: エピソードリスト
            status: フィルタするステータス（pending/passed/failed/review）

        Returns:
            フィルタリング済みリスト

        Example:
            >>> passed = CuratedEpisode.filter_by_status(episodes, "passed")
        """
        return [episode for episode in episodes if episode.validation_status == status]

    @staticmethod
    def filter_by_quality(episodes: List["CuratedEpisode"], min_quality: str = "B") -> List["CuratedEpisode"]:
        """
        根拠品質でフィルタリング

        Args:
            episodes: エピソードリスト
            min_quality: 最低品質（A/B/C）

        Returns:
            フィルタリング済みリスト

        Example:
            >>> high_quality = CuratedEpisode.filter_by_quality(episodes, min_quality="B")
        """
        quality_order = {"A": 3, "B": 2, "C": 1}
        min_score = quality_order.get(min_quality, 1)

        return [episode for episode in episodes if quality_order.get(episode.evidence_quality, 1) >= min_score]
