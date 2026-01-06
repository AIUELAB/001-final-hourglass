"""
EPGEN Adapter

scripts/generate/mass_production/ のパイプラインをラップするアダプター。
"""

import os
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .base import (
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
    TokenUsage,
)

# プロンプト長推定用の定数
EPGEN_PROMPT_BASE_LENGTH = 2000  # 基本プロンプト長（概算）
EVALUATION_PROMPT_BASE_LENGTH = 1500  # 評価プロンプト長（概算）


class EPGENAdapter(GeneratorAdapter):
    """
    EPGEN アダプター

    scripts/generate/mass_production/ のパイプラインをラップ。
    6段階パイプライン: Selection → Generation → Evaluation → Deduplication → Ranking → Persistence
    """

    def __init__(self, use_haiku_evaluation: bool = True):
        """
        Args:
            use_haiku_evaluation: 評価にHaikuを使用（True=低コスト-92%, False=Sonnet高精度）
        """
        super().__init__("epgen", GeneratorType.EPGEN)
        self._generator = None
        self._evaluator = None
        self._prompt_builder = None
        self._use_haiku_evaluation = use_haiku_evaluation
        # Phase 3: 評価モデル名を追跡
        self._eval_model_name = "claude-3-5-haiku-20241022" if use_haiku_evaluation else "claude-sonnet-4-20250514"

    def _get_generator(self):
        """遅延初期化でジェネレータを取得"""
        if self._generator is None:
            try:
                from scripts.generate.mass_production.generator import ParallelGenerator
                from scripts.generate.mass_production.llm_clients import AnthropicClient

                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

                llm_client = AnthropicClient(api_key=api_key)
                self._generator = ParallelGenerator(llm_client=llm_client)
            except ImportError as e:
                raise ImportError(
                    f"Failed to import ParallelGenerator: {e}. "
                    "Make sure scripts/generate/mass_production/generator.py exists."
                )
        return self._generator

    def _get_evaluator(self):
        """遅延初期化で評価器を取得（Phase 3: Haiku対応）"""
        if self._evaluator is None:
            try:
                from scripts.generate.mass_production.evaluator import BatchEvaluator
                from scripts.generate.mass_production.llm_clients import create_evaluation_client

                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

                # Phase 3: 評価にHaikuを使用（コスト-92%）
                llm_client = create_evaluation_client(use_haiku=self._use_haiku_evaluation, api_key=api_key)
                self._evaluator = BatchEvaluator(llm_client=llm_client)
            except ImportError as e:
                raise ImportError(
                    f"Failed to import BatchEvaluator: {e}. "
                    "Make sure scripts/generate/mass_production/evaluator.py exists."
                )
        return self._evaluator

    def _get_prompt_builder(self):
        """遅延初期化でプロンプトビルダーを取得"""
        if self._prompt_builder is None:
            try:
                from scripts.generate.mass_production.generator import PromptBuilder

                self._prompt_builder = PromptBuilder()
            except ImportError:
                self._prompt_builder = None
        return self._prompt_builder

    def generate(self, candidate: Candidate) -> GenerationResult:
        """
        エピソードを生成

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        import asyncio

        try:
            generator = self._get_generator()

            # GenerationInput形式に変換
            from scripts.generate.mass_production.generator import GenerationInput

            # 具体性強化のための追加コンテキスト
            additional_context = (
                "重要: 以下の要素を必ず含めること:\n"
                "- 西暦年号を2つ以上\n"
                "- 固有名詞（人名、作品名、組織名、地名）を5つ以上\n"
                "- 「」で囲んだ作品名・イベント名を2つ以上\n"
                "- 数値データを3つ以上\n"
                "抽象的な表現や推測・伝聞は禁止"
            )

            gen_input = GenerationInput(
                person_id=candidate.person_id,
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
                additional_context=additional_context,
            )

            # 非同期生成を同期的に実行
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # generate_sync メソッドがあれば使用（リスト形式で渡す）
            if hasattr(generator, "generate_sync"):
                results = generator.generate_sync([gen_input])
                result = results[0] if results else None
            else:
                # generate_batch を使用
                results = loop.run_until_complete(generator.generate_batch([gen_input]))
                result = results[0] if results else None

            if result and result.success:
                episode_text = result.episode_text

                # トークン使用量を推定（生成）
                prompt_text = (
                    f"{candidate.person_name} {candidate.age}歳 {candidate.category}" + " " * EPGEN_PROMPT_BASE_LENGTH
                )
                gen_token_usage = TokenUsage.estimate_from_text(
                    prompt=prompt_text,
                    response=episode_text,
                    model=self._model_name,
                )
                self.record_token_usage(gen_token_usage)

                # 評価を実行
                evaluation = self.evaluate(episode_text, candidate)

                # 生成と評価の合計トークン使用量
                total_token_usage = gen_token_usage
                if hasattr(self, "_last_eval_tokens") and self._last_eval_tokens:
                    total_token_usage = gen_token_usage + self._last_eval_tokens

                return GenerationResult(
                    success=True,
                    candidate=candidate,
                    episode_text=episode_text,
                    episode_type=getattr(result, "episode_type", "ACHIEVEMENT"),
                    char_count=len(episode_text),
                    evaluation=evaluation,
                    generator_type=self.generator_type,
                    evidence=self._extract_evidence(episode_text),
                    token_usage=total_token_usage,
                )
            else:
                error_msg = getattr(result, "error", "Generation failed") if result else "No result"
                return GenerationResult(
                    success=False,
                    candidate=candidate,
                    error_message=str(error_msg),
                    generator_type=self.generator_type,
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                candidate=candidate,
                error_message=str(e),
                generator_type=self.generator_type,
            )

    def evaluate(self, text: str, candidate: Candidate) -> EvaluationResult:
        """
        エピソードを評価

        EPGEN の BatchEvaluator を使用して7軸評価を実行。

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            evaluator = self._get_evaluator()

            # BatchEvaluatorはリスト形式で受け取る
            episode_data = {
                "episode_text": text,
                "person_name": candidate.person_name,
                "age": candidate.age,
                "category": candidate.category,
            }

            # 評価実行（バッチサイズ1で実行）
            results = evaluator.evaluate_batch([episode_data], batch_size=1)

            if results and len(results) > 0:
                eval_result = results[0]
                scores = eval_result.scores

                # トークン使用量を推定（評価）
                eval_prompt = f"{text} {candidate.person_name}" + " " * EVALUATION_PROMPT_BASE_LENGTH
                eval_response = f"scores: {scores}"  # 概算
                eval_token_usage = TokenUsage.estimate_from_text(
                    prompt=eval_prompt,
                    response=eval_response,
                    model=self._model_name,
                )
                self.record_token_usage(eval_token_usage)
                self._last_eval_tokens = eval_token_usage

                axis_scores = AxisScores(
                    memorability=scores.memorability,
                    empathy=scores.empathy,
                    surprise=scores.surprise,
                    generation_quality=scores.generation_quality,
                    educational_value=scores.educational_value,
                    story_quality=scores.story_quality,
                    factual_density=scores.factual_density,
                )

                # 統合スコア計算 (100x スケール: 470-700が目標範囲)
                composite_score = (
                    scores.composite_score * 100 if scores.composite_score < 100 else scores.composite_score
                )

                # 品質ゲートチェック（EPGEN基準）
                gate_failures = []
                if axis_scores.factual_density < 6.5:
                    gate_failures.append("factual_density < 6.5")
                if axis_scores.generation_quality < 6.5:
                    gate_failures.append("generation_quality < 6.5")
                if axis_scores.memorability < 5.5:
                    gate_failures.append("memorability < 5.5")

                return EvaluationResult(
                    axis_scores=axis_scores,
                    composite_score=composite_score,
                    super_total_score=0.0,  # 後で計算
                    passed_gate=len(gate_failures) == 0,
                    gate_failures=gate_failures,
                )
            else:
                raise ValueError("No evaluation result returned")

        except Exception as e:
            # 評価失敗時はデフォルト値
            return EvaluationResult(
                axis_scores=AxisScores(),
                composite_score=0.0,
                super_total_score=0.0,
                passed_gate=False,
                gate_failures=[f"Evaluation error: {str(e)}"],
            )

    def improve(self, result: GenerationResult, feedback: str) -> Optional[GenerationResult]:
        """
        エピソードを改善

        Args:
            result: 元の生成結果
            feedback: 改善フィードバック

        Returns:
            GenerationResult: 改善された生成結果、または None
        """
        # EPGEN では generate_with_retry を利用
        return self.generate(result.candidate)

    def _extract_evidence(self, text: str) -> list[str]:
        """テキストから根拠を抽出"""
        import re

        evidence = []

        # 年号抽出
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text)
        for year in years:
            evidence.append(f"{year}年")

        # 「」内の固有名詞
        quoted = re.findall(r"「([^」]+)」", text)
        for q in quoted[:3]:  # 最大3件
            evidence.append(f"「{q}」")

        # 数値データ
        numbers = re.findall(r"\d+[万億%位回番]", text)
        for n in numbers[:3]:
            evidence.append(n)

        return evidence


