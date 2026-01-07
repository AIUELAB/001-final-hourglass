"""
Quality Enhancer - SAGE 品質向上機能

人物事実キャッシュ、失敗パターン学習、段階的品質向上。
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR, RejectionReason


# ==============================================================================
# 人物事実キャッシュ
# ==============================================================================


@dataclass
class PersonFacts:
    """人物事実データ"""

    person_id: str
    person_name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    category: str = ""
    key_facts: list[str] = field(default_factory=list)
    key_works: list[str] = field(default_factory=list)
    key_years: list[int] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "person_name": self.person_name,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "category": self.category,
            "key_facts": self.key_facts,
            "key_works": self.key_works,
            "key_years": self.key_years,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersonFacts":
        return cls(**data)

    def to_context(self) -> str:
        """プロンプト用コンテキスト生成"""
        lines = [f"人物: {self.person_name}"]

        if self.birth_year:
            lines.append(f"生年: {self.birth_year}年")
        if self.death_year:
            lines.append(f"没年: {self.death_year}年")
        if self.category:
            lines.append(f"カテゴリ: {self.category}")

        if self.key_facts:
            lines.append("主な事実:")
            for fact in self.key_facts[:5]:
                lines.append(f"  - {fact}")

        if self.key_works:
            lines.append("主な作品/業績:")
            for work in self.key_works[:5]:
                lines.append(f"  - {work}")

        if self.key_years:
            lines.append(f"重要な年: {', '.join(str(y) for y in self.key_years[:5])}")

        return "\n".join(lines)


class PersonFactsCache:
    """
    人物事実キャッシュ

    生成時に使用する事実情報をキャッシュし、
    プロンプトの具体性を向上。
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir / "person_facts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / "index.json"
        self._index: dict[str, PersonFacts] = {}
        self._load_index()

    def _load_index(self) -> None:
        """インデックス読み込み"""
        if self._index_file.exists():
            try:
                with open(self._index_file, encoding="utf-8") as f:
                    data = json.load(f)
                for pid, facts in data.items():
                    self._index[pid] = PersonFacts.from_dict(facts)
            except (json.JSONDecodeError, KeyError):
                self._index = {}

    def _save_index(self) -> None:
        """インデックス保存"""
        data = {pid: facts.to_dict() for pid, facts in self._index.items()}
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, person_id: str) -> Optional[PersonFacts]:
        """人物事実を取得"""
        return self._index.get(person_id)

    def set(self, facts: PersonFacts) -> None:
        """人物事実を保存"""
        facts.last_updated = datetime.now().isoformat()
        self._index[facts.person_id] = facts
        self._save_index()

    def extract_and_cache(self, person_id: str, person_name: str, episode_text: str) -> PersonFacts:
        """
        エピソードから事実を抽出してキャッシュ

        Args:
            person_id: 人物ID
            person_name: 人物名
            episode_text: エピソードテキスト

        Returns:
            PersonFacts: 抽出された事実
        """
        existing = self.get(person_id)
        if existing is None:
            existing = PersonFacts(person_id=person_id, person_name=person_name)

        # 年号抽出
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", episode_text)
        for year in years:
            y = int(year)
            if y not in existing.key_years:
                existing.key_years.append(y)

        # 作品名抽出
        works = re.findall(r"「([^」]+)」", episode_text)
        for work in works:
            if work not in existing.key_works and len(work) > 2:
                existing.key_works.append(work)

        # 保存
        self.set(existing)
        return existing

    def get_stats(self) -> dict[str, Any]:
        """統計情報"""
        return {
            "total_persons": len(self._index),
            "avg_facts_per_person": (
                sum(len(f.key_facts) for f in self._index.values()) / len(self._index) if self._index else 0
            ),
            "avg_works_per_person": (
                sum(len(f.key_works) for f in self._index.values()) / len(self._index) if self._index else 0
            ),
        }


# ==============================================================================
# 失敗パターン学習
# ==============================================================================


@dataclass
class FailurePattern:
    """失敗パターン"""

    pattern_id: str
    rejection_reason: str
    count: int = 0
    examples: list[str] = field(default_factory=list)
    mitigation: str = ""
    last_seen: str = ""


