"""
Celebrity Score v2 - 体感ランキング用スコア計算モジュール

設計方針:
- 案A（トレンド重視型）を採用 + LLM品質スコア追加
- エピソード数・LLM品質を新規シグナルとして追加
- カテゴリ上限で偏り抑制（政治家700）
- 同名曖昧性は確信度<0.8で半減

v1（fame_score_v3）との違い:
- v1: 長期的な評価重視（Wikidata中心）
- v2: 話題性・トレンド・品質重視（エピソード数+LLM品質追加）
"""

import hashlib
import math
from dataclasses import dataclass
from typing import Optional

# 正規化パラメータ
MAX_PV = 10_000_000
MAX_SITELINKS = 200
MAX_INLINKS = 100_000
MAX_GOOGLE_HITS = 1_000_000_000
MAX_EPISODE_COUNT = 30
MAX_LLM_QUALITY = 10.0  # LLM品質スコアの最大値

# 重み配分（国際バランス型 v2.1）
WEIGHTS = {
    "multi_lang_pv": 0.22,  # 0.25→0.22 やや縮小
    "sitelinks": 0.18,  # 0.05→0.18 ★国際的知名度を大幅増加
    "inlinks": 0.12,  # 0.08→0.12 参照度増加
    "google_hits": 0.25,  # 0.30→0.25 やや縮小
    "episode_count": 0.13,  # 0.18→0.13 縮小
    "llm_quality": 0.10,  # 0.14→0.10 縮小
}

# 日本人ボーナス（v2.1: 50%削減でバランス調整）
# 外国人もTop10に入るバランスを実現
JAPAN_PV_BONUS = 0  # 国際的話題性ボーナス削除
JAPAN_FAME_BONUS = 25  # 50→25 国内評価ボーナス
JAPAN_JA_PV_BONUS = 75  # 150→75 日本語Wikipedia PVボーナス
JAPAN_DOMESTIC_FOCUS_BONUS = 60  # 120→60 国内フォーカス度ボーナス
JAPAN_INTL_STAR_BONUS = 135  # 270→135 国際スターボーナス
JAPAN_INTL_STAR_PV_THRESHOLD = 1_000_000  # 国際スター判定閾値（PV基準）
JAPAN_INTL_STAR_SITELINKS_THRESHOLD = 100  # 国際スター判定閾値（sitelinks基準）
MAX_JA_PV = 400_000  # 日本語PV正規化の最大値

# カテゴリ上限（偏り抑制）- 政治家を700に
CATEGORY_CAPS = {
    "政治・社会": 700,
    "アニメ・漫画・ゲーム": 700,
    "アニメ": 700,
    "漫画": 700,
    "ゲーム": 700,
}

# 政治家・天皇ペナルティ（思想的中立性のため）
POLITICIAN_PENALTY = 0.7  # 30%減点
POLITICIAN_CATEGORIES = {"政治・社会", "皇室"}  # 皇室カテゴリも対象
IMPERIAL_KEYWORDS = {"天皇", "皇后", "皇太子", "皇太后", "上皇"}


@dataclass
class CelebritySignals:
    """v2スコア計算用のシグナル"""

    multi_lang_pv: int = 0
    sitelinks: int = 0
    inlinks: int = 0
    google_hits: Optional[int] = None
    episode_count: int = 1
    llm_quality: float = 0.0  # LLM品質スコア（0-10）
    category: str = ""
    disambiguation_confidence: float = 1.0
    # 日本人ブレンド用
    is_japanese: bool = False
    fame_score_japan: float = 0.0
    ja_pv: int = 0  # 日本語Wikipedia PV（国内知名度の直接指標）
    # バズ補正（一時的なPVスパイク対策）
    buzz_adjustment: float = 1.0  # 1.0=補正なし、0.5=PV半減など
    # 政治家ペナルティ用
    person_name: str = ""  # 天皇判定用


@dataclass
class CelebrityScoreResult:
    """v2スコア計算結果"""

    score: float
    raw_score: float  # 上限適用前
    category_cap_applied: bool
    confidence_penalty_applied: bool
    japan_pv_bonus_applied: bool
    buzz_adjustment_applied: bool  # バズ補正が適用されたか
    politician_penalty_applied: bool = False  # 政治家ペナルティが適用されたか
    components: dict = None


