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
import re
from dataclasses import dataclass

import numpy as np

from .config import (
    WEIGHTS,
    LLM_WEIGHTS,
    TYPE_BONUS,
    TYPE_MAPPING,
    HISTORICAL_KEYWORDS,
    KEYWORD_BONUS_MAX,
    TIER1_KEYWORDS,
    TIER1_DIRECT_BONUS,
    MAJOR_AWARD_KEYWORDS,
    PRIMARY_TOPIC_BONUS,
    PRIMARY_TOPIC_THRESHOLD,
    ACHIEVEMENT_CONTEXT,
    NEGATIVE_CONTEXT,
    NEGATIVE_CONTEXT_PENALTY,
    NEGATIVE_CONTEXT_MAX_PENALTY,
    OTHER_PERSON_REFERENCE_PATTERNS,
    FUTURE_REFERENCE_PATTERNS,
    PENALTY_KEYWORDS,
    PENALTY_MAX,
    RETROSPECTIVE_PATTERNS,
    RETROSPECTIVE_PENALTY_PER_PATTERN,
    RETROSPECTIVE_PENALTY_MAX,
    CONCRETE_EVENT_INDICATORS,
    LACK_OF_SPECIFICITY_PENALTY,
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
    retrospective_penalty: float  # 0-20 (回顧・具体性欠如ペナルティ)
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

    def _count_negative_contexts(self, text: str) -> int:
        """否定コンテキストの出現数をカウント"""
        return sum(1 for ctx in NEGATIVE_CONTEXT if ctx in text)

    def _has_other_person_reference(self, text: str) -> bool:
        """他者参照パターンがあるかチェック（例: ノーベル賞物理学者を含む）"""
        return any(re.search(pattern, text) for pattern in OTHER_PERSON_REFERENCE_PATTERNS)

    def _has_future_reference(self, text: str) -> bool:
        """未来参照パターンがあるかチェック（例: 翌年、彼はノーベル賞を受賞）"""
        return any(re.search(pattern, text) for pattern in FUTURE_REFERENCE_PATTERNS)

    def _keyword_is_subject_achievement(self, text: str, keyword: str) -> bool:
        """キーワードが主語の達成を表すかチェック（他者参照・未来参照でない）"""
        # キーワード周辺のコンテキストを取得
        kw_pos = text.find(keyword)
        if kw_pos < 0:
            return False

        # キーワード前後50文字のコンテキスト
        start = max(0, kw_pos - 50)
        end = min(len(text), kw_pos + len(keyword) + 50)
        context = text[start:end]

        # 他者参照パターンチェック
        if self._has_other_person_reference(context):
            return False

        # 未来参照パターンチェック
        if self._has_future_reference(context):
            return False

        return True

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
        negative_count = self._count_negative_contexts(text_head)  # 複数カウント

        # 他者参照・未来参照チェック（冒頭部分）
        has_other_ref = self._has_other_person_reference(text_head)
        has_future_ref = self._has_future_reference(episode_text)

        # キーワードボーナス
        keyword_bonus = 0
        primary_topic_found = False

        for kw in HISTORICAL_KEYWORDS["tier1"]:
            if kw in episode_text:
                # キーワードが主語の達成かチェック
                is_subject_achievement = self._keyword_is_subject_achievement(episode_text, kw)

                if is_subject_achievement:
                    keyword_bonus += 10
                else:
                    # 他者参照・未来参照の場合は半減
                    keyword_bonus += 5

                # 主題一致ボーナス: 冒頭100文字以内に出現
                if kw in text_head and not primary_topic_found:
                    # 否定コンテキスト・他者参照・未来参照がない場合のみフルボーナス
                    if not has_negative and not has_other_ref and not has_future_ref:
                        keyword_bonus += PRIMARY_TOPIC_BONUS
                    primary_topic_found = True

        for kw in HISTORICAL_KEYWORDS["tier2"]:
            if kw in episode_text:
                keyword_bonus += 6
                # tier2も主題一致ボーナス対象
                if kw in text_head and not primary_topic_found:
                    if has_achievement and not has_negative and not has_other_ref:
                        keyword_bonus += PRIMARY_TOPIC_BONUS // 2
                    primary_topic_found = True

        for kw in HISTORICAL_KEYWORDS["tier3"]:
            if kw in episode_text:
                keyword_bonus += 3

        # 否定コンテキストペナルティ（累積、最大値あり）
        if negative_count > 0:
            penalty = min(negative_count * NEGATIVE_CONTEXT_PENALTY, NEGATIVE_CONTEXT_MAX_PENALTY)
            keyword_bonus -= penalty

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

    def calculate_retrospective_penalty(self, episode_text: str) -> float:
        """
        回顧・具体性欠如ペナルティ計算（0-20）

        「晩年の回顧」「人生を振り返り」など具体的事象がない
        エピソードにペナルティを適用する。
        """
        penalty = 0.0

        # 1. 回顧パターン検出
        retrospective_count = 0
        for pattern in RETROSPECTIVE_PATTERNS:
            if re.search(pattern, episode_text):
                retrospective_count += 1

        if retrospective_count > 0:
            penalty += min(
                retrospective_count * RETROSPECTIVE_PENALTY_PER_PATTERN,
                RETROSPECTIVE_PENALTY_MAX,
            )

        # 2. 具体性欠如の検出
        # 具体的イベント指標が1つもない場合、追加ペナルティ
        has_concrete_event = any(re.search(pattern, episode_text) for pattern in CONCRETE_EVENT_INDICATORS)

        if not has_concrete_event and retrospective_count > 0:
            # 回顧表現があり、かつ具体的イベントがない場合のみ追加ペナルティ
            penalty += LACK_OF_SPECIFICITY_PENALTY

        return min(penalty, 20.0)  # 最大20点

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
            memorability=float(row.get("memorability_score") or 0),
            empathy=float(row.get("empathy_score") or 0),
            surprise=float(row.get("surprise_score") or 0),
            generation_quality=float(row.get("generation_quality_score") or 0),
            educational_value=float(row.get("educational_value") or 0),
            storytelling_quality=float(row.get("story_quality") or 0),
            factual_density=float(row.get("factual_density") or 0),
        )

        # 各コンポーネント計算
        person_fame = self.calculate_person_fame(data.celebrity_score_v2, data.sitelinks_count)
        llm_quality = self.calculate_llm_quality(data)
        historical_impact = self.calculate_historical_impact(data.episode_text, data.episode_type)
        pv_signal = self.calculate_pv_signal(data.multi_lang_pv)
        episode_bonus = self.calculate_episode_bonus(data.episode_count)
        penalty = self.calculate_penalty(data.episode_text)
        retrospective_penalty = self.calculate_retrospective_penalty(data.episode_text)

        # 加重合計
        total = (
            person_fame * WEIGHTS["person_fame"]
            + llm_quality * WEIGHTS["llm_quality"]
            + historical_impact * WEIGHTS["historical_impact"]
            + pv_signal * WEIGHTS["pv_signal"]
            + episode_bonus * WEIGHTS["episode_bonus"]
            - penalty
            - retrospective_penalty  # 回顧・具体性欠如ペナルティ適用
        )

        # Tier1キーワード直接ボーナス（ノーベル賞、グラミー賞等）
        if any(kw in data.episode_text for kw in TIER1_KEYWORDS):
            total += TIER1_DIRECT_BONUS

        # 国際賞カテゴリボーナス（低知名度人物でも国際賞受賞EPは上位に）
        # TIER1とは別に加算。最大1つのボーナスのみ適用
        award_bonus = 0
        for keyword, bonus in MAJOR_AWARD_KEYWORDS.items():
            if keyword in data.episode_text:
                award_bonus = max(award_bonus, bonus)
        total += award_bonus

        # 上限クランプを削除: 100超の値を許容し、同率問題を解消
        # raw値をそのまま使用することで、ランキング順位が一意に決まる
        total = max(0, total)  # 下限のみ維持

        # Tier1エピソードの最低スコア保証（78点フロア）
        # ノーベル賞等の重要イベントは最低78点を保証
        if any(kw in data.episode_text for kw in TIER1_KEYWORDS):
            total = max(total, 78.0)

        tier = self.calculate_tier(total)

        return ScoreBreakdown(
            person_fame=person_fame,
            llm_quality=llm_quality,
            historical_impact=historical_impact,
            pv_signal=pv_signal,
            episode_bonus=episode_bonus,
            penalty=penalty,
            retrospective_penalty=retrospective_penalty,
            total_score=total,
            tier=tier,
        )


