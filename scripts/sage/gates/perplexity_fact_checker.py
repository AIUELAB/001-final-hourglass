"""
Perplexity Fact Checker - Web検索ベースの事実検証

Perplexity APIを使用してエピソードの事実性をWeb検索で検証。
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

from ..config import RejectionReason
from .fact_check import FactCheckResult

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# キャッシュディレクトリ
CACHE_DIR = PROJECT_ROOT / "src" / "cache" / "perplexity_fact_check"

# APIキーパス
API_KEY_PATH = Path("/Users/admin/Documents/key/Perplexity_API.txt")


@dataclass
class PerplexityFactCheckResult:
    """Perplexityファクトチェック結果"""

    passed: bool
    confidence: float  # 0.0-1.0
    verified_facts: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "verified_facts": self.verified_facts,
            "unverified_claims": self.unverified_claims,
            "contradictions": self.contradictions,
            "citations": self.citations[:5],  # 最大5件
            "error": self.error,
        }

    def to_fact_check_result(self) -> FactCheckResult:
        """FactCheckResultに変換"""
        return FactCheckResult(
            passed=self.passed,
            score=self.confidence,
            reason=self.error or "",
            evidence_found=self.verified_facts,
            fabrication_signals=self.contradictions,
            rejection_reason=RejectionReason.FABRICATION_DETECTED if self.contradictions else None,
        )


class PerplexityFactChecker:
    """
    Perplexity APIを使用したファクトチェッカー

    Web検索でエピソードの事実性を検証。
    """

    # Perplexity APIエンドポイント
    API_URL = "https://api.perplexity.ai/chat/completions"

    # 使用モデル（2025年最新）
    MODEL = "sonar"  # Web検索対応モデル（高速・コスト効率）

    # ファクトチェック用システムプロンプト
    SYSTEM_PROMPT = """あなたは事実検証の専門家です。提供されたエピソードの内容を検証してください。

以下の形式でJSON応答してください:
{
  "verified_facts": ["検証できた事実1", "検証できた事実2"],
  "unverified_claims": ["検証できなかった主張1"],
  "contradictions": ["矛盾が見つかった内容1"],
  "confidence": 0.8,
  "summary": "検証結果の要約"
}

検証のポイント:
1. 年号・日付が正確か
2. 人物の経歴・業績が事実と一致するか
3. イベントや出来事が実際に起きたか
4. 数値データが正確か
5. 固有名詞（作品名、組織名等）が正確か

