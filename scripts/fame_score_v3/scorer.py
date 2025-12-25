"""
有名人度スコア計算モジュール。

複数のシグナルを正規化・統合してスコアを計算する。
"""

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# 架空キャラクターのsitelinkガードレール
FICTIONAL_SITELINKS_WARNING_THRESHOLD = 100
FICTIONAL_SITELINKS_CAP = 50  # 異常に高い場合のキャップ


@dataclass
class FameSignals:
    """有名人度の各シグナル"""

    multi_lang_pv: int = 0  # 多言語Wikipedia合計PV
    sitelinks: int = 0  # 言語版数
    inlinks: int = 0  # 被リンク数
    google_hits: Optional[int] = None  # Google検索ヒット数（Phase 2）


@dataclass
class FameScore:
    """計算された有名人度スコア"""

    score: float  # 最終スコア（0-1000）
    rank: int  # 順位（1-N）
    normalized_pv: float  # 正規化されたPV
    normalized_sitelinks: float  # 正規化された言語版数
    normalized_inlinks: float  # 正規化された被リンク数
    raw_score: float  # 正規化前の合成スコア


# 正規化パラメータ
MAX_PV = 10_000_000  # 最大1000万PV
MAX_SITELINKS = 200  # 最大200言語
MAX_INLINKS = 100_000  # 最大10万被リンク
MAX_GOOGLE_HITS = 1_000_000_000  # 最大10億ヒット

# 重み（Phase 1: Google検索なし）
WEIGHTS_PHASE1 = {
    "multi_lang_pv": 0.50,
    "sitelinks": 0.30,
    "inlinks": 0.20,
}

# 重み（Phase 2: Google検索あり）
WEIGHTS_PHASE2 = {
    "multi_lang_pv": 0.40,
    "sitelinks": 0.25,
    "inlinks": 0.15,
    "google_hits": 0.20,
}


def normalize_pv(pv: int) -> float:
    """PVを0-1に正規化（対数スケール）"""
    if pv <= 0:
        return 0.0
    return math.log1p(pv) / math.log1p(MAX_PV)


def normalize_sitelinks(count: int) -> float:
    """言語版数を0-1に正規化（線形スケール）"""
    if count <= 0:
        return 0.0
    return min(count / MAX_SITELINKS, 1.0)


def normalize_inlinks(count: int) -> float:
    """被リンク数を0-1に正規化（対数スケール）"""
    if count <= 0:
        return 0.0
    return math.log1p(count) / math.log1p(MAX_INLINKS)


def normalize_google_hits(hits: int) -> float:
    """Google検索ヒット数を0-1に正規化（対数スケール）"""
    if hits <= 0:
        return 0.0
    return math.log1p(hits) / math.log1p(MAX_GOOGLE_HITS)


def stable_tiebreaker(person_id: str) -> float:
    """
    安定したハッシュ由来の極小値（0-0.001）。

    同点の場合に決定的な順序を保証するために使用。
    """
    h = hashlib.md5(person_id.encode()).hexdigest()
    return int(h[:8], 16) / (16**8) * 0.001


def calculate_fame_score(
    signals: FameSignals,
    person_id: str = "",
    person_type: str = "REAL",
) -> FameScore:
    """
    有名人度スコアを計算。

    Args:
        signals: 各シグナルの値
        person_id: 人物ID（タイブレーク用）
        person_type: "REAL" または "FICTIONAL"

    Returns:
        FameScore オブジェクト
    """
    # 架空キャラクターのガードレール
    sitelinks_for_calc = signals.sitelinks
    if person_type == "FICTIONAL":
        if signals.sitelinks > FICTIONAL_SITELINKS_WARNING_THRESHOLD:
            logger.warning(
                f"FICTIONAL character {person_id} has unusually high sitelinks: "
                f"{signals.sitelinks} (capped to {FICTIONAL_SITELINKS_CAP})"
            )
            # 異常に高いsitelinksをキャップ
            sitelinks_for_calc = min(signals.sitelinks, FICTIONAL_SITELINKS_CAP)

    # 正規化
    norm_pv = normalize_pv(signals.multi_lang_pv)
    norm_sitelinks = normalize_sitelinks(sitelinks_for_calc)
    norm_inlinks = normalize_inlinks(signals.inlinks)

    # 重み付け合成
    if signals.google_hits is not None:
        # Phase 2: Google検索あり
        norm_google = normalize_google_hits(signals.google_hits)
        weights = WEIGHTS_PHASE2
        raw = (
            weights["multi_lang_pv"] * norm_pv
            + weights["sitelinks"] * norm_sitelinks
            + weights["inlinks"] * norm_inlinks
            + weights["google_hits"] * norm_google
        )
    else:
        # Phase 1: Google検索なし
        weights = WEIGHTS_PHASE1
        raw = (
            weights["multi_lang_pv"] * norm_pv
            + weights["sitelinks"] * norm_sitelinks
            + weights["inlinks"] * norm_inlinks
        )

    # タイブレーカーを追加（極小値）
    if person_id:
        raw += stable_tiebreaker(person_id)

    # 0-1000スケーリング（小数点2桁）
    score = min(max(raw * 1000, 0), 1000)
    score = round(score, 2)

    return FameScore(
        score=score,
        rank=0,  # 後で計算
        normalized_pv=round(norm_pv, 4),
        normalized_sitelinks=round(norm_sitelinks, 4),
        normalized_inlinks=round(norm_inlinks, 4),
        raw_score=round(raw, 6),
    )


def assign_ranks(scores: list[tuple[str, float]]) -> dict[str, int]:
    """
    スコアから順位を割り当て。

    Args:
        scores: [(person_id, score), ...] のリスト

    Returns:
        {person_id: rank, ...}
    """
    # スコア降順でソート
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    # 順位を割り当て
    ranks = {}
    for i, (person_id, _) in enumerate(sorted_scores, start=1):
        ranks[person_id] = i

    return ranks


if __name__ == "__main__":
    # テスト実行
    print("=== スコア計算テスト ===\n")

    test_cases = [
        # (名前, multi_lang_pv, sitelinks, inlinks)
        ("大谷翔平（想定）", 5_000_000, 50, 5000),
        ("スティーブ・ジョブズ（想定）", 10_000_000, 120, 20000),
        ("マイケル・ジョーダン（想定）", 8_000_000, 100, 15000),
        ("小泉八雲（想定）", 100_000, 15, 500),
        ("一般人", 1000, 1, 10),
    ]

    results = []
    for name, pv, sitelinks, inlinks in test_cases:
        signals = FameSignals(
            multi_lang_pv=pv,
            sitelinks=sitelinks,
            inlinks=inlinks,
        )
        score = calculate_fame_score(signals, name)
        results.append((name, score.score))

        print(f"{name}:")
        print(f"  入力: PV={pv:,}, 言語版数={sitelinks}, 被リンク={inlinks}")
        print(
            f"  正規化: PV={score.normalized_pv:.4f}, "
            f"言語版数={score.normalized_sitelinks:.4f}, "
            f"被リンク={score.normalized_inlinks:.4f}"
        )
        print(f"  スコア: {score.score:.2f}")
        print()

    # 順位を計算
    print("=== 順位 ===")
    ranks = assign_ranks(results)
    for name, _ in sorted(results, key=lambda x: ranks[x[0]]):
        print(f"  {ranks[name]}位: {name}")