class FailureLearner:
    """
    失敗パターン学習

    棄却理由を分析し、再発防止策を学習。
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir / "failure_patterns"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._patterns_file = self.cache_dir / "patterns.json"
        self._patterns: dict[str, FailurePattern] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """パターン読み込み"""
        if self._patterns_file.exists():
            try:
                with open(self._patterns_file, encoding="utf-8") as f:
                    data = json.load(f)
                for pid, pattern in data.items():
                    self._patterns[pid] = FailurePattern(**pattern)
            except (json.JSONDecodeError, KeyError):
                self._patterns = {}

    def _save_patterns(self) -> None:
        """パターン保存"""
        data = {pid: p.__dict__ for pid, p in self._patterns.items()}
        with open(self._patterns_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_failure(
        self,
        rejection_reason: RejectionReason,
        episode_text: str = "",
        details: str = "",
    ) -> None:
        """
        失敗を記録

        Args:
            rejection_reason: 棄却理由
            episode_text: エピソードテキスト（例として保存）
            details: 詳細
        """
        pattern_id = rejection_reason.value

        if pattern_id not in self._patterns:
            self._patterns[pattern_id] = FailurePattern(
                pattern_id=pattern_id,
                rejection_reason=rejection_reason.value,
                mitigation=self._get_default_mitigation(rejection_reason),
            )

        pattern = self._patterns[pattern_id]
        pattern.count += 1
        pattern.last_seen = datetime.now().isoformat()

        # 例を追加（最大5件）
        if episode_text and len(pattern.examples) < 5:
            pattern.examples.append(episode_text[:200])

        self._save_patterns()

    def _get_default_mitigation(self, reason: RejectionReason) -> str:
        """デフォルト対策を取得"""
        mitigations = {
            RejectionReason.LOW_FACTUAL_DENSITY: "年号と固有名詞を追加",
            RejectionReason.LOW_GENERATION_QUALITY: "文章構成を改善",
            RejectionReason.HIGH_SIMILARITY: "異なる観点からエピソードを生成",
            RejectionReason.FABRICATION_DETECTED: "検証可能な事実のみ使用",
            RejectionReason.NO_EVIDENCE: "具体的な証拠を追加",
            RejectionReason.PROHIBITED_PATTERN: "禁止表現を避ける",
            RejectionReason.LOW_SPECIFICITY: "具体的な詳細を追加",
        }
        return mitigations.get(reason, "品質改善")

    def get_mitigation(self, rejection_reason: RejectionReason) -> str:
        """対策を取得"""
        pattern = self._patterns.get(rejection_reason.value)
        if pattern:
            return pattern.mitigation
        return self._get_default_mitigation(rejection_reason)

    def get_top_failures(self, limit: int = 5) -> list[FailurePattern]:
        """頻出失敗パターンを取得"""
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.count,
            reverse=True,
        )
        return sorted_patterns[:limit]

    def get_stats(self) -> dict[str, Any]:
        """統計情報"""
        total_failures = sum(p.count for p in self._patterns.values())
        top_reasons = Counter({p.pattern_id: p.count for p in self._patterns.values()}).most_common(5)

        return {
            "total_patterns": len(self._patterns),
            "total_failures": total_failures,
            "top_reasons": top_reasons,
        }


# ==============================================================================
# 品質向上パイプライン
# ==============================================================================


class QualityEnhancer:
    """
    品質向上パイプライン

    機能:
    - 人物事実キャッシュ活用
    - 失敗パターン学習
    - コンテキスト強化
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.person_cache = PersonFactsCache(cache_dir)
        self.failure_learner = FailureLearner(cache_dir)

    def enhance_prompt(
        self,
        person_id: str,
        person_name: str,
        base_prompt: str,
    ) -> str:
        """
        プロンプトを強化

        Args:
            person_id: 人物ID
            person_name: 人物名
            base_prompt: ベースプロンプト

        Returns:
            強化されたプロンプト
        """
        # 人物事実を追加
        facts = self.person_cache.get(person_id)
        if facts:
            context = facts.to_context()
            enhanced = f"{base_prompt}\n\n【参考情報】\n{context}"
        else:
            enhanced = base_prompt

        return enhanced

    def get_retry_guidance(self, rejection_reasons: list[str]) -> str:
        """
        リトライ時のガイダンスを取得

        Args:
            rejection_reasons: 棄却理由リスト

        Returns:
            ガイダンステキスト
        """
        guidance_parts = ["【改善指示】"]

        for reason in rejection_reasons:
            try:
                reason_enum = RejectionReason(reason)
                mitigation = self.failure_learner.get_mitigation(reason_enum)
                guidance_parts.append(f"- {mitigation}")
            except ValueError:
                # 未知の理由
                guidance_parts.append(f"- {reason}を改善")

        return "\n".join(guidance_parts)

    def record_success(
        self,
        person_id: str,
        person_name: str,
        episode_text: str,
    ) -> None:
        """
        成功を記録（事実キャッシュ更新）

        Args:
            person_id: 人物ID
            person_name: 人物名
            episode_text: エピソードテキスト
        """
        self.person_cache.extract_and_cache(person_id, person_name, episode_text)

    def record_failure(
        self,
        rejection_reason: RejectionReason,
        episode_text: str = "",
    ) -> None:
        """
        失敗を記録

        Args:
            rejection_reason: 棄却理由
            episode_text: エピソードテキスト
        """
        self.failure_learner.record_failure(rejection_reason, episode_text)

    def get_stats(self) -> dict[str, Any]:
        """統計情報"""
        return {
            "person_cache": self.person_cache.get_stats(),
            "failure_learner": self.failure_learner.get_stats(),
        }


# ==============================================================================
# 便利関数
# ==============================================================================


def enhance_generation_prompt(
    person_id: str,
    person_name: str,
    prompt: str,
) -> str:
    """プロンプトを強化"""
    enhancer = QualityEnhancer()
    return enhancer.enhance_prompt(person_id, person_name, prompt)


def get_improvement_suggestions(rejection_reasons: list[str]) -> str:
    """改善提案を取得"""
    enhancer = QualityEnhancer()
    return enhancer.get_retry_guidance(rejection_reasons)


if __name__ == "__main__":
    print("=== Quality Enhancer Test ===")

    enhancer = QualityEnhancer()

    # 人物事実キャッシュテスト
    facts = PersonFacts(
        person_id="P123",
        person_name="テスト太郎",
        birth_year=1950,
        key_facts=["ノーベル賞受賞"],
        key_works=["代表作A", "代表作B"],
        key_years=[1980, 1990, 2000],
    )
    enhancer.person_cache.set(facts)

    enhanced = enhancer.enhance_prompt("P123", "テスト太郎", "エピソードを生成してください")
    print(f"Enhanced prompt:\n{enhanced[:300]}...")
    print()

    # 失敗パターン学習テスト
    enhancer.record_failure(RejectionReason.LOW_FACTUAL_DENSITY, "テストエピソード")
    guidance = enhancer.get_retry_guidance(["low_factual_density"])
    print(f"Retry guidance:\n{guidance}")
    print()

    # 統計
    print(f"Stats: {enhancer.get_stats()}")
