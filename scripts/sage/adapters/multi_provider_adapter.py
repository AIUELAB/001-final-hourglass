"""
Multi-Provider Adapter

Phase 5: Claude/OpenAI/Gemini を切り替え可能なアダプター。
"""

import json
import re
from typing import Optional

from .base import (
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
    TokenUsage,
)
from .providers import (
    LLMClient,
    ProviderConfig,
    ProviderType,
    create_client,
    get_available_providers,
)


# プロンプトテンプレート
GENERATION_SYSTEM_PROMPT = """あなたは伝記エピソード生成の専門家です。
与えられた人物の特定年齢時点での重要なエピソードを、具体的な事実に基づいて生成してください。

【必須要素】
- 西暦年号を2つ以上含める
- 固有名詞（人名、作品名、組織名、地名）を5つ以上含める
- 「」で囲んだ作品名・イベント名を2つ以上含める
- 数値データを3つ以上含める

【禁止事項】
- 抽象的な表現や推測・伝聞
- メタ的な表現（「このエピソード」「読者」等）
- 「ある日」「いつか」等の曖昧な時間表現
- 「と言われている」「かもしれない」等の不確実な表現

【形式】
- 200〜500文字
- 「あなたと同じX歳のとき、」で始める
- 具体的な達成や転機を中心に記述"""

GENERATION_USER_PROMPT = """以下の人物のエピソードを生成してください。

人物名: {person_name}
年齢: {age}歳
カテゴリ: {category}
人物タイプ: {person_type}

「あなたと同じ{age}歳のとき、{person_name}は」で始めてください。"""

EVALUATION_SYSTEM_PROMPT = """あなたはエピソード品質評価の専門家です。
与えられたエピソードを7つの軸で0-10のスコアで評価してください。

【評価軸】
1. 記憶性 (memorability): 印象に残りやすさ
2. 共感性 (empathy): 感情的な共感を呼ぶか
3. 意外性 (surprise): 予想外の発見があるか
4. 生成品質 (generation_quality): 文章の質、流れ
5. 教育的価値 (educational_value): 学びがあるか
6. ストーリー品質 (story_quality): 物語としての完成度
7. 事実密度 (factual_density): 具体的事実の密度

【出力形式】
必ず以下のJSON形式で出力してください：
{
    "memorability": 7.5,
    "empathy": 6.0,
    "surprise": 8.0,
    "generation_quality": 7.0,
    "educational_value": 6.5,
    "story_quality": 7.0,
    "factual_density": 8.5,
    "reasoning": "評価の理由を簡潔に"
}"""

EVALUATION_USER_PROMPT = """以下のエピソードを評価してください。

人物名: {person_name}
年齢: {age}歳

エピソード:
{episode_text}"""


