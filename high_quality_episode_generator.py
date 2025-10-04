#!/usr/bin/env python3
"""
超高品質エピソード生成システム

機能:
1. LLM評価4 Phase対応のプロンプト生成
2. 反復改善による自動品質向上
3. ベンチマーク参照による学習型生成
4. 詳細な統計情報とレポート

生成モード:
- prompt_optimized: プロンプト改善のみ（高速）
- iterative: 反復改善（高品質）
- learning: Few-Shot Learning（最高品質）
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import openai
import anthropic

from advanced_llm_evaluator import AdvancedLLMEvaluator, AdvancedEvaluationResult
from episode_improvement_engine import EpisodeImprovementEngine, ImprovementPlan


@dataclass
class GenerationStats:
    """生成統計"""
    total_generated: int = 0
    pass_first_try: int = 0
    pass_after_iteration: int = 0
    failed: int = 0
    total_score: float = 0.0
    total_iterations: int = 0

    @property
    def avg_score(self) -> float:
        return self.total_score / self.total_generated if self.total_generated > 0 else 0.0

    @property
    def avg_iterations(self) -> float:
        return self.total_iterations / self.total_generated if self.total_generated > 0 else 0.0

    @property
    def pass_rate(self) -> float:
        total_pass = self.pass_first_try + self.pass_after_iteration
        return total_pass / self.total_generated if self.total_generated > 0 else 0.0


@dataclass
class GenerationResult:
    """生成結果"""
    episode_id: str
    person_name: str
    age: int
    episode_text: str
    score: int
    grade: str
    iterations: int
    passed: bool
    mode: str
    improvements_applied: List[str]
    cost_estimate: float


class HighQualityEpisodeGenerator:
    """超高品質エピソード生成システム"""

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: str = "iterative",
        max_iterations: int = 3,
        pass_threshold: int = 60
    ):
        """
        Args:
            provider: LLMプロバイダー ("openai" or "anthropic")
            model: モデル名（Noneの場合はデフォルト）
            mode: 生成モード ("prompt_optimized", "iterative", "learning")
            max_iterations: 最大反復回数
            pass_threshold: 合格スコア閾値
        """
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.mode = mode
        self.max_iterations = max_iterations
        self.pass_threshold = pass_threshold

        # コンポーネント初期化
        self.evaluator = AdvancedLLMEvaluator(provider=provider, model=model)
        self.improver = EpisodeImprovementEngine(provider=provider, model=model)

        # 統計情報
        self.stats = GenerationStats()

        # ベンチマークライブラリ
        self.benchmarks = self._load_benchmarks()

        # APIクライアント初期化
        self._init_api_client()

    def _get_default_model(self, provider: str) -> str:
        """デフォルトモデルを取得"""
        if provider == "openai":
            return "gpt-4o-mini"
        elif provider == "anthropic":
            return "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _init_api_client(self):
        """APIクライアント初期化"""
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _load_benchmarks(self) -> Dict[str, Dict]:
        """ベンチマークエピソードを読み込み"""
        return {
            "高スコア_匿名アーティスト": {
                "person_name": "Ado",
                "age": 21,
                "score": 91,
                "strong_points": ["匿名での紅白出場", "Billboard1位", "新しい成功モデル"],
                "episode": "あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。YouTubeでの楽曲は若者を中心に広範な支持を集め、新時代の音楽シーンを象徴する存在となった。"
            },
            "高スコア_芸能ブレイク": {
                "person_name": "新垣結衣",
                "age": 18,
                "score": 85,
                "strong_points": ["無名からブレイク", "ネット現象", "数値的成功"],
                "episode": "あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、芸能界でのブレイクを果たした。沖縄から上京してわずか3年、無名の新人モデルだった彼女は「本当にこの子で大丈夫？」という制作側の不安の中、笑顔とダンスで日本中を魅了した。CM放送後、ネット上で「ガッキー」の愛称が広まり、検索数が急上昇。この年7回のCM出演契約が決定し、翌年には映画『恋空』で興行収入39億円を記録する大女優への階段を駆け上がった。"
            },
            "高スコア_文学賞": {
                "person_name": "又吉直樹",
                "age": 35,
                "score": 85,
                "strong_points": ["異業種からの転身", "記録的売上", "二刀流"],
                "episode": "あなたと同じ35歳のとき、又吉直樹はお笑い芸人として活動しながら『火花』で芥川賞を受賞した。純文学としては異例の238万部を売り上げ、「芸人が芥川賞？」という世間の驚きを結果で覆した。お笑い芸人と作家の二刀流という新しい可能性を切り開き、その後多くの芸人が文筆活動に挑戦する契機となった。"
            }
        }

    def generate(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str] = None,
        episode_id: str = "Unknown"
    ) -> GenerationResult:
        """
        高品質エピソードを生成

        Args:
            person_name: 人物名
            age: 年齢
            wikipedia_data: Wikipedia情報（オプション）
            episode_id: エピソードID

        Returns:
            GenerationResult: 生成結果
        """
        self.stats.total_generated += 1

        if self.mode == "prompt_optimized":
            return self._generate_with_optimized_prompt(
                person_name, age, wikipedia_data, episode_id
            )
        elif self.mode == "iterative":
            return self._generate_with_iteration(
                person_name, age, wikipedia_data, episode_id
            )
        elif self.mode == "learning":
            return self._generate_with_few_shot(
                person_name, age, wikipedia_data, episode_id
            )
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _generate_with_optimized_prompt(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str],
        episode_id: str
    ) -> GenerationResult:
        """プロンプト改善モードで生成"""

        # Phase対応プロンプト作成
        prompt = self._create_phase_aware_prompt(person_name, age, wikipedia_data)

        # エピソード生成
        episode_text = self._call_llm_for_generation(prompt)

        # 評価
        result = self.evaluator.evaluate(episode_text, person_name, age)

        # 統計更新
        self.stats.total_score += result.total_score
        if result.passed:
            self.stats.pass_first_try += 1
        else:
            self.stats.failed += 1

        return GenerationResult(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            episode_text=episode_text,
            score=result.total_score,
            grade=result.grade,
            iterations=1,
            passed=result.passed,
            mode="prompt_optimized",
            improvements_applied=[],
            cost_estimate=self._estimate_cost(1, 0)
        )

    def _generate_with_iteration(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str],
        episode_id: str
    ) -> GenerationResult:
        """反復改善モードで生成"""

        improvements_history = []
        best_episode = None
        best_result = None
        best_score = 0

        for iteration in range(1, self.max_iterations + 1):
            # プロンプト作成（改善提案を組み込み）
            prompt = self._create_phase_aware_prompt(
                person_name, age, wikipedia_data, improvements_history
            )

            # エピソード生成
            episode_text = self._call_llm_for_generation(prompt)

            # 評価
            result = self.evaluator.evaluate(episode_text, person_name, age)

            # ベストスコア更新
            if result.total_score > best_score:
                best_score = result.total_score
                best_episode = episode_text
                best_result = result

            # 合格判定
            if result.total_score >= self.pass_threshold:
                self.stats.total_score += result.total_score
                self.stats.total_iterations += iteration

                if iteration == 1:
                    self.stats.pass_first_try += 1
                else:
                    self.stats.pass_after_iteration += 1

                return GenerationResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=age,
                    episode_text=episode_text,
                    score=result.total_score,
                    grade=result.grade,
                    iterations=iteration,
                    passed=True,
                    mode="iterative",
                    improvements_applied=improvements_history,
                    cost_estimate=self._estimate_cost(iteration, iteration)
                )

            # 改善提案生成
            if iteration < self.max_iterations:
                plan = self.improver.generate_improvement_plan(result, episode_id)
                improvements_history = [
                    {
                        "category": imp.category,
                        "problem": imp.problem,
                        "solution": imp.solution,
                        "example": imp.after_example
                    }
                    for imp in plan.improvements[:3]  # 上位3件
                ]

                # レート制限対策
                time.sleep(1)

        # 最大反復回数に達した場合、ベストエピソードを返す
        self.stats.total_score += best_score
        self.stats.total_iterations += self.max_iterations
        self.stats.failed += 1

        return GenerationResult(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            episode_text=best_episode,
            score=best_score,
            grade=best_result.grade,
            iterations=self.max_iterations,
            passed=False,
            mode="iterative",
            improvements_applied=improvements_history,
            cost_estimate=self._estimate_cost(self.max_iterations, self.max_iterations)
        )

    def _generate_with_few_shot(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str],
        episode_id: str
    ) -> GenerationResult:
        """Few-Shot Learning モードで生成"""

        # 類似ベンチマークを選択
        similar_benchmarks = self._select_similar_benchmarks(person_name, age)

        # Few-Shotプロンプト作成
        prompt = self._create_few_shot_prompt(
            person_name, age, wikipedia_data, similar_benchmarks
        )

        # エピソード生成
        episode_text = self._call_llm_for_generation(prompt)

        # 評価
        result = self.evaluator.evaluate(episode_text, person_name, age)

        # 統計更新
        self.stats.total_score += result.total_score
        self.stats.total_iterations += 1

        if result.passed:
            self.stats.pass_first_try += 1
        else:
            self.stats.failed += 1

        return GenerationResult(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            episode_text=episode_text,
            score=result.total_score,
            grade=result.grade,
            iterations=1,
            passed=result.passed,
            mode="learning",
            improvements_applied=[],
            cost_estimate=self._estimate_cost(1, 0)
        )

    def _create_phase_aware_prompt(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str],
        improvements: Optional[List[Dict]] = None
    ) -> str:
        """Phase対応プロンプトを作成"""

        base_prompt = f"""あなたは{person_name}（{age}歳時点）の人生で最も印象的なエピソードを作成します。

