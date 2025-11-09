#!/usr/bin/env python3
"""
RULE_184: 社会的影響特化LLM改善ルール

Phase 9専用ルール - 社会的影響スコアを重点的に改善する。
歴史的文脈、影響範囲、社会的意義を強化したプロンプトを使用。
"""

import os
from typing import Dict, Optional
from openai import OpenAI
from anthropic import Anthropic


SOCIAL_IMPACT_IMPROVEMENT_PROMPT = """あなたはエピソード改善の専門家です。
以下のエピソードの「社会的影響」スコアを向上させてください。

現在のエピソード:
{episode_text}

現在の評価:
- 総合スコア: {total_score}点
- 社会的影響: {social_impact}点 ← この項目を重点改善

社会的影響を高めるための改善指針:
1. 歴史的文脈の明確化
   - その業績が「なぜ」重要なのか
   - 当時の社会状況との関連
   - 前例のない点を具体化

2. 影響範囲の具体化
   - 影響を受けた人数・規模（発行部数、視聴者数等）
   - 地理的・時間的広がり（国際展開、何年継続等）
   - 他分野への波及効果（後続作品、社会変化等）

3. 社会的意義の強調
   - 文化・社会への貢献
   - パラダイムシフト、ジャンル確立
   - 後世への影響（受賞歴、評価等）

4. 客観的な裏付け
   - 記録、統計データ（売上、記録、数値）
   - メディア報道、社会的評価
   - 専門家の評価、公式認定

改善例:
改善前（社会的影響38点）:
「あなたと同じ40歳のとき、手塚治虫は『ブラック・ジャック』の連載を開始し、医療漫画という新ジャンルを確立した。生涯で15万枚の原稿を描き、700作品以上を世に送り出した。」

改善後（期待社会的影響55点）:
「あなたと同じ40歳のとき、手塚治虫は『ブラック・ジャック』の連載を開始し、医療漫画という新ジャンルを確立した。週刊少年チャンピオンで連載開始からわずか3ヶ月で発行部数が150万部増加し、社会現象となった。医療倫理をテーマにした本作は、30カ国以上で翻訳され、後の『Dr.コトー診療所』『医龍』など医療ドラマブームの原点となった。生涯で15万枚の原稿を描き、700作品以上を世に送り出し、ユネスコによる『20世紀最も影響力のある漫画家』に選出された。」

改善ポイント:
- 発行部数150万部増（定量的影響）
- 30カ国翻訳（地理的広がり）
- 後続作品への影響（時間的広がり）
- ユネスコ選出（客観的評価）

制約条件:
- 文字数: 150-280文字（重要: この範囲に必ず収める）
- 必ず「あなたと同じ{age}歳のとき」で始める
- 実在の事実のみを使用（創作・誇張禁止）
- 敬称は不要
- **必ず動詞または形容詞で終わる（名詞で終わることは絶対禁止）**
  NG例: 「〜の先駆者」「〜への挑戦に成功」「〜を切り開いた者」
  OK例: 「〜を切り開いた」「〜に成功した」「〜を変えた」

改善後のエピソードのみを出力してください（説明不要）。"""


