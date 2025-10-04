#!/usr/bin/env python3
"""
LLMベース感情的インパクト評価器（LLM Impact Evaluator）
OpenAI APIまたはAnthropic APIを使用した高精度インパクト評価

評価項目（各10点満点、合計50点）:
1. 人生の転換点スコア（Turning Point Score）
2. 意外性スコア（Surprise Score）
3. リスクテイキングスコア（Risk-Taking Score）
4. 共感性スコア（Relatability Score）
5. センセーショナル度（Sensational Score）

合格基準: 30点以上（60%）
"""

import os
import json
from typing import Optional, Dict
from dataclasses import dataclass
import time


@dataclass
class LLMImpactScore:
    """LLMベースのインパクトスコア"""
    turning_point: int
    surprise: int
    risk_taking: int
    relatability: int
    sensational: int
    total: int
    passed: bool
    reasoning: str  # LLMの判定理由


class LLMImpactEvaluator:
    """LLMベース感情的インパクト評価器"""

    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Args:
            provider: "openai" or "anthropic"
            model: モデル名（Noneの場合はデフォルト）
        """
        self.provider = provider.lower()
        self.min_passing_score = 30

        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.model = model or "gpt-4o-mini"  # コスト効率重視
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model = model or "claude-3-haiku-20240307"  # コスト効率重視
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")
        else:
            raise ValueError(f"未対応のプロバイダー: {provider}")

    def evaluate(self, episode_text: str, person_name: str, age: int) -> LLMImpactScore:
        """
        エピソードの感情的インパクトをLLMで評価

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            LLMImpactScore: インパクトスコア
        """
        prompt = self._create_evaluation_prompt(episode_text, person_name, age)

        # プロバイダーに応じてAPI呼び出し
        if self.provider == "openai":
            response = self._call_openai(prompt)
        else:
            response = self._call_anthropic(prompt)

        # レスポンスをパース
        score = self._parse_response(response)
        return score

    def _create_evaluation_prompt(self, episode_text: str, person_name: str, age: int) -> str:
        """評価用プロンプトを生成"""
        return f"""あなたはエピソードの感情的インパクトを評価する専門家です。

以下のエピソードを5つの観点から評価してください：

【エピソード】
人物名: {person_name}
年齢: {age}歳
内容: {episode_text}

【評価基準】

1. 人生の転換点スコア（0-10点）
   - 10点: 人生を賭けた決断（辞職、引退、全財産投資、逮捕、ノーベル賞等）
   - 7点: 重要な決断（起業、創業、受賞、MVP、海外進出、連覇等）
   - 4点: 重要だが予想可能（新事業、挑戦開始）
   - 0点: 日常業務の延長

2. 意外性スコア（0-10点）
   - 10点: 常識を覆す（ガレージ創業、エリート転身、匿名成功、顔非公開等）
   - 7点: 前例のない挑戦（史上初、最年少、日本人初、〜ぶり等）
   - 4点: 業界標準を超える（業界初、国内初）
   - 0点: 当然の結果（順当、予想通り）

3. リスクテイキングスコア（0-10点）
   - 10点: 全てを失うリスク（年収捨てる、全財産、無一文、借金）
   - 7点: 大きなリスク（安定捨てる、退職、中退）
   - 4点: 計算されたリスク（新分野挑戦）
   - 0点: リスクなし（既存事業、安全路線）

4. 共感性スコア（0-10点）
   - 10点: 誰もが経験する葛藤（安定vs夢、失敗の恐怖、周囲の反対）
   - 7点: 一部が経験する選択（キャリア、人生の岐路、決断、感動、涙）
   - 4点: 特定の人が経験（仕事の挑戦、魅了）
   - 0点: 一般人に無関係（大企業戦略、M&A）

5. センセーショナル度（0-10点）
   - 10点: 映画のような展開（ガレージ→世界企業、伝説、奇跡、ノーベル賞、紅白、世界初等）
   - 7点: 劇的な展開（革命、衝撃、芥川賞、MVP、金メダル、連覇、偉業等）
   - 4点: 興味深い（注目、話題、人気）
   - 0点: ニュース価値なし（通常、標準的）

【出力形式】
以下のJSON形式で出力してください：

{{
  "turning_point": <0-10の整数>,
  "surprise": <0-10の整数>,
  "risk_taking": <0-10の整数>,
  "relatability": <0-10の整数>,
  "sensational": <0-10の整数>,
  "reasoning": "<各スコアの理由を簡潔に説明（200文字以内）>"
}}