【必須要件】
- 200-250文字
- 「あなたと同じ{age}歳のとき」で開始
- {age}歳時点の出来事が全体の70%以上

【評価基準（合計100点、60点以上で合格）】

Phase 1: 構造（20点）
✓ 起承転結が完結している
✓ {age}歳時点の出来事が明確
✓ Wikipedia等で検証可能な固有名詞（作品名、賞の名前、数値）

Phase 2: インパクト（30点）
✓ 感情的インパクト: 不安、葛藤、決断の瞬間を描写
  例: 「本当にこの子で大丈夫？という制作側の不安の中」
✓ 社会的インパクト: 業界や後続への影響
  例: 「新しい成功モデルを確立した」
✓ 具体的数値: 売上、記録、視聴率、受賞回数

Phase 3: ストーリーテリング（25点）
✓ 逆境からの成長を描く
✓ 「無名から有名へ」「不可能を可能に」の構図
✓ 読者の共感を呼ぶ人間ドラマ

Phase 4: 独自性（25点）
✓ 「史上初」「XX歳最年少」「日本人初」などの要素
✓ 前例のない挑戦
✓ 常識を覆す新規性
"""

        # Wikipedia情報追加
        if wikipedia_data:
            base_prompt += f"\n【参考情報】\n{wikipedia_data}\n"

        # 改善提案追加
        if improvements:
            base_prompt += "\n【前回の改善ポイント】\n"
            for i, imp in enumerate(improvements, 1):
                base_prompt += f"{i}. {imp['category']}: {imp['solution']}\n"
                base_prompt += f"   例: {imp['example']}\n"

        # ベンチマーク例追加
        benchmark = self._get_best_matching_benchmark(person_name)
        if benchmark:
            base_prompt += f"""
