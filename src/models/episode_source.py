"""
EpisodeSource - 情報源データモデル

episode_sources.csvの行を表現するデータクラス。
情報源の収集・管理・冪等性保証を提供します。
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class EpisodeSource:
    """
    情報源データモデル

    Attributes:
        source_id: ソースID（MD5ハッシュ、自動生成）
        person_name: 人物名
        person_id: 人物ID（既存 or 新規）
        person_type: 人物タイプ（REAL/FICTIONAL）
        source_url: 情報源URL
        source_type: ソースタイプ（wikidata/wikipedia/manual）
        raw_text: 抽出テキスト（キーフレーズのみ、250文字以内）
        context: 文脈情報（オプション）
        evidence_quality: 根拠品質（A/B/C）
        verification_status: 検証ステータス（verified/unverified/rejected）
        collected_at: 収集日時
        verified_at: 検証日時（オプション）
    """

    person_name: str
    person_id: str
    person_type: str
    source_url: str
    source_type: str
    raw_text: str
    evidence_quality: str = "C"  # デフォルトは未検証
    verification_status: str = "unverified"
    context: Optional[str] = None
    source_id: str = field(default="", init=False)
    collected_at: datetime = field(default_factory=datetime.now)
    verified_at: Optional[datetime] = None

    def __post_init__(self):
        """初期化後処理：source_id生成とバリデーション"""
        # source_id生成
        if not self.source_id:
            self.source_id = self.generate_source_id(self.person_name, self.source_url)

        # バリデーション
        self.validate()

    @staticmethod
    def generate_source_id(person_name: str, source_url: str) -> str:
        """
        ソースIDをMD5ハッシュで生成（冪等性保証）

        Args:
            person_name: 人物名
            source_url: ソースURL

        Returns:
            source_id (例: SRC-a3f5b9c2d4e6f8a0)

        Example:
            >>> EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
            'SRC-...'
        """
        composite_key = f"{person_name}||{source_url}"
        hash_digest = hashlib.md5(composite_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"SRC-{hash_digest[:16]}"

    def validate(self):
        """
        データバリデーション

        Raises:
            ValueError: バリデーション失敗時

        チェック項目:
        - 必須フィールド存在確認
        - URL形式検証
        - person_type値検証（REAL/FICTIONAL）
        - evidence_quality値検証（A/B/C）
        - verification_status値検証
        - raw_text文字数制限（250文字以内推奨）
        """
        # 必須フィールド
        if not self.person_name:
            raise ValueError("person_name is required")
        if not self.person_id:
            raise ValueError("person_id is required")
        if not self.source_url:
            raise ValueError("source_url is required")
        if not self.raw_text:
            raise ValueError("raw_text is required")

        # URL形式検証
        url_pattern = r"^https?://.+"
        if not re.match(url_pattern, self.source_url):
            raise ValueError(f"Invalid URL format: {self.source_url}")

        # person_type検証
        valid_person_types = ["REAL", "FICTIONAL"]
        if self.person_type not in valid_person_types:
            raise ValueError(f"Invalid person_type: {self.person_type}. Must be one of {valid_person_types}")

        # evidence_quality検証
        valid_qualities = ["A", "B", "C"]
        if self.evidence_quality not in valid_qualities:
            raise ValueError(f"Invalid evidence_quality: {self.evidence_quality}. Must be one of {valid_qualities}")

        # verification_status検証
        valid_statuses = ["verified", "unverified", "rejected"]
        if self.verification_status not in valid_statuses:
            raise ValueError(
                f"Invalid verification_status: {self.verification_status}. Must be one of {valid_statuses}"
            )

        # source_type検証
        valid_source_types = ["wikidata", "wikipedia", "manual"]
        if self.source_type not in valid_source_types:
            raise ValueError(f"Invalid source_type: {self.source_type}. Must be one of {valid_source_types}")

        # raw_text文字数警告（250文字以内推奨、著作権遵守）
        if len(self.raw_text) > 250:
            import logging

            logging.warning(
                f"raw_text exceeds 250 characters ({len(self.raw_text)} chars). "
                "Consider trimming for copyright compliance."
            )

    def to_dict(self) -> dict:
        """
        辞書形式に変換

        Returns:
            辞書形式のデータ

        Example:
            >>> source = EpisodeSource(...)
            >>> data = source.to_dict()
        """
        return {
            "source_id": self.source_id,
            "person_name": self.person_name,
            "person_id": self.person_id,
            "person_type": self.person_type,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "raw_text": self.raw_text,
            "context": self.context or "",
            "evidence_quality": self.evidence_quality,
            "verification_status": self.verification_status,
            "collected_at": self.collected_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EpisodeSource":
        """
        辞書からインスタンス生成

        Args:
            data: 辞書データ

        Returns:
            EpisodeSourceインスタンス

        Example:
            >>> data = {"person_name": "...", ...}
            >>> source = EpisodeSource.from_dict(data)
        """
        # datetimeフィールド変換
        collected_at = data.get("collected_at")
        if isinstance(collected_at, str):
            collected_at = datetime.fromisoformat(collected_at)
        elif collected_at is None:
            collected_at = datetime.now()

        verified_at = data.get("verified_at")
        if isinstance(verified_at, str) and verified_at:
            verified_at = datetime.fromisoformat(verified_at)
        else:
            verified_at = None

        instance = cls(
            person_name=data["person_name"],
            person_id=data["person_id"],
            person_type=data["person_type"],
            source_url=data["source_url"],
            source_type=data["source_type"],
            raw_text=data["raw_text"],
            context=data.get("context"),
            evidence_quality=data.get("evidence_quality", "C"),
            verification_status=data.get("verification_status", "unverified"),
            collected_at=collected_at,
            verified_at=verified_at,
        )

        # source_idが提供されている場合は上書き
        if "source_id" in data and data["source_id"]:
            instance.source_id = data["source_id"]

        return instance

    @staticmethod
    def is_duplicate(source_id: str, csv_path: Path) -> bool:
        """
        既存ソースとの重複チェック（冪等性保証）

        Args:
            source_id: 検証対象のソースID
            csv_path: 既存ソースCSVパス

        Returns:
            True: 重複, False: 新規

        Example:
            >>> is_dup = EpisodeSource.is_duplicate("SRC-abc123", Path("episode_sources.csv"))
        """
        if not csv_path.exists():
            return False

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        return source_id in df["source_id"].values

    @staticmethod
    def save_to_csv(sources: List["EpisodeSource"], csv_path: Path, append: bool = False):
        """
        CSV保存（UTF-8 BOM、Excel対応）

        Args:
            sources: 保存するソースリスト
            csv_path: 保存先CSVパス
            append: True=追記、False=上書き

        Example:
            >>> sources = [EpisodeSource(...), ...]
            >>> EpisodeSource.save_to_csv(sources, Path("episode_sources.csv"))
        """
        if not sources:
            return

        # 辞書リストに変換
        data = [source.to_dict() for source in sources]
        df = pd.DataFrame(data)

        # 追記モード
        if append and csv_path.exists():
            existing_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            df = pd.concat([existing_df, df], ignore_index=True)

            # 重複除外（source_id基準）
            df = df.drop_duplicates(subset=["source_id"], keep="first")

        # 親ディレクトリ作成
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # CSV保存（UTF-8 BOM）
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def load_from_csv(csv_path: Path) -> List["EpisodeSource"]:
        """
        CSV読み込み

        Args:
            csv_path: 読み込み元CSVパス

        Returns:
            EpisodeSourceリスト

        Example:
            >>> sources = EpisodeSource.load_from_csv(Path("episode_sources.csv"))
        """
        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # NaN処理
        df = df.fillna("")

        sources = []
        for _, row in df.iterrows():
            try:
                source = EpisodeSource.from_dict(row.to_dict())
                sources.append(source)
            except Exception as e:
                import logging

                logging.error(f"Failed to load row: {e}")
                continue

        return sources