class MultiProviderAdapter(GeneratorAdapter):
    """
    マルチプロバイダアダプター

    Claude/OpenAI/Gemini を切り替えて使用可能。
    """

    def __init__(
        self,
        provider_type: ProviderType = ProviderType.ANTHROPIC,
        generation_config: Optional[ProviderConfig] = None,
        evaluation_config: Optional[ProviderConfig] = None,
    ):
        """
        Args:
            provider_type: 使用するプロバイダ
            generation_config: 生成用設定（オプション）
            evaluation_config: 評価用設定（オプション）
        """
        super().__init__(f"multi_{provider_type.value}", GeneratorType.EPGEN)
        self.provider_type = provider_type
        self._generation_client: Optional[LLMClient] = None
        self._evaluation_client: Optional[LLMClient] = None
        self._generation_config = generation_config
        self._evaluation_config = evaluation_config

    def _get_generation_client(self) -> LLMClient:
        """生成用クライアント取得（遅延初期化）"""
        if self._generation_client is None:
            self._generation_client = create_client(self.provider_type, self._generation_config)
        return self._generation_client

    def _get_evaluation_client(self) -> LLMClient:
        """評価用クライアント取得（遅延初期化）"""
        if self._evaluation_client is None:
            self._evaluation_client = create_client(self.provider_type, self._evaluation_config)
        return self._evaluation_client

    def generate(self, candidate: Candidate) -> GenerationResult:
        """
        エピソード生成

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        try:
            client = self._get_generation_client()

            # プロンプト構築
            user_prompt = GENERATION_USER_PROMPT.format(
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
                person_type=candidate.person_type,
            )

            # 生成実行
            text, usage = client.generate(user_prompt, GENERATION_SYSTEM_PROMPT)

            if not text or len(text) < 100:
                return GenerationResult(
                    success=False,
                    candidate=candidate,
                    error_message="Generated text too short",
                    generator_type=self.generator_type,
                )

            # トークン使用量を記録
            token_usage = TokenUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                model=client.config.model_name,
            )
            self.record_token_usage(token_usage)

            # 評価実行
            evaluation = self.evaluate(text, candidate)

            return GenerationResult(
                success=True,
                candidate=candidate,
                episode_text=text,
                episode_type="ACHIEVEMENT",
                char_count=len(text),
                evaluation=evaluation,
                generator_type=self.generator_type,
                evidence=self._extract_evidence(text),
                token_usage=token_usage,
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                candidate=candidate,
                error_message=str(e),
                generator_type=self.generator_type,
            )

    def evaluate(self, text: str, candidate: Candidate) -> EvaluationResult:
        """
        エピソード評価

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            client = self._get_evaluation_client()

            # プロンプト構築
            user_prompt = EVALUATION_USER_PROMPT.format(
                person_name=candidate.person_name,
                age=candidate.age,
                episode_text=text,
            )

            # 評価実行
            response, usage = client.generate(user_prompt, EVALUATION_SYSTEM_PROMPT)

            # JSONパース
            scores_dict = self._parse_evaluation_response(response)

            # トークン使用量を記録
            eval_token_usage = TokenUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                model=client.config.model_name,
            )
            self.record_token_usage(eval_token_usage)

            axis_scores = AxisScores(
                memorability=scores_dict.get("memorability", 5.0),
                empathy=scores_dict.get("empathy", 5.0),
                surprise=scores_dict.get("surprise", 5.0),
                generation_quality=scores_dict.get("generation_quality", 5.0),
                educational_value=scores_dict.get("educational_value", 5.0),
                story_quality=scores_dict.get("story_quality", 5.0),
                factual_density=scores_dict.get("factual_density", 5.0),
            )

            # 統合スコア計算
            composite_score = axis_scores.weighted_average() * 100

            # 品質ゲートチェック
            gate_failures = []
            if axis_scores.factual_density < 7.0:
                gate_failures.append("factual_density < 7.0")
            if axis_scores.generation_quality < 8.0:
                gate_failures.append("generation_quality < 8.0")
            if axis_scores.memorability < 5.5:
                gate_failures.append("memorability < 5.5")

            return EvaluationResult(
                axis_scores=axis_scores,
                composite_score=composite_score,
                super_total_score=0.0,  # 後で計算
                passed_gate=len(gate_failures) == 0,
                gate_failures=gate_failures,
            )

        except Exception as e:
            return EvaluationResult(
                axis_scores=AxisScores(),
                composite_score=0.0,
                super_total_score=0.0,
                passed_gate=False,
                gate_failures=[f"Evaluation error: {str(e)}"],
            )

    def improve(self, result: GenerationResult, feedback: str) -> Optional[GenerationResult]:
        """
        エピソード改善

        Args:
            result: 元の生成結果
            feedback: 改善フィードバック

        Returns:
            GenerationResult: 改善された生成結果
        """
        # 単純に再生成
        return self.generate(result.candidate)

    def _parse_evaluation_response(self, response: str) -> dict:
        """評価レスポンスをパース"""
        # JSON部分を抽出
        json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # フォールバック: 正規表現で数値抽出
        scores = {}
        patterns = [
            (r"memorability[\"'\s:]+(\d+\.?\d*)", "memorability"),
            (r"empathy[\"'\s:]+(\d+\.?\d*)", "empathy"),
            (r"surprise[\"'\s:]+(\d+\.?\d*)", "surprise"),
            (r"generation_quality[\"'\s:]+(\d+\.?\d*)", "generation_quality"),
            (r"educational_value[\"'\s:]+(\d+\.?\d*)", "educational_value"),
            (r"story_quality[\"'\s:]+(\d+\.?\d*)", "story_quality"),
            (r"factual_density[\"'\s:]+(\d+\.?\d*)", "factual_density"),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))

        return scores

    def _extract_evidence(self, text: str) -> list[str]:
        """テキストから根拠を抽出"""
        evidence = []

        # 年号抽出
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text)
        for year in years[:3]:
            evidence.append(f"{year}年")

        # 「」内の固有名詞
        quoted = re.findall(r"「([^」]+)」", text)
        for q in quoted[:3]:
            evidence.append(f"「{q}」")

        # 数値データ
        numbers = re.findall(r"\d+[万億%位回番]", text)
        for n in numbers[:3]:
            evidence.append(n)

        return evidence


class AutoProviderAdapter(MultiProviderAdapter):
    """
    自動プロバイダ選択アダプター

    利用可能なプロバイダから自動的に選択。
    """

    def __init__(self, prefer_cheapest: bool = True):
        """
        Args:
            prefer_cheapest: True の場合、最安プロバイダを優先
        """
        available = get_available_providers()
        if not available:
            raise ValueError(
                "No LLM provider available. " "Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY"
            )

        # プロバイダ選択
        if prefer_cheapest:
            from .providers import get_cheapest_provider

            provider = get_cheapest_provider() or available[0]
        else:
            # Anthropic優先
            if ProviderType.ANTHROPIC in available:
                provider = ProviderType.ANTHROPIC
            elif ProviderType.OPENAI in available:
                provider = ProviderType.OPENAI
            else:
                provider = available[0]

        super().__init__(provider_type=provider)
        self.name = f"auto_{provider.value}"
