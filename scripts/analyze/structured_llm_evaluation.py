#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
構造化LLM評価システム

エピソードを7軸で評価するためのLLMベース評価システム。
ルーブリックに基づく構造化プロンプトでJSON形式の評価を出力。

使用方法:
    python scripts/structured_llm_evaluation.py --sample 10  # 10件テスト
    python scripts/structured_llm_evaluation.py --all        # 全50件評価
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Anthropic API
try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


@dataclass
class AxisEvaluation:
    """軸ごとの評価結果"""

    score: int  # 1-10
    reason: str  # 評価理由（1-2文）


@dataclass
class EpisodeEvaluation:
    """エピソード評価結果"""

    sample_no: int
    person_name: str
    memorability: AxisEvaluation  # 記憶性
    empathy: AxisEvaluation  # 共感性
    surprise: AxisEvaluation  # 意外性
    generation_quality: AxisEvaluation  # 生成品質
    educational_value: AxisEvaluation  # educational_value
    story_quality: AxisEvaluation  # story_quality
    fact_density: AxisEvaluation  # factual_density
    overall_comment: str  # 総合コメント


# 評価プロンプトテンプレート
EVALUATION_PROMPT = """あなたはエピソード評価の専門家です。以下のエピソードを7つの軸で評価してください。

# 評価対象エピソード
人物名: {person_name}
年齢: {age}歳
カテゴリ: {category}

本文:
{episode_text}

# 評価基準（各軸1-10点）

## 1. 記憶性（Memorability）
読んだ後、記憶に残りやすいか
- 9-10点: 忘れられない。具体的で鮮明なイメージが残る
- 7-8点: 記憶に残りやすい。印象的な要素がある
- 5-6点: 普通。特に印象的ではない
- 3-4点: 記憶に残りにくい
- 1-2点: 全く記憶に残らない

チェック: 固有名詞、数値、年号、転機、ビジュアルイメージ

## 2. 共感性（Empathy）
読者が感情的に共鳴できるか
- 9-10点: 深く共感。自分の経験と重ね合わせられる
- 7-8点: 共感できる。感情的なつながりを感じる
- 5-6点: 普通。共感の余地はあるが強くない
- 3-4点: 共感しにくい
- 1-2点: 全く共感できない

チェック: 感情描写、困難・挫折、普遍的テーマ

## 3. 意外性（Surprise）
予想外の展開や驚きがあるか
- 9-10点: 非常に驚く。予想を大きく裏切る
- 7-8点: 驚きがある。予想と異なる要素がある
- 5-6点: 普通。驚きはないが興味深い
- 3-4点: 意外性がない。予想通り
- 1-2点: 全く意外性がない。陳腐

チェック: 「実は」「ところが」、ステレオタイプ打破、ギャップ

## 4. 生成品質（Generation Quality）
文章として自然で読みやすいか
- 9-10点: 完璧な文章。プロレベル
- 7-8点: 高品質。読みやすく整っている
- 5-6点: 普通。標準的な品質
- 3-4点: 問題がある。文法ミス、不自然
- 1-2点: 品質が低い。読みにくい

チェック: 文法、流れ、語彙、構成

## 5. educational_value（Educational Value）
読者が何かを学べるか
- 9-10点: 非常に教育的。深い学びがある
- 7-8点: 教育的。知識や教訓が得られる
- 5-6点: 普通。多少の学びはある
- 3-4点: educational_valueが低い
- 1-2点: 全くeducational_valueがない

チェック: 事実情報、教訓、「なるほど」感

## 6. story_quality（Story Quality）
物語として構成が整っているか
- 9-10点: 完璧。起承転結が明確
- 7-8点: 良い。構成が整っている
- 5-6点: 普通。ストーリーとして成立
- 3-4点: 構成が悪い。流れが不自然
- 1-2点: ストーリー性がない

チェック: 導入、展開、転機、結末

## 7. factual_density（Fact Density）
検証可能な事実がどれだけ含まれているか
- 9-10点: 非常に高密度。検証可能な事実が多数
- 7-8点: 密度が高い。事実が複数ある
- 5-6点: 普通。基本的な事実がある
- 3-4点: 低密度。事実がほとんどない
- 1-2点: 事実がない

チェック: 年号、数値、固有名詞、検証可能な出来事

# 出力形式

以下のJSON形式で出力してください。必ず有効なJSONを出力すること。

```json
{{
  "memorability": {{"score": X, "reason": "理由（1-2文）"}},
  "empathy": {{"score": X, "reason": "理由（1-2文）"}},
  "surprise": {{"score": X, "reason": "理由（1-2文）"}},
  "generation_quality": {{"score": X, "reason": "理由（1-2文）"}},
  "educational_value": {{"score": X, "reason": "理由（1-2文）"}},
  "story_quality": {{"score": X, "reason": "理由（1-2文）"}},
  "fact_density": {{"score": X, "reason": "理由（1-2文）"}},
  "overall_comment": "総合的なコメント（2-3文）"
}}
```

スコアは整数（1-10）で、理由は日本語で簡潔に記述してください。
"""