重要: JSON形式のみを出力し、余計な説明は含めないでください。
"""

    def _call_openai(self, prompt: str) -> str:
        """OpenAI APIを呼び出し"""
        try:
            import openai
        except ImportError:
            raise ImportError("openaiパッケージがインストールされていません: pip install openai")

        client = openai.OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは厳格で客観的なエピソード評価者です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 一貫性重視
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API呼び出しエラー: {e}")

    def _call_anthropic(self, prompt: str) -> str:
        """Anthropic APIを呼び出し"""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropicパッケージがインストールされていません: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API呼び出しエラー: {e}")

    def _parse_response(self, response: str) -> LLMImpactScore:
        """LLMレスポンスをパースしてスコアに変換"""
        try:
            data = json.loads(response)

            turning_point = int(data.get("turning_point", 0))
            surprise = int(data.get("surprise", 0))
            risk_taking = int(data.get("risk_taking", 0))
            relatability = int(data.get("relatability", 0))
            sensational = int(data.get("sensational", 0))
            reasoning = data.get("reasoning", "")

            # スコアの範囲チェック
            turning_point = max(0, min(10, turning_point))
            surprise = max(0, min(10, surprise))
            risk_taking = max(0, min(10, risk_taking))
            relatability = max(0, min(10, relatability))
            sensational = max(0, min(10, sensational))

            total = turning_point + surprise + risk_taking + relatability + sensational
            passed = total >= self.min_passing_score

            return LLMImpactScore(
                turning_point=turning_point,
                surprise=surprise,
                risk_taking=risk_taking,
                relatability=relatability,
                sensational=sensational,
                total=total,
                passed=passed,
                reasoning=reasoning
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # パースエラー時はデフォルト値を返す
            print(f"⚠️ レスポンスのパースに失敗: {e}")
            print(f"レスポンス: {response[:200]}...")
            return LLMImpactScore(
                turning_point=0,
                surprise=0,
                risk_taking=0,
                relatability=0,
                sensational=0,
                total=0,
                passed=False,
                reasoning="評価エラー: レスポンスのパースに失敗しました"
            )

    def get_impact_report(self, score: LLMImpactScore, person_name: str, age: int) -> str:
        """
        インパクト評価レポートを生成

        Args:
            score: LLMインパクトスコア
            person_name: 人物名
            age: 年齢

        Returns:
            str: レポート文字列
        """
        status = "✅ 合格" if score.passed else "❌ 不合格"
        percentage = (score.total / 50) * 100

        report = f"""
LLMベース感情的インパクト評価: {status}

人物: {person_name}（{age}歳）
総合スコア: {score.total}/50点（{percentage:.0f}%）

詳細スコア:
  1. 人生の転換点: {score.turning_point}/10点 {"★" * score.turning_point}
  2. 意外性: {score.surprise}/10点 {"★" * score.surprise}
  3. リスクテイキング: {score.risk_taking}/10点 {"★" * score.risk_taking}
  4. 共感性: {score.relatability}/10点 {"★" * score.relatability}
  5. センセーショナル度: {score.sensational}/10点 {"★" * score.sensational}

判定理由:
{score.reasoning}

合格基準: 30点以上（60%）
結果: {"✅ 合格" if score.passed else f"❌ 不合格（あと{30 - score.total}点必要）"}

使用モデル: {self.provider} / {self.model}
"""
        return report


def test_llm_impact_evaluator():
    """LLMインパクト評価器のテスト"""

    # 環境変数チェック
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ OPENAI_API_KEYまたはANTHROPIC_API_KEY環境変数が設定されていません")
        return

    # プロバイダー選択
    provider = "openai" if os.getenv("OPENAI_API_KEY") else "anthropic"
    print(f"使用プロバイダー: {provider}")
    print("=" * 80)

    evaluator = LLMImpactEvaluator(provider=provider)

    # テストケース1: Ado（高インパクト）
    print("テストケース1: Ado - 紅白出場・Billboard1位（21歳）")
    print("=" * 80)

    ado_episode = """あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。YouTubeでの楽曲は若者を中心に広範な支持を集め、新時代の音楽シーンを象徴する存在となった。"""

    score = evaluator.evaluate(ado_episode, "Ado", 21)
    print(evaluator.get_impact_report(score, "Ado", 21))

    # レート制限対策
    time.sleep(2)

    # テストケース2: スティーブ・ジョブズ（中インパクト）
    print("\n" + "=" * 80)
    print("テストケース2: スティーブ・ジョブズ - iPhone発表（52歳）")
    print("=" * 80)

    jobs_episode = """あなたと同じ52歳のとき、スティーブ・ジョブズはMacworld2007でiPhoneを発表し、携帯電話を再定義した。タッチスクリーン技術により年間10億台超のスマートフォン市場を創出し、アップルの時価総額を40億ドルから3500億ドルへと875倍に成長させた。"""

    score = evaluator.evaluate(jobs_episode, "スティーブ・ジョブズ", 52)
    print(evaluator.get_impact_report(score, "スティーブ・ジョブズ", 52))

    # レート制限対策
    time.sleep(2)

    # テストケース3: 川端康成（低インパクト - キーワードベースで0点）
    print("\n" + "=" * 80)
    print("テストケース3: 川端康成 - 伊豆の踊子（27歳）")
    print("=" * 80)

    kawabata_episode = """あなたと同じ27歳のとき、川端康成は『伊豆の踊子』発表、青春文学の金字塔この作品は時代を超えて読み継がれ、多くの読者の心に深い感動を与え続けている。数多くの名作を世に送り出した。作品は世代を超えて愛され、日本文学の宝となっている。日本の美を世界に伝える架け橋となった。"""

    score = evaluator.evaluate(kawabata_episode, "川端康成", 27)
    print(evaluator.get_impact_report(score, "川端康成", 27))


if __name__ == '__main__':
    test_llm_impact_evaluator()
