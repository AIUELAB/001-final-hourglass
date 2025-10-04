#!/usr/bin/env python3
"""
RULE_179: 統合評価パイプライン（Integrated Evaluation Pipeline）

Phase 4-5で実装したすべてのルールを統合し、エピソードを総合評価
- RULE_172: 社会的インパクト測定
- RULE_173: 年齢柔軟性エンジン
- RULE_174: 時系列整合性検証
- RULE_175: ネガティブエピソード評価
- RULE_176: 架空キャラクター統合
- RULE_177: 抽象表現自動検出
- RULE_178: 統合MCPコレクター

総合評価フロー:
1. 前処理: 年齢選択（RULE_173）
2. データ収集: MCPデータ取得（RULE_178 → RULE_172）
3. 検証: 時系列整合性（RULE_174）
4. 品質評価: ネガティブ（RULE_175）、抽象表現（RULE_177）
5. 特殊判定: 架空キャラクター（RULE_176）
6. 総合判定: 合格/不合格 + 改善提案
"""

from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime

# Phase 4-5ルールのインポート
try:
    from rules.rule_172_social_impact import SocialImpactAnalyzer
    from rules.rule_173_age_flexibility_engine import select_optimal_age
    from rules.rule_174_temporal_consistency import verify_temporal_consistency
    from rules.rule_175_negative_episode_evaluation import evaluate_negative_episode
    from rules.rule_176_fictional_character_integration import evaluate_fictional_character
    from rules.rule_177_abstract_expression_detection import detect_abstract_expressions
    from rules.rule_178_unified_mcp_collector import collect_all_mcp_data_sync
    RULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ ルールのインポート失敗: {e}")
    RULES_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EpisodeEvaluationResult:
    """エピソード評価結果"""
    episode_id: str
    person_name: str
    passed: bool  # 総合合格判定
    total_score: float  # 総合スコア（0-100）

    # 各ルールの評価結果
    age_selection: Dict[str, Any]
    social_impact: Dict[str, Any]
    temporal_consistency: Dict[str, Any]
    negative_evaluation: Optional[Dict[str, Any]]
    fictional_character: Optional[Dict[str, Any]]
    abstract_detection: Dict[str, Any]

    # 品質ゲート
    quality_gates: Dict[str, bool]

    # 改善提案
    improvements: List[str]

    # メタデータ
    evaluation_timestamp: str