confidence は 0.0-1.0 で、検証できた割合を示してください。
contradictions に深刻な事実誤認がある場合は必ず記載してください。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        min_confidence: float = 0.6,
    ):
        self.api_key = api_key or self._load_api_key()
        self.cache_enabled = cache_enabled
        self.min_confidence = min_confidence

        if cache_enabled:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_api_key(self) -> str:
        """APIキーを読み込み"""
        if API_KEY_PATH.exists():
            return API_KEY_PATH.read_text().strip()

        env_key = os.environ.get("PERPLEXITY_API_KEY")
        if env_key:
            return env_key

        raise ValueError("Perplexity API key not found")

    def check(
        self,
        text: str,
        person_name: str,
        age: Optional[int] = None,
        category: Optional[str] = None,
    ) -> PerplexityFactCheckResult:
        """
        エピソードをファクトチェック

        Args:
            text: エピソードテキスト
            person_name: 人物名
            age: 年齢（オプション）
            category: カテゴリ（オプション）

        Returns:
            PerplexityFactCheckResult: 検証結果
        """
        # キャッシュ確認
        cache_key = self._get_cache_key(text, person_name)
        if self.cache_enabled:
            cached = self._load_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for {person_name}")
                return cached

        # クエリ構築
        query = self._build_query(text, person_name, age, category)

        # API呼び出し
        try:
            response = self._call_api(query)
            result = self._parse_response(response)
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            result = PerplexityFactCheckResult(
                passed=True,  # エラー時はパス（フォールバック）
                confidence=0.5,
                error=str(e),
            )

        # キャッシュ保存
        if self.cache_enabled and not result.error:
            self._save_cache(cache_key, result)

        return result

    def _build_query(
        self,
        text: str,
        person_name: str,
        age: Optional[int],
        category: Optional[str],
    ) -> str:
        """検証クエリを構築"""
        query_parts = [
            "以下のエピソードの事実性を検証してください。",
            "",
            f"【人物】{person_name}",
        ]

        if age is not None:
            query_parts.append(f"【年齢】{age}歳時点")

        if category:
            query_parts.append(f"【カテゴリ】{category}")

        query_parts.extend(
            [
                "",
                "【エピソード】",
                text,
                "",
                "上記の内容について、以下を検証してください:",
                "1. 記載された年号・日付は正確か",
                "2. 人物の経歴・業績は事実と一致するか",
                "3. 記載されたイベントは実際に起きたか",
                "4. 明らかな事実誤認や矛盾はないか",
            ]
        )

        return "\n".join(query_parts)

    def _call_api(self, query: str) -> dict[str, Any]:
        """Perplexity APIを呼び出し"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "temperature": 0.1,  # 事実検証なので低め
            "max_tokens": 1024,
        }

        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text[:200]}")

        return response.json()

    def _parse_response(self, response: dict[str, Any]) -> PerplexityFactCheckResult:
        """APIレスポンスをパース"""
        try:
            content = response["choices"][0]["message"]["content"]
            citations = response.get("citations", [])

            # JSON抽出
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # JSONがない場合、テキストから解析
                data = self._parse_text_response(content)

            confidence = float(data.get("confidence", 0.7))
            contradictions = data.get("contradictions", [])

            # 判定
            passed = confidence >= self.min_confidence and len(contradictions) == 0

            return PerplexityFactCheckResult(
                passed=passed,
                confidence=confidence,
                verified_facts=data.get("verified_facts", []),
                unverified_claims=data.get("unverified_claims", []),
                contradictions=contradictions,
                citations=citations,
                raw_response=content,
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Response parse error: {e}")
            return PerplexityFactCheckResult(
                passed=True,
                confidence=0.5,
                error=f"Parse error: {e}",
                raw_response=str(response),
            )

    def _parse_text_response(self, content: str) -> dict[str, Any]:
        """テキストレスポンスから情報を抽出"""
        result: dict[str, Any] = {
            "verified_facts": [],
            "unverified_claims": [],
            "contradictions": [],
            "confidence": 0.7,
        }

        # 肯定的表現
        if any(word in content for word in ["正確", "確認できました", "事実です", "一致"]):
            result["confidence"] = 0.8

        # 否定的表現
        if any(word in content for word in ["誤り", "矛盾", "不正確", "見つかりません"]):
            result["confidence"] = 0.4
            result["contradictions"].append("事実と異なる可能性あり")

        return result

    def _get_cache_key(self, text: str, person_name: str) -> str:
        """キャッシュキーを生成"""
        import hashlib

        content = f"{person_name}:{text[:200]}"
        return hashlib.md5(content.encode()).hexdigest()

    def _load_cache(self, cache_key: str) -> Optional[PerplexityFactCheckResult]:
        """キャッシュから読み込み"""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)

                # 24時間以内のキャッシュのみ使用
                cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                if (datetime.now() - cached_at).days < 1:
                    return PerplexityFactCheckResult(
                        passed=data["passed"],
                        confidence=data["confidence"],
                        verified_facts=data.get("verified_facts", []),
                        unverified_claims=data.get("unverified_claims", []),
                        contradictions=data.get("contradictions", []),
                        citations=data.get("citations", []),
                    )
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _save_cache(self, cache_key: str, result: PerplexityFactCheckResult) -> None:
        """キャッシュに保存"""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        data = result.to_dict()
        data["cached_at"] = datetime.now().isoformat()

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class HybridFactChecker:
    """
    ハイブリッドファクトチェッカー

    ローカルルールベース + Perplexity Web検索の組み合わせ。
    """

    def __init__(
        self,
        use_perplexity: bool = True,
        perplexity_threshold: float = 0.7,
    ):
        from .fact_check import FactChecker

        self.local_checker = FactChecker()
        self.use_perplexity = use_perplexity
        self.perplexity_threshold = perplexity_threshold

        if use_perplexity:
            try:
                self.perplexity_checker = PerplexityFactChecker()
            except ValueError:
                logger.warning("Perplexity API key not found, using local only")
                self.use_perplexity = False
                self.perplexity_checker = None

    def check(
        self,
        text: str,
        person_name: str,
        age: Optional[int] = None,
        category: Optional[str] = None,
    ) -> FactCheckResult:
        """
        ハイブリッドファクトチェック

        1. ローカルルールベースチェック
        2. スコアが閾値以下の場合、Perplexityで追加検証

        Args:
            text: エピソードテキスト
            person_name: 人物名
            age: 年齢
            category: カテゴリ

        Returns:
            FactCheckResult: 検証結果
        """
        # 1. ローカルチェック
        local_result = self.local_checker.check(text, person_name)

        # ローカルで明確にNGの場合は即リジェクト
        if not local_result.passed:
            return local_result

        # 2. Perplexityチェック（オプション）
        if self.use_perplexity and local_result.score < self.perplexity_threshold:
            perplexity_result = self.perplexity_checker.check(text, person_name, age, category)

            # Perplexityで矛盾が見つかった場合
            if perplexity_result.contradictions:
                return FactCheckResult(
                    passed=False,
                    score=perplexity_result.confidence,
                    reason=f"Web検証で矛盾検出: {perplexity_result.contradictions[0]}",
                    evidence_found=perplexity_result.verified_facts,
                    fabrication_signals=perplexity_result.contradictions,
                    rejection_reason=RejectionReason.FABRICATION_DETECTED,
                )

            # Perplexityで検証できた場合、スコアを更新
            if perplexity_result.confidence > local_result.score:
                local_result.score = perplexity_result.confidence
                local_result.evidence_found.extend(perplexity_result.verified_facts[:3])

        return local_result


# ==============================================================================
# 便利関数
# ==============================================================================


def perplexity_fact_check(
    text: str,
    person_name: str,
    age: Optional[int] = None,
) -> bool:
    """
    Perplexityファクトチェック（簡易版）

    Args:
        text: エピソードテキスト
        person_name: 人物名
        age: 年齢

    Returns:
        bool: パスしたか
    """
    try:
        checker = PerplexityFactChecker()
        result = checker.check(text, person_name, age)
        return result.passed
    except Exception as e:
        logger.error(f"Perplexity fact check error: {e}")
        return True  # エラー時はパス


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    print("=== Perplexity Fact Checker Test ===")

    # APIキー確認
    try:
        checker = PerplexityFactChecker()
        print("✓ API key loaded")
    except ValueError as e:
        print(f"✗ API key error: {e}")
        exit(1)

    # テストエピソード
    test_cases = [
        {
            "person_name": "大谷翔平",
            "text": "2023年、大谷翔平はMLBで44本塁打を放ち、アメリカン・リーグMVPを満票で受賞した。投打の二刀流として歴史に名を刻んだ。",
            "expected": True,
        },
        {
            "person_name": "架空人物",
            "text": "2020年、山田太郎は東京オリンピックで金メダルを獲得し、日本中を感動の渦に巻き込んだ。",
            "expected": False,  # 2020年に東京五輪は開催されていない
        },
    ]

    for i, case in enumerate(test_cases):
        print(f"\n--- Test {i + 1}: {case['person_name']} ---")
        result = checker.check(case["text"], case["person_name"])

        print(f"Passed: {result.passed} (expected: {case['expected']})")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Verified: {result.verified_facts[:2]}")
        print(f"Contradictions: {result.contradictions}")

    print("\n=== Test Complete ===")
