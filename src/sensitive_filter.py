"""
Sensitive Filter - センシティブ候補のフィルタリング

このモジュールはセンシティブな人物候補を検出し、
--allow-sensitiveフラグなしでは追加をブロックします。

主な機能:
- センシティブカテゴリ検出
- センシティブキーワード検出
- レビュー必要カテゴリ検出
- 許可リスト判定

使用方法:
    >>> from src.sensitive_filter import SensitiveFilter
    >>> from src.source_adapters.base import PersonCandidate
    >>>
    >>> filter = SensitiveFilter()
    >>> candidate = PersonCandidate(person_name="テスト太郎", category="犯罪者")
    >>> is_sensitive, reason = filter.is_sensitive(candidate)
    >>> if is_sensitive:
    ...     print(f"Blocked: {reason}")
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from src.csv_path_resolver import get_project_root
from src.source_adapters.base import PersonCandidate

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SensitiveFilter:
    """センシティブ候補のフィルタリング"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス（省略時はデフォルト）
        """
        if config_path is None:
            config_path = str(get_project_root() / "config" / "sensitive_keywords.yaml")

        # 設定ファイルの読み込み
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        logger.info(f"Sensitive filter loaded: {config_path}")
        logger.info(f"  Sensitive categories: {len(self.config.get('sensitive_categories', []))}")
        logger.info(f"  Sensitive keywords: {len(self.config.get('sensitive_keywords', []))}")
        logger.info(f"  Review required categories: {len(self.config.get('review_required_categories', []))}")
        logger.info(f"  Allow list: {len(self.config.get('allow_list', []))}")

    def is_sensitive(self, candidate: PersonCandidate) -> Tuple[bool, str]:
        """
        候補がセンシティブかどうかを判定

        Args:
            candidate: 検証対象の候補人物

        Returns:
            (is_sensitive, reason):
            - is_sensitive: センシティブな場合True
            - reason: 判定理由

        Example:
            >>> filter = SensitiveFilter()
            >>> candidate = PersonCandidate(person_name="テスト太郎", category="犯罪者")
            >>> is_sensitive, reason = filter.is_sensitive(candidate)
            >>> print(is_sensitive, reason)
            True sensitive_category: 犯罪者
        """
        # 許可リストチェック
        if candidate.person_name in self.config.get("allow_list", []):
            logger.debug(f"{candidate.person_name}: Allow list match")
            return (False, "")

        # カテゴリチェック
        if candidate.category in self.config.get("sensitive_categories", []):
            return (True, f"sensitive_category: {candidate.category}")

        # キーワードチェック
        if candidate.description:
            for keyword in self.config.get("sensitive_keywords", []):
                if keyword in candidate.description:
                    return (True, f"sensitive_keyword: {keyword}")

        return (False, "")

    def requires_review(self, candidate: PersonCandidate) -> Tuple[bool, str]:
        """
        候補がレビュー必要かどうかを判定

        Args:
            candidate: 検証対象の候補人物

        Returns:
            (requires_review, reason):
            - requires_review: レビューが必要な場合True
            - reason: 判定理由

        Example:
            >>> filter = SensitiveFilter()
            >>> candidate = PersonCandidate(person_name="テスト太郎", category="政治家")
            >>> requires_review, reason = filter.requires_review(candidate)
            >>> print(requires_review, reason)
            True review_required_category: 政治家
        """
        if candidate.category in self.config.get("review_required_categories", []):
            return (True, f"review_required_category: {candidate.category}")

        return (False, "")

    def filter_candidates(
        self, candidates: List[PersonCandidate], allow_sensitive: bool = False
    ) -> Tuple[List[PersonCandidate], List[PersonCandidate], List[PersonCandidate]]:
        """
        候補リストをフィルタリング

        Args:
            candidates: 候補人物のリスト
            allow_sensitive: True の場合、センシティブ候補も承認

        Returns:
            (approved_candidates, review_required_candidates, blocked_candidates):
            - approved_candidates: 承認済み候補
            - review_required_candidates: レビュー必要候補
            - blocked_candidates: ブロック候補

        Example:
            >>> filter = SensitiveFilter()
            >>> candidates = [
            ...     PersonCandidate(person_name="A", category="科学者"),
            ...     PersonCandidate(person_name="B", category="政治家"),
            ...     PersonCandidate(person_name="C", category="犯罪者")
            ... ]
            >>> approved, review, blocked = filter.filter_candidates(candidates, allow_sensitive=False)
            >>> print(len(approved), len(review), len(blocked))
            1 1 1
        """
        approved = []
        review_required = []
        blocked = []

        for candidate in candidates:
            # センシティブチェック
            is_sens, sens_reason = self.is_sensitive(candidate)

            if is_sens:
                if allow_sensitive:
                    # --allow-sensitiveフラグがある場合は承認
                    logger.info(f"{candidate.person_name}: Sensitive but allowed - {sens_reason}")
                    approved.append(candidate)
                else:
                    # ブロック
                    candidate.skip_reason = sens_reason
                    logger.warning(f"{candidate.person_name}: Blocked - {sens_reason}")
                    blocked.append(candidate)
                continue

            # レビュー必要チェック
            needs_review, review_reason = self.requires_review(candidate)

            if needs_review:
                candidate.skip_reason = review_reason
                logger.info(f"{candidate.person_name}: Review required - {review_reason}")
                review_required.append(candidate)
                continue

            # 承認
            approved.append(candidate)

        logger.info(
            f"Filter results: {len(approved)} approved, {len(review_required)} review required, {len(blocked)} blocked"
        )

        return approved, review_required, blocked

    def get_statistics(self) -> dict:
        """
        フィルタ設定の統計情報を取得

        Returns:
            統計情報の辞書

        Example:
            >>> filter = SensitiveFilter()
            >>> stats = filter.get_statistics()
            >>> print(stats)
            {'sensitive_categories': 5, 'sensitive_keywords': 12, ...}
        """
        return {
            "sensitive_categories": len(self.config.get("sensitive_categories", [])),
            "sensitive_keywords": len(self.config.get("sensitive_keywords", [])),
            "review_required_categories": len(self.config.get("review_required_categories", [])),
            "allow_list": len(self.config.get("allow_list", [])),
        }


if __name__ == "__main__":
    # 動作確認用
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.source_adapters.base import PersonCandidate

    filter = SensitiveFilter()

    print("=== Sensitive Filter Test ===\n")

    # 統計情報
    stats = filter.get_statistics()
    print("Filter statistics:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # テストケース
    test_candidates = [
        PersonCandidate(person_name="山中伸弥", category="科学・技術"),
        PersonCandidate(person_name="安倍晋三", category="政治家", description="第90代・第96代内閣総理大臣"),
        PersonCandidate(person_name="テスト太郎", category="犯罪者", description="詐欺で逮捕された人物"),
        PersonCandidate(
            person_name="ネルソン・マンデラ",
            category="政治家",
            description="南アフリカ共和国大統領、逮捕歴あり",
        ),
    ]

    print("\n" + "=" * 60)
    print("Test 1: allow_sensitive=False")
    print("=" * 60)

    approved, review, blocked = filter.filter_candidates(test_candidates, allow_sensitive=False)

    print(f"\nApproved ({len(approved)}):")
    for candidate in approved:
        print(f"  - {candidate.person_name} ({candidate.category})")

    print(f"\nReview Required ({len(review)}):")
    for candidate in review:
        print(f"  - {candidate.person_name} ({candidate.category}) - {candidate.skip_reason}")

    print(f"\nBlocked ({len(blocked)}):")
    for candidate in blocked:
        print(f"  - {candidate.person_name} ({candidate.category}) - {candidate.skip_reason}")

    print("\n" + "=" * 60)
    print("Test 2: allow_sensitive=True")
    print("=" * 60)

    approved2, review2, blocked2 = filter.filter_candidates(test_candidates, allow_sensitive=True)

    print(f"\nApproved ({len(approved2)}):")
    for candidate in approved2:
        print(f"  - {candidate.person_name} ({candidate.category})")

    print(f"\nReview Required ({len(review2)}):")
    for candidate in review2:
        print(f"  - {candidate.person_name} ({candidate.category}) - {candidate.skip_reason}")

    print(f"\nBlocked ({len(blocked2)}):")
    for candidate in blocked2:
        print(f"  - {candidate.person_name} ({candidate.category}) - {candidate.skip_reason}")
