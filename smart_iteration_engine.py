"""
Smart Iteration Engine
======================

超高品質エピソード生成のための統合システム
最大3回の反復改善で目標品質を達成

Phase 2: Smart Iteration - Complete Generation System
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 既存コンポーネントのインポート
from ultra_high_quality_prompt import UltraHighQualityPromptGenerator
from instant_quality_gate import InstantQualityGate, QualityGateResult
from auto_fix_engine import AutoFixEngine

# Phase 4.9 (2025-11-01): QualityGateSystem統合（日本語品質チェッカーv2含む）
from quality_gate_system import QualityGateSystem, ApprovalStatus


@dataclass
class IterationResult:
    """反復処理の結果"""
    iteration: int
    episode_text: str
    gate_result: QualityGateResult
    gate_passed: bool
    gate_score: float

    # LLM評価（Phase 3）は後で追加
    llm_score: Optional[float] = None
    total_score: Optional[float] = None

    improvements_applied: List[str] = field(default_factory=list)
    generation_time: float = 0.0
    tokens_used: int = 0


@dataclass
class GenerationResult:
    """最終生成結果"""
    success: bool
    final_episode: str
    iterations: List[IterationResult]
    total_iterations: int
    total_time: float
    total_tokens: int

    final_gate_score: float
    final_llm_score: Optional[float] = None
    final_total_score: Optional[float] = None

    failure_reason: Optional[str] = None


class SmartIterationEngine:
    """
    スマート反復エンジン

    自動改善ループ：
    1. Ultra-High Quality Promptで生成
    2. Instant Quality Gateで検証
    3. 失敗時→Auto Fix Engineで改善→再生成
    4. 最大3回まで反復
    """

    def __init__(
        self,
        max_iterations: int = 3,
        target_gate_score: float = 8.0,
        llm_provider: str = "openai",
        model: Optional[str] = None,
        enable_llm_evaluation: bool = False
    ):
        """
        初期化

        Args:
            max_iterations: 最大反復回数
            target_gate_score: 目標ゲートスコア（10点満点）
            llm_provider: LLMプロバイダー（openai/anthropic）
            model: モデル名
            enable_llm_evaluation: LLM評価を有効化（Phase 3）
        """
        self.max_iterations = max_iterations
        self.target_gate_score = target_gate_score
        self.llm_provider = llm_provider
        self.model = model or self._default_model()
        self.enable_llm_evaluation = enable_llm_evaluation

        # コンポーネント初期化
        self.prompt_generator = UltraHighQualityPromptGenerator()
        self.quality_gate = InstantQualityGate()
        self.fix_engine = AutoFixEngine()

        # Phase 4.9 (2025-11-01): QualityGateSystem統合
        # 日本語品質チェッカーv2を含む統一品質ゲートシステム
        self.quality_gate_system = QualityGateSystem()

        # LLM評価器（HybridImpactEvaluator統合）
        self.llm_evaluator = None
        if enable_llm_evaluation:
            from hybrid_impact_evaluator import HybridImpactEvaluator
            try:
                self.llm_evaluator = HybridImpactEvaluator(
                    llm_provider=llm_provider,
                    llm_model=model,
                    enable_llm=True
                )
                print(f"✅ LLM評価有効化: HybridImpactEvaluator")
            except Exception as e:
                print(f"⚠️ LLM評価初期化失敗: {e}")
                print("キーワードベース評価のみで継続します")

    def _default_model(self) -> str:
        """デフォルトモデルを返す"""
        if self.llm_provider == "openai":
            return "gpt-4o"
        elif self.llm_provider == "anthropic":
            return "claude-3-5-sonnet-20241022"
        return "gpt-4o"

    def generate_episode(
        self,
        person_name: str,
        age: int,
        category: str,
        additional_context: Optional[Dict] = None
    ) -> GenerationResult:
        """
        エピソードを生成（反復改善付き）

        Args:
            person_name: 人物名
            age: 年齢
            category: カテゴリ
            additional_context: 追加コンテキスト

        Returns:
            GenerationResult
        """
        start_time = time.time()

        # Stage 2: 事前検証（EpisodeGuardian統合 - EntityTypeのみ）
        try:
            from episode_guardian import EntityTypeValidator, Severity

            # 既知のグループリスト（簡易版）
            known_groups = set()
            validator = EntityTypeValidator(known_groups)

            pre_check_episode = {
                'person_name': person_name,
                'episode_text': '',  # 生成前なので空
                'age': age,
                'category': category
            }

            # EntityTypeのみ検証（episode_textを必要としない）
            validation_result = validator.validate(pre_check_episode)

            if not validation_result.is_valid and validation_result.severity == Severity.CRITICAL:
                print(f"❌ Pre-generation validation failed: {validation_result.message}")
                return GenerationResult(
                    success=False,
                    final_episode="",
                    iterations=[],
                    total_iterations=0,
                    total_time=time.time() - start_time,
                    total_tokens=0,
                    final_gate_score=0.0,
                    failure_reason=f"CRITICAL: {validation_result.message}"
                )
        except ImportError:
            print("⚠️ EntityTypeValidator not available, skipping pre-validation")

        iterations = []
        total_tokens = 0

        # 括弧制約の準備
        bracket_word = additional_context.get('bracket_text') if additional_context else None
        bracket_constraint = ""

        if bracket_word:
            # 括弧内ワード使用を禁止する制約を追加
            bracket_constraint = f"""

