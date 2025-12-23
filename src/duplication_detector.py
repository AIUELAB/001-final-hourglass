"""
Duplication Detector - 4層重複判定システム

このモジュールは候補人物がMASTER CSVに既に存在するかを4層の判定で検出します。

4層重複判定:
    Layer 1: 完全一致 (person_name)
    Layer 2: 正規化一致 (PersonNameNormalizer)
    Layer 3: 別名一致 (ALIAS_KEYWORDS)
    Layer 4: 類似一致 (SequenceMatcher ≥0.85 + 属性検証)

使用方法:
    >>> import pandas as pd
    >>> from src.duplication_detector import DuplicationDetector
    >>> from src.source_adapters import PersonCandidate
    >>>
    >>> master_df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv")
    >>> detector = DuplicationDetector(master_df)
    >>>
    >>> candidate = PersonCandidate(person_name="山中伸弥", category="科学・技術")
    >>> is_dup, matched, conf, layer = detector.detect_duplicate(candidate)
    >>> if is_dup:
    ...     print(f"重複検出: {matched} (layer={layer}, confidence={conf})")
"""

from difflib import SequenceMatcher
from typing import Dict, Optional, Tuple

import pandas as pd

from src.source_adapters.base import PersonCandidate


class DuplicationDetector:
    """4層重複判定システム"""

    def __init__(self, master_df: pd.DataFrame):
        """
        Args:
            master_df: MASTER CSVのDataFrame（person_name列必須）
        """
        if "person_name" not in master_df.columns:
            raise ValueError("master_df must have 'person_name' column")

        self.master_df = master_df
        self.master_names = set(master_df["person_name"].dropna().unique())

        # PersonNameNormalizerを遅延インポート（循環依存回避）
        self.normalizer = None
        self.alias_map = None

        # パフォーマンス改善: 正規化キャッシュ（N+1問題解消）
        self._normalized_cache: Dict[str, str] = {}  # master_name -> normalized_name
        self._normalized_reverse: Dict[str, str] = {}  # normalized_name -> master_name
        self._cache_built = False

    def _load_normalizer(self):
        """PersonNameNormalizerを遅延ロード"""
        if self.normalizer is None:
            import sys
            from pathlib import Path

            # scripts/data/normalize_person_names.py から PersonNameNormalizer をインポート
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "data"))

            from normalize_person_names import (
                ALIAS_KEYWORDS,
                PersonNameNormalizer,
            )

            self.normalizer = PersonNameNormalizer()
            self.alias_map = ALIAS_KEYWORDS

            # キャッシュ構築（N+1問題解消）
            self._build_cache()

    def _build_cache(self):
        """正規化キャッシュを事前構築（O(n)→O(1)最適化）"""
        if self._cache_built or self.normalizer is None:
            return

        for master_name in self.master_names:
            result = self.normalizer.normalize(master_name)
            if result:
                normalized = result.normalized_name
                self._normalized_cache[master_name] = normalized
                # 逆引き: 正規化名→元名（最初の一致を優先）
                if normalized not in self._normalized_reverse:
                    self._normalized_reverse[normalized] = master_name

        self._cache_built = True

    def detect_duplicate(self, candidate: PersonCandidate) -> Tuple[bool, Optional[str], float, str]:
        """
        候補人物の重複を4層判定

        Args:
            candidate: 検証対象の候補人物

        Returns:
            (is_duplicate, matched_name, confidence, layer)
            - is_duplicate: 重複している場合True
            - matched_name: マッチした人物名（重複でない場合None）
            - confidence: 信頼度スコア（0.0-1.0）
            - layer: 検出層（"exact", "normalized", "alias", "similar", "none"）

        Example:
            >>> detector = DuplicationDetector(master_df)
            >>> candidate = PersonCandidate(person_name="山中伸弥")
            >>> is_dup, matched, conf, layer = detector.detect_duplicate(candidate)
            >>> print(f"{is_dup}, {matched}, {conf}, {layer}")
            True, 山中伸弥, 1.0, exact
        """
        # Layer 1: 完全一致
        if candidate.person_name in self.master_names:
            return (True, candidate.person_name, 1.0, "exact")

        # PersonNameNormalizer をロード（遅延ロード）
        self._load_normalizer()
        if self.normalizer is None:
            raise RuntimeError("normalizer not initialized after _load_normalizer()")
        if self.alias_map is None:
            raise RuntimeError("alias_map not initialized after _load_normalizer()")

        # キャッシュが未構築の場合は構築（テストでnormalizerを直接設定した場合用）
        if not self._cache_built:
            self._build_cache()

        # Layer 2: 正規化一致（キャッシュ使用: O(1)）
        normalized_result = self.normalizer.normalize(candidate.person_name)
        if normalized_result:
            normalized_name = normalized_result.normalized_name

            # キャッシュから O(1) で検索
            if normalized_name in self._normalized_reverse:
                return (True, self._normalized_reverse[normalized_name], 1.0, "normalized")

        # Layer 3: 別名一致
        canonical_name = self.alias_map.get(candidate.person_name)
        if canonical_name and canonical_name in self.master_names:
            return (True, canonical_name, 1.0, "alias")

        # Layer 4: 類似一致（SequenceMatcher ≥0.85 + 属性検証、キャッシュ使用）
        normalized_candidate_name = normalized_result.normalized_name if normalized_result else candidate.person_name

        for master_name in self.master_names:
            # キャッシュから正規化名を取得（O(1)）
            normalized_master_name = self._normalized_cache.get(master_name, master_name)

            # 文字列類似度計算
            similarity = SequenceMatcher(None, normalized_candidate_name, normalized_master_name).ratio()

            if similarity >= 0.85:
                # 属性ベースの検証
                if self._verify_attributes(candidate, master_name):
                    return (True, master_name, similarity, "similar")

        return (False, None, 0.0, "none")

    def _verify_attributes(self, candidate: PersonCandidate, master_name: str) -> bool:
        """
        属性ベースの追加検証

        類似度≥0.85の場合、属性（category, birth_year, person_type）を
        追加検証して誤検出を防ぐ。

        Args:
            candidate: 検証対象の候補
            master_name: マスター内の人物名

        Returns:
            属性が一致する場合True（2つ以上の属性が一致）

        Example:
            >>> detector._verify_attributes(candidate, "山中伸弥")
            True  # category, birth_year が一致
        """
        # master_name の行を取得
        master_rows = self.master_df[self.master_df["person_name"] == master_name]
        if master_rows.empty:
            return False

        master_row = master_rows.iloc[0]

        score = 0
        checks = 0

        # カテゴリ一致チェック
        if pd.notna(master_row.get("category")) and candidate.category:
            checks += 1
            if master_row["category"] == candidate.category:
                score += 1

        # 生年一致チェック（±1年以内）
        if pd.notna(master_row.get("birth_year")) and candidate.birth_year:
            checks += 1
            master_birth_year = int(master_row["birth_year"])
            if abs(master_birth_year - candidate.birth_year) <= 1:
                score += 1

        # person_type一致チェック
        if pd.notna(master_row.get("person_type")) and candidate.person_type:
            checks += 1
            if master_row["person_type"] == candidate.person_type:
                score += 1

        # 2つ以上の属性をチェックし、過半数が一致すればOK
        if checks == 0:
            # 属性情報がない場合は類似度のみで判定（慎重に）
            return False

        return score / checks >= 0.5

    def get_statistics(self) -> Dict[str, int]:
        """
        マスターDBの統計情報を取得

        Returns:
            統計情報の辞書

        Example:
            >>> detector.get_statistics()
            {'total_persons': 7256, 'total_episodes': 12238}
        """
        unique_persons = self.master_df["person_name"].nunique()
        total_episodes = len(self.master_df)

        return {
            "total_persons": unique_persons,
            "total_episodes": total_episodes,
        }