【高スコア例（{benchmark['score']}点）】
人物: {benchmark['person_name']}（{benchmark['age']}歳）
強み: {', '.join(benchmark['strong_points'])}

{benchmark['episode']}
"""

        base_prompt += "\n【出力】\n200-250文字の高品質エピソード（「あなたと同じ{age}歳のとき」で開始）\n"

        return base_prompt

    def _create_few_shot_prompt(
        self,
        person_name: str,
        age: int,
        wikipedia_data: Optional[str],
        benchmarks: List[Dict]
    ) -> str:
        """Few-Shot Learningプロンプトを作成"""

        prompt = f"""以下は高品質エピソードの例です（85-91点）。これらの特徴を学習し、{person_name}（{age}歳）の高品質エピソードを作成してください。

"""

        for i, bench in enumerate(benchmarks, 1):
            prompt += f"""【例{i}: {bench['person_name']}（{bench['age']}歳）- {bench['score']}点】
{bench['episode']}

強み: {', '.join(bench['strong_points'])}

"""

        prompt += f"""
上記の例に学び、以下の基準を満たす{person_name}（{age}歳）のエピソードを作成:

1. 感情的インパクト: 葛藤や決断の瞬間
2. 具体的数値: 売上、記録、受賞など
3. 社会的影響: 業界への影響
4. 独自性: 「史上初」「最年少」などの要素
5. ストーリー性: 逆境からの成長

