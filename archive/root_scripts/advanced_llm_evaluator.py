#!/usr/bin/env python3
"""
次世代LLM評価システム - Chain-of-Thought評価

特徴:
1. 段階的推論による透明性の向上
2. 4つのPhaseによる多段階評価（100点満点）
3. 詳細なフィードバックと改善提案
4. OpenAI/Anthropic両対応
5. Phase 7.3 Week 4, Day 2: LLMレスポンスキャッシング統合
"""

import os
import json
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import time

# Phase 7.3 Week 4, Day 2: LLMレスポンスキャッシング統合
from scripts.llm_response_cache import LLMResponseCache, CachedLLMClient


@dataclass
class ThinkingStep:
    """推論ステップ"""
    step_number: int
    step_name: str
    thinking: str
    score: Optional[int] = None


@dataclass
class PhaseScore:
    """Phase別スコア"""
    phase_name: str
    max_score: int
    actual_score: int
    reasoning: str
    breakdown: Dict[str, int]


@dataclass
class ImprovementSuggestion:
    """改善提案"""
    category: str
    current_score: int
    target_score: int
    gap: int
    suggestion: str
    example: str


@dataclass
class AdvancedEvaluationResult:
    """高度な評価結果"""
    # 基本情報
    person_name: str
    age: int
    episode_text: str

    # 推論プロセス
    thinking_steps: List[ThinkingStep]

    # Phase別評価
    phase1_structure: PhaseScore  # 構造分析（0-20点）
    phase2_impact: PhaseScore     # インパクト分析（0-30点）
    phase3_storytelling: PhaseScore  # ストーリーテリング（0-25点）
    phase4_uniqueness: PhaseScore    # 独自性（0-25点）

    # 総合評価
    total_score: int
    percentage: float
    passed: bool
    grade: str  # S(90+), A(80-89), B(70-79), C(60-69), D(<60)

    # 改善提案
    improvements: List[ImprovementSuggestion]

    # メタ情報
    model_used: str
    evaluation_time: float


