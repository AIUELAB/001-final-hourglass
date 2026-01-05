#!/usr/bin/env python3
"""
バッチ品質評価モジュール

7軸評価 + 構造チェックによる品質ゲート
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .config import QUALITY_SCORE_WEIGHTS, QualityGateConfig


@dataclass
class EvaluationScores:
    """評価スコア"""

    # 7軸スコア（1-10）
    factual_density: float = 0.0  # 事実密度
    generation_quality: float = 0.0  # 生成品質
    memorability: float = 0.0  # 記憶性
    surprise: float = 0.0  # 意外性
    story_quality: float = 0.0  # ストーリー品質
    educational_value: float = 0.0  # 教育的価値
    empathy: float = 0.0  # 共感性

    # 構造スコア
    year_count: int = 0  # 年号数
    number_count: int = 0  # 数値数
    proper_noun_count: int = 0  # 固有名詞数
    char_count: int = 0  # 文字数

    # 総合スコア
    composite_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "事実密度": self.factual_density,
            "生成品質スコア": self.generation_quality,
            "記憶性スコア": self.memorability,
            "意外性スコア": self.surprise,
            "ストーリー品質": self.story_quality,
            "教育的価値": self.educational_value,
            "共感性スコア": self.empathy,
            "year_count": self.year_count,
            "number_count": self.number_count,
            "proper_noun_count": self.proper_noun_count,
            "char_count": self.char_count,
            "composite_score": self.composite_score,
        }


@dataclass
class EvaluationResult:
    """評価結果"""

    episode_text: str
    person_name: str
    age: int
    scores: EvaluationScores
    passed_gate: bool
    gate_failures: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuralEvaluator:
    """構造的評価器"""

    # 年号パターン
    YEAR_PATTERN = re.compile(r"\d{4}年")

    # 数値パターン（単位付き）
    NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?(?:歳|万|億|円|ドル|人|名|本|件|回|%|kg|m|km|時間|日|週|月|年間)?")

    # 固有名詞検出用の簡易パターン（カタカナ連続、漢字+敬称など）
    PROPER_NOUN_PATTERNS = [
        re.compile(r"[ァ-ヶー]{3,}"),  # カタカナ3文字以上
        re.compile(r"「[^」]+」"),  # カギ括弧内
        re.compile(r"『[^』]+』"),  # 二重カギ括弧内
    ]

    def evaluate(self, text: str) -> Dict[str, int]:
        """
        構造的評価を実行

        Args:
            text: 評価対象テキスト

        Returns:
            構造スコア辞書
        """
        # 年号カウント
        years = self.YEAR_PATTERN.findall(text)

        # 数値カウント（年号を除く）
        numbers = self.NUMBER_PATTERN.findall(text)
        # 年号と重複する数値を除外
        numbers = [n for n in numbers if not n.endswith("年")]

        # 固有名詞カウント
        proper_nouns = set()
        for pattern in self.PROPER_NOUN_PATTERNS:
            matches = pattern.findall(text)
            proper_nouns.update(matches)

        return {
            "year_count": len(years),
            "number_count": len(numbers),
            "proper_noun_count": len(proper_nouns),
            "char_count": len(text),
        }


class BatchEvaluator:
    """バッチ品質評価器"""

    # 7軸評価プロンプトテンプレート
    EVALUATION_PROMPT_TEMPLATE = """# エピソード品質評価タスク

以下の{count}件のエピソードを評価してください。

## 評価軸（各1-10点）
1. 事実密度: 具体的な年号・数値・固有名詞の豊富さ
2. 生成品質: 文章の自然さ、読みやすさ、完成度
3. 記憶性: 印象に残るか、覚えやすいか
4. 意外性: 新しい発見や驚きがあるか
5. ストーリー品質: 物語としての構成、起承転結
6. 教育的価値: 学びや気づきがあるか
7. 共感性: 感情移入できるか、共感を呼ぶか

## 評価対象エピソード
{episodes}

