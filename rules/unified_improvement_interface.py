#!/usr/bin/env python3
"""
RULE_183: 統合改善インターフェース

RULE_180（パターンベース）とRULE_182（LLMベース）を統合し、
最適な改善方法を自動選択するハイブリッドシステム。
"""

import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import time

from rules.rule_180_automatic_improvement_engine import improve_episode_automatically
from rules.rule_182_llm_improvement_engine import improve_episode_with_llm
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated

logger = logging.getLogger(__name__)


@dataclass
class ImprovementStrategy:
    """改善戦略の定義"""
    name: str
    score_threshold: Optional[Tuple[float, float]]  # (min, max)
    use_llm: bool
    use_pattern: bool
    description: str


# 事前定義された戦略
STRATEGIES = {
    "none": ImprovementStrategy(
        name="none",
        score_threshold=(70.0, 100.0),
        use_llm=False,
        use_pattern=False,
        description="スコア70点以上 - 改善不要"
    ),
    "pattern_only": ImprovementStrategy(
        name="pattern_only",
        score_threshold=(60.0, 70.0),
        use_llm=False,
        use_pattern=True,
        description="スコア60-70点 - パターンベース改善のみ"
    ),
    "llm_primary": ImprovementStrategy(
        name="llm_primary",
        score_threshold=(0.0, 60.0),
        use_llm=True,
        use_pattern=False,  # フォールバックは内部で処理
        description="スコア60点未満 - LLM優先（フォールバック付き）"
    ),
    "hybrid": ImprovementStrategy(
        name="hybrid",
        score_threshold=None,
        use_llm=True,
        use_pattern=True,
        description="両方実行して良い方を選択"
    )
}


class CostManager:
    """LLM使用コスト管理"""

    def __init__(self, daily_limit_usd: float = 5.0):
        self.daily_limit = daily_limit_usd
        self.daily_usage = 0.0
        self.usage_history = []

    def can_use_llm(self, estimated_cost: float = 0.02) -> bool:
        """LLM使用可能かチェック"""
        return (self.daily_usage + estimated_cost) <= self.daily_limit

    def record_usage(self, cost: float, episode_id: str = ""):
        """使用記録"""
        self.daily_usage += cost
        self.usage_history.append({
            "episode_id": episode_id,
            "cost": cost,
            "timestamp": time.time()
        })

    def get_remaining_budget(self) -> float:
        """残予算取得"""
        return max(0, self.daily_limit - self.daily_usage)

    def reset_daily(self):
        """日次リセット"""
        self.daily_usage = 0.0
        self.usage_history = []