class StructuredLLMEvaluator:
    """構造化LLM評価器"""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def evaluate_episode(
        self, sample_no: int, person_name: str, age: float, category: str, episode_text: str, retry_count: int = 3
    ) -> Optional[Dict]:
        """
        単一エピソードを評価

        Args:
            sample_no: サンプル番号
            person_name: 人物名
            age: 年齢
            category: カテゴリ
            episode_text: エピソード本文
            retry_count: リトライ回数

        Returns:
            評価結果の辞書、失敗時はNone
        """
        prompt = EVALUATION_PROMPT.format(
            person_name=person_name,
            age=int(age) if pd.notna(age) else "不明",
            category=category,
            episode_text=episode_text,
        )

        for attempt in range(retry_count):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=0.3,  # 低めで安定性重視
                    messages=[{"role": "user", "content": prompt}],
                )

                # レスポンスからJSONを抽出
                content = response.content[0].text

                # JSON部分を抽出
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                    result["sample_no"] = sample_no
                    result["person_name"] = person_name
                    return result
                else:
                    print(f"  [Warning] JSON not found in response for sample {sample_no}")

            except json.JSONDecodeError as e:
                print(f"  [Warning] JSON parse error for sample {sample_no}: {e}")
            except anthropic.APIError as e:
                print(f"  [Error] API error for sample {sample_no}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2**attempt)  # Exponential backoff
            except Exception as e:
                print(f"  [Error] Unexpected error for sample {sample_no}: {e}")

        return None

    def evaluate_batch(self, samples_df: pd.DataFrame, delay: float = 1.0) -> List[Dict]:
        """
        バッチ評価

        Args:
            samples_df: サンプルデータフレーム
            delay: リクエスト間の待機時間（秒）

        Returns:
            評価結果のリスト
        """
        results = []
        total = len(samples_df)

        for idx, row in samples_df.iterrows():
            sample_no = row.get("sample_no", idx + 1)
            person_name = str(row.get("person_name", "不明"))

            print(f"[{sample_no}/{total}] {person_name}...", end=" ")

            result = self.evaluate_episode(
                sample_no=sample_no,
                person_name=person_name,
                age=row.get("age", 0),
                category=str(row.get("category", "")),
                episode_text=str(row.get("episode_text", "")),
            )

            if result:
                results.append(result)
                print("OK")
            else:
                print("FAILED")

            # レート制限対策
            time.sleep(delay)

        return results


def results_to_dataframe(results: List[Dict]) -> pd.DataFrame:
    """評価結果をDataFrameに変換"""
    rows = []
    for r in results:
        row = {
            "sample_no": r.get("sample_no"),
            "person_name": r.get("person_name"),
        }

        # 各軸のスコアと理由
        axes = [
            ("memorability", "記憶性"),
            ("empathy", "共感性"),
            ("surprise", "意外性"),
            ("generation_quality", "生成品質"),
            ("educational_value", "educational_value"),
            ("story_quality", "story_quality"),
            ("fact_density", "factual_density"),
        ]

        for eng_name, jp_name in axes:
            axis_data = r.get(eng_name, {})
            row[f"{jp_name}_スコア"] = axis_data.get("score", 0)
            row[f"{jp_name}_理由"] = axis_data.get("reason", "")

        row["総合コメント"] = r.get("overall_comment", "")
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="構造化LLM評価")
    parser.add_argument("--sample", type=int, default=10, help="評価するサンプル数（デフォルト: 10）")
    parser.add_argument("--all", action="store_true", help="全50件を評価")
    parser.add_argument(
        "--model", type=str, default="claude-3-haiku-20240307", help="使用するモデル（デフォルト: claude-3-haiku）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "structured_llm_evaluation_results.csv",
        help="出力ファイルパス",
    )
    parser.add_argument("--delay", type=float, default=1.0, help="リクエスト間の待機時間（秒）")

    args = parser.parse_args()

    # データ読み込み
    samples_path = PROJECT_ROOT / "reports" / "gold_standard_samples_50.csv"
    if not samples_path.exists():
        print(f"Error: Samples file not found: {samples_path}")
        sys.exit(1)

    df = pd.read_csv(samples_path, encoding="utf-8-sig")

    # サンプル数の決定
    n_samples = len(df) if args.all else min(args.sample, len(df))
    samples_df = df.head(n_samples)

    print("=" * 70)
    print("構造化LLM評価システム")
    print("=" * 70)
    print(f"モデル: {args.model}")
    print(f"評価件数: {n_samples}")
    print(f"出力先: {args.output}")
    print("=" * 70)

    # 評価実行
    evaluator = StructuredLLMEvaluator(model=args.model)
    results = evaluator.evaluate_batch(samples_df, delay=args.delay)

    if not results:
        print("\nError: No results obtained")
        sys.exit(1)

    # DataFrame変換
    results_df = results_to_dataframe(results)

    # 保存
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.output, encoding="utf-8-sig", index=False)

    # 統計表示
    print("\n" + "=" * 70)
    print("評価完了サマリー")
    print("=" * 70)
    print(f"評価成功: {len(results)}/{n_samples}件")

    score_cols = [c for c in results_df.columns if c.endswith("_スコア")]
    print("\n【軸ごとの統計】")
    for col in score_cols:
        vals = results_df[col]
        axis_name = col.replace("_スコア", "")
        print(f"  {axis_name}: 平均={vals.mean():.1f}, 範囲={vals.min()}-{vals.max()}")

    print(f"\n✅ 結果を保存しました: {args.output}")

    # JSON形式でも保存
    json_output = args.output.with_suffix(".json")
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON形式: {json_output}")


if __name__ == "__main__":
    main()