## 出力形式（JSON配列）
[
  {{"index": 0, "事実密度": 8, "生成品質スコア": 7, "記憶性スコア": 6, "意外性スコア": 5, "ストーリー品質": 7, "教育的価値": 6, "共感性スコア": 5}},
  ...
]

JSON配列のみを出力してください。説明は不要です。
"""

    def __init__(
        self,
        llm_client: Any,
        config: Optional[QualityGateConfig] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            llm_client: LLMクライアント
            config: 品質ゲート設定
            weights: スコア重み
        """
        self.llm = llm_client
        self.config = config or QualityGateConfig()
        self.weights = weights or QUALITY_SCORE_WEIGHTS
        self.structural_evaluator = StructuralEvaluator()

    def evaluate_batch(
        self,
        episodes: List[Dict[str, Any]],
        batch_size: int = 20,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[EvaluationResult]:
        """
        バッチで7軸評価

        Args:
            episodes: エピソードリスト
            batch_size: バッチサイズ
            progress_callback: 進捗コールバック

        Returns:
            評価結果リスト
        """
        results = []
        total = len(episodes)

        for i in range(0, total, batch_size):
            batch = episodes[i : i + batch_size]

            # LLM評価
            llm_scores = self._evaluate_batch_llm(batch)

            # 構造評価と結果統合
            for j, ep in enumerate(batch):
                text = ep.get("episode_text", "")
                person_name = ep.get("person_name", "")
                age = ep.get("age", 0)

                # 構造評価
                structural = self.structural_evaluator.evaluate(text)

                # LLMスコア取得
                llm_score = llm_scores[j] if j < len(llm_scores) else {}

                # スコアオブジェクト作成
                scores = EvaluationScores(
                    factual_density=llm_score.get("事実密度", 5.0),
                    generation_quality=llm_score.get("生成品質スコア", 5.0),
                    memorability=llm_score.get("記憶性スコア", 5.0),
                    surprise=llm_score.get("意外性スコア", 5.0),
                    story_quality=llm_score.get("ストーリー品質", 5.0),
                    educational_value=llm_score.get("教育的価値", 5.0),
                    empathy=llm_score.get("共感性スコア", 5.0),
                    year_count=structural["year_count"],
                    number_count=structural["number_count"],
                    proper_noun_count=structural["proper_noun_count"],
                    char_count=structural["char_count"],
                )

                # 複合スコア計算
                scores.composite_score = self._calculate_composite_score(scores)

                # ゲートチェック
                passed, failures = self._check_gate(scores)

                results.append(
                    EvaluationResult(
                        episode_text=text,
                        person_name=person_name,
                        age=age,
                        scores=scores,
                        passed_gate=passed,
                        gate_failures=failures,
                        metadata=ep.get("metadata", {}),
                    )
                )

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        return results

    def _evaluate_batch_llm(self, batch: List[Dict]) -> List[Dict]:
        """LLMでバッチ評価"""
        if not batch:
            return []

        # プロンプト構築
        episodes_text = ""
        for i, ep in enumerate(batch):
            text = ep.get("episode_text", "")[:500]  # 長すぎる場合は切り詰め
            episodes_text += f"\n### エピソード {i}\n{text}\n"

        prompt = self.EVALUATION_PROMPT_TEMPLATE.format(
            count=len(batch),
            episodes=episodes_text,
        )

        try:
            # LLM呼び出し
            response = self.llm.generate(prompt)

            # JSON解析
            scores = self._parse_llm_response(response)
            return scores

        except Exception as e:
            # エラー時はデフォルトスコアを返す
            return [self._default_scores() for _ in batch]

    def _parse_llm_response(self, response: str) -> List[Dict]:
        """LLMレスポンスを解析"""
        # JSON部分を抽出
        json_match = re.search(r"\[[\s\S]*\]", response)
        if not json_match:
            return []

        try:
            scores = json.loads(json_match.group())
            return scores
        except json.JSONDecodeError:
            return []

    def _default_scores(self) -> Dict:
        """デフォルトスコア"""
        return {
            "事実密度": 5.0,
            "生成品質スコア": 5.0,
            "記憶性スコア": 5.0,
            "意外性スコア": 5.0,
            "ストーリー品質": 5.0,
            "教育的価値": 5.0,
            "共感性スコア": 5.0,
        }

    def _calculate_composite_score(self, scores: EvaluationScores) -> float:
        """複合スコアを計算"""
        weighted_sum = (
            scores.factual_density * self.weights.get("事実密度", 0.25)
            + scores.generation_quality * self.weights.get("生成品質スコア", 0.20)
            + scores.memorability * self.weights.get("記憶性スコア", 0.20)
            + scores.surprise * self.weights.get("意外性スコア", 0.10)
            + scores.story_quality * self.weights.get("ストーリー品質", 0.10)
            + scores.educational_value * self.weights.get("教育的価値", 0.10)
            + scores.empathy * self.weights.get("共感性スコア", 0.05)
        )
        return round(weighted_sum, 2)

    def _check_gate(self, scores: EvaluationScores) -> tuple[bool, List[str]]:
        """品質ゲートチェック"""
        failures = []

        # 7軸スコアチェック
        if scores.factual_density < self.config.min_factual_density:
            failures.append(f"事実密度不足: {scores.factual_density:.1f} < {self.config.min_factual_density}")

        if scores.generation_quality < self.config.min_generation_quality:
            failures.append(f"生成品質不足: {scores.generation_quality:.1f} < {self.config.min_generation_quality}")

        if scores.memorability < self.config.min_memorability:
            failures.append(f"記憶性不足: {scores.memorability:.1f} < {self.config.min_memorability}")

        # 構造チェック
        if scores.year_count < self.config.min_year_count:
            failures.append(f"年号不足: {scores.year_count} < {self.config.min_year_count}")

        if scores.number_count < self.config.min_number_count:
            failures.append(f"数値不足: {scores.number_count} < {self.config.min_number_count}")

        return len(failures) == 0, failures


class MockLLMEvaluator:
    """テスト用モック評価器"""

    def generate(self, prompt: str) -> str:
        """モック評価"""
        # プロンプトからエピソード数を抽出
        count_match = re.search(r"(\d+)件", prompt)
        count = int(count_match.group(1)) if count_match else 1

        # ランダムなスコアを生成
        import random

        results = []
        for i in range(count):
            results.append(
                {
                    "index": i,
                    "事実密度": random.randint(6, 10),
                    "生成品質スコア": random.randint(6, 10),
                    "記憶性スコア": random.randint(5, 9),
                    "意外性スコア": random.randint(4, 8),
                    "ストーリー品質": random.randint(5, 9),
                    "教育的価値": random.randint(5, 8),
                    "共感性スコア": random.randint(4, 8),
                }
            )

        return json.dumps(results, ensure_ascii=False)


class FinalRanker:
    """最終選定器"""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or QUALITY_SCORE_WEIGHTS

    def rank_and_select(
        self,
        results: List[EvaluationResult],
        top_k: int = 1,
    ) -> List[EvaluationResult]:
        """
        各人物×年齢から最高品質を選択

        Args:
            results: 評価結果リスト
            top_k: 各グループから選択する件数

        Returns:
            選定結果リスト
        """
        # ゲート通過のみ
        passed = [r for r in results if r.passed_gate]

        # 人物×年齢でグループ化
        groups: Dict[tuple, List[EvaluationResult]] = {}
        for r in passed:
            key = (r.person_name, r.age)
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        # 各グループから上位を選択
        selected = []
        for key, group in groups.items():
            # 複合スコアでソート
            sorted_group = sorted(
                group,
                key=lambda x: x.scores.composite_score,
                reverse=True,
            )
            selected.extend(sorted_group[:top_k])

        return selected

    def get_statistics(
        self,
        results: List[EvaluationResult],
    ) -> Dict[str, Any]:
        """統計情報を取得"""
        if not results:
            return {}

        passed = [r for r in results if r.passed_gate]

        # スコア統計
        composite_scores = [r.scores.composite_score for r in results]
        factual_scores = [r.scores.factual_density for r in results]
        quality_scores = [r.scores.generation_quality for r in results]

        return {
            "total_count": len(results),
            "passed_count": len(passed),
            "pass_rate": len(passed) / len(results) if results else 0,
            "composite_score": {
                "mean": sum(composite_scores) / len(composite_scores),
                "min": min(composite_scores),
                "max": max(composite_scores),
            },
            "factual_density": {
                "mean": sum(factual_scores) / len(factual_scores),
                "min": min(factual_scores),
                "max": max(factual_scores),
            },
            "generation_quality": {
                "mean": sum(quality_scores) / len(quality_scores),
                "min": min(quality_scores),
                "max": max(quality_scores),
            },
        }

    def select_best(
        self,
        episodes: List[Dict[str, Any]],
        top_k: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        辞書形式のエピソードから最高品質を選択

        Args:
            episodes: エピソード辞書リスト
            top_k: 各グループから選択する件数

        Returns:
            選定結果リスト
        """
        if not episodes:
            return []

        # 人物×年齢でグループ化
        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for ep in episodes:
            key = (ep.get("person_name", ""), ep.get("age", 0))
            if key not in groups:
                groups[key] = []
            groups[key].append(ep)

        # 各グループから上位を選択
        selected = []
        for key, group in groups.items():
            # 複合スコアでソート（scores辞書内のcomposite or 生成品質スコア）
            def get_score(ep: Dict) -> float:
                scores = ep.get("scores", {})
                if isinstance(scores, dict):
                    return scores.get("composite", scores.get("生成品質スコア", 0.0))
                return 0.0

            sorted_group = sorted(group, key=get_score, reverse=True)
            selected.extend(sorted_group[:top_k])

        return selected


def main():
    """デモ実行"""
    print("=== バッチ評価デモ ===")

    # モッククライアントでテスト
    client = MockLLMEvaluator()
    evaluator = BatchEvaluator(client)

    # テストエピソード
    episodes = [
        {
            "episode_text": "あなたと同じ30歳のとき、山田太郎は1985年に東京で開催された国際会議に参加した。100人以上の専門家と交流し、3年間で5つのプロジェクトを立ち上げた。",
            "person_name": "山田太郎",
            "age": 30,
        },
        {
            "episode_text": "あなたと同じ25歳のとき、鈴木花子は1990年にパリで個展を開催した。50点の作品を展示し、2週間で1万人の来場者を集めた。",
            "person_name": "鈴木花子",
            "age": 25,
        },
        {
            "episode_text": "彼は成功した。",  # 低品質
            "person_name": "テスト",
            "age": 40,
        },
    ]

    def progress(completed: int, total: int):
        print(f"\r評価進捗: {completed}/{total}", end="", flush=True)

    results = evaluator.evaluate_batch(episodes, batch_size=10, progress_callback=progress)

    print("\n\n評価結果:")
    for r in results:
        status = "✓" if r.passed_gate else "✗"
        print(f"  [{status}] {r.person_name}({r.age}歳)")
        print(f"      複合スコア: {r.scores.composite_score:.2f}")
        print(f"      事実密度: {r.scores.factual_density:.1f}, 生成品質: {r.scores.generation_quality:.1f}")
        if r.gate_failures:
            print(f"      失敗理由: {', '.join(r.gate_failures)}")

    # 統計
    ranker = FinalRanker()
    stats = ranker.get_statistics(results)
    print("\n統計:")
    print(f"  通過率: {stats.get('pass_rate', 0):.1%}")
    print(f"  平均複合スコア: {stats.get('composite_score', {}).get('mean', 0):.2f}")


if __name__ == "__main__":
    main()
