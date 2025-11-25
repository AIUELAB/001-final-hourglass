#!/usr/bin/env python3
"""
RULE_185: 微調整特化改善プロンプト

Phase 10専用のエピソード改善ルール。
既存の良い要素を保持しつつ、社会的影響のみをピンポイントで強化する。

改善戦略:
- 最小限の変更（10-30文字追加）
- 社会的影響に関する情報のみ追加・強化
- 受入基準: +3点以上（Phase 9の+5点から緩和）
"""

import os
from typing import Dict, Optional
from openai import OpenAI


# 微調整特化プロンプト
MICRO_ADJUSTMENT_PROMPT = """あなたはエピソード微調整の専門家です。
以下のエピソードの「社会的影響」スコアを+3点以上向上させてください。

【最重要制約】
- 既存の良い要素は保持する（削除・大幅変更禁止）
- 社会的影響に関する情報のみ追加・強化
- **合計文字数: 150-280文字（厳守） - これが最優先**
- **元のエピソードが150文字未満の場合、150文字以上に必ず拡張**
- **元のエピソードが150文字以上の場合、10-30文字のみ追加**

【微調整の指針】
1. 影響範囲の具体化
   - 人数・規模を数値で示す（例: 累計1000万部、視聴者3000万人）
   - 地理的広がり（全国、世界○○カ国等）
   - 時間的継続性（○○年継続、現在も○○等）

2. 歴史的文脈の明確化
   - 位置づけを示す（初の○○、史上○位、日本初等）
   - 当時の社会的背景・意義
   - 前例との比較

3. 客観的裏付けの追加
   - 具体的な記録・データ（売上、記録、統計）
   - 受賞歴、公式認定（○○賞受賞、ギネス認定等）
   - メディア評価、専門家評価

4. 既存情報の強化（追加ではなく置換で文字数増加を抑える）
   - 曖昧な表現 → 具体的な表現（同じ長さか短く）
   - 「人気を博した」→「累計○○万部」
   - 「高く評価された」→「○○賞受賞」
   - 「影響を与えた」→「○○万人に影響」
   - **重要**: 新しい文を追加するより、既存文に数値を埋め込む方が効率的

【厳守事項】
- **絶対文字数: 150-280文字（この範囲外は絶対に不可）**
- **元が150文字未満の場合: 150文字以上に拡張必須**
- **元が150文字以上の場合: +10~30文字のみ追加**
- 必ず「あなたと同じ{age}歳のとき」で始める
- 実在の事実のみを使用（創作・誇張・推測禁止）
- 敬称は不要
- 既存の年齢・固有名詞・基本情報は変更しない
- 新しい文の追加より、既存文への数値埋め込みを優先

現在のエピソード（{char_count}文字）:
---
{episode_text}
---

人物名: {person_name}
年齢: {age}歳
現在の総合スコア: {current_total_score:.1f}点
現在の社会的影響: {current_social_impact:.1f}点
合格までのギャップ: {gap_to_pass:.1f}点

**目標文字数**: {target_char_min}~{target_char_max}文字（元の{char_count}文字 + 10~30文字）

改善後のエピソードのみを出力してください（説明・前置き・後書き不要）。
"""


