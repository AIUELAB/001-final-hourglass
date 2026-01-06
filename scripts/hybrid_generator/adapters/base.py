"""
Generator Adapter Base

EPGEN と既存生成器の共通インターフェース定義。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class GeneratorType(Enum):
    """生成器の種類"""

    EPGEN = "epgen"
    LEGACY = "legacy"


@dataclass
class Candidate:
    """生成候補"""

    person_id: str
    person_name: str
    age: int
    category: str
    person_type: str = "REAL"
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    slot: Optional[str] = None
    tier: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "person_id": self.person_id,
            "person_name": self.person_name,
            "age": self.age,
            "category": self.category,
            "person_type": self.person_type,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "slot": self.slot,
            "tier": self.tier,
        }


@dataclass
class AxisScores:
    """7軸スコア"""

    memorability: float = 0.0  # 記憶性スコア
    empathy: float = 0.0  # 共感性スコア
    surprise: float = 0.0  # 意外性スコア
    generation_quality: float = 0.0  # 生成品質スコア
    educational_value: float = 0.0  # 教育的価値
    story_quality: float = 0.0  # ストーリー品質
    factual_density: float = 0.0  # 事実密度

    def to_dict(self) -> dict[str, float]:
        """辞書に変換"""
        return {
            "記憶性スコア": self.memorability,
            "共感性スコア": self.empathy,
            "意外性スコア": self.surprise,
            "生成品質スコア": self.generation_quality,
            "教育的価値": self.educational_value,
            "ストーリー品質": self.story_quality,
            "事実密度": self.factual_density,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "AxisScores":
        """辞書から生成"""
        return cls(
            memorability=data.get("記憶性スコア", 0.0),
            empathy=data.get("共感性スコア", 0.0),
            surprise=data.get("意外性スコア", 0.0),
            generation_quality=data.get("生成品質スコア", 0.0),
            educational_value=data.get("教育的価値", 0.0),
            story_quality=data.get("ストーリー品質", 0.0),
            factual_density=data.get("事実密度", 0.0),
        )

    def average(self) -> float:
        """7軸平均"""
        values = [
            self.memorability,
            self.empathy,
            self.surprise,
            self.generation_quality,
            self.educational_value,
            self.story_quality,
            self.factual_density,
        ]
        return sum(values) / len(values)

    def weighted_average(self) -> float:
        """加重平均（事実密度と生成品質を重視）"""
        weights = {
            "memorability": 1.0,
            "empathy": 1.0,
            "surprise": 1.0,
            "generation_quality": 1.5,  # 重み増
            "educational_value": 1.0,
            "story_quality": 1.0,
            "factual_density": 1.5,  # 重み増
        }
        total_weight = sum(weights.values())
        weighted_sum = (
            self.memorability * weights["memorability"]
            + self.empathy * weights["empathy"]
            + self.surprise * weights["surprise"]
            + self.generation_quality * weights["generation_quality"]
            + self.educational_value * weights["educational_value"]
            + self.story_quality * weights["story_quality"]
            + self.factual_density * weights["factual_density"]
        )
        return weighted_sum / total_weight


@dataclass
class EvaluationResult:
    """評価結果"""

    axis_scores: AxisScores
    composite_score: float = 0.0
    super_total_score: float = 0.0
    passed_gate: bool = False
    gate_failures: list[str] = field(default_factory=list)
    raw_response: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "axis_scores": self.axis_scores.to_dict(),
            "composite_score": self.composite_score,
            "super_total_score": self.super_total_score,
            "passed_gate": self.passed_gate,
            "gate_failures": self.gate_failures,
        }


@dataclass
class GenerationResult:
    """生成結果"""

    success: bool
    candidate: Candidate
    episode_text: str = ""
    episode_type: str = "ACHIEVEMENT"
    char_count: int = 0
    evaluation: Optional[EvaluationResult] = None
    generator_type: GeneratorType = GeneratorType.LEGACY
    generation_timestamp: str = ""
    error_message: str = ""
    retry_count: int = 0
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.generation_timestamp:
            self.generation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.episode_text and not self.char_count:
            self.char_count = len(self.episode_text)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "success": self.success,
            "person_id": self.candidate.person_id,
            "person_name": self.candidate.person_name,
            "age": self.candidate.age,
            "category": self.candidate.category,
            "person_type": self.candidate.person_type,
            "episode_text": self.episode_text,
            "episode_type": self.episode_type,
            "char_count": self.char_count,
            "generator_type": self.generator_type.value,
            "generation_timestamp": self.generation_timestamp,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            **(self.evaluation.to_dict() if self.evaluation else {}),
        }

    def to_csv_row(self) -> dict[str, Any]:
        """CSV行形式に変換"""
        row = {
            "person_id": self.candidate.person_id,
            "person_name": self.candidate.person_name,
            "age": self.candidate.age,
            "category": self.candidate.category,
            "person_type": self.candidate.person_type,
            "episode_text": self.episode_text,
            "episode_type": self.episode_type,
            "char_count": self.char_count,
            "generation_timestamp": self.generation_timestamp,
            "slot": self.candidate.slot or "",
            "tier": self.candidate.tier or "",
        }

        if self.evaluation:
            row.update(self.evaluation.axis_scores.to_dict())
            row["composite_score"] = self.evaluation.composite_score
            row["super_total_score"] = self.evaluation.super_total_score

        return row


class GeneratorAdapter(ABC):
    """
    生成器アダプターの抽象基底クラス

    EPGEN と既存生成器を統一インターフェースで扱う。
    """

    def __init__(self, name: str, generator_type: GeneratorType):
        self.name = name
        self.generator_type = generator_type
        self._generation_count = 0
        self._success_count = 0
        self._total_tokens = 0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self._generation_count == 0:
            return 0.0
        return self._success_count / self._generation_count

    @property
    def average_tokens(self) -> float:
        """平均トークン消費"""
        if self._generation_count == 0:
            return 0.0
        return self._total_tokens / self._generation_count

    @abstractmethod
    def generate(self, candidate: Candidate) -> GenerationResult:
        """
        エピソードを生成

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        pass

    @abstractmethod
    def evaluate(self, text: str, candidate: Candidate) -> EvaluationResult:
        """
        エピソードを評価

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        pass

    @abstractmethod
    def improve(self, result: GenerationResult, feedback: str) -> Optional[GenerationResult]:
        """
        エピソードを改善

        Args:
            result: 元の生成結果
            feedback: 改善フィードバック

        Returns:
            GenerationResult: 改善された生成結果、または None
        """
        pass

    def generate_with_retry(self, candidate: Candidate, max_retries: int = 2) -> GenerationResult:
        """
        リトライ付きで生成

        Args:
            candidate: 生成候補
            max_retries: 最大リトライ回数

        Returns:
            GenerationResult: 生成結果
        """
        result = self.generate(candidate)
        retry_count = 0

        while not result.success and retry_count < max_retries:
            retry_count += 1
            result = self.generate(candidate)
            result.retry_count = retry_count

        self._generation_count += 1
        if result.success:
            self._success_count += 1

        return result

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得"""
        return {
            "name": self.name,
            "generator_type": self.generator_type.value,
            "generation_count": self._generation_count,
            "success_count": self._success_count,
            "success_rate": self.success_rate,
            "total_tokens": self._total_tokens,
            "average_tokens": self.average_tokens,
        }

    def reset_stats(self) -> None:
        """統計をリセット"""
        self._generation_count = 0
        self._success_count = 0
        self._total_tokens = 0