def log_normalize(value: float, max_value: float) -> float:
    """対数正規化（0-1スケール）"""
    if value <= 0:
        return 0.0
    return min(math.log(1 + value) / math.log(1 + max_value), 1.0)


def linear_normalize(value: float, max_value: float) -> float:
    """線形正規化（0-1スケール）"""
    if value <= 0:
        return 0.0
    return min(value / max_value, 1.0)


def sqrt_normalize(value: float, max_value: float) -> float:
    """平方根正規化（0-1スケール、緩やかな飽和）"""
    if value <= 0:
        return 0.0
    return min(math.sqrt(value) / math.sqrt(max_value), 1.0)


def calculate_celebrity_score_v2(
    signals: CelebritySignals,
    person_id: str = "",
) -> CelebrityScoreResult:
    """
    Celebrity Score v2を計算。

    Args:
        signals: 計算用シグナル
        person_id: 人物ID（デバッグ用）

    Returns:
        CelebrityScoreResult: スコアと詳細情報
    """
    # バズ補正適用（一時的なPVスパイク対策）
    adjusted_pv = int(signals.multi_lang_pv * signals.buzz_adjustment)
    buzz_adjustment_applied = signals.buzz_adjustment < 1.0

    # 各シグナルを正規化
    pv_norm = log_normalize(adjusted_pv, MAX_PV)
    sitelinks_norm = linear_normalize(signals.sitelinks, MAX_SITELINKS)
    inlinks_norm = log_normalize(signals.inlinks, MAX_INLINKS)
    episode_norm = sqrt_normalize(signals.episode_count, MAX_EPISODE_COUNT)
    llm_quality_norm = linear_normalize(signals.llm_quality, MAX_LLM_QUALITY)

    # Google検索がない場合は他のシグナルで補完
    if signals.google_hits is not None and signals.google_hits > 0:
        google_norm = log_normalize(signals.google_hits, MAX_GOOGLE_HITS)
        weights = WEIGHTS.copy()
    else:
        google_norm = 0.0
        # Google検索なしの場合は重みを再配分（国際バランス型 v2.1）
        weights = {
            "multi_lang_pv": 0.30,  # PV重視
            "sitelinks": 0.28,  # ★国際的知名度を大幅増加
            "inlinks": 0.18,  # 参照度増加
            "google_hits": 0.00,
            "episode_count": 0.14,
            "llm_quality": 0.10,
        }

    # 重み付き合計
    raw_score = (
        pv_norm * weights["multi_lang_pv"]
        + sitelinks_norm * weights["sitelinks"]
        + inlinks_norm * weights["inlinks"]
        + google_norm * weights["google_hits"]
        + episode_norm * weights["episode_count"]
        + llm_quality_norm * weights["llm_quality"]
    ) * 1000

    # コンポーネント保存
    components = {
        "pv_norm": pv_norm,
        "sitelinks_norm": sitelinks_norm,
        "inlinks_norm": inlinks_norm,
        "google_norm": google_norm,
        "episode_norm": episode_norm,
        "llm_quality_norm": llm_quality_norm,
        "weights": weights,
    }

    # バズ補正情報を保存
    if buzz_adjustment_applied:
        components["buzz_adjustment"] = {
            "original_pv": signals.multi_lang_pv,
            "adjusted_pv": adjusted_pv,
            "adjustment_factor": signals.buzz_adjustment,
        }

    score = raw_score
    category_cap_applied = False
    confidence_penalty_applied = False
    japan_pv_bonus_applied = False

    # 日本人ボーナス（5軸評価）
    # 1. 国内評価（fame_score_japan基準）
    # 2. 日本語PV（ja_pv基準）
    # 3. 国内フォーカス度（ja_ratio基準）
    # 4. 国際スター補正（sitelinks>=80の日本人）★新規
    if signals.is_japanese:
        # 1. 国内評価ボーナス（fame_score_japanを0-1に正規化）
        fame_japan_norm = min(signals.fame_score_japan / 1000.0, 1.0)
        fame_bonus = fame_japan_norm * JAPAN_FAME_BONUS

        # 2. 日本語PVボーナス（国内知名度の直接指標）
        ja_pv_norm = log_normalize(signals.ja_pv, MAX_JA_PV)
        ja_pv_bonus = ja_pv_norm * JAPAN_JA_PV_BONUS

        # 3. 国内フォーカス度ボーナス（ja_pv/multi_lang_pv比率）
        # 国内中心の有名人（CM女王、国内ドラマ中心）を優遇
        if signals.multi_lang_pv > 0 and signals.ja_pv > 0:
            ja_ratio = signals.ja_pv / signals.multi_lang_pv
            # ja_ratio 0.5-1.0 を 0-1 にマップ（50%以上を評価）
            domestic_focus = max(0.0, min((ja_ratio - 0.5) * 2, 1.0))
            domestic_focus_bonus = domestic_focus * JAPAN_DOMESTIC_FOCUS_BONUS
        else:
            ja_ratio = 0.0
            domestic_focus = 0.0
            domestic_focus_bonus = 0.0

        # 4. 国際スター補正★新規（大谷翔平、イチロー等）
        # multi_lang_pv >= 1M または sitelinks >= 100 の日本人は国際スター
        # ja_ratioが低くても、日本での知名度は最高レベル
        is_intl_star = (
            signals.multi_lang_pv >= JAPAN_INTL_STAR_PV_THRESHOLD
            or signals.sitelinks >= JAPAN_INTL_STAR_SITELINKS_THRESHOLD
        )
        if is_intl_star:
            # 国際スターボーナス（PVとsitelinksの両方を考慮）
            pv_factor = 0.0
            sl_factor = 0.0

            if signals.multi_lang_pv >= JAPAN_INTL_STAR_PV_THRESHOLD:
                # PV基準：1M-5Mを0.6-1.0にマップ（より急峻に）
                pv_factor = min(0.6 + (signals.multi_lang_pv - 1_000_000) / 10_000_000, 1.0)

            if signals.sitelinks >= JAPAN_INTL_STAR_SITELINKS_THRESHOLD:
                # sitelinks基準：100-200を0.3-0.7にマップ（PVより低く）
                sl_factor = min(0.3 + (signals.sitelinks - 100) / 250, 0.7)

            # 両方の最大値を採用（PV優先）
            intl_star_factor = max(pv_factor, sl_factor)
            intl_star_bonus = intl_star_factor * JAPAN_INTL_STAR_BONUS
        else:
            intl_star_bonus = 0.0

        # 合計ボーナス
        japan_total_bonus = fame_bonus + ja_pv_bonus + domestic_focus_bonus + intl_star_bonus
        score += japan_total_bonus
        japan_pv_bonus_applied = True

        components["japan_bonus"] = {
            "fame_score_japan": signals.fame_score_japan,
            "fame_japan_norm": fame_japan_norm,
            "fame_bonus": fame_bonus,
            "ja_pv": signals.ja_pv,
            "ja_pv_norm": ja_pv_norm,
            "ja_pv_bonus": ja_pv_bonus,
            "ja_ratio": ja_ratio,
            "domestic_focus": domestic_focus,
            "domestic_focus_bonus": domestic_focus_bonus,
            "is_intl_star": is_intl_star,
            "intl_star_bonus": intl_star_bonus,
            "total_bonus": japan_total_bonus,
            "original_score": raw_score,
            "boosted_score": score,
        }

    # カテゴリ上限適用（タイブレーカー付き）
    category_cap = CATEGORY_CAPS.get(signals.category)
    if category_cap and score > category_cap:
        # 超過分を0.001未満の微小値として残す（順位差を保持）
        excess_ratio = min((score - category_cap) / (1000 - category_cap), 1.0)
        score = category_cap + excess_ratio * 0.0009  # 700.0000 ~ 700.0009
        category_cap_applied = True

    # 政治家・天皇ペナルティ（思想的中立性のため）
    politician_penalty_applied = False
    is_politician = signals.category in POLITICIAN_CATEGORIES
    is_imperial = any(kw in signals.person_name for kw in IMPERIAL_KEYWORDS)
    if signals.is_japanese and (is_politician or is_imperial):
        score *= POLITICIAN_PENALTY
        politician_penalty_applied = True
        components["politician_penalty"] = {
            "is_politician": is_politician,
            "is_imperial": is_imperial,
            "penalty_factor": POLITICIAN_PENALTY,
            "original_score": score / POLITICIAN_PENALTY,
            "penalized_score": score,
        }

    # 同名曖昧性ペナルティ
    if signals.disambiguation_confidence < 0.8:
        score *= 0.5
        confidence_penalty_applied = True

    # スコアを0-1000に収める
    score = max(0.0, min(score, 1000.0))

    # タイブレーカー: 高スコア日本人はPVで、それ以外はperson_idで
    # これにより大谷翔平（PV最大）が1位になる
    if person_id and person_id.startswith("P"):
        if signals.is_japanese and score >= 900 and signals.multi_lang_pv > 0:
            # 高スコア日本人: PVでタイブレーク（国際スターを優先）
            # PV 1M → 0.0001, PV 5M → 0.0005
            tiebreaker = signals.multi_lang_pv * 1e-10
            score += tiebreaker
        else:
            # 通常: person_id hexでタイブレーク
            try:
                id_val = int(person_id[1:], 16)  # P01046A9 → 01046A9 → 16910249
                tiebreaker = id_val * 1e-12  # 確実に一意の微小値
                score += tiebreaker
            except ValueError:
                pass

    return CelebrityScoreResult(
        score=round(score, 12),  # 12桁でタイブレーカーを保持
        raw_score=round(raw_score, 6),
        category_cap_applied=category_cap_applied,
        confidence_penalty_applied=confidence_penalty_applied,
        japan_pv_bonus_applied=japan_pv_bonus_applied,
        buzz_adjustment_applied=buzz_adjustment_applied,
        politician_penalty_applied=politician_penalty_applied,
        components=components,
    )


