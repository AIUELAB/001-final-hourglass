#!/usr/bin/env python3
"""
エピソード改善提案エンジン

機能:
1. 評価結果から改善ポイントを自動抽出
2. 高スコアエピソードをベンチマークとして提示
3. 具体的な改善例を生成
4. 優先順位付けされた改善計画を提案
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import time

from advanced_llm_evaluator import AdvancedLLMEvaluator, AdvancedEvaluationResult


@dataclass
class BenchmarkExample:
    """ベンチマーク例"""
    person_name: str
    age: int
    score: int
    strong_points: List[str]
    episode_excerpt: str


@dataclass
class DetailedImprovement:
    """詳細な改善提案"""
    priority: int  # 1-3（優先度）
    category: str
    current_score: int
    target_score: int
    impact: str  # "高", "中", "低"
    difficulty: str  # "易", "中", "難"

    # 改善内容
    problem: str
    solution: str
    before_example: str
    after_example: str

    # ベンチマーク
    benchmark: Optional[BenchmarkExample]


@dataclass
class ImprovementPlan:
    """改善計画"""
    episode_id: str
    person_name: str
    age: int
    current_score: int
    target_score: int

    improvements: List[DetailedImprovement]

    estimated_time: str  # "30分", "1時間" など
    estimated_difficulty: str  # "易", "中", "難"
    expected_score_gain: int


class EpisodeImprovementEngine:
    """エピソード改善提案エンジン"""

    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Args:
            provider: LLMプロバイダー
            model: モデル名
        """
        self.provider = provider
        self.model = model

        # ベンチマークエピソード（高スコア例）
        self.benchmarks = self._load_benchmarks()

    def _load_benchmarks(self) -> Dict[str, BenchmarkExample]:
        """高スコアエピソードをベンチマークとして読み込み"""
        return {
            "匿名アーティスト成功": BenchmarkExample(
                person_name="Ado",
                age=21,
                score=37,
                strong_points=["匿名での紅白出場", "Billboard1位", "前例のない挑戦"],
                episode_excerpt="「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。"
            ),
            "文学賞受賞": BenchmarkExample(
                person_name="又吉直樹",
                age=35,
                score=34,
                strong_points=["芥川賞受賞", "238万部", "お笑い芸人からの転身"],
                episode_excerpt="お笑い芸人として活動しながら『火花』で芥川賞を受賞。純文学としては異例の238万部を売り上げ、お笑い芸人と作家の二刀流という新しい可能性を切り開いた。"
            ),
            "スポーツ記録": BenchmarkExample(
                person_name="室伏広治",
                age=38,
                score=31,
                strong_points=["金メダル", "アジア人初", "84m86cmの記録"],
                episode_excerpt="アテネ五輪で金メダルを獲得し、ハンマー投げでアジア人初の五輪王者となった。84m86cmの日本記録を樹立し、世界陸上でも金メダルを獲得。"
            )
        }

    def generate_improvement_plan(
        self,
        evaluation_result: AdvancedEvaluationResult,
        episode_id: str = "Unknown"
    ) -> ImprovementPlan:
        """
        評価結果から改善計画を生成

        Args:
            evaluation_result: 高度な評価結果
            episode_id: エピソードID

        Returns:
            ImprovementPlan: 改善計画
        """
        current_score = evaluation_result.total_score
        target_score = max(60, current_score + 15)  # 最低60点、または現在+15点

        # Phase別スコアから改善ポイントを抽出
        improvements = self._analyze_weak_points(evaluation_result)

        # 優先順位付け
        improvements = self._prioritize_improvements(improvements)

        # 見積もり
        estimated_time = self._estimate_time(improvements)
        estimated_difficulty = self._estimate_difficulty(improvements)
        expected_gain = sum(imp.target_score - imp.current_score for imp in improvements[:3])

        return ImprovementPlan(
            episode_id=episode_id,
            person_name=evaluation_result.person_name,
            age=evaluation_result.age,
            current_score=current_score,
            target_score=target_score,
            improvements=improvements,
            estimated_time=estimated_time,
            estimated_difficulty=estimated_difficulty,
            expected_score_gain=expected_gain
        )

    def _analyze_weak_points(
        self,
        result: AdvancedEvaluationResult
    ) -> List[DetailedImprovement]:
        """弱点を分析して改善提案を生成"""
        improvements = []
        priority = 1

        # Phase 1: 構造分析
        if result.phase1_structure.actual_score < result.phase1_structure.max_score * 0.8:
            for key, score in result.phase1_structure.breakdown.items():
                if key == "文章構造" and score < 6:
                    improvements.append(self._create_structure_improvement(
                        result.episode_text, priority
                    ))
                    priority += 1
                elif key == "年齢時点明確性" and score < 6:
                    improvements.append(self._create_age_clarity_improvement(
                        result.episode_text, result.age, priority
                    ))
                    priority += 1
                elif key == "検証可能性" and score < 5:
                    improvements.append(self._create_verifiability_improvement(
                        result.episode_text, priority
                    ))
                    priority += 1

        # Phase 2: インパクト分析
        if result.phase2_impact.actual_score < result.phase2_impact.max_score * 0.8:
            for key, score in result.phase2_impact.breakdown.items():
                if key == "感情的インパクト" and score < 8:
                    improvements.append(self._create_emotional_improvement(
                        result.episode_text, priority
                    ))
                    priority += 1
                elif key == "社会的インパクト" and score < 8:
                    improvements.append(self._create_social_improvement(
                        result.episode_text, priority
                    ))
                    priority += 1

        # Phase 3: ストーリーテリング
        if result.phase3_storytelling.actual_score < result.phase3_storytelling.max_score * 0.8:
            for key, score in result.phase3_storytelling.breakdown.items():
                if key == "具体性" and score < 7:
                    improvements.append(self._create_specificity_improvement(
                        result.episode_text, priority
                    ))
                    priority += 1

        # Phase 4: 独自性
        if result.phase4_uniqueness.actual_score < result.phase4_uniqueness.max_score * 0.8:
            for key, score in result.phase4_uniqueness.breakdown.items():
                if key == "意外性" and score < 8:
                    improvements.append(self._create_surprise_improvement(
                        result.episode_text, result.person_name, priority
                    ))
                    priority += 1

        return improvements

    def _create_emotional_improvement(self, episode_text: str, priority: int) -> DetailedImprovement:
        """感情的インパクト改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="感情的インパクト",
            current_score=6,
            target_score=9,
            impact="高",
            difficulty="中",
            problem="感情的な葛藤や決断の瞬間が不明確",
            solution="具体的な葛藤、不安、決断の瞬間を追加",
            before_example="新垣結衣は上京してポッキーCMに出演した。",
            after_example="新垣結衣は「本当にこの子で大丈夫？」という制作側の不安の中、笑顔とダンスで日本中を魅了した。",
            benchmark=self.benchmarks.get("匿名アーティスト成功")
        )

    def _create_specificity_improvement(self, episode_text: str, priority: int) -> DetailedImprovement:
        """具体性改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="具体性・数値データ",
            current_score=5,
            target_score=8,
            impact="高",
            difficulty="易",
            problem="具体的な数値やデータが不足",
            solution="売上高、視聴率、受賞回数、記録などの具体的数値を追加",
            before_example="映画が大ヒットした。",
            after_example="映画『恋空』で興行収入39億円を記録した。",
            benchmark=self.benchmarks.get("文学賞受賞")
        )

    def _create_surprise_improvement(self, episode_text: str, person_name: str, priority: int) -> DetailedImprovement:
        """意外性改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="意外性・新規性",
            current_score=6,
            target_score=9,
            impact="高",
            difficulty="中",
            problem="前例のない挑戦や常識を覆す要素が弱い",
            solution="「史上初」「日本人初」「XX歳最年少」などの要素を追加",
            before_example="新しい試みに挑戦した。",
            after_example="匿名アーティストという新しい成功モデルを確立した。",
            benchmark=self.benchmarks.get("匿名アーティスト成功")
        )

    def _create_structure_improvement(self, episode_text: str, priority: int) -> DetailedImprovement:
        """構造改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="文章構造",
            current_score=4,
            target_score=7,
            impact="中",
            difficulty="易",
            problem="起承転結が不明確、または文章が途中で終わる",
            solution="起（背景）→ 承（挑戦）→ 転（決断/困難）→ 結（成果）の流れを完結させる",
            before_example="活動を始めた。成功した。",
            after_example="無名の新人として活動を始めた。多くの困難の中、決断を下し、最終的に大きな成功を収めた。",
            benchmark=None
        )

    def _create_age_clarity_improvement(self, episode_text: str, age: int, priority: int) -> DetailedImprovement:
        """年齢明確性改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="年齢時点の明確性",
            current_score=5,
            target_score=7,
            impact="中",
            difficulty="易",
            problem="「XX歳のとき」の記述が70%未満",
            solution="エピソードの70%以上を年齢時点の出来事で記述する",
            before_example=f"{age}歳で決断した。その後、大きな成功を収めた。",
            after_example=f"あなたと同じ{age}歳のとき、重要な決断を下した。この{age}歳での挑戦が、その後の成功の基礎となった。",
            benchmark=None
        )

    def _create_verifiability_improvement(self, episode_text: str, priority: int) -> DetailedImprovement:
        """検証可能性改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="事実の検証可能性",
            current_score=4,
            target_score=6,
            impact="中",
            difficulty="中",
            problem="年代、具体的な名称、数値データが不足",
            solution="Wikipedia等で検証可能な具体的事実を追加",
            before_example="有名なCMに出演した。",
            after_example="江崎グリコのポッキーCM「ポッキーダンス」に出演した。",
            benchmark=None
        )

    def _create_social_improvement(self, episode_text: str, priority: int) -> DetailedImprovement:
        """社会的インパクト改善を生成"""
        return DetailedImprovement(
            priority=priority,
            category="社会的インパクト",
            current_score=6,
            target_score=9,
            impact="高",
            difficulty="中",
            problem="社会や業界への影響が不明確",
            solution="業界への影響、社会的変化、後続への影響を追加",
            before_example="新しい分野を開拓した。",
            after_example="匿名アーティストという新しい成功モデルを確立し、音楽業界の新しい潮流を作った。",
            benchmark=self.benchmarks.get("匿名アーティスト成功")
        )

    def _prioritize_improvements(self, improvements: List[DetailedImprovement]) -> List[DetailedImprovement]:
        """改善提案を優先順位付け"""
        # スコアリング: impact × difficulty の逆数
        impact_score = {"高": 3, "中": 2, "低": 1}
        difficulty_score = {"易": 3, "中": 2, "難": 1}

        for imp in improvements:
            score = impact_score[imp.impact] * difficulty_score[imp.difficulty]
            imp.priority = score

        # 優先順位でソート（降順）
        return sorted(improvements, key=lambda x: x.priority, reverse=True)

    def _estimate_time(self, improvements: List[DetailedImprovement]) -> str:
        """改善所要時間を見積もり"""
        total_minutes = len(improvements) * 15  # 1改善あたり15分
        if total_minutes < 30:
            return "30分"
        elif total_minutes < 60:
            return "1時間"
        else:
            return f"{total_minutes // 60}時間"

    def _estimate_difficulty(self, improvements: List[DetailedImprovement]) -> str:
        """改善難易度を見積もり"""
        difficulties = [imp.difficulty for imp in improvements]
        if "難" in difficulties:
            return "難"
        elif "中" in difficulties:
            return "中"
        else:
            return "易"

    def get_improvement_report(self, plan: ImprovementPlan) -> str:
        """改善計画レポートを生成"""
        report = f"""
{'='*80}
エピソード改善計画
{'='*80}

【対象エピソード】
エピソードID: {plan.episode_id}
人物: {plan.person_name}（{plan.age}歳）
現在のスコア: {plan.current_score}/100点
目標スコア: {plan.target_score}/100点（+{plan.target_score - plan.current_score}点）

【見積もり】
所要時間: {plan.estimated_time}
難易度: {plan.estimated_difficulty}
期待スコア上昇: +{plan.expected_score_gain}点

{'='*80}
【改善提案】（優先度順）
{'='*80}
"""

        for i, imp in enumerate(plan.improvements[:5], 1):  # 上位5件
            report += f"""
{i}. {imp.category}（優先度: {imp.priority}）
   現在: {imp.current_score}点 → 目標: {imp.target_score}点（+{imp.target_score - imp.current_score}点）
   インパクト: {imp.impact} / 難易度: {imp.difficulty}

   【問題点】
   {imp.problem}

   【解決策】
   {imp.solution}

   【改善例】
   ❌ Before: {imp.before_example}
   ✅ After: {imp.after_example}
"""

            if imp.benchmark:
                report += f"""
   【ベンチマーク】
   {imp.benchmark.person_name}（{imp.benchmark.age}歳）- {imp.benchmark.score}点
   強み: {', '.join(imp.benchmark.strong_points)}
   例: {imp.benchmark.episode_excerpt}
"""

        return report

    def export_to_json(self, plan: ImprovementPlan, filepath: str):
        """改善計画をJSONファイルにエクスポート"""
        data = {
            "episode_id": plan.episode_id,
            "person_name": plan.person_name,
            "age": plan.age,
            "current_score": plan.current_score,
            "target_score": plan.target_score,
            "improvements": [
                {
                    "priority": imp.priority,
                    "category": imp.category,
                    "current_score": imp.current_score,
                    "target_score": imp.target_score,
                    "impact": imp.impact,
                    "difficulty": imp.difficulty,
                    "problem": imp.problem,
                    "solution": imp.solution,
                    "before_example": imp.before_example,
                    "after_example": imp.after_example,
                    "benchmark": asdict(imp.benchmark) if imp.benchmark else None
                }
                for imp in plan.improvements
            ],
            "estimated_time": plan.estimated_time,
            "estimated_difficulty": plan.estimated_difficulty,
            "expected_score_gain": plan.expected_score_gain
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def test_improvement_engine():
    """改善提案エンジンのテスト"""

    # まず評価を実施
    print("ステップ1: エピソード評価中...")
    print("="*80)

    evaluator = AdvancedLLMEvaluator(provider="openai")

    aragaki_episode = """あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、芸能界でのブレイクを果たした。沖縄から上京してわずか3年、無名の新人モデルだった彼女は「本当にこの子で大丈夫？」という制作側の不安の中、笑顔とダンスで日本中を魅了した。CM放送後、ネット上で「ガッキー」の愛称が広まり、検索数が急上昇。この年7回のCM出演契約が決定し、翌年には映画『恋空』で興行収入39億円を記録する大女優への階段を駆け上がった。"""

    result = evaluator.evaluate(aragaki_episode, "新垣結衣", 18)
    print(f"評価完了: {result.total_score}/100点（グレード: {result.grade}）\n")

    # 改善計画を生成
    print("ステップ2: 改善計画生成中...")
    print("="*80)

    engine = EpisodeImprovementEngine(provider="openai")
    plan = engine.generate_improvement_plan(result, episode_id="EP052")

    # レポート表示
    print(engine.get_improvement_report(plan))

    # JSON出力
    engine.export_to_json(plan, "test_aragaki_improvement_plan.json")
    print(f"\n✅ 改善計画をtest_aragaki_improvement_plan.jsonに保存しました")


if __name__ == '__main__':
    test_improvement_engine()
