#!/usr/bin/env python3
"""
LLMベースの7軸スコアリングモジュール

Claude APIを使用してエピソードの7軸スコアを自動評価する
"""

import os
import json
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import anthropic
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# 7軸の定義
SEVEN_AXES = [
    "記憶性スコア",      # Memorability: 印象に残りやすさ
    "共感性スコア",      # Empathy: 感情移入しやすさ
    "意外性スコア",      # Surprise: 予想外の展開・事実
    "生成品質スコア",    # Generation Quality: 文章の質
    "教育的価値",        # Educational Value: 学びになる度合い
    "ストーリー品質",    # Story Quality: 物語としての完成度
    "事実密度",          # Factual Density: 具体的事実の密度
]

# 評価プロンプト
SCORING_PROMPT = """あなたはエピソード品質評価の専門家です。以下のエピソードを7つの軸で評価してください。

## 評価対象エピソード
- 人物名: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}
- エピソードタイプ: {episode_type}
- エピソード内容:
{episode_text}

## 評価基準（各軸 1.0〜10.0点）

1. **記憶性スコア** (1-10): 読者の印象に残りやすいか
   - 10点: 誰もが知る歴史的瞬間、社会に大きな影響を与えた出来事
   - 7点: 分野内では有名なエピソード
   - 4点: 個人的なエピソードで一般的な印象度は低い
   - 1点: 非常に平凡で記憶に残りにくい

2. **共感性スコア** (1-10): 感情移入しやすいか
   - 10点: 多くの人が強く共感できる普遍的な体験
   - 7点: 特定の層に強く響く体験
   - 4点: 共感しにくい特殊な状況
   - 1点: 感情的つながりが全くない

3. **意外性スコア** (1-10): 予想外の展開や事実があるか
   - 10点: 常識を覆す驚きの事実・展開
   - 7点: 意外な側面がある
   - 4点: 予想通りの内容
   - 1点: 完全に予測可能

4. **生成品質スコア** (1-10): 文章の質が高いか
   - 10点: プロの文章、読みやすく洗練されている
   - 7点: 良い文章、問題なく読める
   - 4点: やや読みにくい、表現に問題がある
   - 1点: 文法・表現に重大な問題

5. **教育的価値** (1-10): 学びになる内容か
   - 10点: 重要な教訓、歴史的意義がある
   - 7点: 有用な知識・視点を提供
   - 4点: 軽い雑学程度
   - 1点: 学びがない

6. **ストーリー品質** (1-10): 物語として面白いか
   - 10点: 起承転結が明確、ドラマチック
   - 7点: 良い構成、興味を引く
   - 4点: 平坦な叙述
   - 1点: 物語性がない

7. **事実密度** (1-10): 具体的な事実が多いか
   - 10点: 数値、日付、固有名詞が豊富で検証可能
   - 7点: 具体的な事実がいくつかある
   - 4点: 抽象的な記述が多い
   - 1点: 事実がほとんどない

## 出力形式
以下のJSON形式で回答してください。reasoningは簡潔に（各20文字以内）。

```json
{{
  "記憶性スコア": {{"score": 8.0, "reasoning": "歴史的転換点"}},
  "共感性スコア": {{"score": 7.5, "reasoning": "挑戦への共感"}},
  "意外性スコア": {{"score": 6.0, "reasoning": "予想通りの展開"}},
  "生成品質スコア": {{"score": 8.5, "reasoning": "読みやすい文章"}},
  "教育的価値": {{"score": 7.0, "reasoning": "ビジネス教訓"}},
  "ストーリー品質": {{"score": 8.0, "reasoning": "起承転結あり"}},
  "事実密度": {{"score": 9.0, "reasoning": "数値と日付多数"}}
}}
```
"""


@dataclass
class ScoreResult:
    """スコア結果を保持するデータクラス"""
    scores: Dict[str, float]
    reasoning: Dict[str, str]
    raw_response: str
    success: bool
    error_message: Optional[str] = None