def assign_ranks_v2(scores: list[tuple[str, float]]) -> dict[str, int]:
    """
    スコアに基づいて順位を割り当て。

    Args:
        scores: [(person_id, score), ...]のリスト

    Returns:
        {person_id: rank, ...}
    """
    # スコア降順でソート
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    ranks = {}
    current_rank = 1
    prev_score = None

    for i, (person_id, score) in enumerate(sorted_scores):
        if score != prev_score:
            current_rank = i + 1
        ranks[person_id] = current_rank
        prev_score = score

    return ranks


if __name__ == "__main__":
    # テスト実行
    print("=== Celebrity Score v2 テスト ===\n")

    test_cases = [
        (
            "大谷翔平",
            CelebritySignals(
                multi_lang_pv=13000000,
                sitelinks=100,
                inlinks=500,
                google_hits=32800000,
                episode_count=10,
                category="スポーツ",
            ),
        ),
        (
            "マドンナ",
            CelebritySignals(
                multi_lang_pv=5000000,
                sitelinks=150,
                inlinks=800,
                google_hits=10000000,
                episode_count=5,
                category="音楽",
            ),
        ),
        (
            "ドナルド・トランプ",
            CelebritySignals(
                multi_lang_pv=8000000,
                sitelinks=180,
                inlinks=1000,
                google_hits=50000000,
                episode_count=15,
                category="政治・社会",  # 上限800適用
            ),
        ),
        (
            "短名テスト",
            CelebritySignals(
                multi_lang_pv=100000,
                sitelinks=20,
                inlinks=50,
                google_hits=1000000,
                episode_count=2,
                category="音楽",
                disambiguation_confidence=0.5,  # 半減
            ),
        ),
    ]

    for name, signals in test_cases:
        result = calculate_celebrity_score_v2(signals)
        print(f"{name}:")
        print(f"  スコア: {result.score}")
        print(f"  生スコア: {result.raw_score}")
        print(f"  カテゴリ上限: {result.category_cap_applied}")
        print(f"  曖昧性ペナルティ: {result.confidence_penalty_applied}")
        print()
