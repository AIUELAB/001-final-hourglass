#!/usr/bin/env python3
"""
PostLLMValidator - LLM生成エピソードの品質検証

機能:
1. リード文フォーマット検証（あなたと同じ○歳のとき）
2. メタ表現検出（FICTIONAL専用）
3. 文字数チェック（150-300文字推奨）
4. 年齢整合性チェック
5. 品質スコア算出
6. リトライ可能なエラー判定
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class QualityLevel(Enum):
    """品質レベル"""

    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"  # 70-89%
    ACCEPTABLE = "acceptable"  # 50-69%
    POOR = "poor"  # 30-49%
    UNACCEPTABLE = "unacceptable"  # 0-29%


@dataclass
class ValidationResult:
    """バリデーション結果"""

    is_valid: bool
    quality_score: float  # 0.0-1.0
    quality_level: QualityLevel
    errors: list[str]
    warnings: list[str]
    retryable: bool  # リトライで改善可能か
    retry_hints: list[str]  # リトライ時のヒント


class PostLLMValidator:
    """LLM生成エピソードのバリデータ"""

    # リード文の正規パターン
    LEAD_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、")

    # メタ表現パターン（FICTIONALタイプで禁止）
    META_PATTERNS = [
        (r"架空の", "「架空の」という表現は不可"),
        (r"フィクション", "「フィクション」という表現は不可"),
        (r"設定上", "「設定上」という表現は不可"),
        (r"作品内では", "「作品内では」という表現は不可"),
        (r"公式な描写は存在しません", "メタ説明は不可"),
        (r"実在しない", "「実在しない」という表現は不可"),
        (r"申し訳ございませんが", "謝罪表現は不可"),
        (r"キャラクターです", "メタ表現は不可"),
        (r"存在しません", "「存在しません」は不可"),
        (r"描かれていません", "「描かれていません」は不可"),
        (r"物語の中で", "「物語の中で」は不可"),
        (r"作品世界", "「作品世界」は不可"),
        (r"著作権の関係", "著作権言及は不可"),
    ]

    # 文字数制限
    MIN_CHARS = 100
    RECOMMENDED_MIN = 150
    RECOMMENDED_MAX = 300
    MAX_CHARS = 500

    def __init__(self):
        """初期化"""
        pass

    def validate(
        self,
        episode_text: str,
        age: Optional[int] = None,
        person_type: str = "REAL",
    ) -> ValidationResult:
        """
        エピソードテキストをバリデーション

        Args:
            episode_text: エピソードテキスト
            age: 期待される年齢
            person_type: 人物タイプ（REAL/FICTIONAL）

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        retry_hints = []
        score_deductions = 0.0

        # 空チェック
        if not episode_text or not episode_text.strip():
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                quality_level=QualityLevel.UNACCEPTABLE,
                errors=["エピソードテキストが空です"],
                warnings=[],
                retryable=True,
                retry_hints=["エピソードテキストを生成してください"],
            )

        text = episode_text.strip()

        # 1. リード文チェック
        lead_result = self._check_lead_format(text, age)
        if lead_result["error"]:
            errors.append(lead_result["error"])
            retry_hints.append(lead_result["hint"])
            score_deductions += 0.3
        elif lead_result["warning"]:
            warnings.append(lead_result["warning"])
            score_deductions += 0.1

        # 2. メタ表現チェック（FICTIONALの場合）
        if person_type.upper() == "FICTIONAL":
            meta_result = self._check_meta_expressions(text)
            if meta_result["errors"]:
                errors.extend(meta_result["errors"])
                retry_hints.extend(meta_result["hints"])
                score_deductions += 0.2 * len(meta_result["errors"])

        # 3. 文字数チェック
        char_result = self._check_char_count(text)
        if char_result["error"]:
            errors.append(char_result["error"])
            retry_hints.append(char_result["hint"])
            score_deductions += 0.2
        elif char_result["warning"]:
            warnings.append(char_result["warning"])
            score_deductions += 0.05

        # 4. 品質スコア算出
        quality_score = max(0.0, 1.0 - score_deductions)

        # 5. 品質レベル判定
        quality_level = self._get_quality_level(quality_score)

        # 6. 有効性判定
        is_valid = len(errors) == 0 and quality_score >= 0.5

        # 7. リトライ可能性判定
        retryable = len(errors) > 0 and quality_score < 0.9

        return ValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            quality_level=quality_level,
            errors=errors,
            warnings=warnings,
            retryable=retryable,
            retry_hints=retry_hints,
        )

    def _check_lead_format(self, text: str, expected_age: Optional[int]) -> dict:
        """
        リード文フォーマットをチェック

        Args:
            text: テキスト
            expected_age: 期待される年齢

        Returns:
            {"error": str|None, "warning": str|None, "hint": str}
        """
        match = self.LEAD_PATTERN.match(text)

        if not match:
            return {
                "error": "リード文が「あなたと同じ○歳のとき、」形式ではありません",
                "warning": None,
                "hint": "「あなたと同じ{年齢}歳のとき、」で始めてください",
            }

        lead_age = int(match.group(1))

        if expected_age is not None and lead_age != expected_age:
            return {
                "error": f"リード文の年齢({lead_age})と期待値({expected_age})が不一致",
                "warning": None,
                "hint": f"年齢を{expected_age}に修正してください",
            }

        return {"error": None, "warning": None, "hint": ""}

    def _check_meta_expressions(self, text: str) -> dict:
        """
        メタ表現をチェック

        Args:
            text: テキスト

        Returns:
            {"errors": list[str], "hints": list[str]}
        """
        errors = []
        hints = []

        for pattern, message in self.META_PATTERNS:
            if re.search(pattern, text):
                errors.append(f"メタ表現検出: {message}")
                hints.append(f"「{pattern}」を含まない表現に書き直してください")

        return {"errors": errors, "hints": hints}

    def _check_char_count(self, text: str) -> dict:
        """
        文字数をチェック

        Args:
            text: テキスト

        Returns:
            {"error": str|None, "warning": str|None, "hint": str}
        """
        char_count = len(text)

        if char_count < self.MIN_CHARS:
            return {
                "error": f"文字数が少なすぎます({char_count}文字、最低{self.MIN_CHARS}文字)",
                "warning": None,
                "hint": f"少なくとも{self.MIN_CHARS}文字以上に拡張してください",
            }

        if char_count > self.MAX_CHARS:
            return {
                "error": f"文字数が多すぎます({char_count}文字、最大{self.MAX_CHARS}文字)",
                "warning": None,
                "hint": f"{self.MAX_CHARS}文字以内に要約してください",
            }

        if char_count < self.RECOMMENDED_MIN:
            return {
                "error": None,
                "warning": f"文字数がやや少なめです({char_count}文字、推奨{self.RECOMMENDED_MIN}文字以上)",
                "hint": "",
            }

        if char_count > self.RECOMMENDED_MAX:
            return {
                "error": None,
                "warning": f"文字数がやや多めです({char_count}文字、推奨{self.RECOMMENDED_MAX}文字以下)",
                "hint": "",
            }

        return {"error": None, "warning": None, "hint": ""}

    def _get_quality_level(self, score: float) -> QualityLevel:
        """
        スコアから品質レベルを判定

        Args:
            score: 品質スコア（0.0-1.0）

        Returns:
            QualityLevel
        """
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def generate_retry_prompt(self, result: ValidationResult, original_prompt: str) -> str:
        """
        リトライ用のプロンプトを生成

        Args:
            result: バリデーション結果
            original_prompt: 元のプロンプト

        Returns:
            強化されたプロンプト
        """
        if not result.retryable:
            return original_prompt

        hints = "\n".join(f"- {h}" for h in result.retry_hints)

        enhanced_prompt = f"""{original_prompt}

【重要な修正指示】
以下の点を必ず修正してください:
{hints}

【禁止事項】
- 「架空の」「フィクション」「設定上」などのメタ表現は使用しない
- 「存在しません」「描かれていません」などの否定的表現は使用しない
- 「申し訳ございませんが」などの謝罪表現は使用しない

【必須】
- 「あなたと同じ○歳のとき、」で始める
- 具体的なエピソードを{self.RECOMMENDED_MIN}-{self.RECOMMENDED_MAX}文字で記述
"""
        return enhanced_prompt


