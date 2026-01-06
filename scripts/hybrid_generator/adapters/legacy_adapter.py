"""
Legacy Generator Adapter

既存の src/episode_generator.py をラップするアダプター。
"""

import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from .base import (
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
)


class LegacyGeneratorAdapter(GeneratorAdapter):
    """
    既存生成器アダプター

    src/episode_generator.py の EpisodeGenerator をラップ。
    """

    def __init__(self):
        super().__init__("legacy", GeneratorType.LEGACY)
        self._generator = None
        self._evaluator = None

    def _get_generator(self):
        """遅延初期化でジェネレータを取得"""
        if self._generator is None:
            try:
                from episode_generator import EpisodeGenerator

                self._generator = EpisodeGenerator()
            except ImportError as e:
                raise ImportError(
                    f"Failed to import EpisodeGenerator: {e}. " "Make sure src/episode_generator.py exists."
                )
        return self._generator

    def generate(self, candidate: Candidate) -> GenerationResult:
        """
        エピソードを生成

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        try:
            generator = self._get_generator()

            # 生成パラメータを準備
            params = {
                "person_name": candidate.person_name,
                "age": candidate.age,
                "category": candidate.category,
                "person_type": candidate.person_type,
            }

            # 生成実行
            result = generator.generate(**params)

            if result and "episode_text" in result:
                episode_text = result["episode_text"]

                # 評価を実行
                evaluation = self.evaluate(episode_text, candidate)

                return GenerationResult(
                    success=True,
                    candidate=candidate,
                    episode_text=episode_text,
                    episode_type=result.get("episode_type", "ACHIEVEMENT"),
                    char_count=len(episode_text),
                    evaluation=evaluation,
                    generator_type=self.generator_type,
                    evidence=self._extract_evidence(episode_text),
                )
            else:
                return GenerationResult(
                    success=False,
                    candidate=candidate,
                    error_message="No episode text generated",
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

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            generator = self._get_generator()

            # calculate_scores メソッドを使用
            scores = generator.calculate_scores(text, candidate.person_name, candidate.age)

            axis_scores = AxisScores(
                memorability=scores.get("記憶性スコア", 5.0),
                empathy=scores.get("共感性スコア", 5.0),
                surprise=scores.get("意外性スコア", 5.0),
                generation_quality=scores.get("生成品質スコア", 5.0),
                educational_value=scores.get("教育的価値", 5.0),
                story_quality=scores.get("ストーリー品質", 5.0),
                factual_density=scores.get("事実密度", 5.0),
            )

            # 統合スコア計算（7軸の加重平均 × 100）
            composite_score = axis_scores.weighted_average() * 100

            # 品質ゲートチェック
            gate_failures = []
            if axis_scores.factual_density < 6.0:
                gate_failures.append("factual_density < 6.0")
            if axis_scores.generation_quality < 6.0:
                gate_failures.append("generation_quality < 6.0")

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
        # Legacy generator では単純に再生成
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

        return evidence
