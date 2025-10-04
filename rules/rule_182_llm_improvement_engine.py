#!/usr/bin/env python3
"""
RULE_182: LLM改善エンジン（LLM Improvement Engine）

RULE_180のパターンマッチング型改善を、LLMによる文脈理解型改善で補完
- 複雑な時系列矛盾の修正
- 文脈を考慮した抽象表現の具体化
- より自然な文章への改善
- 事実に基づく改善提案

LLMプロバイダー:
- OpenAI GPT-4
- Anthropic Claude-3.5-Sonnet

改善フロー:
1. 問題分析（LLMによる詳細分析）
2. 改善生成（文脈を考慮した改善案作成）
3. 品質検証（改善結果の自動検証）
4. フォールバック（失敗時はRULE_180を使用）
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import os
import logging
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class LLMImprovementResult:
    """LLM改善結果"""
    improved_text: str
    analysis: str
    improvements_applied: List[str]
    validation_score: float  # 0-10
    intent_preservation: float  # 0-10
    fluency_score: float  # 0-10
    factual_accuracy: float  # 0-10
    llm_tokens_used: int
    processing_time: float


class LLMProvider(ABC):
    """LLMプロバイダーの抽象基底クラス"""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """
        テキスト生成

        Args:
            prompt: プロンプト
            max_tokens: 最大トークン数
            temperature: 温度パラメータ（0-1）

        Returns:
            生成されたテキスト
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を取得"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4プロバイダー"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        初期化

        Args:
            api_key: OpenAI APIキー（Noneの場合は環境変数から取得）
            model: モデル名
        """
        try:
            from openai import OpenAI
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found")
            self.client = OpenAI(api_key=self.api_key)
            self.model = model
            logger.info(f"✅ OpenAI {model} 初期化成功")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"❌ OpenAI初期化失敗: {e}")
            raise

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """テキスト生成"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ OpenAI生成失敗: {e}")
            raise

    def get_provider_name(self) -> str:
        return f"OpenAI-{self.model}"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude-3.5-Sonnetプロバイダー"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        初期化

        Args:
            api_key: Anthropic APIキー（Noneの場合は環境変数から取得）
            model: モデル名
        """
        try:
            from anthropic import Anthropic
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found")
            self.client = Anthropic(api_key=self.api_key)
            self.model = model
            logger.info(f"✅ Anthropic {model} 初期化成功")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            logger.error(f"❌ Anthropic初期化失敗: {e}")
            raise

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """テキスト生成"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"❌ Anthropic生成失敗: {e}")
            raise

    def get_provider_name(self) -> str:
        return f"Anthropic-{self.model}"


class MockLLMProvider(LLMProvider):
    """テスト用モックプロバイダー"""

    def __init__(self):
        logger.info("✅ MockLLMProvider 初期化（テストモード）")

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """モック生成（プロンプトに基づく簡易応答）"""
        if "問題分析" in prompt or "分析" in prompt:
            return json.dumps({
                "issues": [
                    {
                        "location": "多くの",
                        "type": "抽象表現",
                        "severity": "WARNING",
                        "suggestion": "具体的な数値に置き換え"
                    }
                ]
            }, ensure_ascii=False)
        elif "改善" in prompt:
            # 元のテキストから抽象表現を削除した簡易版を返す
            return "あなたと同じ28歳のとき、大谷翔平はMLBでMVPを受賞した。投打二刀流として46本塁打、156奪三振を記録。"
        elif "検証" in prompt or "評価" in prompt:
            return json.dumps({
                "problems_solved": True,
                "intent_preservation": 9.0,
                "fluency": 9.5,
                "factual_accuracy": 10.0,
                "overall_score": 9.5
            }, ensure_ascii=False)
        else:
            return "Mock response"

    def get_provider_name(self) -> str:
        return "Mock-LLM"