class UnifiedImprovementInterface:
    """統合改善インターフェース"""

    def __init__(self, cost_manager: Optional[CostManager] = None):
        self.cost_manager = cost_manager or CostManager()
        self.stats = {
            "total_improvements": 0,
            "rule180_count": 0,
            "rule182_count": 0,
            "hybrid_count": 0,
            "skipped_count": 0,
            "fallback_count": 0
        }

    def select_strategy(
        self,
        evaluation_result,
        strategy_mode: str = "auto"
    ) -> ImprovementStrategy:
        """
        改善戦略を選択

        Args:
            evaluation_result: RULE_179評価結果
            strategy_mode: "auto", "force_pattern", "force_llm", "hybrid"

        Returns:
            選択された戦略
        """
        if strategy_mode == "force_pattern":
            return STRATEGIES["pattern_only"]
        elif strategy_mode == "force_llm":
            return STRATEGIES["llm_primary"]
        elif strategy_mode == "hybrid":
            return STRATEGIES["hybrid"]

        # Auto戦略: passedフラグとスコアベース選択
        score = evaluation_result.total_score
        passed = evaluation_result.passed

        # まず合格フラグをチェック
        if passed and score >= 70.0:
            return STRATEGIES["none"]  # 改善不要（合格済み）

        # 不合格の場合はスコアで判断
        if score >= 60.0:
            return STRATEGIES["pattern_only"]  # パターンベースで十分
        else:
            # 低スコア: LLM使用（コスト制限チェック）
            if self.cost_manager.can_use_llm():
                return STRATEGIES["llm_primary"]
            else:
                logger.warning("⚠️ コスト上限到達 - RULE_180にフォールバック")
                return STRATEGIES["pattern_only"]

    def improve_episode_unified(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        database_age: int,
        person_context: Dict[str, Any],
        strategy_mode: str = "auto",
        llm_provider: str = "openai"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        統合改善API

        Args:
            episode_id: エピソードID
            person_name: 人物名
            episode_text: 元のエピソードテキスト
            database_age: データベース年齢
            person_context: 人物コンテキスト（birth_year, category等）
            strategy_mode: "auto", "force_pattern", "force_llm", "hybrid"
            llm_provider: "openai", "anthropic", "mock"

        Returns:
            (改善後テキスト, 改善サマリー)
        """
        logger.info(f"🔧 統合改善開始: {episode_id}")

        # 1. 評価
        evaluation_result = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=episode_text,
            database_age=database_age,
            birth_year=person_context.get("birth_year")
        )

        original_score = evaluation_result.total_score
        logger.info(f"   元のスコア: {original_score:.1f}点")

        # 2. 戦略選択
        strategy = self.select_strategy(evaluation_result, strategy_mode)
        logger.info(f"   選択戦略: {strategy.name} - {strategy.description}")

        # 3. 改善実行
        if strategy.name == "none":
            # 改善不要
            self.stats["skipped_count"] += 1
            return episode_text, {
                "improved": False,
                "method": "none",
                "reason": "score_already_high",
                "original_score": original_score,
                "final_score": original_score
            }

        elif strategy.name == "pattern_only":
            # RULE_180のみ
            return self._improve_with_pattern(
                episode_text,
                evaluation_result,
                person_context,
                original_score
            )

        elif strategy.name == "llm_primary":
            # RULE_182優先
            return self._improve_with_llm(
                episode_text,
                evaluation_result,
                person_context,
                llm_provider,
                original_score
            )

        elif strategy.name == "hybrid":
            # ハイブリッド
            return self._improve_hybrid(
                episode_id,
                person_name,
                episode_text,
                database_age,
                evaluation_result,
                person_context,
                llm_provider,
                original_score
            )

    def _improve_with_pattern(
        self,
        episode_text: str,
        evaluation_result,
        person_context: Dict[str, Any],
        original_score: float
    ) -> Tuple[str, Dict[str, Any]]:
        """RULE_180による改善"""
        logger.info("   🔧 RULE_180で改善中...")

        improved_text, improvements = improve_episode_automatically(
            episode_text,
            evaluation_result,
            max_iterations=3
        )

        self.stats["rule180_count"] += 1
        self.stats["total_improvements"] += 1

        return improved_text, {
            "improved": True,
            "method": "rule180",
            "improvement_count": len(improvements),
            "original_score": original_score,
            "improvements": [str(imp) for imp in improvements]
        }

    def _improve_with_llm(
        self,
        episode_text: str,
        evaluation_result,
        person_context: Dict[str, Any],
        llm_provider: str,
        original_score: float
    ) -> Tuple[str, Dict[str, Any]]:
        """RULE_182による改善"""
        logger.info(f"   🤖 RULE_182({llm_provider})で改善中...")

        improved_text, summary = improve_episode_with_llm(
            episode_text,
            evaluation_result,
            person_context,
            provider=llm_provider,
            use_fallback=True
        )

        # コスト記録
        if summary.get("method") == "llm":
            self.cost_manager.record_usage(0.02)  # 推定コスト
            self.stats["rule182_count"] += 1
        elif "fallback" in summary.get("method", ""):
            self.stats["fallback_count"] += 1
            self.stats["rule180_count"] += 1

        self.stats["total_improvements"] += 1

        summary["original_score"] = original_score
        return improved_text, summary

    def _improve_hybrid(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        database_age: int,
        evaluation_result,
        person_context: Dict[str, Any],
        llm_provider: str,
        original_score: float
    ) -> Tuple[str, Dict[str, Any]]:
        """ハイブリッド改善（両方試して良い方を選択）"""
        logger.info("   🎯 ハイブリッド改善: 両方実行して比較中...")

        # RULE_180で改善
        text_180, summary_180 = self._improve_with_pattern(
            episode_text, evaluation_result, person_context, original_score
        )

        # 再評価
        eval_180 = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=text_180,
            database_age=database_age,
            birth_year=person_context.get("birth_year")
        )
        score_180 = eval_180.total_score

        # RULE_182で改善
        text_182, summary_182 = self._improve_with_llm(
            episode_text, evaluation_result, person_context, llm_provider, original_score
        )

        # 再評価
        eval_182 = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=text_182,
            database_age=database_age,
            birth_year=person_context.get("birth_year")
        )
        score_182 = eval_182.total_score

        logger.info(f"   RULE_180スコア: {score_180:.1f}点")
        logger.info(f"   RULE_182スコア: {score_182:.1f}点")

        # 高スコアを採用
        if score_182 > score_180:
            logger.info("   ✅ RULE_182（LLM）が優位 - 採用")
            self.stats["hybrid_count"] += 1
            return text_182, {
                **summary_182,
                "method": "hybrid_llm_win",
                "original_score": original_score,
                "rule180_score": score_180,
                "rule182_score": score_182,
                "final_score": score_182
            }
        else:
            logger.info("   ✅ RULE_180（パターン）が優位 - 採用")
            self.stats["hybrid_count"] += 1
            return text_180, {
                **summary_180,
                "method": "hybrid_pattern_win",
                "original_score": original_score,
                "rule180_score": score_180,
                "rule182_score": score_182,
                "final_score": score_180
            }

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            **self.stats,
            "cost_usage": self.cost_manager.daily_usage,
            "cost_limit": self.cost_manager.daily_limit,
            "remaining_budget": self.cost_manager.get_remaining_budget()
        }


# グローバルインスタンス（シングルトン）
_unified_interface = None


def get_unified_interface(reset: bool = False) -> UnifiedImprovementInterface:
    """統合インターフェースのシングルトン取得"""
    global _unified_interface
    if _unified_interface is None or reset:
        _unified_interface = UnifiedImprovementInterface()
    return _unified_interface


# 便利な関数エイリアス
def improve_episode_auto(
    episode_id: str,
    person_name: str,
    episode_text: str,
    database_age: int,
    person_context: Dict[str, Any],
    llm_provider: str = "openai"
) -> Tuple[str, Dict[str, Any]]:
    """
    自動戦略で改善（最も推奨）

    スコアに応じて最適な改善方法を自動選択
    """
    interface = get_unified_interface()
    return interface.improve_episode_unified(
        episode_id, person_name, episode_text, database_age,
        person_context, strategy_mode="auto", llm_provider=llm_provider
    )


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)

    print("🚀 RULE_183: 統合改善インターフェース テスト\n")

    # テストケース
    test_cases = [
        {
            "episode_id": "EP_TEST_HIGH",
            "person_name": "テスト人物A",
            "episode_text": "あなたと同じ30歳のとき、テスト人物Aは2020年にノーベル物理学賞を受賞した。量子コンピューティングの分野で画期的な発見をし、Nature誌に論文が掲載された。",
            "database_age": 30,
            "person_context": {"person_name": "テスト人物A", "birth_year": 1990, "category": "科学者"},
            "expected_strategy": "none"
        },
        {
            "episode_id": "EP_TEST_MID",
            "episode_text": "あなたと同じ25歳のとき、テスト人物Bは優れた成績を収めた。",
            "database_age": 25,
            "person_context": {"person_name": "テスト人物B", "birth_year": 1995, "category": "アスリート"},
            "expected_strategy": "pattern_only or llm_primary"
        },
        {
            "episode_id": "EP_TEST_LOW",
            "episode_text": "あなたと同じ28歳のとき、素晴らしい業績を残した。",
            "database_age": 28,
            "person_context": {"person_name": "テスト人物C", "birth_year": 1992, "category": "不明"},
            "expected_strategy": "llm_primary"
        }
    ]

    interface = get_unified_interface()

    print("=" * 80)
    print("📊 戦略選択テスト")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        print(f"\nテストケース {i}:")
        print(f"  エピソード: {test['episode_text'][:50]}...")
        print(f"  期待戦略: {test['expected_strategy']}")

        # Mockプロバイダーでテスト
        try:
            improved_text, summary = interface.improve_episode_unified(
                test["episode_id"],
                test["person_context"]["person_name"],
                test["episode_text"],
                test["database_age"],
                test["person_context"],
                strategy_mode="auto",
                llm_provider="mock"
            )

            print(f"  実行戦略: {summary.get('method', 'unknown')}")
            print(f"  改善: {'✅' if summary.get('improved') else '❌'}")

        except Exception as e:
            print(f"  ❌ エラー: {e}")

    print("\n" + "=" * 80)
    print("📈 統計情報")
    print("=" * 80)

    stats = interface.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ テスト完了")