【重要な制約 - 括弧内ワードの使用禁止】
エピソード本文に「{bracket_word}」という単語を使用しないでください。
代わりに以下の一般名詞を使用してください：
- グループ名 → "コンビ"、"グループ"、"バンド"、"チーム"、"ユニット"
- 作品名 → "作品"、"シリーズ"、"番組"
- チーム名 → "チーム"、"クラブ"

例:
❌ 悪い例: "くりぃむしちゅーは..."、"くりぃむしちゅーを結成"
✅ 良い例: "コンビは..."、"コンビを結成"

❌ 悪い例: "ちびまる子ちゃんで..."、"ちびまる子ちゃんの人気"
✅ 良い例: "作品で..."、"作品の人気"
"""

        # 初期プロンプト生成（括弧制約を追加）
        initial_prompt = self.prompt_generator.generate_prompt(
            person_name=person_name,
            age=age,
            category=category,
            additional_context=additional_context
        )

        # 括弧制約を末尾に追加
        if bracket_constraint:
            initial_prompt += bracket_constraint

        current_prompt = initial_prompt
        previous_episode = None

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
            print("=" * 60)

            # LLM生成（デモ用: 実際のLLM呼び出しは省略）
            episode_text, tokens = self._call_llm(current_prompt, person_name, age)
            total_tokens += tokens

            # 品質ゲート検証
            gate_result = self.quality_gate.validate(
                episode_text=episode_text,
                target_age=age,
                person_name=person_name
            )

            # Phase 4.9 (2025-11-01): 日本語品質チェック（QualityGateSystem）
            print(f"🔍 Phase 4.9: 日本語品質チェック実行中...")
            episode_data = {
                'person_name': person_name,
                'episode_age': age,
                'episode_content': episode_text,
                'category': category
            }

            # QualityGateSystemで検証（日本語品質チェッカーv2含む）
            gate_system_result = self.quality_gate_system.validate_episode_sync(episode_data)

            # 自動修正が実施された場合、テキストを更新
            if 'episode_content' in episode_data and episode_data['episode_content'] != episode_text:
                episode_text = episode_data['episode_content']
                print(f"✅ 日本語品質チェック: 自動修正を適用しました")

            # 日本語品質チェックの結果をgate_resultに反映
            if gate_system_result.status != ApprovalStatus.APPROVED:
                gate_result.passed = False
                for violation in gate_system_result.violations:
                    if 'JAPANESE_QUALITY' in violation or 'RULE_300' in violation:
                        print(f"⚠️ {violation}")
            else:
                print(f"✅ 日本語品質チェック: 合格")

            # 結果記録
            iter_result = IterationResult(
                iteration=iteration,
                episode_text=episode_text,
                gate_result=gate_result,
                gate_passed=gate_result.passed,
                gate_score=gate_result.total_score,
                generation_time=time.time() - start_time,
                tokens_used=tokens
            )
            iterations.append(iter_result)

            # 結果表示
            status = "✅ PASS" if gate_result.passed else "❌ FAIL"
            print(f"Status: {status}")
            print(f"Gate Score: {gate_result.total_score:.1f}/10.0")
            print(f"Episode Length: {len(episode_text)} chars")

            # 合格判定
            if gate_result.passed and gate_result.total_score >= self.target_gate_score:
                print(f"\n🎉 Success on iteration {iteration}!")

                # LLM評価（オプション）
                if self.enable_llm_evaluation and self.llm_evaluator:
                    print(f"🔍 LLM評価実施中...")
                    llm_score = self._evaluate_with_llm(episode_text, person_name, age)
                    iter_result.llm_score = llm_score
                    # 総合スコア: Gate 10点 + LLM 30点 = 40点満点
                    iter_result.total_score = gate_result.total_score + llm_score
                    print(f"📊 LLMスコア: {llm_score:.1f}/30.0")
                    print(f"📊 総合スコア: {iter_result.total_score:.1f}/40.0")

                return GenerationResult(
                    success=True,
                    final_episode=episode_text,
                    iterations=iterations,
                    total_iterations=iteration,
                    total_time=time.time() - start_time,
                    total_tokens=total_tokens,
                    final_gate_score=gate_result.total_score,
                    final_llm_score=iter_result.llm_score,
                    final_total_score=iter_result.total_score
                )

            # 失敗時: 改善提案生成
            if iteration < self.max_iterations:
                print(f"\n🔧 Generating improvement suggestions...")

                fix_suggestions = self.fix_engine.generate_fix_suggestions(
                    episode_text=episode_text,
                    gate_result=gate_result,
                    target_age=age,
                    person_name=person_name
                )

                # 改善プロンプト生成
                improvement_prompt = self.fix_engine.apply_fixes_to_prompt(
                    original_text=episode_text,
                    fix_suggestions=fix_suggestions,
                    max_fixes=3
                )

                current_prompt = improvement_prompt
                iter_result.improvements_applied = fix_suggestions['priority_order'][:3]

                print(f"Improvements to apply: {', '.join(iter_result.improvements_applied)}")
            else:
                print(f"\n⚠️ Max iterations reached")

        # 最大反復回数到達（失敗）
        best_iteration = max(iterations, key=lambda x: x.gate_score)

        return GenerationResult(
            success=False,
            final_episode=best_iteration.episode_text,
            iterations=iterations,
            total_iterations=self.max_iterations,
            total_time=time.time() - start_time,
            total_tokens=total_tokens,
            final_gate_score=best_iteration.gate_score,
            failure_reason=f"Could not reach target score {self.target_gate_score} in {self.max_iterations} iterations"
        )

    def _call_llm(self, prompt: str, person_name: str, age: int) -> Tuple[str, int]:
        """
        LLMを呼び出してエピソードを生成

        Args:
            prompt: プロンプト
            person_name: 人物名
            age: 年齢

        Returns:
            (episode_text, tokens_used)
        """
        print(f"📝 Calling {self.llm_provider} ({self.model})...")

        if self.llm_provider == "openai":
            return self._call_openai(prompt)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            # デモモード: ダミーエピソード
            dummy_episode = f"""あなたと同じ{age}歳のとき、{person_name}は業界で初めて革新的な取り組みを断行した。「本当にこの人で大丈夫か？」という周囲の強い懸念があったが、従来の常識を覆し、わずか3ヶ月で売上100億円を達成。従業員1000人を超える巨大企業へと成長させ、年間売上500億円を記録した。業界に衝撃を与えたこの決断が、日本全体に転機をもたらし、{person_name}は新時代を切り開いた存在となった。"""
            estimated_tokens = len(prompt) // 4 + len(dummy_episode) // 4
            return dummy_episode, estimated_tokens

    def _call_openai(self, prompt: str) -> Tuple[str, int]:
        """OpenAI APIを呼び出し"""
        import openai

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "あなたは超高品質なエピソード生成の専門家です。指示に従って、180-250文字の感動的なエピソードを生成してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        episode_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens

        return episode_text, tokens_used

    def _call_anthropic(self, prompt: str) -> Tuple[str, int]:
        """Anthropic APIを呼び出し"""
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.7,
            system="あなたは超高品質なエピソード生成の専門家です。指示に従って、180-250文字の感動的なエピソードを生成してください。",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        episode_text = response.content[0].text.strip()
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return episode_text, tokens_used

    def _evaluate_with_llm(self, episode_text: str, person_name: str, age: int) -> float:
        """
        LLMでエピソードを評価（Phase 3）

        Args:
            episode_text: エピソード
            person_name: 人物名
            age: 年齢

        Returns:
            LLMスコア（30点満点）
        """
        if not self.llm_evaluator:
            return 0.0

        try:
            hybrid_score = self.llm_evaluator.evaluate(episode_text, person_name, age)
            # HybridImpactEvaluatorは50点満点なので、30点満点に正規化
            # キーワードスコア（20点） + LLMスコア（30点）= 50点
            # LLM部分のみを取得
            if hybrid_score.llm_used and hybrid_score.llm_score is not None:
                # LLMスコアは50点満点で返ってくる
                # 30点満点に変換: (llm_score / 50) * 30
                return (hybrid_score.llm_score / 50.0) * 30.0
            else:
                # LLM未使用の場合はキーワードスコアのみ（20点満点を30点満点に変換）
                return (hybrid_score.keyword_score / 50.0) * 30.0
        except Exception as e:
            print(f"⚠️ LLM評価エラー: {e}")
            return 0.0

    def generate_batch(
        self,
        person_list: List[Dict],
        parallel: bool = False
    ) -> List[GenerationResult]:
        """
        バッチ生成

        Args:
            person_list: 人物リスト [{"name": "...", "age": ..., "category": "..."}]
            parallel: 並列実行

        Returns:
            GenerationResult のリスト
        """
        results = []

        print(f"\n🚀 Starting batch generation for {len(person_list)} people")
        print(f"Parallel: {parallel}")
        print("=" * 60)

        for i, person in enumerate(person_list, 1):
            print(f"\n📍 [{i}/{len(person_list)}] {person['name']} ({person['age']}歳)")

            result = self.generate_episode(
                person_name=person['name'],
                age=person['age'],
                category=person.get('category', 'エンターテインメント')
            )

            results.append(result)

            status = "✅" if result.success else "❌"
            print(f"{status} {person['name']}: {result.total_iterations} iterations, {result.final_gate_score:.1f} score")

        # サマリー表示
        self._print_batch_summary(results)

        return results

    def _print_batch_summary(self, results: List[GenerationResult]) -> None:
        """バッチ結果サマリーを表示"""
        print(f"\n{'='*60}")
        print("📊 Batch Generation Summary")
        print(f"{'='*60}")

        total = len(results)
        success = sum(1 for r in results if r.success)
        success_rate = success / total * 100

        avg_iterations = sum(r.total_iterations for r in results) / total
        avg_time = sum(r.total_time for r in results) / total
        avg_score = sum(r.final_gate_score for r in results) / total
        total_tokens = sum(r.total_tokens for r in results)

        print(f"\nTotal: {total}")
        print(f"Success: {success}/{total} ({success_rate:.1f}%)")
        print(f"Average Iterations: {avg_iterations:.1f}")
        print(f"Average Time: {avg_time:.1f}s")
        print(f"Average Score: {avg_score:.1f}/10.0")
        print(f"Total Tokens: {total_tokens:,}")

        # スコア分布
        score_ranges = {
            "9.0+": sum(1 for r in results if r.final_gate_score >= 9.0),
            "8.0-8.9": sum(1 for r in results if 8.0 <= r.final_gate_score < 9.0),
            "7.0-7.9": sum(1 for r in results if 7.0 <= r.final_gate_score < 8.0),
            "<7.0": sum(1 for r in results if r.final_gate_score < 7.0),
        }

        print(f"\nScore Distribution:")
        for range_name, count in score_ranges.items():
            percentage = count / total * 100
            print(f"  {range_name}: {count} ({percentage:.1f}%)")


def main():
    """メイン処理 - デモンストレーション"""
    print("=" * 60)
    print("🚀 Smart Iteration Engine Demo")
    print("=" * 60)

    engine = SmartIterationEngine(
        max_iterations=3,
        target_gate_score=8.0,
        llm_provider="openai",
        enable_llm_evaluation=False  # Phase 3で有効化
    )

    # テストケース1: 単一生成
    print("\n" + "=" * 60)
    print("📝 Test 1: Single Episode Generation")
    print("=" * 60)

    result = engine.generate_episode(
        person_name="新垣結衣",
        age=18,
        category="エンターテインメント"
    )

    print(f"\n{'='*60}")
    print("📊 Final Result")
    print(f"{'='*60}")
    print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"Iterations: {result.total_iterations}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Tokens: {result.total_tokens:,}")
    print(f"Final Score: {result.final_gate_score:.1f}/10.0")
    print(f"\nFinal Episode:")
    print(result.final_episode)

    # テストケース2: バッチ生成
    print("\n\n" + "=" * 60)
    print("📝 Test 2: Batch Generation")
    print("=" * 60)

    test_people = [
        {"name": "新垣結衣", "age": 18, "category": "エンターテインメント"},
        {"name": "松下幸之助", "age": 56, "category": "ビジネス"},
        {"name": "イチロー", "age": 45, "category": "スポーツ"},
    ]

    batch_results = engine.generate_batch(test_people)

    print(f"\n{'='*60}")
    print("✅ Demo Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