class LLMImprovementEngine:
    """
    LLM改善エンジン

    LLMを使用してエピソードを文脈理解に基づいて改善
    """

    # Few-Shot Examples（良い改善例）
    FEW_SHOT_EXAMPLES = """
以下は良い改善例です:

例1:
元: "素晴らしい業績を残した"
改善: "ノーベル物理学賞を受賞した"
理由: 抽象表現を具体的な事実に置き換え

例2:
元: "多くの人々に影響を与えた"
改善: "累計視聴者数1億人を超えるYouTuberとして活躍した"
理由: 具体的な数値と職業を明記

例3:
元: "悪質な犯罪で糾弾された"
改善: "横領事件で逮捕され、懲役5年の判決を受けた"
理由: センセーショナルな表現を客観的な事実に置き換え
"""

    def __init__(self, provider: LLMProvider):
        """
        初期化

        Args:
            provider: LLMプロバイダー
        """
        self.provider = provider
        self.stats = {
            "total_improvements": 0,
            "successful_improvements": 0,
            "failed_improvements": 0,
            "fallback_count": 0
        }
        logger.info(f"🤖 LLM改善エンジン初期化: {provider.get_provider_name()}")

    def analyze_issues(
        self,
        episode_text: str,
        evaluation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        問題分析

        Args:
            episode_text: エピソードテキスト
            evaluation_result: RULE_179の評価結果

        Returns:
            問題リスト
        """
        # 評価結果から問題を抽出
        issues = []

        # EpisodeEvaluationResultオブジェクトを辞書に変換
        if not isinstance(evaluation_result, dict):
            evaluation_result = {
                "temporal_consistency": evaluation_result.temporal_consistency if hasattr(evaluation_result, "temporal_consistency") else None,
                "negative_evaluation": evaluation_result.negative_evaluation if hasattr(evaluation_result, "negative_evaluation") else None,
                "abstract_detection": evaluation_result.abstract_detection if hasattr(evaluation_result, "abstract_detection") else None,
            }

        # 時系列問題
        if "temporal_consistency" in evaluation_result:
            temporal = evaluation_result["temporal_consistency"]
            if temporal and not temporal.get("passed", True):
                for issue in temporal.get("inconsistencies", []):
                    issues.append({
                        "type": "時系列矛盾",
                        "severity": issue.get("severity", "WARNING"),
                        "message": issue.get("message", ""),
                        "evidence": issue.get("evidence", "")
                    })

        # ネガティブ表現
        if "negative_evaluation" in evaluation_result and evaluation_result["negative_evaluation"]:
            negative = evaluation_result["negative_evaluation"]
            if not negative.get("passed", True):
                for issue in negative.get("issues", []):
                    issues.append({
                        "type": "ネガティブ表現",
                        "severity": issue.get("severity", "WARNING"),
                        "message": issue.get("message", ""),
                        "evidence": issue.get("evidence", "")
                    })

        # 抽象表現
        if "abstract_detection" in evaluation_result and evaluation_result["abstract_detection"]:
            abstract = evaluation_result["abstract_detection"]
            if not abstract.get("passed", True):
                for expr in abstract.get("abstract_expressions", []):
                    issues.append({
                        "type": "抽象表現",
                        "severity": "WARNING",
                        "message": expr.get("suggestion", ""),
                        "evidence": expr.get("expression", "")
                    })

        logger.info(f"🔍 問題分析: {len(issues)}件の問題を検出")
        return issues

    def generate_improvement(
        self,
        episode_text: str,
        issues: List[Dict[str, Any]],
        person_context: Dict[str, Any]
    ) -> str:
        """
        改善案を生成

        Args:
            episode_text: 元のエピソードテキスト
            issues: 問題リスト
            person_context: 人物情報

        Returns:
            改善後のエピソードテキスト
        """
        # プロンプト構築
        prompt = self._build_improvement_prompt(episode_text, issues, person_context)

        logger.info(f"🤖 LLM改善生成開始")

        try:
            # LLM生成
            improved_text = self.provider.generate(prompt, max_tokens=400, temperature=0.3)

            # 余分な説明文を除去（改善後のテキストのみ抽出）
            improved_text = self._extract_improved_text(improved_text)

            logger.info(f"✅ LLM改善生成成功")
            return improved_text

        except Exception as e:
            logger.error(f"❌ LLM改善生成失敗: {e}")
            raise

    def _build_improvement_prompt(
        self,
        episode_text: str,
        issues: List[Dict[str, Any]],
        person_context: Dict[str, Any]
    ) -> str:
        """改善プロンプトを構築"""

        issues_text = "\n".join([
            f"- {issue['type']}: {issue['evidence']} ({issue['message']})"
            for issue in issues
        ])

        prompt = f"""あなたはエピソード品質管理の専門家です。
以下のエピソードを改善してください。

{self.FEW_SHOT_EXAMPLES}

【タスク】
元のエピソード（{len(episode_text)}文字）:
{episode_text}

人物情報:
- 名前: {person_context.get('person_name', '不明')}
- 生年: {person_context.get('birth_year', '不明')}
- 職業: {person_context.get('category', '不明')}

改善すべき問題:
{issues_text}

【絶対厳守の制約】
1. **文字数: 必ず150文字以上250文字以内** ← これは絶対に守ってください
2. 主語の保持: 「あなたと同じXX歳のとき」を必ず含める
3. 具体性: 抽象的な表現は使わず、具体的な事実（大会名、記録、年月）を記載
4. 客観性: 主観的評価（素晴らしい、優れた等）は使用禁止
5. 検証可能性: Wikipedia等で確認できる事実のみを使用

【出力形式】
- 改善後のエピソード本文のみを出力
- 説明文、理由、注釈は一切不要
- 出力文字数: {max(150, len(episode_text))}文字以上を目標に

改善後のエピソード:"""

        return prompt

    def _extract_improved_text(self, llm_output: str) -> str:
        """LLM出力から改善後テキストのみを抽出"""

        # 余分な説明文を除去
        lines = llm_output.strip().split('\n')

        # 「改善後:」などのラベルがあれば除去
        improved_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # ラベル除去
            line = re.sub(r'^(改善後|改善版|修正後|結果)[：:]\s*', '', line)

            # 説明文らしき行をスキップ
            if line.startswith('理由:') or line.startswith('説明:'):
                continue

            improved_lines.append(line)

        # 最初の実質的な文を返す
        if improved_lines:
            return improved_lines[0]

        return llm_output.strip()

    def validate_improvement(
        self,
        original: str,
        improved: str,
        evaluation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        改善結果を検証

        Args:
            original: 元のテキスト
            improved: 改善後テキスト
            evaluation_result: 元の評価結果

        Returns:
            検証結果
        """
        # 基本チェック
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        # 1. 文字数チェック
        if not (150 <= len(improved) <= 250):
            validation_result["errors"].append(
                f"文字数制約違反: {len(improved)}文字（150-250文字必須）"
            )
            validation_result["is_valid"] = False

        # 2. 主語の保持チェック
        pattern = r"あなたと同じ\d+歳のとき"
        if not re.search(pattern, improved):
            validation_result["errors"].append("主語「あなたと同じXX歳のとき」が保持されていません")
            validation_result["is_valid"] = False

        # 3. 禁止表現チェック
        forbidden_words = ["素晴らしい", "優れた", "悪質な", "卑劣な", "最低", "最悪"]
        found_forbidden = [word for word in forbidden_words if word in improved]
        if found_forbidden:
            validation_result["warnings"].append(
                f"禁止表現が含まれています: {', '.join(found_forbidden)}"
            )

        # 4. 変更されているかチェック
        if improved == original:
            validation_result["warnings"].append("元のテキストと同じです（改善されていません）")

        logger.info(
            f"🔍 検証結果: {'✅ 合格' if validation_result['is_valid'] else '❌ 不合格'}"
        )

        return validation_result

    def improve_episode(
        self,
        episode_text: str,
        evaluation_result: Dict[str, Any],
        person_context: Dict[str, Any],
        use_fallback: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        エピソードを改善（メインインターフェース）

        Args:
            episode_text: 元のエピソードテキスト
            evaluation_result: RULE_179の評価結果
            person_context: 人物情報
            use_fallback: フォールバック使用（失敗時はRULE_180）

        Returns:
            (改善後テキスト, 改善サマリー)
        """
        import time
        start_time = time.time()

        self.stats["total_improvements"] += 1

        try:
            # 1. 問題分析
            issues = self.analyze_issues(episode_text, evaluation_result)

            if not issues:
                logger.info("✅ 問題なし、改善不要")
                return episode_text, {
                    "improved": False,
                    "reason": "no_issues_detected"
                }

            # 2. 改善生成
            improved_text = self.generate_improvement(episode_text, issues, person_context)
            logger.info(f"📝 LLM生成テキスト（{len(improved_text)}文字）: {improved_text}")

            # 3. 検証
            validation = self.validate_improvement(episode_text, improved_text, evaluation_result)

            if validation["is_valid"]:
                self.stats["successful_improvements"] += 1
                processing_time = time.time() - start_time

                return improved_text, {
                    "improved": True,
                    "method": "llm",
                    "provider": self.provider.get_provider_name(),
                    "issues_count": len(issues),
                    "validation": validation,
                    "processing_time": processing_time
                }
            else:
                logger.warning(f"⚠️ 検証失敗: {validation['errors']}")

                if use_fallback:
                    logger.info("🔄 RULE_180フォールバックを試行")
                    self.stats["fallback_count"] += 1

                    # RULE_180にフォールバック
                    from rules.rule_180_automatic_improvement_engine import improve_episode_automatically
                    fallback_text, fallback_summary = improve_episode_automatically(
                        episode_text,
                        evaluation_result,
                        max_iterations=3
                    )

                    return fallback_text, {
                        "improved": True,
                        "method": "fallback_rule180",
                        "reason": "llm_validation_failed",
                        "validation_errors": validation["errors"],
                        "fallback_summary": fallback_summary
                    }
                else:
                    self.stats["failed_improvements"] += 1
                    return episode_text, {
                        "improved": False,
                        "reason": "validation_failed",
                        "validation": validation
                    }

        except Exception as e:
            logger.error(f"❌ LLM改善失敗: {e}")
            self.stats["failed_improvements"] += 1

            if use_fallback:
                logger.info("🔄 RULE_180フォールバックを試行（例外発生）")
                self.stats["fallback_count"] += 1

                from rules.rule_180_automatic_improvement_engine import improve_episode_automatically
                fallback_text, fallback_summary = improve_episode_automatically(
                    episode_text,
                    evaluation_result,
                    max_iterations=3
                )

                return fallback_text, {
                    "improved": True,
                    "method": "fallback_rule180",
                    "reason": "llm_exception",
                    "error": str(e),
                    "fallback_summary": fallback_summary
                }
            else:
                return episode_text, {
                    "improved": False,
                    "reason": "llm_exception",
                    "error": str(e)
                }

    def get_stats(self) -> Dict[str, int]:
        """統計情報を取得"""
        return self.stats.copy()


# グローバルエンジン（デフォルトはMock）
_default_engine = None


def get_llm_engine(provider: str = "mock") -> LLMImprovementEngine:
    """
    LLM改善エンジンを取得

    Args:
        provider: 'openai', 'anthropic', 'mock'

    Returns:
        LLMImprovementEngine
    """
    global _default_engine

    if provider == "openai":
        llm_provider = OpenAIProvider()
    elif provider == "anthropic":
        llm_provider = AnthropicProvider()
    else:  # mock
        llm_provider = MockLLMProvider()

    _default_engine = LLMImprovementEngine(llm_provider)
    return _default_engine


def improve_episode_with_llm(
    episode_text: str,
    evaluation_result: Dict[str, Any],
    person_context: Dict[str, Any],
    provider: str = "mock",
    use_fallback: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    エピソードをLLMで改善（外部インターフェース）

    Args:
        episode_text: 元のエピソードテキスト
        evaluation_result: RULE_179の評価結果
        person_context: 人物情報
        provider: 'openai', 'anthropic', 'mock'
        use_fallback: フォールバック使用

    Returns:
        (改善後テキスト, 改善サマリー)
    """
    engine = get_llm_engine(provider)
    return engine.improve_episode(
        episode_text,
        evaluation_result,
        person_context,
        use_fallback
    )


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 80)
    print("RULE_182: LLM改善エンジン - テスト実行")
    print("=" * 80)
    print()

    # テストケース
    test_episode = "あなたと同じ28歳のとき、素晴らしい業績を残し、多くの人々に影響を与えた。"

    test_evaluation = {
        "passed": False,
        "total_score": 65.0,
        "abstract_detection": {
            "passed": False,
            "abstract_expressions": [
                {"expression": "素晴らしい", "suggestion": "客観的事実に置き換え"},
                {"expression": "多くの", "suggestion": "具体的な数値に置き換え"}
            ]
        }
    }

    test_person = {
        "person_name": "大谷翔平",
        "birth_year": 1994,
        "age": 28,
        "category": "野球選手"
    }

    print("📝 元のエピソード:")
    print(f"  {test_episode}")
    print()

    # Mockプロバイダーでテスト
    print("🤖 Mock LLMプロバイダーでテスト")
    print()

    improved_text, summary = improve_episode_with_llm(
        test_episode,
        test_evaluation,
        test_person,
        provider="mock",
        use_fallback=True
    )

    print("✅ 改善後:")
    print(f"  {improved_text}")
    print()

    print("📊 改善サマリー:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print()

    # 統計情報
    engine = get_llm_engine("mock")
    stats = engine.get_stats()

    print("📈 統計情報:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