def apply_rule_185(
    episode_text: str,
    episode_age: int,
    current_total_score: float,
    current_social_impact: float,
    gap_to_pass: float,
    person_name: str,
    provider: str = "openai",
    max_retries: int = 3
) -> Dict:
    """
    RULE_185: 微調整特化改善を適用

    Args:
        episode_text: 元のエピソードテキスト
        episode_age: エピソード年齢
        current_total_score: 現在の総合スコア
        current_social_impact: 現在の社会的影響スコア
        gap_to_pass: 合格までのギャップ
        person_name: 人物名
        provider: LLMプロバイダ（"openai"のみサポート）
        max_retries: 最大リトライ回数

    Returns:
        {
            "success": bool,
            "improved_text": str,
            "character_count": int,
            "retry_count": int,
            "error": Optional[str]
        }
    """
    if provider != "openai":
        return {
            "success": False,
            "improved_text": episode_text,
            "character_count": len(episode_text),
            "retry_count": 0,
            "error": f"Unsupported provider: {provider}"
        }

    # OpenAI APIキーチェック
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "improved_text": episode_text,
            "character_count": len(episode_text),
            "retry_count": 0,
            "error": "OPENAI_API_KEY not set"
        }

    client = OpenAI(api_key=api_key)

    # 元の文字数から目標範囲を計算
    original_char_count = len(episode_text)
    target_min = original_char_count + 10
    target_max = min(original_char_count + 30, 280)

    # プロンプト生成
    prompt = MICRO_ADJUSTMENT_PROMPT.format(
        episode_text=episode_text,
        person_name=person_name,
        age=episode_age,
        current_total_score=current_total_score,
        current_social_impact=current_social_impact,
        gap_to_pass=gap_to_pass,
        char_count=original_char_count,
        target_char_min=target_min,
        target_char_max=target_max
    )

    # リトライループ
    for retry in range(max_retries):
        try:
            # OpenAI API呼び出し
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは事実に基づいたエピソード微調整の専門家です。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=400
            )

            improved_text = response.choices[0].message.content.strip()

            # 文字数検証
            char_count = len(improved_text)

            if 150 <= char_count <= 280:
                # 成功
                return {
                    "success": True,
                    "improved_text": improved_text,
                    "character_count": char_count,
                    "retry_count": retry,
                    "error": None
                }
            else:
                # 文字数制約違反 - リトライ
                print(f"  ⚠️ 文字数制約違反 (retry {retry+1}/{max_retries}): {char_count}文字")
                if retry < max_retries - 1:
                    # 次のリトライでより厳格な指示を追加
                    if char_count > 280:
                        prompt += f"\n\n【重要】前回は{char_count}文字で280文字を超過しました。必ず280文字以内に収めてください。"
                    else:
                        prompt += f"\n\n【重要】前回は{char_count}文字で150文字未満でした。必ず150文字以上にしてください。"
                continue

        except Exception as e:
            print(f"  ❌ API呼び出しエラー (retry {retry+1}/{max_retries}): {str(e)}")
            if retry < max_retries - 1:
                continue
            return {
                "success": False,
                "improved_text": episode_text,
                "character_count": len(episode_text),
                "retry_count": retry,
                "error": str(e)
            }

    # 全リトライ失敗
    return {
        "success": False,
        "improved_text": episode_text,
        "character_count": len(episode_text),
        "retry_count": max_retries,
        "error": f"Character count constraint violation after {max_retries} retries"
    }


# テスト用関数
def test_rule_185():
    """RULE_185の動作テスト"""
    test_episode = {
        "episode_text": "あなたと同じ27歳のとき、芥川龍之介は「羅生門」「鼻」などの短編小説を発表し、日本近代文学の代表的作家として確立されました。彼の作品は人間心理を深く掘り下げ、後の文学に大きな影響を与え、現在も芥川賞として文学界で最も権威ある賞の名前に使われています。",
        "episode_age": 27,
        "current_total_score": 72.5,
        "current_social_impact": 49.0,
        "gap_to_pass": 1.0,
        "person_name": "芥川龍之介"
    }

    print("=" * 80)
    print("RULE_185: 微調整特化改善テスト")
    print("=" * 80)

    print(f"\n対象エピソード:")
    print(f"  人物名: {test_episode['person_name']}")
    print(f"  年齢: {test_episode['episode_age']}歳")
    print(f"  現在の総合スコア: {test_episode['current_total_score']:.1f}点")
    print(f"  現在の社会的影響: {test_episode['current_social_impact']:.1f}点")
    print(f"  合格までのギャップ: {test_episode['gap_to_pass']:.1f}点")

    print(f"\n元のエピソード（{len(test_episode['episode_text'])}文字）:")
    print(f"  {test_episode['episode_text']}")

    print(f"\n改善実行中...")
    result = apply_rule_185(**test_episode)

    print(f"\n結果:")
    print(f"  成功: {result['success']}")
    print(f"  文字数: {result['character_count']}文字")
    print(f"  リトライ回数: {result['retry_count']}回")

    if result['success']:
        print(f"\n改善後のエピソード:")
        print(f"  {result['improved_text']}")

        # 文字数差分
        diff = result['character_count'] - len(test_episode['episode_text'])
        print(f"\n文字数変化: {diff:+d}文字")

        print(f"\n✅ テスト成功")
    else:
        print(f"  エラー: {result['error']}")
        print(f"\n❌ テスト失敗")


if __name__ == "__main__":
    test_rule_185()
