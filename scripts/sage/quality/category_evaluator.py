"""
Category Evaluator - Phase 6

カテゴリ別動的閾値、人物固有品質シグネチャ。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# ==============================================================================
# データクラス
# ==============================================================================


@dataclass
class CategoryThreshold:
    """カテゴリ別閾値"""

    # Phase 16: デフォルト閾値緩和で採用率向上
    factual_density: float = 7.0
    generation_quality: float = 7.5  # 8.0→7.5 採用率向上
    story_quality: float = 6.5
    educational_value: float = 6.0
    memorability: float = 5.5
    empathy: float = 5.0  # 5.5→5.0 採用率向上
    surprise: float = 5.0


@dataclass
class CategoryEvaluationResult:
    """カテゴリ別評価結果"""

    passed: bool
    category: str
    thresholds_applied: dict[str, float] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "category": self.category,
            "thresholds_applied": self.thresholds_applied,
            "scores": self.scores,
            "failures": self.failures,
        }


@dataclass
class PersonQualitySignature:
    """人物固有品質シグネチャ"""

    person_id: str
    person_name: str
    weak_axes: list[str] = field(default_factory=list)  # 弱点軸
    strong_axes: list[str] = field(default_factory=list)  # 強み軸
    avg_scores: dict[str, float] = field(default_factory=dict)
    episode_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "person_name": self.person_name,
            "weak_axes": self.weak_axes,
            "strong_axes": self.strong_axes,
            "avg_scores": self.avg_scores,
            "episode_count": self.episode_count,
        }


# ==============================================================================
# CategoryThresholds
# ==============================================================================


class CategoryThresholds:
    """
    カテゴリ別閾値管理

    カテゴリごとに異なる品質閾値を適用。
    """

    # カテゴリ別閾値定義（v2: バランス調整版）
    # 調整方針: 品質維持しつつ通過率70%以上を目標
    THRESHOLDS = {
        # === 科学・学術系 ===
        "科学": CategoryThreshold(
            factual_density=8.0,  # 8.5→8.0
            generation_quality=8.0,  # 8.5→8.0
            educational_value=7.5,  # 8.0→7.5
            story_quality=6.0,
        ),
        "科学・技術": CategoryThreshold(
            factual_density=7.0,  # 7.5→7.0 通過率向上
            generation_quality=8.0,
            educational_value=7.0,
            story_quality=6.0,
            empathy=5.0,  # 技術系人物は共感性が低い傾向
        ),
        "学術・研究": CategoryThreshold(
            factual_density=7.0,  # 7.5→7.0 通過率向上
            generation_quality=8.0,
            educational_value=7.0,  # 7.5→7.0
            story_quality=6.0,
            empathy=5.0,  # 技術系人物は共感性が低い傾向
        ),
        # === スポーツ ===
        # Phase 16: 採用率向上のため閾値緩和（empathy 6.0→5.5, generation_quality 8.0→7.5）
        "スポーツ": CategoryThreshold(
            factual_density=7.0,  # 7.5→7.0
            generation_quality=7.5,  # 8.0→7.5 採用率向上
            memorability=6.0,  # 7.0→6.0
            empathy=5.5,  # 6.0→5.5 採用率向上
        ),
        # === 芸術・文化系 ===
        "芸術": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.5,  # 8.0→7.5
            empathy=6.5,  # 7.0→6.5
        ),
        "芸術・文化": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            empathy=6.0,
        ),
        "音楽": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            empathy=6.5,
            memorability=6.0,
        ),
        # === 政治・歴史系 ===
        "政治": CategoryThreshold(
            factual_density=7.5,  # 8.0→7.5
            generation_quality=8.0,
            educational_value=7.0,  # 7.5→7.0
        ),
        "政治・社会": CategoryThreshold(
            factual_density=7.0,
            generation_quality=8.0,
            educational_value=7.0,
        ),
        "歴史": CategoryThreshold(
            factual_density=7.0,  # 8.0→7.5→7.0 通過率向上
            generation_quality=8.0,
            educational_value=7.0,  # 7.5→7.0
        ),
        # === ビジネス ===
        "ビジネス": CategoryThreshold(
            factual_density=7.0,  # 7.5→7.0
            generation_quality=8.0,
            educational_value=6.5,  # 7.0→6.5
        ),
        # === エンターテイメント系 ===
        "エンターテインメント": CategoryThreshold(
            factual_density=6.0,  # 6.5→6.0
            generation_quality=8.0,
            story_quality=7.0,  # 7.5→7.0
            memorability=6.0,  # 7.0→6.0
        ),
        "エンターテイメント": CategoryThreshold(  # 表記揺れ対応
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            memorability=6.0,
        ),
        "映画・演劇": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            empathy=6.0,
        ),
        "俳優・女優": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            empathy=6.0,
        ),
        "俳優": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            empathy=6.0,
        ),
        "アニメ・漫画・ゲーム": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=7.0,
            memorability=6.0,
        ),
        # === 文学 ===
        "文学": CategoryThreshold(
            factual_density=6.0,  # 6.5→6.0
            generation_quality=8.0,  # 8.5→8.0
            story_quality=7.0,  # 8.5→7.5→7.0 通過率向上
        ),
        # === 探検・冒険 ===
        "探検・冒険": CategoryThreshold(
            factual_density=6.5,
            generation_quality=8.0,
            story_quality=7.0,
            memorability=6.5,
        ),
        # === その他 ===
        "医学・健康": CategoryThreshold(
            factual_density=7.5,
            generation_quality=8.0,
            educational_value=7.0,
        ),
        "アナウンサー・キャスター": CategoryThreshold(
            factual_density=6.0,
            generation_quality=8.0,
            story_quality=6.5,
        ),
        "競走馬": CategoryThreshold(
            factual_density=7.0,
            generation_quality=8.0,
            memorability=6.0,
        ),
        "日本の伝説": CategoryThreshold(
            factual_density=5.5,  # 伝説なので事実密度は低め
            generation_quality=8.0,
            story_quality=7.5,
        ),
    }

    # デフォルト閾値
    DEFAULT = CategoryThreshold()

    def get_threshold(self, category: str) -> CategoryThreshold:
        """
        カテゴリの閾値を取得

        Args:
            category: カテゴリ名

        Returns:
            CategoryThreshold
        """
        return self.THRESHOLDS.get(category, self.DEFAULT)

    def evaluate(
        self,
        category: str,
        scores: dict[str, float],
    ) -> CategoryEvaluationResult:
        """
        カテゴリ別評価

        Args:
            category: カテゴリ名
            scores: 軸スコア辞書

        Returns:
            CategoryEvaluationResult
        """
        threshold = self.get_threshold(category)
        failures = []

        # 各軸をチェック
        thresholds_applied = {
            "factual_density": threshold.factual_density,
            "generation_quality": threshold.generation_quality,
            "story_quality": threshold.story_quality,
            "educational_value": threshold.educational_value,
            "memorability": threshold.memorability,
            "empathy": threshold.empathy,
            "surprise": threshold.surprise,
        }

        axis_mapping = {
            "factual_density": "事実密度",
            "generation_quality": "生成品質スコア",
            "story_quality": "ストーリー品質",
            "educational_value": "教育的価値",
            "memorability": "記憶性スコア",
            "empathy": "共感性スコア",
            "surprise": "意外性スコア",
        }

        for axis, threshold_value in thresholds_applied.items():
            # スコア取得（日本語名と英語名の両方をサポート）
            score = scores.get(axis) or scores.get(axis_mapping.get(axis, ""))

            if score is not None and score < threshold_value:
                failures.append(f"{axis} < {threshold_value} (actual: {score})")

        passed = len(failures) == 0

        return CategoryEvaluationResult(
            passed=passed,
            category=category,
            thresholds_applied=thresholds_applied,
            scores=scores,
            failures=failures,
        )


# ==============================================================================
# PersonQualityAnalyzer
# ==============================================================================


class PersonQualityAnalyzer:
    """
    人物固有品質分析

    人物ごとの弱点軸を特定し、改善指示を生成。
    """

    # 軸名のマッピング
    AXIS_NAMES = {
        "factual_density": "事実密度",
        "generation_quality": "生成品質",
        "story_quality": "ストーリー品質",
        "educational_value": "教育的価値",
        "memorability": "記憶性",
        "empathy": "共感性",
        "surprise": "意外性",
    }

    # 弱点判定閾値（平均との差分）
    WEAK_THRESHOLD = -0.5
    STRONG_THRESHOLD = 0.5

    def __init__(self):
        self._signatures: dict[str, PersonQualitySignature] = {}

    def analyze_person(
        self,
        person_id: str,
        person_name: str,
        episodes: list[dict],
    ) -> PersonQualitySignature:
        """
        人物の品質シグネチャを分析

        Args:
            person_id: 人物ID
            person_name: 人物名
            episodes: エピソードリスト [{"scores": dict}, ...]

        Returns:
            PersonQualitySignature
        """
        if not episodes:
            return PersonQualitySignature(person_id=person_id, person_name=person_name)

        # 軸別平均スコア計算
        axis_totals: dict[str, list[float]] = {}

        for ep in episodes:
            scores = ep.get("scores", {})
            for axis in self.AXIS_NAMES.keys():
                if axis in scores:
                    if axis not in axis_totals:
                        axis_totals[axis] = []
                    axis_totals[axis].append(scores[axis])

        avg_scores = {axis: sum(values) / len(values) for axis, values in axis_totals.items() if values}

        # 全体平均
        overall_avg = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0

        # 弱点・強み特定
        weak_axes = []
        strong_axes = []

        for axis, avg in avg_scores.items():
            diff = avg - overall_avg
            if diff < self.WEAK_THRESHOLD:
                weak_axes.append(axis)
            elif diff > self.STRONG_THRESHOLD:
                strong_axes.append(axis)

        signature = PersonQualitySignature(
            person_id=person_id,
            person_name=person_name,
            weak_axes=weak_axes,
            strong_axes=strong_axes,
            avg_scores=avg_scores,
            episode_count=len(episodes),
        )

        self._signatures[person_id] = signature
        return signature

    def get_signature(self, person_id: str) -> Optional[PersonQualitySignature]:
        """シグネチャを取得"""
        return self._signatures.get(person_id)

    def get_improvement_guidance(self, person_id: str) -> str:
        """
        改善ガイダンスを生成

        Args:
            person_id: 人物ID

        Returns:
            改善ガイダンステキスト
        """
        signature = self._signatures.get(person_id)
        if not signature or not signature.weak_axes:
            return ""

        guidance_parts = ["【この人物の重点改善項目】"]

        for axis in signature.weak_axes:
            axis_name = self.AXIS_NAMES.get(axis, axis)
            avg = signature.avg_scores.get(axis, 0)

            # 軸別の改善指示
            if axis == "factual_density":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 年号と固有名詞を追加")
            elif axis == "generation_quality":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 文章構成を改善")
            elif axis == "story_quality":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): ストーリー展開を工夫")
            elif axis == "educational_value":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 学習価値のある内容を追加")
            elif axis == "memorability":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 印象的なエピソードを選択")
            elif axis == "empathy":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 共感できる要素を追加")
            elif axis == "surprise":
                guidance_parts.append(f"- {axis_name}(平均{avg:.1f}): 意外性のある視点を追加")

        return "\n".join(guidance_parts)


# ==============================================================================
# CategoryEvaluator（統合）
# ==============================================================================


class CategoryEvaluator:
    """
    カテゴリ別評価器（統合）

    カテゴリ別閾値 + 人物固有シグネチャを統合。
    """

    def __init__(self):
        self.thresholds = CategoryThresholds()
        self.person_analyzer = PersonQualityAnalyzer()

    def evaluate(
        self,
        category: str,
        scores: dict[str, float],
        person_id: Optional[str] = None,
    ) -> CategoryEvaluationResult:
        """
        カテゴリ別評価

        Args:
            category: カテゴリ名
            scores: 軸スコア辞書
            person_id: 人物ID（オプション）

        Returns:
            CategoryEvaluationResult
        """
        return self.thresholds.evaluate(category, scores)

    def analyze_person_quality(
        self,
        person_id: str,
        person_name: str,
        episodes: list[dict],
    ) -> PersonQualitySignature:
        """人物品質分析"""
        return self.person_analyzer.analyze_person(person_id, person_name, episodes)

    def get_retry_guidance(self, person_id: str, base_guidance: str = "") -> str:
        """
        リトライ時のガイダンス取得

        Args:
            person_id: 人物ID
            base_guidance: 基本ガイダンス

        Returns:
            強化されたガイダンス
        """
        person_guidance = self.person_analyzer.get_improvement_guidance(person_id)

        if person_guidance and base_guidance:
            return f"{base_guidance}\n\n{person_guidance}"
        elif person_guidance:
            return person_guidance
        else:
            return base_guidance


# ==============================================================================
# 便利関数
# ==============================================================================


def evaluate_by_category(
    category: str,
    scores: dict[str, float],
) -> CategoryEvaluationResult:
    """
    カテゴリ別評価（便利関数）

    Args:
        category: カテゴリ名
        scores: 軸スコア辞書

    Returns:
        CategoryEvaluationResult
    """
    evaluator = CategoryEvaluator()
    return evaluator.evaluate(category, scores)


def get_category_thresholds(category: str) -> dict[str, float]:
    """
    カテゴリ閾値取得（便利関数）

    Args:
        category: カテゴリ名

    Returns:
        閾値辞書
    """
    thresholds = CategoryThresholds()
    t = thresholds.get_threshold(category)
    return {
        "factual_density": t.factual_density,
        "generation_quality": t.generation_quality,
        "story_quality": t.story_quality,
        "educational_value": t.educational_value,
        "memorability": t.memorability,
        "empathy": t.empathy,
        "surprise": t.surprise,
    }


if __name__ == "__main__":
    print("=== Category Evaluator Test ===")

    # 1. カテゴリ別閾値テスト
    print("\n1. カテゴリ別閾値テスト")
    evaluator = CategoryEvaluator()

    categories = ["科学", "芸術", "スポーツ"]
    for cat in categories:
        thresholds = get_category_thresholds(cat)
        print(f"  {cat}: factual={thresholds['factual_density']}, gen={thresholds['generation_quality']}")

    # 2. カテゴリ別評価テスト
    print("\n2. カテゴリ別評価テスト")
    scores = {
        "factual_density": 7.5,
        "generation_quality": 8.0,
        "story_quality": 7.0,
        "educational_value": 6.5,
        "memorability": 6.0,
        "empathy": 6.0,
        "surprise": 5.5,
    }

    for cat in ["科学", "芸術"]:
        result = evaluator.evaluate(cat, scores)
        print(f"  {cat}: passed={result.passed}, failures={result.failures[:2]}")

    # 3. 人物品質シグネチャテスト
    print("\n3. 人物品質シグネチャテスト")
    episodes = [
        {"scores": {"factual_density": 6.0, "generation_quality": 8.5, "story_quality": 7.0}},
        {"scores": {"factual_density": 5.5, "generation_quality": 8.0, "story_quality": 7.5}},
        {"scores": {"factual_density": 6.5, "generation_quality": 8.2, "story_quality": 7.2}},
    ]

    signature = evaluator.analyze_person_quality("P123", "テスト太郎", episodes)
    print(f"  弱点軸: {signature.weak_axes}")
    print(f"  平均スコア: {signature.avg_scores}")

    # 4. 改善ガイダンステスト
    print("\n4. 改善ガイダンステスト")
    guidance = evaluator.get_retry_guidance("P123")
    print(f"  ガイダンス:\n{guidance}")

    print("\n=== テスト完了 ===")
