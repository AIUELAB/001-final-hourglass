"""
EPGEN Adapter

scripts/generate/mass_production/ のパイプラインをラップするアダプター。
"""

import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "generate" / "mass_production"))

from .base import (
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
)


class EPGENAdapter(GeneratorAdapter):
    """
    EPGEN アダプター

    scripts/generate/mass_production/ のパイプラインをラップ。
    6段階パイプライン: Selection → Generation → Evaluation → Deduplication → Ranking → Persistence
    """

    def __init__(self):
        super().__init__("epgen", GeneratorType.EPGEN)
        self._generator = None
        self._evaluator = None
        self._prompt_builder = None

    def _get_generator(self):
        """遅延初期化でジェネレータを取得"""
        if self._generator is None:
            try:
                from generator import ParallelGenerator

                self._generator = ParallelGenerator()
            except ImportError as e:
                raise ImportError(
                    f"Failed to import ParallelGenerator: {e}. "
                    "Make sure scripts/generate/mass_production/generator.py exists."
                )
        return self._generator

    def _get_evaluator(self):
        """遅延初期化で評価器を取得"""
        if self._evaluator is None:
            try:
                from evaluator import QualityEvaluator

                self._evaluator = QualityEvaluator()
            except ImportError as e:
                raise ImportError(
                    f"Failed to import QualityEvaluator: {e}. "
                    "Make sure scripts/generate/mass_production/evaluator.py exists."
                )
        return self._evaluator

    def _get_prompt_builder(self):
        """遅延初期化でプロンプトビルダーを取得"""
        if self._prompt_builder is None:
            try:
                from generator import PromptBuilder

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
            from generator import GenerationInput

            gen_input = GenerationInput(
                person_id=candidate.person_id,
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
                person_type=candidate.person_type,
            )

            # 非同期生成を同期的に実行
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # generate_sync メソッドがあれば使用
            if hasattr(generator, "generate_sync"):
                result = generator.generate_sync(gen_input)
            else:
                # generate_batch を使用
                results = loop.run_until_complete(generator.generate_batch([gen_input]))
                result = results[0] if results else None

            if result and result.success:
                episode_text = result.text

                # 評価を実行
                evaluation = self.evaluate(episode_text, candidate)

                return GenerationResult(
                    success=True,
                    candidate=candidate,
                    episode_text=episode_text,
                    episode_type=getattr(result, "episode_type", "ACHIEVEMENT"),
                    char_count=len(episode_text),
                    evaluation=evaluation,
                    generator_type=self.generator_type,
                    evidence=self._extract_evidence(episode_text),
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

        EPGEN の QualityEvaluator を使用して7軸評価を実行。

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            evaluator = self._get_evaluator()

            # 評価実行
            scores = evaluator.evaluate(
                text=text,
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
            )

            axis_scores = AxisScores(
                memorability=scores.get("memorability", 5.0),
                empathy=scores.get("empathy", 5.0),
                surprise=scores.get("surprise", 5.0),
                generation_quality=scores.get("generation_quality", 5.0),
                educational_value=scores.get("educational_value", 5.0),
                story_quality=scores.get("story_quality", 5.0),
                factual_density=scores.get("factual_density", 5.0),
            )

            # 統合スコア計算
            composite_score = scores.get("composite", axis_scores.weighted_average() * 100)

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
        mock_text = (
            f"あなたと同じ{candidate.age}歳のとき、{candidate.person_name}は"
            f"重要な転機を迎えました。1955年、彼は新たな挑戦を始め、"
            f"困難を乗り越えて大きな成功を収めました。"
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