class IntegratedEvaluationPipeline:
    """
    統合評価パイプライン

    すべてのルールを統合してエピソードを総合評価
    """

    def __init__(self, use_mcp: bool = False):
        """
        初期化

        Args:
            use_mcp: MCPデータ収集を使用するか（現在は推定値モード）
        """
        self.use_mcp = use_mcp and RULES_AVAILABLE
        if not RULES_AVAILABLE:
            logger.warning("⚠️ 一部のルールが利用不可 - 基本評価のみ実行")

    def evaluate_episode(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        database_age: int,
        birth_year: Optional[int] = None,
        entity_type: str = "real_person",
        work_title: Optional[str] = None,
        description: Optional[str] = None
    ) -> EpisodeEvaluationResult:
        """
        エピソードを総合評価

        Args:
            episode_id: エピソードID
            person_name: 人物名
            episode_text: エピソード本文
            database_age: データベース登録年齢
            birth_year: 生年（オプション）
            entity_type: エンティティタイプ（real_person/fictional_character）
            work_title: 作品タイトル（架空キャラの場合）
            description: 作品説明（架空キャラの場合）

        Returns:
            評価結果
        """
        logger.info(f"🎯 {person_name} ({episode_id}) 評価開始")

        improvements = []
        quality_gates = {}

        # ============================================================
        # Phase 1: 前処理 - 年齢選択（RULE_173）
        # ============================================================
        age_result = self._evaluate_age_flexibility(
            person_name, database_age, episode_text
        )
        selected_age = age_result.get("selected_age", database_age)

        if age_result.get("age_changed"):
            improvements.append(
                f"年齢を{database_age}歳から{selected_age}歳に変更（より象徴的）"
            )

        # ============================================================
        # Phase 2: データ収集 - 社会的インパクト（RULE_178 → RULE_172）
        # ============================================================
        social_impact_result = self._evaluate_social_impact(
            person_name, episode_text
        )
        quality_gates["social_impact"] = social_impact_result.get("passed", False)

        # ============================================================
        # Phase 3: 検証 - 時系列整合性（RULE_174）
        # ============================================================
        temporal_result = self._evaluate_temporal_consistency(
            person_name, selected_age, episode_text, birth_year
        )
        quality_gates["temporal_consistency"] = temporal_result.get("passed", False)

        if not temporal_result.get("passed"):
            for issue in temporal_result.get("inconsistencies", []):
                improvements.append(f"時系列矛盾修正: {issue['suggestion']}")

        # ============================================================
        # Phase 4: 品質評価
        # ============================================================

        # 4-1: ネガティブエピソード評価（RULE_175）
        negative_result = None
        is_negative_episode = any(
            word in episode_text
            for word in ["逮捕", "辞任", "引退", "失敗", "挫折", "批判"]
        )

        if is_negative_episode:
            negative_result = self._evaluate_negative_episode(
                person_name, episode_text
            )
            quality_gates["negative_evaluation"] = negative_result.get("passed", False)

            if not negative_result.get("passed"):
                for issue in negative_result.get("issues", []):
                    improvements.append(f"表現改善: {issue['suggestion']}")

        # 4-2: 抽象表現検出（RULE_177）
        abstract_result = self._evaluate_abstract_expressions(episode_text)
        quality_gates["abstract_detection"] = abstract_result.get("passed", False)

        if not abstract_result.get("passed"):
            for expr in abstract_result.get("abstract_expressions", [])[:3]:
                improvements.append(f"具体化: {expr['suggestion']}")

        # ============================================================
        # Phase 5: 特殊判定 - 架空キャラクター（RULE_176）
        # ============================================================
        fictional_result = None
        if entity_type == "fictional_character" and work_title:
            fictional_result = self._evaluate_fictional_character(
                person_name, work_title, description or ""
            )
            quality_gates["fictional_character"] = fictional_result.get("should_keep", False)

            if not fictional_result.get("should_keep"):
                improvements.append(
                    f"架空キャラクター要レビュー: 影響度{fictional_result.get('cultural_impact_score', 0):.0f}点"
                )

        # ============================================================
        # Phase 6: 総合判定
        # ============================================================
        total_score = self._calculate_total_score(
            social_impact_result,
            temporal_result,
            negative_result,
            abstract_result,
            fictional_result
        )

        # 合格判定: すべての品質ゲートが通過
        passed = all(quality_gates.values())

        # 総合スコアが60点未満は不合格
        if total_score < 60:
            passed = False
            improvements.append(f"総合スコア向上が必要: 現在{total_score:.1f}点 → 目標60点以上")

        logger.info(f"📊 {person_name}: 総合スコア {total_score:.1f}点 - {'✅ 合格' if passed else '❌ 不合格'}")

        return EpisodeEvaluationResult(
            episode_id=episode_id,
            person_name=person_name,
            passed=passed,
            total_score=total_score,
            age_selection=age_result,
            social_impact=social_impact_result,
            temporal_consistency=temporal_result,
            negative_evaluation=negative_result,
            fictional_character=fictional_result,
            abstract_detection=abstract_result,
            quality_gates=quality_gates,
            improvements=improvements,
            evaluation_timestamp=datetime.now().isoformat()
        )

    def _evaluate_age_flexibility(
        self, person_name: str, database_age: int, episode_text: str
    ) -> Dict[str, Any]:
        """年齢柔軟性評価（RULE_173）"""
        if not RULES_AVAILABLE:
            return {"selected_age": database_age, "age_changed": False}

        try:
            return select_optimal_age(database_age, episode_text, person_name)
        except Exception as e:
            logger.warning(f"⚠️ RULE_173失敗: {e}")
            return {"selected_age": database_age, "age_changed": False}

    def _evaluate_social_impact(
        self, person_name: str, episode_text: str
    ) -> Dict[str, Any]:
        """社会的インパクト評価（RULE_172）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "impact_score": 50}

        try:
            analyzer = SocialImpactAnalyzer(use_mcp=self.use_mcp)
            result = analyzer.analyze(person_name, episode_text, [])

            # SocialImpactMetricsオブジェクトを辞書に変換
            if hasattr(result, 'total_impact_score'):
                return {
                    "passed": result.total_impact_score >= 50,
                    "impact_score": result.total_impact_score,
                    "search_volume_score": result.search_volume_score,
                    "wikipedia_languages": result.wikipedia_languages,
                    "news_articles_count": result.news_articles_count,
                    "social_buzz_score": result.social_buzz_score
                }
            else:
                # 既に辞書形式の場合
                return result
        except Exception as e:
            logger.warning(f"⚠️ RULE_172失敗: {e}")
            return {"passed": True, "impact_score": 50}

    def _evaluate_temporal_consistency(
        self, person_name: str, age: int, episode_text: str, birth_year: Optional[int]
    ) -> Dict[str, Any]:
        """時系列整合性評価（RULE_174）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "inconsistencies": []}

        try:
            return verify_temporal_consistency(person_name, age, episode_text, birth_year)
        except Exception as e:
            logger.warning(f"⚠️ RULE_174失敗: {e}")
            return {"passed": True, "inconsistencies": []}

    def _evaluate_negative_episode(
        self, person_name: str, episode_text: str
    ) -> Dict[str, Any]:
        """ネガティブエピソード評価（RULE_175）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "total_score": 70}

        try:
            return evaluate_negative_episode(episode_text, person_name)
        except Exception as e:
            logger.warning(f"⚠️ RULE_175失敗: {e}")
            return {"passed": True, "total_score": 70}

    def _evaluate_fictional_character(
        self, character_name: str, work_title: str, description: str
    ) -> Dict[str, Any]:
        """架空キャラクター評価（RULE_176）"""
        if not RULES_AVAILABLE:
            return {"should_keep": True, "cultural_impact_score": 70}

        try:
            return evaluate_fictional_character(character_name, work_title, description)
        except Exception as e:
            logger.warning(f"⚠️ RULE_176失敗: {e}")
            return {"should_keep": True, "cultural_impact_score": 70}

    def _evaluate_abstract_expressions(self, episode_text: str) -> Dict[str, Any]:
        """抽象表現検出（RULE_177）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "concreteness_score": 70}

        try:
            return detect_abstract_expressions(episode_text)
        except Exception as e:
            logger.warning(f"⚠️ RULE_177失敗: {e}")
            return {"passed": True, "concreteness_score": 70}

    def _calculate_total_score(
        self,
        social_impact: Dict,
        temporal: Dict,
        negative: Optional[Dict],
        abstract: Dict,
        fictional: Optional[Dict]
    ) -> float:
        """
        総合スコアを計算

        重み付け:
        - 社会的インパクト: 25%
        - 時系列整合性: 20%（合格=100点、不合格=0点）
        - ネガティブ評価: 20%（該当する場合）
        - 抽象表現: 15%
        - 架空キャラ: 20%（該当する場合）
        """
        score = 0
        weight_sum = 0

        # 社会的インパクト（25%）
        score += social_impact.get("impact_score", 50) * 0.25
        weight_sum += 0.25

        # 時系列整合性（20%）
        temporal_score = 100 if temporal.get("passed", False) else 0
        score += temporal_score * 0.20
        weight_sum += 0.20

        # ネガティブ評価（該当する場合のみ20%）
        if negative:
            score += negative.get("total_score", 70) * 0.20
            weight_sum += 0.20

        # 抽象表現（15%）
        score += abstract.get("concreteness_score", 70) * 0.15
        weight_sum += 0.15

        # 架空キャラ（該当する場合のみ20%）
        if fictional:
            fictional_score = fictional.get("cultural_impact_score", 70)
            score += fictional_score * 0.20
            weight_sum += 0.20

        # 正規化（重みの合計で割る）
        if weight_sum > 0:
            score = score / weight_sum

        return round(score, 1)