【出力】
200-250文字の高品質エピソード（「あなたと同じ{age}歳のとき」で開始）
"""

        return prompt

    def _call_llm_for_generation(self, prompt: str) -> str:
        """LLMを呼び出してエピソード生成"""

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは高品質なエピソード作成の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.7,
                system="あなたは高品質なエピソード作成の専門家です。",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()

    def _get_best_matching_benchmark(self, person_name: str) -> Optional[Dict]:
        """最適なベンチマークを選択"""
        # 簡易実装: ランダムに1つ選択
        import random
        benchmarks = list(self.benchmarks.values())
        return random.choice(benchmarks) if benchmarks else None

    def _select_similar_benchmarks(self, person_name: str, age: int) -> List[Dict]:
        """類似ベンチマークを選択（Few-Shot用）"""
        # 簡易実装: すべてのベンチマークを返す
        return list(self.benchmarks.values())[:3]

    def _estimate_cost(self, generation_calls: int, evaluation_calls: int) -> float:
        """コストを見積もり"""
        if self.provider == "openai":
            # GPT-4o-mini: 生成$0.002、評価$0.001
            return generation_calls * 0.002 + evaluation_calls * 0.001
        elif self.provider == "anthropic":
            # Claude-3.5-sonnet: 生成$0.030、評価$0.015
            return generation_calls * 0.030 + evaluation_calls * 0.015
        return 0.0

    def print_statistics(self):
        """統計情報を表示"""
        print(f"""
{'='*80}
統計情報
{'='*80}
総生成数: {self.stats.total_generated}件

【成功率】
- 一発成功: {self.stats.pass_first_try}件 ({self.stats.pass_first_try/self.stats.total_generated*100:.1f}%)
- 反復後成功: {self.stats.pass_after_iteration}件 ({self.stats.pass_after_iteration/self.stats.total_generated*100:.1f}%)
- 失敗: {self.stats.failed}件 ({self.stats.failed/self.stats.total_generated*100:.1f}%)
- 合格率: {self.stats.pass_rate*100:.1f}%

【品質】
- 平均スコア: {self.stats.avg_score:.1f}点
- 平均反復回数: {self.stats.avg_iterations:.1f}回

【推定コスト】
- 合計: ${self._estimate_cost(self.stats.total_generated, self.stats.total_iterations):.3f}
""")


def test_high_quality_generator():
    """高品質生成システムのテスト"""

    print("="*80)
    print("超高品質エピソード生成システム - テスト")
    print("="*80)

    # テストケース
    test_cases = [
        ("新垣結衣", 18, "EP052"),
        ("Ado", 21, "EP001"),
        ("川端康成", 27, "EP003")
    ]

    # モード別テスト
    modes = ["prompt_optimized", "iterative"]

    for mode in modes:
        print(f"\n{'='*80}")
        print(f"モード: {mode}")
        print('='*80)

        generator = HighQualityEpisodeGenerator(
            provider="openai",
            mode=mode,
            max_iterations=3,
            pass_threshold=60
        )

        for person_name, age, episode_id in test_cases:
            print(f"\n【{person_name}（{age}歳）】")
            result = generator.generate(person_name, age, None, episode_id)

            print(f"スコア: {result.score}点（{result.grade}）")
            print(f"判定: {'✅ 合格' if result.passed else '❌ 不合格'}")
            print(f"反復回数: {result.iterations}回")
            print(f"コスト: ${result.cost_estimate:.4f}")
            print(f"\nエピソード:\n{result.episode_text}")

            time.sleep(2)  # レート制限対策

        # 統計表示
        generator.print_statistics()


if __name__ == '__main__':
    test_high_quality_generator()
