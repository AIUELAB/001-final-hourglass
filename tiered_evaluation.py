#!/usr/bin/env python3
"""
階層的評価ロジックシステム
重要度に応じてAPI使用を最適化し、処理時間を大幅短縮
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvaluationTier(Enum):
    """評価階層"""
    TIER1_QUICK = "tier1_quick"      # 高速評価（2 API）
    TIER2_STANDARD = "tier2_standard" # 標準評価（3 API）
    TIER3_DETAILED = "tier3_detailed" # 詳細評価（5 API）


@dataclass
class TierConfig:
    """階層設定"""
    tier: EvaluationTier
    apis: List[str]
    threshold_min: float
    threshold_max: float
    time_estimate: int  # 秒
    quality_score: float  # 0-1


@dataclass
class EvaluationResult:
    """評価結果"""
    person_id: str
    person_name: str
    tier_used: EvaluationTier
    apis_called: List[str]
    final_score: float
    confidence: float
    processing_time: float
    cached: bool = False


class TieredEvaluator:
    """階層的評価システム"""

    def __init__(self):
        self.tier_configs = self._initialize_tiers()
        self.category_tier_mapping = self._initialize_category_mapping()
        self.quick_pattern_cache = {}

    def _initialize_tiers(self) -> Dict[EvaluationTier, TierConfig]:
        """階層初期化"""
        return {
            EvaluationTier.TIER1_QUICK: TierConfig(
                tier=EvaluationTier.TIER1_QUICK,
                apis=["Google", "Brave"],
                threshold_min=0.0,
                threshold_max=10.0,
                time_estimate=2,
                quality_score=0.7
            ),
            EvaluationTier.TIER2_STANDARD: TierConfig(
                tier=EvaluationTier.TIER2_STANDARD,
                apis=["Google", "Brave", "YouTube"],
                threshold_min=3.0,
                threshold_max=7.0,
                time_estimate=10,
                quality_score=0.85
            ),
            EvaluationTier.TIER3_DETAILED: TierConfig(
                tier=EvaluationTier.TIER3_DETAILED,
                apis=["Google", "Brave", "YouTube", "Twitter", "News"],
                threshold_min=4.0,
                threshold_max=6.0,
                time_estimate=30,
                quality_score=0.95
            )
        }

    def _initialize_category_mapping(self) -> Dict[str, EvaluationTier]:
        """カテゴリ別階層マッピング"""
        return {
            # 高優先度カテゴリ（詳細評価）
            "YouTuber": EvaluationTier.TIER3_DETAILED,
            "歌手": EvaluationTier.TIER3_DETAILED,
            "俳優": EvaluationTier.TIER3_DETAILED,
            "アイドル": EvaluationTier.TIER3_DETAILED,

            # 中優先度カテゴリ（標準評価）
            "声優": EvaluationTier.TIER2_STANDARD,
            "芸人": EvaluationTier.TIER2_STANDARD,
            "スポーツ選手": EvaluationTier.TIER2_STANDARD,
            "政治家": EvaluationTier.TIER2_STANDARD,

            # 低優先度カテゴリ（高速評価）
            "実業家": EvaluationTier.TIER1_QUICK,
            "研究者": EvaluationTier.TIER1_QUICK,
            "その他": EvaluationTier.TIER1_QUICK,
            None: EvaluationTier.TIER1_QUICK
        }

    def determine_tier(
        self,
        row: pd.Series,
        pre_filter_score: Optional[float] = None
    ) -> EvaluationTier:
        """評価階層決定"""

        # 1. 事前フィルタリングスコアがある場合
        if pre_filter_score is not None:
            if pre_filter_score >= 8.0:
                # 明らかに有名 → 簡易確認のみ
                return EvaluationTier.TIER1_QUICK
            elif pre_filter_score <= 2.0:
                # 明らかに無名 → 簡易確認のみ
                return EvaluationTier.TIER1_QUICK
            elif 5.0 <= pre_filter_score < 8.0:
                # 中程度 → 標準評価
                return EvaluationTier.TIER2_STANDARD
            else:
                # 境界線上 → 詳細評価
                return EvaluationTier.TIER3_DETAILED

        # 2. カテゴリベースの判定
        category = row.get('category', None)
        if category in self.category_tier_mapping:
            return self.category_tier_mapping[category]

        # 3. メタデータベースの判定
        has_wikipedia = pd.notna(row.get('wikipedia_url', None))
        has_birth_year = pd.notna(row.get('birth_year', None))

        if has_wikipedia and has_birth_year:
            # 情報が充実 → 標準評価で十分
            return EvaluationTier.TIER2_STANDARD
        elif has_wikipedia or has_birth_year:
            # 部分的な情報 → 詳細評価
            return EvaluationTier.TIER3_DETAILED
        else:
            # 情報不足 → 高速評価
            return EvaluationTier.TIER1_QUICK

    async def evaluate_with_tier(
        self,
        row: pd.Series,
        tier: EvaluationTier,
        cache_system=None,
        api_caller=None
    ) -> EvaluationResult:
        """階層に基づく評価実行"""

        person_id = row.get('person_id', '')
        person_name = row.get('person_name_ja', row.get('person_name', ''))

        logger.info(f"🎯 評価開始: {person_name} (Tier: {tier.value})")

        config = self.tier_configs[tier]
        api_results = {}
        cached_count = 0

        import time
        start_time = time.time()

        # 指定されたAPIのみ呼び出し
        for api_name in config.apis:
            # キャッシュチェック
            if cache_system:
                cached_value, cache_layer = cache_system.get(api_name, person_name)
                if cached_value:
                    api_results[api_name] = cached_value
                    cached_count += 1
                    logger.info(f"  ✅ {api_name}: キャッシュヒット ({cache_layer})")
                    continue

            # API呼び出し（シミュレーション）
            if api_caller:
                result = await api_caller(api_name, person_name)
            else:
                # シミュレーション
                await asyncio.sleep(0.1)
                result = self._simulate_api_result(api_name, person_name)

            api_results[api_name] = result

            # キャッシュ保存
            if cache_system:
                cache_system.set(api_name, person_name, result)

        # スコア計算
        final_score = self._calculate_tiered_score(api_results, tier)
        confidence = self._calculate_confidence(api_results, tier)

        processing_time = time.time() - start_time

        result = EvaluationResult(
            person_id=person_id,
            person_name=person_name,
            tier_used=tier,
            apis_called=list(api_results.keys()),
            final_score=final_score,
            confidence=confidence,
            processing_time=processing_time,
            cached=(cached_count > 0)
        )

        logger.info(f"  📊 結果: スコア={final_score:.2f}, 信頼度={confidence:.2%}, 時間={processing_time:.1f}秒")

        return result

    def _simulate_api_result(self, api_name: str, query: str) -> Dict:
        """API結果シミュレーション"""
        # 名前の長さと複雑さで結果を変える
        name_score = len(query) * hash(query) % 100

        if api_name == "Google":
            return {"results": int(10 ** (3 + name_score / 20))}
        elif api_name == "Brave":
            return {"results": int(10 ** (2 + name_score / 30))}
        elif api_name == "YouTube":
            return {"views": int(10 ** (3 + name_score / 15))}
        elif api_name == "Twitter":
            return {"mentions": int(10 ** (2 + name_score / 25))}
        elif api_name == "News":
            return {"articles": int(10 ** (1 + name_score / 40))}
        else:
            return {}

    def _calculate_tiered_score(self, api_results: Dict, tier: EvaluationTier) -> float:
        """階層別スコア計算"""
        score = 0.0
        weights = self._get_tier_weights(tier)

        # Google結果
        if "Google" in api_results:
            google_score = self._normalize_google(api_results["Google"].get("results", 0))
            score += google_score * weights.get("Google", 0)

        # Brave結果
        if "Brave" in api_results:
            brave_score = self._normalize_brave(api_results["Brave"].get("results", 0))
            score += brave_score * weights.get("Brave", 0)

        # YouTube結果
        if "YouTube" in api_results:
            youtube_score = self._normalize_youtube(api_results["YouTube"].get("views", 0))
            score += youtube_score * weights.get("YouTube", 0)

        # Twitter結果
        if "Twitter" in api_results:
            twitter_score = self._normalize_twitter(api_results["Twitter"].get("mentions", 0))
            score += twitter_score * weights.get("Twitter", 0)

        # News結果
        if "News" in api_results:
            news_score = self._normalize_news(api_results["News"].get("articles", 0))
            score += news_score * weights.get("News", 0)

        return min(score, 10.0)

    def _get_tier_weights(self, tier: EvaluationTier) -> Dict[str, float]:
        """階層別重み付け"""
        if tier == EvaluationTier.TIER1_QUICK:
            return {
                "Google": 0.6,
                "Brave": 0.4
            }
        elif tier == EvaluationTier.TIER2_STANDARD:
            return {
                "Google": 0.4,
                "Brave": 0.3,
                "YouTube": 0.3
            }
        else:  # TIER3_DETAILED
            return {
                "Google": 0.3,
                "Brave": 0.2,
                "YouTube": 0.25,
                "Twitter": 0.15,
                "News": 0.1
            }

    def _normalize_google(self, count: int) -> float:
        """Google結果の正規化（0-10スケール）"""
        if count >= 100000000:  # 1億以上
            return 10.0
        elif count >= 10000000:  # 1000万以上
            return 8.0
        elif count >= 1000000:  # 100万以上
            return 6.0
        elif count >= 100000:  # 10万以上
            return 4.0
        elif count >= 10000:  # 1万以上
            return 2.0
        else:
            return count / 10000 * 2

    def _normalize_brave(self, count: int) -> float:
        """Brave結果の正規化"""
        if count >= 10000:
            return 10.0
        elif count >= 5000:
            return 8.0
        elif count >= 1000:
            return 6.0
        elif count >= 500:
            return 4.0
        else:
            return count / 500 * 4

    def _normalize_youtube(self, views: int) -> float:
        """YouTube視聴回数の正規化"""
        if views >= 100000000:  # 1億以上
            return 10.0
        elif views >= 10000000:  # 1000万以上
            return 8.0
        elif views >= 1000000:  # 100万以上
            return 6.0
        elif views >= 100000:  # 10万以上
            return 4.0
        else:
            return views / 100000 * 4

    def _normalize_twitter(self, mentions: int) -> float:
        """Twitter言及数の正規化"""
        if mentions >= 100000:
            return 10.0
        elif mentions >= 10000:
            return 7.0
        elif mentions >= 1000:
            return 5.0
        elif mentions >= 100:
            return 3.0
        else:
            return mentions / 100 * 3

    def _normalize_news(self, articles: int) -> float:
        """ニュース記事数の正規化"""
        if articles >= 1000:
            return 10.0
        elif articles >= 100:
            return 7.0
        elif articles >= 10:
            return 4.0
        else:
            return articles / 10 * 4

    def _calculate_confidence(self, api_results: Dict, tier: EvaluationTier) -> float:
        """信頼度計算"""
        base_confidence = self.tier_configs[tier].quality_score

        # 成功したAPI数による調整
        success_rate = len(api_results) / len(self.tier_configs[tier].apis)

        # データの一貫性チェック
        consistency_bonus = 0.0
        if len(api_results) >= 2:
            scores = []
            if "Google" in api_results:
                scores.append(self._normalize_google(api_results["Google"].get("results", 0)))
            if "Brave" in api_results:
                scores.append(self._normalize_brave(api_results["Brave"].get("results", 0)))

            if scores:
                # スコアの標準偏差が小さいほど一貫性が高い
                std_dev = np.std(scores) if len(scores) > 1 else 0
                consistency_bonus = max(0, 0.1 - std_dev / 10)

        return min(base_confidence * success_rate + consistency_bonus, 1.0)

    def estimate_total_time(self, df: pd.DataFrame, tier_distribution: Optional[Dict] = None) -> Dict:
        """処理時間推定"""
        if tier_distribution is None:
            # デフォルト分布
            tier_distribution = {
                EvaluationTier.TIER1_QUICK: 0.6,
                EvaluationTier.TIER2_STANDARD: 0.3,
                EvaluationTier.TIER3_DETAILED: 0.1
            }

        total_records = len(df)
        time_estimate = 0

        details = {}
        for tier, ratio in tier_distribution.items():
            count = int(total_records * ratio)
            time = count * self.tier_configs[tier].time_estimate
            time_estimate += time
            details[tier.value] = {
                'count': count,
                'time_seconds': time,
                'time_hours': time / 3600
            }

        return {
            'total_seconds': time_estimate,
            'total_hours': time_estimate / 3600,
            'total_days': time_estimate / 86400,
            'details': details
        }


async def demo_tiered_evaluation():
    """デモ実行"""
    # テストデータ
    test_data = pd.DataFrame([
        {"person_id": "P001", "person_name": "HIKAKIN", "person_name_ja": "ヒカキン",
         "category": "YouTuber", "wikipedia_url": "https://..."},
        {"person_id": "P002", "person_name": "Unknown", "person_name_ja": "不明な人",
         "category": None},
        {"person_id": "P003", "person_name": "Aragaki Yui", "person_name_ja": "新垣結衣",
         "category": "俳優", "birth_year": 1988},
    ])

    evaluator = TieredEvaluator()

    print("🎯 階層的評価システム デモ")
    print("=" * 60)

    results = []
    for idx, row in test_data.iterrows():
        # 階層決定
        tier = evaluator.determine_tier(row)
        print(f"\n評価対象: {row['person_name_ja']}")
        print(f"  カテゴリ: {row.get('category', 'なし')}")
        print(f"  選択階層: {tier.value}")

        # 評価実行
        result = await evaluator.evaluate_with_tier(row, tier)
        results.append(result)

        print(f"  最終スコア: {result.final_score:.2f}")
        print(f"  信頼度: {result.confidence:.2%}")
        print(f"  処理時間: {result.processing_time:.2f}秒")

    # 時間推定
    print("\n📊 4,702件の処理時間推定:")
    time_estimate = evaluator.estimate_total_time(
        pd.DataFrame([{} for _ in range(4702)])
    )

    print(f"  合計時間: {time_estimate['total_hours']:.1f}時間 ({time_estimate['total_days']:.1f}日)")
    for tier_name, details in time_estimate['details'].items():
        print(f"  {tier_name}: {details['count']}件 → {details['time_hours']:.1f}時間")

    return results


if __name__ == "__main__":
    asyncio.run(demo_tiered_evaluation())