if __name__ == "__main__":
    # 動作確認用
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.csv_path_resolver import get_master_csv_path
    from src.source_adapters.base import PersonCandidate

    # MASTER CSV読み込み
    master_csv = get_master_csv_path()
    master_df = pd.read_csv(master_csv, encoding="utf-8-sig")

    detector = DuplicationDetector(master_df)

    # 統計情報
    stats = detector.get_statistics()
    print(f"マスターDB統計: {stats}")

    # テストケース1: 完全一致
    candidate1 = PersonCandidate(person_name="山中伸弥", category="科学・技術")
    is_dup, matched, conf, layer = detector.detect_duplicate(candidate1)
    print(f"\nテスト1 (完全一致): {candidate1.person_name}")
    print(f"  結果: is_dup={is_dup}, matched={matched}, conf={conf:.2f}, layer={layer}")

    # テストケース2: 正規化一致（全角スペース）
    candidate2 = PersonCandidate(person_name="山中　伸弥", category="科学・技術")  # 全角スペース
    is_dup, matched, conf, layer = detector.detect_duplicate(candidate2)
    print(f"\nテスト2 (正規化一致): {candidate2.person_name}")
    print(f"  結果: is_dup={is_dup}, matched={matched}, conf={conf:.2f}, layer={layer}")

    # テストケース3: 別名一致
    candidate3 = PersonCandidate(person_name="山中教授", category="科学・技術")
    is_dup, matched, conf, layer = detector.detect_duplicate(candidate3)
    print(f"\nテスト3 (別名一致): {candidate3.person_name}")
    print(f"  結果: is_dup={is_dup}, matched={matched}, conf={conf:.2f}, layer={layer}")

    # テストケース4: 未収録
    candidate4 = PersonCandidate(person_name="テスト太郎", category="テスト")
    is_dup, matched, conf, layer = detector.detect_duplicate(candidate4)
    print(f"\nテスト4 (未収録): {candidate4.person_name}")
    print(f"  結果: is_dup={is_dup}, matched={matched}, conf={conf:.2f}, layer={layer}")
