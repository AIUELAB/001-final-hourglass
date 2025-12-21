"""
VerifiedSource - 検証済み情報源データモデル

verified_sources.csvの行を表現するデータクラス。
EpisodeSourceを継承し、検証関連フィールドと品質判定ロジックを追加します。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.models.episode_source import EpisodeSource


@dataclass
class VerifiedSource(EpisodeSource):
    """
    検証済み情報源データモデル

    EpisodeSourceを継承し、以下を追加:
    - verifier_notes: 検証者ノート
    - A/B/C品質判定ロジック

    Attributes:
        verifier_notes: 検証者ノート（オプション）
        （その他のフィールドはEpisodeSourceから継承）

    品質判定基準:
        A: 一次情報（公式サイト、学術論文、自伝等）
        B: 二次情報2件以上で裏付けあり
        C: 未検証（単一ソース、出典不明）
    """

    verifier_notes: Optional[str] = None

    def __post_init__(self):
        """初期化後処理：親クラスの処理 + 品質判定"""
        super().__post_init__()

        # 自動品質判定（evidence_qualityが未設定の場合）
        if self.evidence_quality == "C" and self.verification_status == "unverified":
            self.evidence_quality = self.auto_judge_quality()

    def auto_judge_quality(self) -> str:
        """
        URL/source_typeから自動品質判定

        Returns:
            品質（A/B/C）

        判定ロジック:
            A: 政府公式、学術機関、国会図書館等
            B: Wikipedia（一部）、複数ソース確認
            C: 上記以外（単一ソース、出典不明）
        """
        # A判定: 一次情報ドメイン
        A_DOMAIN_PATTERNS = [
            r"\.go\.jp(/|$)",  # 政府公式
            r"\.ac\.jp(/|$)",  # 学術機関
            r"\.edu(/|$)",  # 教育機関
            r"ndl\.go\.jp",  # 国会図書館
        ]

        for pattern in A_DOMAIN_PATTERNS:
            if re.search(pattern, self.source_url):
                return "A"

        # B判定: Wikipedia等の信頼性の高い二次情報
        # 注：複数ソース確認は呼び出し側で判定が必要
        B_DOMAIN_PATTERNS = [
            r"wikipedia\.org",
            r"britannica\.com",
        ]

        for pattern in B_DOMAIN_PATTERNS:
            if re.search(pattern, self.source_url):
                return "B"

        # C判定: 上記以外
        return "C"

    def mark_verified(self, verifier_notes: Optional[str] = None):
        """
        検証済みとしてマーク

        Args:
            verifier_notes: 検証者ノート（オプション）

        Example:
            >>> source = VerifiedSource(...)
            >>> source.mark_verified("品質A確認済み")
        """
        self.verification_status = "verified"
        self.verified_at = datetime.now()
        if verifier_notes:
            self.verifier_notes = verifier_notes

    def mark_rejected(self, reason: str):
        """
        却下としてマーク

        Args:
            reason: 却下理由

        Example:
            >>> source = VerifiedSource(...)
            >>> source.mark_rejected("センシティブキーワード検出")
        """
        self.verification_status = "rejected"
        self.verified_at = datetime.now()
        self.verifier_notes = reason

    def to_dict(self) -> dict:
        """
        辞書形式に変換（親クラスを拡張）

        Returns:
            辞書形式のデータ
        """
        data = super().to_dict()
        data["verifier_notes"] = self.verifier_notes or ""
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "VerifiedSource":
        """
        辞書からインスタンス生成（親クラスを拡張）

        Args:
            data: 辞書データ

        Returns:
            VerifiedSourceインスタンス
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
            verifier_notes=data.get("verifier_notes"),
            collected_at=collected_at,
            verified_at=verified_at,
        )

        # source_idが提供されている場合は上書き
        if "source_id" in data and data["source_id"]:
            instance.source_id = data["source_id"]

        return instance

    @staticmethod
    def filter_by_quality(sources: List["VerifiedSource"], min_quality: str = "B") -> List["VerifiedSource"]:
        """
        品質でフィルタリング

        Args:
            sources: ソースリスト
            min_quality: 最低品質（A/B/C）

        Returns:
            フィルタリング済みリスト

        Example:
            >>> filtered = VerifiedSource.filter_by_quality(sources, min_quality="B")
        """
        quality_order = {"A": 3, "B": 2, "C": 1}
        min_score = quality_order.get(min_quality, 1)

        return [source for source in sources if quality_order.get(source.evidence_quality, 1) >= min_score]

    @staticmethod
    def filter_verified(sources: List["VerifiedSource"]) -> List["VerifiedSource"]:
        """
        検証済みソースのみ抽出

        Args:
            sources: ソースリスト

        Returns:
            検証済みリスト

        Example:
            >>> verified = VerifiedSource.filter_verified(sources)
        """
        return [source for source in sources if source.verification_status == "verified"]

    @staticmethod
    def save_to_csv(sources: List["EpisodeSource"], csv_path: Path, append: bool = False):  # type: ignore[override]
        """
        CSV保存（UTF-8 BOM、Excel対応）

        Args:
            sources: 保存するソースリスト
            csv_path: 保存先CSVパス
            append: True=追記、False=上書き

        Example:
            >>> sources = [VerifiedSource(...), ...]
            >>> VerifiedSource.save_to_csv(sources, Path("verified_sources.csv"))
        """
        import pandas as pd

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
    def load_from_csv(csv_path: Path) -> List["EpisodeSource"]:  # type: ignore[override]
        """
        CSV読み込み

        Args:
            csv_path: 読み込み元CSVパス

        Returns:
            VerifiedSourceリスト

        Example:
            >>> sources = VerifiedSource.load_from_csv(Path("verified_sources.csv"))
        """
        import pandas as pd

        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # NaN処理
        df = df.fillna("")

        sources: List["EpisodeSource"] = []
        for _, row in df.iterrows():
            try:
                source = VerifiedSource.from_dict(row.to_dict())
                sources.append(source)
            except Exception as e:
                import logging

                logging.error(f"Failed to load row: {e}")
                continue

        return sources
