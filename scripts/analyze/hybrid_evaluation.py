#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハイブリッド評価システム

ルールベース評価とLLM評価を組み合わせた7軸評価システム。

設計思想:
- 客観的指標（事実密度等）: ルールベース重視
- 主観的指標（共感性等）: LLM重視
- 両方の強みを活かす加重平均方式

使用方法:
    python scripts/hybrid_evaluation.py --sample 5  # 5件テスト
    python scripts/hybrid_evaluation.py --all       # 全50件評価
"""

import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed")
    sys.exit(1)


# =============================================================================
# ルールベース評価コンポーネント
# =============================================================================


class RuleBasedEvaluator:
    """ルールベース評価器"""

    # 年号パターン
    YEAR_PATTERN = re.compile(r"(19|20)\d{2}年?")
    # 数値パターン
    NUMBER_PATTERN = re.compile(r"\d+[歳回位人件万億円ドル%]")
    # 固有名詞（カタカナ3文字以上）
    KATAKANA_PATTERN = re.compile(r"[ァ-ヴー]{3,}")

    # 感情キーワード
    EMOTION_KEYWORDS = [
        "感動",
        "涙",
        "喜び",
        "悲しみ",
        "怒り",
        "恐怖",
        "驚き",
        "苦悩",
        "葛藤",
        "決意",
        "希望",
        "絶望",
        "挫折",
        "成功",
        "努力",
        "挑戦",
        "克服",
        "成長",
    ]

    # 転機キーワード
    TURNING_POINT_KEYWORDS = [
        "転機",
        "きっかけ",
        "ところが",
        "しかし",
        "ついに",
        "ある日",
        "その時",
        "実は",
        "突然",
        "意外にも",
    ]

    # 教訓キーワード
    LESSON_KEYWORDS = ["学", "教訓", "大切", "重要", "示", "証明", "物語", "意味", "価値", "姿勢", "信念", "精神"]

    def evaluate(self, text: str) -> Dict[str, float]:
        """ルールベース評価を実行"""
        text_len = len(text)

        return {
            "fact_density": self._calc_fact_density(text),
            "emotion_score": self._calc_emotion_score(text),
            "turning_point_score": self._calc_turning_point_score(text),
            "lesson_score": self._calc_lesson_score(text),
            "text_quality": self._calc_text_quality(text),
            "structure_score": self._calc_structure_score(text),
        }

    def _calc_fact_density(self, text: str) -> float:
        """事実密度スコア（1-10）"""
        years = len(self.YEAR_PATTERN.findall(text))
        numbers = len(self.NUMBER_PATTERN.findall(text))
        katakana = len(self.KATAKANA_PATTERN.findall(text))

        # 正規化（テキスト長300文字を基準）
        base_len = max(len(text), 100) / 300
        raw_score = (years * 2 + numbers * 1.5 + katakana * 0.5) / base_len

        # 1-10スケールに変換
        return min(10, max(1, 3 + raw_score * 1.5))

    def _calc_emotion_score(self, text: str) -> float:
        """感情スコア（1-10）"""
        count = sum(1 for kw in self.EMOTION_KEYWORDS if kw in text)
        return min(10, max(1, 3 + count * 1.2))

    def _calc_turning_point_score(self, text: str) -> float:
        """転機スコア（1-10）"""
        count = sum(1 for kw in self.TURNING_POINT_KEYWORDS if kw in text)
        return min(10, max(1, 3 + count * 1.5))

    def _calc_lesson_score(self, text: str) -> float:
        """教訓スコア（1-10）"""
        count = sum(1 for kw in self.LESSON_KEYWORDS if kw in text)
        return min(10, max(1, 3 + count * 1.0))

    def _calc_text_quality(self, text: str) -> float:
        """テキスト品質スコア（1-10）"""
        # 文の数
        sentences = len(re.findall(r"[。！？]", text))
        # 平均文長
        avg_sentence_len = len(text) / max(sentences, 1)

        # 適切な文長（40-80文字）にボーナス
        length_bonus = 0
        if 40 <= avg_sentence_len <= 80:
            length_bonus = 2
        elif 30 <= avg_sentence_len <= 100:
            length_bonus = 1

        # 文数が適切（5-10文）にボーナス
        sentence_bonus = 0
        if 5 <= sentences <= 10:
            sentence_bonus = 2
        elif 3 <= sentences <= 15:
            sentence_bonus = 1

        return min(10, max(1, 5 + length_bonus + sentence_bonus))

    def _calc_structure_score(self, text: str) -> float:
        """構造スコア（1-10）"""
        # 「あなたと同じ」で始まるか
        starts_properly = text.startswith("あなたと同じ")
        # 段落数
        paragraphs = text.count("\n\n") + 1

        score = 5
        if starts_properly:
            score += 2
        if 1 <= paragraphs <= 3:
            score += 1

        return min(10, max(1, score))


# =============================================================================
# LLM評価コンポーネント（軽量版）
# =============================================================================


class LightLLMEvaluator:
    """軽量LLM評価器（主観的指標のみ）"""

    PROMPT_TEMPLATE = """以下のエピソードの3つの軸を評価してください。