class MockEPGENAdapter(GeneratorAdapter):
    """
    モック EPGEN アダプター（テスト用）

    実際のLLM呼び出しなしでテスト可能。
    """

    def __init__(self):
        super().__init__("mock_epgen", GeneratorType.EPGEN)

    def generate(self, candidate: Candidate) -> GenerationResult:
        """モック生成"""
        # 具体性チェックを通過するリアルなモックテキスト
        mock_text = (
            f"あなたと同じ{candidate.age}歳のとき、{candidate.person_name}は"
            f"人生の転機を迎えました。1995年、彼は「新世紀プロジェクト」を"
            f"立ち上げ、東京大学との共同研究で100万件のデータを分析。"
            f"この成果は「サイエンス」誌に掲載され、業界に革命をもたらしました。"
        )

        axis_scores = AxisScores(
            memorability=7.0,
            empathy=6.5,
            surprise=7.5,
            generation_quality=7.0,
            educational_value=6.5,
            story_quality=7.0,
            factual_density=7.0,
        )

        evaluation = EvaluationResult(
            axis_scores=axis_scores,
            composite_score=680.0,
            super_total_score=450000.0,
            passed_gate=True,
            gate_failures=[],
        )

        return GenerationResult(
            success=True,
            candidate=candidate,
            episode_text=mock_text,
            episode_type="ACHIEVEMENT",
            char_count=len(mock_text),
            evaluation=evaluation,
            generator_type=self.generator_type,
            evidence=["1955年"],
        )

    def evaluate(self, text: str, candidate: Candidate) -> EvaluationResult:
        """モック評価"""
        axis_scores = AxisScores(
            memorability=7.0,
            empathy=6.5,
            surprise=7.5,
            generation_quality=7.0,
            educational_value=6.5,
            story_quality=7.0,
            factual_density=7.0,
        )

        return EvaluationResult(
            axis_scores=axis_scores,
            composite_score=680.0,
            super_total_score=450000.0,
            passed_gate=True,
            gate_failures=[],
        )

    def improve(self, result: GenerationResult, feedback: str) -> Optional[GenerationResult]:
        """モック改善"""
        return self.generate(result.candidate)
