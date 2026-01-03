"""
Episode Fame Score v6 算出ロジック

案A: バランス重視
- person_fame: 30% (celebrity_score_v2 + sitelinks正規化)
- llm_quality: 25% (LLM 7軸加重平均)
- historical_impact: 20% (キーワード + タイプボーナス)
- pv_signal: 15% (Wikipedia PV正規化)
- episode_bonus: 10% (エピソード数飽和)
"""

import math
from dataclasses import dataclass

import numpy as np

from .config import (
    WEIGHTS,
    LLM_WEIGHTS,
    TYPE_BONUS,
    TYPE_MAPPING,
    HISTORICAL_KEYWORDS,
    KEYWORD_BONUS_MAX,
    PRIMARY_TOPIC_BONUS,
    PRIMARY_TOPIC_THRESHOLD,
    ACHIEVEMENT_CONTEXT,
    NEGATIVE_CONTEXT,
    NEGATIVE_CONTEXT_PENALTY,
    PENALTY_KEYWORDS,
    PENALTY_MAX,
    BIAS_CONTROL,
    NORMALIZATION,
    EPISODE_COUNT_SATURATION,
    TIER_THRESHOLDS,
)


@dataclass
class EpisodeData:
    """エピソードデータ"""

    episode_id: str
    person_id: str
    person_name: str
    episode_text: str
    episode_type: str
    episode_count: int
    celebrity_score_v2: float
    sitelinks_count: int
    multi_lang_pv: int
    # LLM 7軸スコア
    memorability: float
    empathy: float
    surprise: float
    generation_quality: float
    educational_value: float
    storytelling_quality: float
    factual_density: float


@dataclass
class ScoreBreakdown:
    """スコア内訳"""

    person_fame: float  # 0-100
    llm_quality: float  # 0-100
    historical_impact: float  # 0-100
    pv_signal: float  # 0-100
    episode_bonus: float  # 0-100
    penalty: float  # 0-15
    total_score: float  # 0-100
    tier: int  # 1-5