class LLMScorer:
    """LLMベースのエピソードスコアラー"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        初期化

        Args:
            api_key: Anthropic API Key（省略時は環境変数から取得）
            model: 使用するモデル名
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.request_count = 0
        self.total_tokens = 0

    def score_episode(
        self,
        person_name: str,
        age: float,
        category: str,
        episode_type: str,
        episode_text: str,
        retry_count: int = 2
    ) -> ScoreResult:
        """
        単一エピソードをスコアリング

        Args:
            person_name: 人物名
            age: 年齢
            category: カテゴリ
            episode_type: エピソードタイプ
            episode_text: エピソード本文
            retry_count: リトライ回数

        Returns:
            ScoreResult: スコア結果
        """
        prompt = SCORING_PROMPT.format(
            person_name=person_name,
            age=age,
            category=category,
            episode_type=episode_type,
            episode_text=episode_text
        )

        for attempt in range(retry_count + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                self.request_count += 1
                self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

                # レスポンスをパース
                raw_text = response.content[0].text
                return self._parse_response(raw_text)

            except anthropic.RateLimitError:
                if attempt < retry_count:
                    time.sleep(5 * (attempt + 1))  # バックオフ
                    continue
                return ScoreResult(
                    scores={},
                    reasoning={},
                    raw_response="",
                    success=False,
                    error_message="Rate limit exceeded"
                )
            except Exception as e:
                if attempt < retry_count:
                    time.sleep(1)
                    continue
                return ScoreResult(
                    scores={},
                    reasoning={},
                    raw_response="",
                    success=False,
                    error_message=str(e)
                )

        return ScoreResult(
            scores={},
            reasoning={},
            raw_response="",
            success=False,
            error_message="Max retries exceeded"
        )

    def _parse_response(self, raw_text: str) -> ScoreResult:
        """
        LLMレスポンスをパース

        Args:
            raw_text: LLMの生テキスト

        Returns:
            ScoreResult: パース結果
        """
        try:
            # JSONブロックを抽出
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                return ScoreResult(
                    scores={},
                    reasoning={},
                    raw_response=raw_text,
                    success=False,
                    error_message="No JSON found in response"
                )

            json_str = raw_text[json_start:json_end]
            data = json.loads(json_str)

            scores = {}
            reasoning = {}

            for axis in SEVEN_AXES:
                if axis in data:
                    item = data[axis]
                    if isinstance(item, dict):
                        scores[axis] = float(item.get("score", 5.0))
                        reasoning[axis] = item.get("reasoning", "")
                    else:
                        scores[axis] = float(item)
                        reasoning[axis] = ""
                else:
                    scores[axis] = 5.0  # デフォルト値
                    reasoning[axis] = "未評価"

            return ScoreResult(
                scores=scores,
                reasoning=reasoning,
                raw_response=raw_text,
                success=True
            )

        except json.JSONDecodeError as e:
            return ScoreResult(
                scores={},
                reasoning={},
                raw_response=raw_text,
                success=False,
                error_message=f"JSON parse error: {e}"
            )
        except Exception as e:
            return ScoreResult(
                scores={},
                reasoning={},
                raw_response=raw_text,
                success=False,
                error_message=str(e)
            )

    def score_batch(
        self,
        episodes: List[Dict],
        delay: float = 0.5,
        progress_callback=None
    ) -> List[Tuple[Dict, ScoreResult]]:
        """
        複数エピソードを一括スコアリング

        Args:
            episodes: エピソードのリスト（各要素はdict）
            delay: リクエスト間の遅延（秒）
            progress_callback: 進捗コールバック関数

        Returns:
            List[Tuple[Dict, ScoreResult]]: (エピソード, スコア結果)のリスト
        """
        results = []

        for i, episode in enumerate(episodes):
            result = self.score_episode(
                person_name=episode.get("person_name", ""),
                age=float(episode.get("age", 0)),
                category=episode.get("category", ""),
                episode_type=episode.get("episode_type", ""),
                episode_text=episode.get("episode_text", "")
            )

            results.append((episode, result))

            if progress_callback:
                progress_callback(i + 1, len(episodes), result.success)

            if i < len(episodes) - 1:
                time.sleep(delay)

        return results

    def get_usage_stats(self) -> Dict:
        """
        使用統計を取得

        Returns:
            Dict: 統計情報
        """
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_tokens * 0.000003  # 概算
        }


def compare_scores(
    existing_scores: Dict[str, float],
    llm_scores: Dict[str, float]
) -> Dict[str, Dict]:
    """
    既存スコアとLLMスコアを比較

    Args:
        existing_scores: 既存の7軸スコア
        llm_scores: LLMによる7軸スコア

    Returns:
        Dict: 比較結果
    """
    comparison = {}

    for axis in SEVEN_AXES:
        existing = existing_scores.get(axis, 0)
        llm = llm_scores.get(axis, 0)
        diff = llm - existing

        comparison[axis] = {
            "existing": existing,
            "llm": llm,
            "difference": round(diff, 2),
            "significant": abs(diff) >= 1.5  # 1.5点以上の差は有意
        }

    return comparison


if __name__ == "__main__":
    # テスト実行
    scorer = LLMScorer()

    # テストエピソード
    result = scorer.score_episode(
        person_name="手塚治虫",
        age=20,
        category="漫画・アニメ",
        episode_type="INNOVATION",
        episode_text="1947年、手塚治虫は『新宝島』を発表。映画的なコマ割りと動きのある表現で、日本漫画の表現技法を革新した。この作品は40万部を売り上げ、多くの漫画家に影響を与えた。"
    )

    if result.success:
        print("=== スコア結果 ===")
        for axis, score in result.scores.items():
            reasoning = result.reasoning.get(axis, "")
            print(f"{axis}: {score:.1f} ({reasoning})")

        print(f"\n使用統計: {scorer.get_usage_stats()}")
    else:
        print(f"エラー: {result.error_message}")