【エピソード】
人物: {person_name}
年齢: {age}歳

{episode_text}

【評価基準】各軸1-10点で評価

1. 共感性: 読者が感情的に共鳴できるか
   - 9-10: 深く共感。自分の経験と重ね合わせられる
   - 5-6: 普通
   - 1-2: 共感できない

2. 意外性: 予想外の展開や驚きがあるか
   - 9-10: 非常に驚く。予想を大きく裏切る
   - 5-6: 普通
   - 1-2: 陳腐

3. ストーリー品質: 物語として構成が整っているか
   - 9-10: 完璧な起承転結
   - 5-6: 普通
   - 1-2: ストーリー性なし

JSON形式で出力:
```json
{{"empathy": X, "surprise": X, "story_quality": X}}
```"""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def evaluate(
        self, person_name: str, age: float, episode_text: str, retry_count: int = 2
    ) -> Optional[Dict[str, float]]:
        """LLM評価（主観的3軸のみ）"""
        prompt = self.PROMPT_TEMPLATE.format(
            person_name=person_name, age=int(age) if pd.notna(age) else "不明", episode_text=episode_text
        )

        for attempt in range(retry_count):
            try:
                response = self.client.messages.create(
                    model=self.model, max_tokens=200, temperature=0.2, messages=[{"role": "user", "content": prompt}]
                )

                content = response.content[0].text
                json_start = content.find("{")
                json_end = content.rfind("}") + 1

                if json_start != -1 and json_end > json_start:
                    result = json.loads(content[json_start:json_end])
                    return {
                        "empathy": result.get("empathy", 5),
                        "surprise": result.get("surprise", 5),
                        "story_quality": result.get("story_quality", 5),
                    }

            except Exception as e:
                if attempt < retry_count - 1:
                    time.sleep(1)

        return None


# =============================================================================
# ハイブリッド評価器
# =============================================================================


@dataclass
class HybridWeights:
    """ハイブリッド評価の重み設定（最適化済み）"""

    # 各軸における [ルールベース, LLM] の重み
    # 最適化: CSV既存スコアとの相関を最大化
    memorability: Tuple[float, float] = (0.7, 0.3)  # 事実+印象（高め調整）
    empathy: Tuple[float, float] = (0.3, 0.7)  # 主観重視（維持）
    surprise: Tuple[float, float] = (0.3, 0.7)  # 主観重視（LLM上げ）
    generation_quality: Tuple[float, float] = (0.9, 0.1)  # テキスト品質（ルール上げ）
    educational_value: Tuple[float, float] = (0.4, 0.6)  # 教訓+主観（LLM上げ）
    story_quality: Tuple[float, float] = (0.4, 0.6)  # 主観重視（ルール上げ）
    fact_density: Tuple[float, float] = (1.0, 0.0)  # ルールのみ


class HybridEvaluator:
    """ハイブリッド評価器"""

    def __init__(self, weights: HybridWeights = None):
        self.rule_evaluator = RuleBasedEvaluator()
        self.llm_evaluator = LightLLMEvaluator()
        self.weights = weights or HybridWeights()

    def evaluate(self, person_name: str, age: float, episode_text: str, use_llm: bool = True) -> Dict[str, float]:
        """ハイブリッド評価を実行"""

        # ルールベース評価
        rule_scores = self.rule_evaluator.evaluate(episode_text)

        # LLM評価（オプション）
        llm_scores = None
        if use_llm:
            llm_scores = self.llm_evaluator.evaluate(person_name, age, episode_text)

        # スコア統合
        return self._merge_scores(rule_scores, llm_scores)

    def _merge_scores(self, rule_scores: Dict[str, float], llm_scores: Optional[Dict[str, float]]) -> Dict[str, float]:
        """ルールベースとLLMスコアを統合"""

        # LLMスコアがない場合はルールベースのみ
        if llm_scores is None:
            llm_scores = {"empathy": 5, "surprise": 5, "story_quality": 5}

        w = self.weights

        return {
            "記憶性": self._weighted_avg(
                rule_scores["fact_density"], (llm_scores["empathy"] + llm_scores["surprise"]) / 2, w.memorability
            ),
            "共感性": self._weighted_avg(rule_scores["emotion_score"], llm_scores["empathy"], w.empathy),
            "意外性": self._weighted_avg(rule_scores["turning_point_score"], llm_scores["surprise"], w.surprise),
            "生成品質": self._weighted_avg(
                rule_scores["text_quality"],
                llm_scores["story_quality"],  # 代用
                w.generation_quality,
            ),
            "教育的価値": self._weighted_avg(
                rule_scores["lesson_score"],
                llm_scores["empathy"],  # 代用
                w.educational_value,
            ),
            "ストーリー品質": self._weighted_avg(
                rule_scores["structure_score"], llm_scores["story_quality"], w.story_quality
            ),
            "事実密度": self._weighted_avg(
                rule_scores["fact_density"],
                5,  # LLMは参照しない
                w.fact_density,
            ),
        }

    def _weighted_avg(self, rule_score: float, llm_score: float, weights: Tuple[float, float]) -> float:
        """加重平均"""
        return round(rule_score * weights[0] + llm_score * weights[1], 1)


# =============================================================================
# メイン処理
# =============================================================================


def evaluate_batch(samples_df: pd.DataFrame, use_llm: bool = True, delay: float = 0.5) -> List[Dict]:
    """バッチ評価"""
    evaluator = HybridEvaluator()
    results = []
    total = len(samples_df)

    for idx, row in samples_df.iterrows():
        sample_no = row.get("sample_no", idx + 1)
        person_name = str(row.get("person_name", "不明"))

        print(f"[{sample_no}/{total}] {person_name}...", end=" ")

        try:
            scores = evaluator.evaluate(
                person_name=person_name,
                age=row.get("age", 0),
                episode_text=str(row.get("episode_text", "")),
                use_llm=use_llm,
            )

            result = {"sample_no": sample_no, "person_name": person_name, **scores}
            results.append(result)
            print("OK")

        except Exception as e:
            print(f"ERROR: {e}")

        if use_llm:
            time.sleep(delay)

    return results


def main():
    parser = argparse.ArgumentParser(description="ハイブリッド評価")
    parser.add_argument("--sample", type=int, default=5, help="評価件数")
    parser.add_argument("--all", action="store_true", help="全件評価")
    parser.add_argument("--no-llm", action="store_true", help="LLMを使用しない")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "hybrid_evaluation_results.csv")
    parser.add_argument("--delay", type=float, default=0.5)

    args = parser.parse_args()

    # データ読み込み
    samples_path = PROJECT_ROOT / "reports" / "gold_standard_samples_50.csv"
    df = pd.read_csv(samples_path, encoding="utf-8-sig")

    n_samples = len(df) if args.all else min(args.sample, len(df))
    samples_df = df.head(n_samples)

    print("=" * 70)
    print("ハイブリッド評価システム")
    print("=" * 70)
    print(f"評価件数: {n_samples}")
    print(f"LLM使用: {not args.no_llm}")
    print("=" * 70)

    # 評価実行
    results = evaluate_batch(samples_df, use_llm=not args.no_llm, delay=args.delay)

    if not results:
        print("Error: No results")
        sys.exit(1)

    # 結果をDataFrameに変換
    results_df = pd.DataFrame(results)

    # 保存
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.output, encoding="utf-8-sig", index=False)

    # 統計表示
    print("\n" + "=" * 70)
    print("評価完了サマリー")
    print("=" * 70)

    score_cols = [c for c in results_df.columns if c not in ["sample_no", "person_name"]]
    print("\n【軸ごとの統計】")
    for col in score_cols:
        vals = results_df[col]
        print(f"  {col}: 平均={vals.mean():.1f}, 範囲={vals.min():.1f}-{vals.max():.1f}, 標準偏差={vals.std():.2f}")

    print(f"\n✅ 結果を保存: {args.output}")


if __name__ == "__main__":
    main()