class EpisodeFameV6Scorer:
    """Episode Fame v6 スコア算出器"""

    def __init__(self, all_episodes: list[dict]):
        """
        Args:
            all_episodes: 全エピソードデータ（正規化用）
        """
        self.all_episodes = all_episodes
        self._compute_normalization_params()

    def _compute_normalization_params(self):
        """正規化パラメータを計算"""
        # celebrity_score_v2
        celeb_scores = [float(e.get("celebrity_score_v2") or 0) for e in self.all_episodes]
        self.celeb_p1, self.celeb_p99 = self._percentile_bounds(celeb_scores)

        # sitelinks
        sitelinks = [int(float(e.get("sitelinks_count") or 0)) for e in self.all_episodes]
        self.sitelinks_p1, self.sitelinks_p99 = self._percentile_bounds(sitelinks, use_log=True)

        # multi_lang_pv
        pvs = [int(float(e.get("multi_lang_pv") or 0)) for e in self.all_episodes]
        self.pv_p1, self.pv_p99 = self._percentile_bounds(pvs, use_log=True)

    def _percentile_bounds(self, values: list, use_log: bool = False) -> tuple[float, float]:
        """パーセンタイル境界を計算"""
        arr = np.array(values, dtype=float)
        if use_log and NORMALIZATION["use_log"]:
            arr = np.log1p(arr)
        p_low, p_high = NORMALIZATION["percentile_clip"]
        p1 = np.percentile(arr, p_low)
        p99 = np.percentile(arr, p_high)
        return float(p1), float(p99)

    def _normalize(self, value: float, p1: float, p99: float, use_log: bool = False) -> float:
        """0-1に正規化"""
        if use_log and NORMALIZATION["use_log"]:
            value = math.log1p(value)
        if p99 <= p1:
            return 0.5
        clipped = max(p1, min(p99, value))
        return (clipped - p1) / (p99 - p1)

    def calculate_person_fame(self, celeb_score: float, sitelinks: int) -> float:
        """人物知名度スコア（0-100）"""
        # celebrity_score_v2 (70%) + sitelinks (30%)
        celeb_norm = self._normalize(celeb_score, self.celeb_p1, self.celeb_p99)
        sitelinks_norm = self._normalize(sitelinks, self.sitelinks_p1, self.sitelinks_p99, use_log=True)
        combined = celeb_norm * 0.7 + sitelinks_norm * 0.3
        return combined * 100

    def calculate_llm_quality(self, data: EpisodeData) -> float:
        """LLM品質スコア（0-100）"""
        scores = {
            "memorability": data.memorability,
            "surprise": data.surprise,
            "storytelling_quality": data.storytelling_quality,
            "educational_value": data.educational_value,
            "factual_density": data.factual_density,
            "empathy": data.empathy,
            "generation_quality": data.generation_quality,
        }

        weighted_sum = 0.0
        weight_sum = 0.0
        for key, weight in LLM_WEIGHTS.items():
            value = scores.get(key, 0) or 0
            # 10点満点を100点に換算
            weighted_sum += (value / 10.0) * weight * 100
            weight_sum += weight

        if weight_sum > 0:
            return weighted_sum / weight_sum
        return 50.0  # デフォルト

    def _has_achievement_context(self, text: str) -> bool:
        """達成コンテキストがあるかチェック"""
        return any(ctx in text for ctx in ACHIEVEMENT_CONTEXT)

    def _has_negative_context(self, text: str) -> bool:
        """否定コンテキストがあるかチェック"""
        return any(ctx in text for ctx in NEGATIVE_CONTEXT)

    def calculate_historical_impact(self, episode_text: str, episode_type: str) -> float:
        """歴史的インパクトスコア（0-100）"""
        score = 50.0  # ベース

        # タイプボーナス（日本語→英語変換対応）
        en_type = TYPE_MAPPING.get(episode_type, episode_type)  # 日本語なら変換、英語ならそのまま
        type_bonus = TYPE_BONUS.get(en_type, 0)
        score += type_bonus

        # コンテキスト分析
        text_head = episode_text[:PRIMARY_TOPIC_THRESHOLD]  # 冒頭部分
        has_achievement = self._has_achievement_context(episode_text)
        has_negative = self._has_negative_context(text_head)  # 冒頭の否定コンテキストのみチェック

        # キーワードボーナス
        keyword_bonus = 0
        primary_topic_found = False

        for kw in HISTORICAL_KEYWORDS["tier1"]:
            if kw in episode_text:
                keyword_bonus += 10
                # 主題一致ボーナス: 冒頭100文字以内に出現 + 達成コンテキストあり
                if kw in text_head and not primary_topic_found:
                    if has_achievement and not has_negative:
                        # 達成コンテキストあり、否定コンテキストなし → フルボーナス
                        keyword_bonus += PRIMARY_TOPIC_BONUS
                    elif not has_negative:
                        # 達成コンテキストなし、否定コンテキストなし → 半分ボーナス
                        keyword_bonus += PRIMARY_TOPIC_BONUS // 2
                    # 否定コンテキストあり → ボーナスなし
                    primary_topic_found = True

        for kw in HISTORICAL_KEYWORDS["tier2"]:
            if kw in episode_text:
                keyword_bonus += 6
                # tier2も主題一致ボーナス対象
                if kw in text_head and not primary_topic_found:
                    if has_achievement and not has_negative:
                        keyword_bonus += PRIMARY_TOPIC_BONUS // 2
                    primary_topic_found = True

        for kw in HISTORICAL_KEYWORDS["tier3"]:
            if kw in episode_text:
                keyword_bonus += 3

        # 否定コンテキストペナルティ（冒頭に否定的言及がある場合）
        if has_negative:
            keyword_bonus -= NEGATIVE_CONTEXT_PENALTY

        score += min(max(0, keyword_bonus), KEYWORD_BONUS_MAX + PRIMARY_TOPIC_BONUS)

        return min(100, max(0, score))

    def calculate_pv_signal(self, pv: int) -> float:
        """PVシグナルスコア（0-100）"""
        norm = self._normalize(pv, self.pv_p1, self.pv_p99, use_log=True)
        return norm * 100

    def calculate_episode_bonus(self, count: int) -> float:
        """エピソード数ボーナス（0-100）"""
        # 飽和関数: min(1.0, log(1 + count) / log(1 + saturation))
        if count <= 0:
            return 0
        ratio = math.log1p(count) / math.log1p(EPISODE_COUNT_SATURATION)
        return min(1.0, ratio) * 100

    def calculate_penalty(self, episode_text: str) -> float:
        """ペナルティ計算（0-15）"""
        penalty = 0
        for kw in PENALTY_KEYWORDS:
            if kw in episode_text:
                penalty += 3
        return min(penalty, PENALTY_MAX)

    def calculate_tier(self, score: float) -> int:
        """ティア判定"""
        for tier, threshold in sorted(TIER_THRESHOLDS.items(), reverse=True):
            if score >= threshold:
                return tier
        return 1

    def score_episode(self, row: dict) -> ScoreBreakdown:
        """エピソードをスコアリング"""
        data = EpisodeData(
            episode_id=row.get("episode_id", ""),
            person_id=row.get("person_id", ""),
            person_name=row.get("person_name", ""),
            episode_text=row.get("episode_text", ""),
            episode_type=row.get("episode_type", ""),
            episode_count=int(float(row.get("episode_count") or 1)),
            celebrity_score_v2=float(row.get("celebrity_score_v2") or 0),
            sitelinks_count=int(float(row.get("sitelinks_count") or 0)),
            multi_lang_pv=int(float(row.get("multi_lang_pv") or 0)),
            memorability=float(row.get("記憶性スコア") or 0),
            empathy=float(row.get("共感性スコア") or 0),
            surprise=float(row.get("意外性スコア") or 0),
            generation_quality=float(row.get("生成品質スコア") or 0),
            educational_value=float(row.get("教育的価値") or 0),
            storytelling_quality=float(row.get("ストーリー品質") or 0),
            factual_density=float(row.get("事実密度") or 0),
        )

        # 各コンポーネント計算
        person_fame = self.calculate_person_fame(data.celebrity_score_v2, data.sitelinks_count)
        llm_quality = self.calculate_llm_quality(data)
        historical_impact = self.calculate_historical_impact(data.episode_text, data.episode_type)
        pv_signal = self.calculate_pv_signal(data.multi_lang_pv)
        episode_bonus = self.calculate_episode_bonus(data.episode_count)
        penalty = self.calculate_penalty(data.episode_text)

        # 加重合計
        total = (
            person_fame * WEIGHTS["person_fame"]
            + llm_quality * WEIGHTS["llm_quality"]
            + historical_impact * WEIGHTS["historical_impact"]
            + pv_signal * WEIGHTS["pv_signal"]
            + episode_bonus * WEIGHTS["episode_bonus"]
            - penalty
        )
        total = max(0, min(100, total))
        tier = self.calculate_tier(total)

        return ScoreBreakdown(
            person_fame=person_fame,
            llm_quality=llm_quality,
            historical_impact=historical_impact,
            pv_signal=pv_signal,
            episode_bonus=episode_bonus,
            penalty=penalty,
            total_score=total,
            tier=tier,
        )


def apply_bias_control(ranked_episodes: list[dict]) -> list[dict]:
    """
    同一人物制限を適用してランキングを調整

    Args:
        ranked_episodes: スコア降順でソート済みのエピソードリスト

    Returns:
        制限適用後のランキング
    """
    result = []
    person_counts = {}  # person_id -> count in result
    deferred = []  # 制限で外れたエピソード

    for ep in ranked_episodes:
        person_id = ep.get("person_id", "")
        current_count = person_counts.get(person_id, 0)
        current_rank = len(result) + 1

        # 現在の順位に対する制限を確認
        limit = None
        for threshold, max_count in sorted(BIAS_CONTROL.items()):
            if current_rank <= threshold:
                limit = max_count
                break

        if limit is None or current_count < limit:
            # 制限内なので採用
            result.append(ep)
            person_counts[person_id] = current_count + 1
        else:
            # 制限超過なので後回し
            deferred.append(ep)

    # 後回しにしたエピソードを末尾に追加
    result.extend(deferred)

    return result