class AdvancedLLMEvaluator:
    """次世代LLM評価システム"""

    def __init__(self, provider: str = "openai", model: Optional[str] = None, enable_cache: bool = True):
        """
        Args:
            provider: "openai" or "anthropic"
            model: モデル名（Noneの場合はデフォルト）
            enable_cache: キャッシュの有効化（Phase 7.3 Week 4, Day 2）
        """
        self.provider = provider.lower()
        self.min_passing_score = 60

        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.model = model or "gpt-4o-mini"
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model = model or "claude-3-5-sonnet-20241022"
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")
        else:
            raise ValueError(f"未対応のプロバイダー: {provider}")

        # Phase 7.3 Week 4, Day 2: LLMレスポンスキャッシング初期化
        self.enable_cache = enable_cache
        if enable_cache:
            self.llm_cache = LLMResponseCache(
                cache_dir="cache/llm_responses",
                default_ttl=86400,  # 24時間
                max_memory_entries=1000,
                enable_disk_cache=True
            )
            self.cached_client = CachedLLMClient(
                cache=self.llm_cache,
                provider=self.provider,
                model=self.model
            )
        else:
            self.llm_cache = None
            self.cached_client = None

    async def evaluate_async(self, episode_text: str, person_name: str, age: int) -> AdvancedEvaluationResult:
        """
        Chain-of-Thought評価を実施（非同期版、Phase 7.3 Week 4, Day 2: キャッシング対応）

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            AdvancedEvaluationResult: 高度な評価結果
        """
        start_time = time.time()

        # プロンプト作成
        prompt = self._create_cot_prompt(episode_text, person_name, age)

        # API呼び出し（キャッシュ対応）
        if self.enable_cache and self.cached_client:
            # Phase 7.3 Week 4, Day 2: キャッシュ統合
            # プロンプトは決定的（episode_text, person_name, age のみ使用）
            async def llm_call():
                if self.provider == "openai":
                    return await self._call_openai_async(prompt)
                else:
                    return await self._call_anthropic_async(prompt)

            response, was_cached = await self.cached_client.call_llm_with_cache(
                person_name=person_name,
                age=age,
                prompt=prompt,
                llm_function=llm_call
            )
        else:
            # キャッシュ無効時は直接API呼び出し
            if self.provider == "openai":
                response = await self._call_openai_async(prompt)
            else:
                response = await self._call_anthropic_async(prompt)

        # レスポンスをパース
        result = self._parse_cot_response(response, episode_text, person_name, age)

        # 評価時間を記録
        result.evaluation_time = time.time() - start_time
        result.model_used = f"{self.provider}/{self.model}"

        return result

    def evaluate(self, episode_text: str, person_name: str, age: int) -> AdvancedEvaluationResult:
        """
        Chain-of-Thought評価を実施（同期版、後方互換性のため維持）

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            AdvancedEvaluationResult: 高度な評価結果
        """
        return asyncio.run(self.evaluate_async(episode_text, person_name, age))

    def _create_cot_prompt(self, episode_text: str, person_name: str, age: int) -> str:
        """Chain-of-Thought評価用プロンプトを生成"""
        return f"""あなたは年齢比較コンテンツのエピソード評価専門家です。
以下のエピソードを段階的に分析し、100点満点で評価してください。

【エピソード】
人物名: {person_name}
年齢: {age}歳
内容: {episode_text}

【評価プロセス】

## ステップ1: エピソードの要約
このエピソードを50文字以内で要約してください。

## ステップ2: 主要な転換点の特定
このエピソードで最も重要な人生の転換点は何ですか？

## ステップ3: Phase別評価

### Phase 1: 構造分析（0-20点）
以下の3項目を評価：
- 文章構造の完全性（0-7点）: 起承転結が明確か？
- 年齢時点の明確性（0-7点）: 「XX歳のとき」の記述が70%以上か？
- 事実の検証可能性（0-6点）: 具体的な年、数値、名称があるか？

### Phase 2: インパクト分析（0-30点）
以下の3項目を評価：
- 感情的インパクト（0-10点）: 読者の感情を動かすか？
- 社会的インパクト（0-10点）: 社会や業界への影響は？
- 個人的インパクト（0-10点）: 本人のキャリアへの影響は？

### Phase 3: ストーリーテリング（0-25点）
以下の3項目を評価：
- 起承転結の完成度（0-10点）: ストーリーとして完結しているか？
- 具体性と数値の使用（0-8点）: 具体的な数値やデータがあるか？
- 読者の共感性（0-7点）: 読者が感情移入できるか？

### Phase 4: 独自性（0-25点）
以下の3項目を評価：
- 意外性・新規性（0-10点）: 予想外の展開や前例のない挑戦か？
- 差別化要素（0-8点）: 他の人物との違いは明確か？
- 記憶に残る要素（0-7点）: 印象的なキーワードや表現があるか？

## ステップ4: 総合判定
- 合計点数（0-100点）
- グレード判定: S(90+), A(80-89), B(70-79), C(60-69), D(<60)
- 合否判定: 60点以上で合格

## ステップ5: 改善提案
スコアが60点未満の場合、最も改善効果の高い3つの提案を具体例付きで提示してください。

【出力形式】
以下のJSON形式で出力してください：

{{
  "thinking_steps": [
    {{
      "step_number": 1,
      "step_name": "エピソードの要約",
      "thinking": "<要約内容>"
    }},
    {{
      "step_number": 2,
      "step_name": "主要な転換点",
      "thinking": "<転換点の説明>"
    }}
  ],
  "phase1_structure": {{
    "phase_name": "構造分析",
    "max_score": 20,
    "actual_score": <0-20>,
    "reasoning": "<判定理由>",
    "breakdown": {{
      "文章構造": <0-7>,
      "年齢時点明確性": <0-7>,
      "検証可能性": <0-6>
    }}
  }},
  "phase2_impact": {{
    "phase_name": "インパクト分析",
    "max_score": 30,
    "actual_score": <0-30>,
    "reasoning": "<判定理由>",
    "breakdown": {{
      "感情的インパクト": <0-10>,
      "社会的インパクト": <0-10>,
      "個人的インパクト": <0-10>
    }}
  }},
  "phase3_storytelling": {{
    "phase_name": "ストーリーテリング",
    "max_score": 25,
    "actual_score": <0-25>,
    "reasoning": "<判定理由>",
    "breakdown": {{
      "起承転結": <0-10>,
      "具体性": <0-8>,
      "共感性": <0-7>
    }}
  }},
  "phase4_uniqueness": {{
    "phase_name": "独自性",
    "max_score": 25,
    "actual_score": <0-25>,
    "reasoning": "<判定理由>",
    "breakdown": {{
      "意外性": <0-10>,
      "差別化": <0-8>,
      "記憶性": <0-7>
    }}
  }},
  "total_score": <0-100>,
  "grade": "<S|A|B|C|D>",
  "improvements": [
    {{
      "category": "<改善カテゴリー>",
      "current_score": <現在のスコア>,
      "target_score": <目標スコア>,
      "gap": <差分>,
      "suggestion": "<改善提案>",
      "example": "<具体例>"
    }}
  ]
}}

重要:
- JSON形式のみを出力し、余計な説明は含めないでください
- すべてのスコアは整数で出力してください
- 改善提案は最大3つまでとしてください
"""

    async def _call_openai_async(self, prompt: str) -> str:
        """OpenAI APIを呼び出し（非同期版、Phase 7.3 Week 4, Day 2）"""
        try:
            import openai
        except ImportError:
            raise ImportError("openaiパッケージがインストールされていません: pip install openai")

        client = openai.AsyncOpenAI(api_key=self.api_key)

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは段階的推論を得意とする、厳格で客観的なエピソード評価者です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API呼び出しエラー: {e}")

    def _call_openai(self, prompt: str) -> str:
        """OpenAI APIを呼び出し（同期版、後方互換性のため維持）"""
        return asyncio.run(self._call_openai_async(prompt))

    async def _call_anthropic_async(self, prompt: str) -> str:
        """Anthropic APIを呼び出し（非同期版、Phase 7.3 Week 4, Day 2）"""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropicパッケージがインストールされていません: pip install anthropic")

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        try:
            message = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API呼び出しエラー: {e}")

    def _call_anthropic(self, prompt: str) -> str:
        """Anthropic APIを呼び出し（同期版、後方互換性のため維持）"""
        return asyncio.run(self._call_anthropic_async(prompt))

    def _parse_cot_response(
        self,
        response: str,
        episode_text: str,
        person_name: str,
        age: int
    ) -> AdvancedEvaluationResult:
        """Chain-of-Thoughtレスポンスをパース"""
        try:
            data = json.loads(response)

            # 推論ステップのパース
            thinking_steps = []
            for step in data.get("thinking_steps", []):
                thinking_steps.append(ThinkingStep(
                    step_number=step.get("step_number", 0),
                    step_name=step.get("step_name", ""),
                    thinking=step.get("thinking", "")
                ))

            # Phase別スコアのパース
            phase1 = self._parse_phase_score(data.get("phase1_structure", {}))
            phase2 = self._parse_phase_score(data.get("phase2_impact", {}))
            phase3 = self._parse_phase_score(data.get("phase3_storytelling", {}))
            phase4 = self._parse_phase_score(data.get("phase4_uniqueness", {}))

            # 総合スコア
            total_score = int(data.get("total_score", 0))
            percentage = (total_score / 100) * 100
            passed = total_score >= self.min_passing_score
            grade = data.get("grade", "D")

            # 改善提案のパース
            improvements = []
            for imp in data.get("improvements", []):
                improvements.append(ImprovementSuggestion(
                    category=imp.get("category", ""),
                    current_score=int(imp.get("current_score", 0)),
                    target_score=int(imp.get("target_score", 0)),
                    gap=int(imp.get("gap", 0)),
                    suggestion=imp.get("suggestion", ""),
                    example=imp.get("example", "")
                ))

            return AdvancedEvaluationResult(
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                thinking_steps=thinking_steps,
                phase1_structure=phase1,
                phase2_impact=phase2,
                phase3_storytelling=phase3,
                phase4_uniqueness=phase4,
                total_score=total_score,
                percentage=percentage,
                passed=passed,
                grade=grade,
                improvements=improvements,
                model_used="",
                evaluation_time=0.0
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️ レスポンスのパースに失敗: {e}")
            print(f"レスポンス: {response[:500]}...")

            # デフォルト値を返す
            return AdvancedEvaluationResult(
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                thinking_steps=[],
                phase1_structure=PhaseScore("構造分析", 20, 0, "パースエラー", {}),
                phase2_impact=PhaseScore("インパクト分析", 30, 0, "パースエラー", {}),
                phase3_storytelling=PhaseScore("ストーリーテリング", 25, 0, "パースエラー", {}),
                phase4_uniqueness=PhaseScore("独自性", 25, 0, "パースエラー", {}),
                total_score=0,
                percentage=0.0,
                passed=False,
                grade="D",
                improvements=[],
                model_used="",
                evaluation_time=0.0
            )

    def _parse_phase_score(self, phase_data: Dict) -> PhaseScore:
        """Phase別スコアデータをパース"""
        return PhaseScore(
            phase_name=phase_data.get("phase_name", ""),
            max_score=int(phase_data.get("max_score", 0)),
            actual_score=int(phase_data.get("actual_score", 0)),
            reasoning=phase_data.get("reasoning", ""),
            breakdown=phase_data.get("breakdown", {})
        )

    def get_detailed_report(self, result: AdvancedEvaluationResult) -> str:
        """
        詳細な評価レポートを生成

        Args:
            result: 評価結果

        Returns:
            str: レポート文字列
        """
        status = "✅ 合格" if result.passed else "❌ 不合格"

        report = f"""
{'='*80}
次世代LLM評価レポート: {status}
{'='*80}

【基本情報】
人物: {result.person_name}（{result.age}歳）
総合スコア: {result.total_score}/100点（{result.percentage:.0f}%）
グレード: {result.grade}
評価時間: {result.evaluation_time:.2f}秒
使用モデル: {result.model_used}

{'='*80}
【推論プロセス】
{'='*80}
"""

        for step in result.thinking_steps:
            report += f"\n{step.step_number}. {step.step_name}\n"
            report += f"   {step.thinking}\n"

        report += f"""
{'='*80}
【Phase別評価】
{'='*80}

Phase 1: {result.phase1_structure.phase_name} ({result.phase1_structure.actual_score}/{result.phase1_structure.max_score}点)
理由: {result.phase1_structure.reasoning}
内訳: {result.phase1_structure.breakdown}

Phase 2: {result.phase2_impact.phase_name} ({result.phase2_impact.actual_score}/{result.phase2_impact.max_score}点)
理由: {result.phase2_impact.reasoning}
内訳: {result.phase2_impact.breakdown}

Phase 3: {result.phase3_storytelling.phase_name} ({result.phase3_storytelling.actual_score}/{result.phase3_storytelling.max_score}点)
理由: {result.phase3_storytelling.reasoning}
内訳: {result.phase3_storytelling.breakdown}

Phase 4: {result.phase4_uniqueness.phase_name} ({result.phase4_uniqueness.actual_score}/{result.phase4_uniqueness.max_score}点)
理由: {result.phase4_uniqueness.reasoning}
内訳: {result.phase4_uniqueness.breakdown}

{'='*80}
【総合判定】
{'='*80}
総合スコア: {result.total_score}/100点
グレード: {result.grade}
合否: {"✅ 合格" if result.passed else f"❌ 不合格（あと{60 - result.total_score}点必要）"}
"""

        if result.improvements:
            report += f"""
{'='*80}
【改善提案】
{'='*80}
"""
            for i, imp in enumerate(result.improvements, 1):
                report += f"""
{i}. {imp.category}
   現在: {imp.current_score}点 → 目標: {imp.target_score}点（+{imp.gap}点）
   提案: {imp.suggestion}
   例: {imp.example}
"""

        return report

    def export_to_json(self, result: AdvancedEvaluationResult, filepath: str):
        """
        評価結果をJSONファイルにエクスポート

        Args:
            result: 評価結果
            filepath: 出力ファイルパス
        """
        # dataclassをdictに変換
        data = {
            "person_name": result.person_name,
            "age": result.age,
            "episode_text": result.episode_text,
            "thinking_steps": [asdict(step) for step in result.thinking_steps],
            "phase1_structure": asdict(result.phase1_structure),
            "phase2_impact": asdict(result.phase2_impact),
            "phase3_storytelling": asdict(result.phase3_storytelling),
            "phase4_uniqueness": asdict(result.phase4_uniqueness),
            "total_score": result.total_score,
            "percentage": result.percentage,
            "passed": result.passed,
            "grade": result.grade,
            "improvements": [asdict(imp) for imp in result.improvements],
            "model_used": result.model_used,
            "evaluation_time": result.evaluation_time
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def test_advanced_evaluator():
    """次世代LLM評価器のテスト"""

    # 環境変数チェック
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ OPENAI_API_KEYまたはANTHROPIC_API_KEY環境変数が設定されていません")
        return

    # プロバイダー選択
    provider = "openai" if os.getenv("OPENAI_API_KEY") else "anthropic"
    print(f"使用プロバイダー: {provider}")
    print("="*80)

    evaluator = AdvancedLLMEvaluator(provider=provider)

    # テストケース: 新垣結衣（28点のボーダーライン）
    print("テストケース: 新垣結衣 - ポッキーCM（18歳）")
    print("="*80)

    aragaki_episode = """あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、芸能界でのブレイクを果たした。沖縄から上京してわずか3年、無名の新人モデルだった彼女は「本当にこの子で大丈夫？」という制作側の不安の中、笑顔とダンスで日本中を魅了した。CM放送後、ネット上で「ガッキー」の愛称が広まり、検索数が急上昇。この年7回のCM出演契約が決定し、翌年には映画『恋空』で興行収入39億円を記録する大女優への階段を駆け上がった。"""

    result = evaluator.evaluate(aragaki_episode, "新垣結衣", 18)

    # 詳細レポート表示
    print(evaluator.get_detailed_report(result))

    # JSON出力
    evaluator.export_to_json(result, "test_aragaki_advanced_evaluation.json")
    print(f"\n✅ 評価結果をtest_aragaki_advanced_evaluation.jsonに保存しました")


if __name__ == '__main__':
    test_advanced_evaluator()