def _contains_tier1_keyword(episode_text: str) -> bool:
    """エピソードテキストにTier1キーワードが含まれるかチェック"""
    if not episode_text:
        return False
    return any(kw in episode_text for kw in TIER1_KEYWORDS)


def apply_bias_control(ranked_episodes: list[dict]) -> list[dict]:
    """
    同一人物制限を適用してランキングを調整

    Args:
        ranked_episodes: スコア降順でソート済みのエピソードリスト

    Returns:
        制限適用後のランキング

    Note:
        Tier1キーワード（ノーベル賞、大統領就任等）を含むエピソードは
        制限を+1件緩和し、最重要転機が落ちにくくなるよう保護する。
        追加枠は「通常枠が埋まった後に」適用される。
    """
    result = []
    person_counts = {}  # person_id -> count in result
    person_tier1_used = {}  # person_id -> Tier1追加枠を使用したかどうか
    deferred = []  # 制限で外れたエピソード

    # Tier1エピソード保護のための追加枠
    TIER1_EXTRA_SLOTS = 1  # Tier1キーワード含有時に+1件の追加枠

    for ep in ranked_episodes:
        person_id = ep.get("person_id", "")
        episode_text = ep.get("episode_text", "")
        current_count = person_counts.get(person_id, 0)
        current_rank = len(result) + 1

        # Tier1キーワード判定
        is_tier1 = _contains_tier1_keyword(episode_text)

        # 現在の順位に対する制限を確認
        limit = None
        for threshold, max_count in sorted(BIAS_CONTROL.items()):
            if current_rank <= threshold:
                limit = max_count
                break

        # 通常枠での判定
        if limit is None or current_count < limit:
            # 制限内なので採用（通常枠）
            result.append(ep)
            person_counts[person_id] = current_count + 1
        elif is_tier1 and not person_tier1_used.get(person_id, False):
            # 通常枠は埋まっているが、Tier1追加枠が使える
            result.append(ep)
            person_counts[person_id] = current_count + 1
            person_tier1_used[person_id] = True  # 追加枠を消費
        else:
            # 制限超過なので後回し
            deferred.append(ep)

    # 後回しにしたエピソードを末尾に追加
    result.extend(deferred)

    return result