class Rule184SocialImpactImprover:
    """RULE_184: 社会的影響特化LLM改善"""

    def __init__(self, provider: str = "openai"):
        """
        Args:
            provider: LLMプロバイダー ("openai" or "anthropic")
        """
        self.provider = provider.lower()

        if self.provider == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4o-mini"
        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def improve_episode(
        self,
        episode_text: str,
        episode_age: int,
        current_total_score: float,
        current_social_impact: float,
        person_name: str
    ) -> Dict[str, any]:
        """
        エピソードの社会的影響を改善

        Args:
            episode_text: 現在のエピソードテキスト
            episode_age: エピソード年齢
            current_total_score: 現在の総合スコア
            current_social_impact: 現在の社会的影響スコア
            person_name: 人物名（ログ用）

        Returns:
            {
                "improved_text": str,
                "original_text": str,
                "success": bool,
                "error": Optional[str],
                "provider": str,
                "model": str
            }
        """
        try:
            # プロンプト生成
            prompt = SOCIAL_IMPACT_IMPROVEMENT_PROMPT.format(
                episode_text=episode_text,
                age=episode_age,
                total_score=current_total_score,
                social_impact=current_social_impact
            )

            # LLM呼び出し
            if self.provider == "openai":
                improved_text = self._call_openai(prompt)
            else:
                improved_text = self._call_anthropic(prompt)

            # 文字数チェック
            char_count = len(improved_text)
            if not (150 <= char_count <= 280):
                return {
                    "improved_text": episode_text,  # 元のテキストを返す
                    "original_text": episode_text,
                    "success": False,
                    "error": f"文字数制約違反: {char_count}文字（150-280文字必須）",
                    "provider": self.provider,
                    "model": self.model
                }

            # 開始フレーズチェック
            expected_start = f"あなたと同じ{episode_age}歳のとき"
            if not improved_text.startswith(expected_start):
                return {
                    "improved_text": episode_text,
                    "original_text": episode_text,
                    "success": False,
                    "error": f"開始フレーズ違反: '{expected_start}'で始まっていない",
                    "provider": self.provider,
                    "model": self.model
                }

            return {
                "improved_text": improved_text,
                "original_text": episode_text,
                "success": True,
                "error": None,
                "provider": self.provider,
                "model": self.model
            }

        except Exception as e:
            return {
                "improved_text": episode_text,
                "original_text": episode_text,
                "success": False,
                "error": str(e),
                "provider": self.provider,
                "model": self.model
            }

    def _call_openai(self, prompt: str) -> str:
        """OpenAI API呼び出し"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "あなたは歴史的エピソードの改善専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, prompt: str) -> str:
        """Anthropic API呼び出し"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=400,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()


def apply_rule_184(
    episode_text: str,
    episode_age: int,
    current_total_score: float,
    current_social_impact: float,
    person_name: str,
    provider: str = "openai"
) -> Dict[str, any]:
    """
    RULE_184を適用してエピソードを改善

    Args:
        episode_text: エピソードテキスト
        episode_age: エピソード年齢
        current_total_score: 現在の総合スコア
        current_social_impact: 現在の社会的影響スコア
        person_name: 人物名
        provider: LLMプロバイダー

    Returns:
        改善結果辞書
    """
    improver = Rule184SocialImpactImprover(provider=provider)
    return improver.improve_episode(
        episode_text=episode_text,
        episode_age=episode_age,
        current_total_score=current_total_score,
        current_social_impact=current_social_impact,
        person_name=person_name
    )


if __name__ == "__main__":
    # テスト実行
    print("=" * 80)
    print("RULE_184: 社会的影響特化LLM改善 - テスト")
    print("=" * 80)

    # テストエピソード（手塚治虫の例）
    test_episode = "あなたと同じ40歳のとき、手塚治虫は「ブラック・ジャック」の連載を開始し、医療漫画という新ジャンルを確立した。生涯で15万枚の原稿を描き、700作品以上を世に送り出した。"

    print(f"\n元のエピソード ({len(test_episode)}文字):")
    print(test_episode)
    print(f"\n現在のスコア: 総合74.6点, 社会的影響42.0点")

    # OpenAIで改善
    print("\n🔄 OpenAI GPT-4o-miniで改善中...")
    result = apply_rule_184(
        episode_text=test_episode,
        episode_age=40,
        current_total_score=74.6,
        current_social_impact=42.0,
        person_name="手塚治虫",
        provider="openai"
    )

    if result["success"]:
        print(f"\n✅ 改善成功 ({len(result['improved_text'])}文字):")
        print(result["improved_text"])
    else:
        print(f"\n❌ 改善失敗: {result['error']}")

    print("\n" + "=" * 80)