def main():
    """テスト実行"""
    validator = PostLLMValidator()

    # テストケース
    test_cases: list[dict[str, str | int]] = [
        {
            "text": "あなたと同じ25歳のとき、彼は初めてのアルバムをリリースしました。",
            "age": 25,
            "type": "REAL",
        },
        {
            "text": "このキャラクターは架空の存在であり、実在しません。",
            "age": 10,
            "type": "FICTIONAL",
        },
        {
            "text": "あなたと同じ16歳のとき、悟空は亀仙人の元で修行を開始しました。かめはめ波の習得に挑み、武天老師から戦いの基礎を学びました。",
            "age": 16,
            "type": "FICTIONAL",
        },
    ]

    for case in test_cases:
        print(f"\n{'=' * 60}")
        text = str(case["text"])
        age = int(case["age"])
        person_type = str(case["type"])
        print(f"テキスト: {text[:50]}...")
        result = validator.validate(text, age, person_type)
        print(f"有効: {'✅' if result.is_valid else '❌'}")
        print(f"スコア: {result.quality_score:.2f}")
        print(f"レベル: {result.quality_level.value}")
        if result.errors:
            print(f"エラー: {result.errors}")
        if result.warnings:
            print(f"警告: {result.warnings}")


if __name__ == "__main__":
    main()
