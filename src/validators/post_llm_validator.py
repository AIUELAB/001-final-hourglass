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

    # Phase 32: 1-5歳エピソード品質ゲートパターン（幼児には不可能な行動・主観的表現を禁止）
    EARLY_CHILDHOOD_FORBIDDEN_PATTERNS = [
        # 幼児には不可能な創作活動
        (r"制作した", "1-5歳児には不可能な行動"),
        (r"執筆した", "1-5歳児には不可能な行動"),
        (r"作曲した", "1-5歳児には不可能な行動"),
        (r"発明した", "1-5歳児には不可能な行動"),
        (r"発表した", "1-5歳児には不可能な行動"),
        (r"出版した", "1-5歳児には不可能な行動"),
        (r"設立した", "1-5歳児には不可能な行動"),
        (r"起業した", "1-5歳児には不可能な行動"),
        (r"論文", "1-5歳児には不可能な学術活動"),
        (r"研究を始めた", "1-5歳児には不可能な学術活動"),
        # 検証不可能な主観的表現
        (r"情熱を秘めていた", "検証不可能な内面描写"),
        (r"才能の片鱗", "検証不可能な主観表現"),
        (r"運命を感じ", "検証不可能な主観表現"),
        (r"決意を固めた", "1-5歳児の決意は検証不可能"),
        (r"志を立てた", "1-5歳児の志は検証不可能"),
        (r"夢を抱いた", "1-5歳児の夢は検証不可能"),
        (r"強い意志", "1-5歳児の意志は検証不可能"),
        (r"深い感銘", "1-5歳児の感銘は検証不可能"),
        (r"芸術への情熱", "検証不可能な主観表現"),
    ]

    # Phase 32: 1-5歳エピソードで推奨されるパターン（第三者視点・記録ベース）
    EARLY_CHILDHOOD_RECOMMENDED_PATTERNS = [
        # 出典・伝聞系
        r"伝記によると",
        r"家族の証言",
        r"公式記録",
        r"と言われて",
        r"とされて",
        r"後年.*語った",
        r"母親.*によると",
        r"父親.*によると",
        r"両親.*によると",
        r"父は",
        r"母は",
        # 誕生・成長系
        r"誕生",
        r"生まれた",
        r"名付けられた",
        r"育った",
        r"家庭環境",
        # 開始・活動系
        r"を始め",
        r"に没頭",
        r"デビュー",
        r"演奏",
        r"出演",
        r"参加",
        r"入学",
        r"指導を受け",
        r"教育を施",
        # 記録系
        r"写真.*残",
        r"記録.*残",
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
        work_title: str = "",
    ) -> ValidationResult:
        """
        エピソードテキストをバリデーション

        Args:
            episode_text: エピソードテキスト
            age: 期待される年齢
            person_type: 人物タイプ（REAL/FICTIONAL）
            work_title: 作品名（FICTIONALの場合に使用）

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

            # 2.1 EPUP: 作品名チェック（FICTIONALでwork_titleがある場合）
            if work_title:
                work_title_result = self._check_fictional_work_title(text, work_title)
                if work_title_result["error"]:
                    errors.append(work_title_result["error"])
                    retry_hints.append(work_title_result["hint"])
                    score_deductions += 0.3  # 作品名欠落は重大なエラー

        # 2.5 Phase 32: 幼児エピソード品質チェック（1-5歳の場合）
        if age is not None and 1 <= age <= 5:
            early_childhood_result = self._check_early_childhood_quality(text, age)
            if early_childhood_result["errors"]:
                errors.extend(early_childhood_result["errors"])
                retry_hints.extend(early_childhood_result["hints"])
                score_deductions += 0.3 * len(early_childhood_result["errors"])
            if early_childhood_result["warnings"]:
                warnings.extend(early_childhood_result["warnings"])
                score_deductions += 0.1

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

    def _check_fictional_work_title(self, text: str, work_title: str) -> dict:
        """
        EPUP: FICTIONALキャラクターエピソードの作品名チェック

        架空キャラクターのエピソードは冒頭に『作品名』を含む必要がある。
        正しい形式: 「あなたと同じ○歳のとき、[人物名]『[作品名]』は...」

        Args:
            text: エピソードテキスト
            work_title: 期待される作品名

        Returns:
            {"error": str|None, "hint": str}
        """
        # 冒頭100文字に『作品名』があるか
        lead = text[:100]
        expected = f"『{work_title}』"

        if expected not in lead:
            # 作品名のバリエーションもチェック（略称、英語表記など）
            # 例: 「NARUTO」→「『NARUTO』」「『ナルト』」
            work_title_normalized = work_title.strip()
            has_any_work_title = "『" in lead and "』" in lead

            if has_any_work_title:
                # 何らかの作品名はあるが、期待と一致しない
                return {
                    "error": f"作品名が一致しません。期待: {expected}",
                    "hint": f"作品名を『{work_title}』に統一してください",
                }
            else:
                # 作品名が全くない
                return {
                    "error": f"FICTIONALエピソードに『{work_title}』が冒頭にありません",
                    "hint": f"「[人物名]『{work_title}』は」形式で開始してください",
                }

        return {"error": None, "hint": ""}

    def _check_early_childhood_quality(self, text: str, age: int) -> dict:
        """
        Phase 32: 1-5歳エピソードの品質チェック

        幼児エピソードは第三者視点・記録ベースであることを検証し、
        幼児には不可能な行動や検証不可能な主観表現を検出する。

        Args:
            text: エピソードテキスト
            age: 年齢（1-5歳を想定）

        Returns:
            {"errors": list[str], "warnings": list[str], "hints": list[str]}
        """
        errors = []
        warnings = []
        hints = []

        # 禁止パターンのチェック（重大なエラー）
        for pattern, message in self.EARLY_CHILDHOOD_FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                errors.append(f"幼児エピソード品質違反: {message}")
                hints.append(f"「{pattern}」を含まない第三者視点・記録ベースの表現に書き直してください")

        # 推奨パターンの有無チェック（警告レベル）
        has_recommended = False
        for pattern in self.EARLY_CHILDHOOD_RECOMMENDED_PATTERNS:
            if re.search(pattern, text):
                has_recommended = True
                break

        if not has_recommended:
            warnings.append("幼児エピソード品質警告: 第三者視点・記録ベースの表現が不足しています")
            hints.append("「伝記によると」「家族の証言では」などの出典を明記した表現を追加してください")

        return {"errors": errors, "warnings": warnings, "hints": hints}

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
