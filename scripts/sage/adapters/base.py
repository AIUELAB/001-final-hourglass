"""
Generator Adapter Base

EPGEN と既存生成器の共通インターフェース定義。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Claude API 料金 (per 1M tokens, 2026-01時点)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


@dataclass
class TokenUsage:
    """トークン使用量"""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "claude-sonnet-4-20250514"
    # Phase 19: キャッシュ統計
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """
        推定コスト（USD）

        Phase 19: キャッシュ対応コスト計算
        - 通常入力: 標準料金
        - キャッシュ読み取り: 90%割引（0.1倍）
        - キャッシュ作成: 25%追加（1.25倍）
        """
        pricing = PRICING.get(self.model, PRICING["claude-sonnet-4-20250514"])

        # 通常入力トークン（キャッシュ対象外）
        normal_input = self.input_tokens - self.cache_read_input_tokens
        input_cost = (normal_input / 1_000_000) * pricing["input"]

        # キャッシュ読み取りトークン（90%割引）
        cache_read_cost = (self.cache_read_input_tokens / 1_000_000) * pricing["input"] * 0.1

        # キャッシュ作成トークン（25%追加）
        cache_create_cost = (self.cache_creation_input_tokens / 1_000_000) * pricing["input"] * 1.25

        # 出力トークン
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]

        return input_cost + cache_read_cost + cache_create_cost + output_cost

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            model=self.model,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens + other.cache_creation_input_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            # Phase 19: キャッシュ統計
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
        }

    @classmethod
    def estimate_from_text(
        cls,
        prompt: str,
        response: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> "TokenUsage":
        """
        テキストからトークン数を推定

        日本語: ~1.5文字/トークン
        英語: ~4文字/トークン
        混合: ~2文字/トークン（保守的推定）
        """
        # 日本語文字の割合を計算
        jp_chars = sum(1 for c in prompt + response if ord(c) > 0x3000)
        total_chars = len(prompt + response) or 1
        jp_ratio = jp_chars / total_chars

        # 文字/トークン比を計算（日本語多いほど低い）
        chars_per_token = 4 - (jp_ratio * 2.5)  # 4 (英語) ~ 1.5 (日本語)

        input_tokens = int(len(prompt) / chars_per_token)
        output_tokens = int(len(response) / chars_per_token)

        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )

    @classmethod
    def from_api_response(
        cls,
        usage: dict[str, int],
        model: str = "claude-sonnet-4-20250514",
    ) -> "TokenUsage":
        """
        Phase 19: API応答からTokenUsageを生成（キャッシュ対応）
        """
        return cls(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model=model,
            cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
            cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
        )


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
    canonical_age: Optional[int] = None  # Phase 27: 架空キャラ・動物の設定年齢

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
            "canonical_age": self.canonical_age,
        }


@dataclass
class AxisScores:
    """8軸スコア（iconic_score追加）"""

    memorability: float = 0.0  # memorability_score
    empathy: float = 0.0  # empathy_score
    surprise: float = 0.0  # surprise_score
    generation_quality: float = 0.0  # generation_quality_score
    educational_value: float = 0.0  # educational_value
    story_quality: float = 0.0  # story_quality
    factual_density: float = 0.0  # factual_density
    iconic_score: float = 0.0  # iconic_score（感銘度）

    def to_dict(self) -> dict[str, float]:
        """辞書に変換（Phase 28: 英語キー）"""
        return {
            "memorability_score": self.memorability,
            "empathy_score": self.empathy,
            "surprise_score": self.surprise,
            "generation_quality_score": self.generation_quality,
            "educational_value": self.educational_value,
            "story_quality": self.story_quality,
            "factual_density": self.factual_density,
            "iconic_score": self.iconic_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "AxisScores":
        """辞書から生成（Phase 28: 英語キー + 後方互換）"""
        # 英語キー優先、日本語キーにフォールバック
        return cls(
            memorability=data.get("memorability_score", data.get("memorability_score", 0.0)),
            empathy=data.get("empathy_score", data.get("empathy_score", 0.0)),
            surprise=data.get("surprise_score", data.get("surprise_score", 0.0)),
            generation_quality=data.get("generation_quality_score", data.get("generation_quality_score", 0.0)),
            educational_value=data.get("educational_value", data.get("educational_value", 0.0)),
            story_quality=data.get("story_quality", data.get("story_quality", 0.0)),
            factual_density=data.get("factual_density", data.get("factual_density", 0.0)),
            iconic_score=data.get("iconic_score", data.get("iconic_score", 0.0)),
        )

    def average(self) -> float:
        """8軸平均"""
        values = [
            self.memorability,
            self.empathy,
            self.surprise,
            self.generation_quality,
            self.educational_value,
            self.story_quality,
            self.factual_density,
            self.iconic_score,
        ]
        return sum(values) / len(values)

    def weighted_average(self) -> float:
        """加重平均（factual_density、生成品質、象徴性を重視）"""
        weights = {
            "memorability": 1.0,
            "empathy": 1.0,
            "surprise": 1.0,
            "generation_quality": 1.5,  # 重み増
            "educational_value": 1.0,
            "story_quality": 1.0,
            "factual_density": 1.5,  # 重み増
            "iconic_score": 1.5,  # 重み増（感銘度重視）
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
            + self.iconic_score * weights["iconic_score"]
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
    token_usage: Optional[TokenUsage] = None  # トークン使用量追跡
    # Phase 26: モデル追跡とコスト可視化
    model: str = ""  # 使用モデル名（claude-3-5-haiku-20241022 等）
    cost_usd: float = 0.0  # エピソード単位のコスト（USD）

    def __post_init__(self) -> None:
        if not self.generation_timestamp:
            self.generation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.episode_text and not self.char_count:
            self.char_count = len(self.episode_text)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        result = {
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
        if self.token_usage:
            result["token_usage"] = self.token_usage.to_dict()
        return result

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

        # Phase 26: モデル追跡とコスト可視化
        row["model"] = self.model
        row["generator_type"] = (
            self.generator_type.value if hasattr(self.generator_type, "value") else str(self.generator_type)
        )
        row["cost_usd"] = self.cost_usd

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
        # Phase 1: 詳細トークン計測
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_call_count = 0
        self._model_name = "claude-sonnet-4-20250514"

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

    @property
    def total_token_usage(self) -> TokenUsage:
        """累計トークン使用量"""
        return TokenUsage(
            input_tokens=self._total_input_tokens,
            output_tokens=self._total_output_tokens,
            model=self._model_name,
        )

    def record_token_usage(self, usage: TokenUsage) -> None:
        """トークン使用量を記録"""
        self._total_input_tokens += usage.input_tokens
        self._total_output_tokens += usage.output_tokens
        self._total_tokens += usage.total_tokens
        self._llm_call_count += 1

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
        token_usage = self.total_token_usage
        return {
            "name": self.name,
            "generator_type": self.generator_type.value,
            "generation_count": self._generation_count,
            "success_count": self._success_count,
            "success_rate": self.success_rate,
            "total_tokens": self._total_tokens,
            "average_tokens": self.average_tokens,
            # Phase 1: 詳細トークン計測
            "llm_call_count": self._llm_call_count,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "estimated_cost_usd": token_usage.estimated_cost_usd,
            "model": self._model_name,
        }

    def reset_stats(self) -> None:
        """統計をリセット"""
        self._generation_count = 0
        self._success_count = 0
        self._total_tokens = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_call_count = 0