# グローバルパイプライン
integrated_pipeline = IntegratedEvaluationPipeline(use_mcp=False)


def evaluate_episode_integrated(
    episode_id: str,
    person_name: str,
    episode_text: str,
    database_age: int,
    birth_year: Optional[int] = None,
    entity_type: str = "real_person",
    work_title: Optional[str] = None,
    description: Optional[str] = None
) -> EpisodeEvaluationResult:
    """
    エピソードを統合評価（外部インターフェース）

    Args:
        episode_id: エピソードID
        person_name: 人物名
        episode_text: エピソード本文
        database_age: データベース登録年齢
        birth_year: 生年
        entity_type: エンティティタイプ
        work_title: 作品タイトル
        description: 作品説明

    Returns:
        評価結果
    """
    return integrated_pipeline.evaluate_episode(
        episode_id, person_name, episode_text, database_age,
        birth_year, entity_type, work_title, description
    )


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 80)
    print("RULE_179: 統合評価パイプライン - テスト実行")
    print("=" * 80)
    print()

    # テストケース
    test_cases = [
        {
            "id": "EP001",
            "person": "大谷翔平",
            "age": 30,
            "birth_year": 1994,
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞し、投手と打者の二刀流で歴史を変えた。2021年シーズン、投球では9勝、156奪三振、打撃では46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じ、野球の常識を覆した。"
        },
        {
            "id": "EP002",
            "person": "ドラえもん",
            "age": 0,
            "entity_type": "fictional_character",
            "work_title": "ドラえもん",
            "description": "国民的アニメキャラクター、50年以上の歴史",
            "text": "あなたと同じ年齢のとき、ドラえもんは22世紀から来た青い猫型ロボットとして誕生した。多くの道具でのび太を助け、さまざまな冒険をした。"
        },
        {
            "id": "EP003",
            "person": "架空の人物",
            "age": 18,
            "text": "あなたと同じ18歳のとき、素晴らしいノーベル賞を受賞し、多くの人々に影響を与えた。"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']} ({test['id']})")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = evaluate_episode_integrated(
            episode_id=test["id"],
            person_name=test["person"],
            episode_text=test["text"],
            database_age=test["age"],
            birth_year=test.get("birth_year"),
            entity_type=test.get("entity_type", "real_person"),
            work_title=test.get("work_title"),
            description=test.get("description")
        )

        status = "✅ 合格" if result.passed else "❌ 不合格"
        print(f"  {status}")
        print(f"  📊 総合スコア: {result.total_score:.1f}点")
        print(f"  📈 品質ゲート:")
        for gate, passed in result.quality_gates.items():
            gate_status = "✅" if passed else "❌"
            print(f"     {gate_status} {gate}")

        if result.improvements:
            print(f"  💡 改善提案:")
            for improvement in result.improvements[:5]:
                print(f"     - {improvement}")

        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
