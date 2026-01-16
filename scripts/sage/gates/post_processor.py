#!/usr/bin/env python3
"""
SAGE Turbo 後処理モジュール

生成後のエピソードに対して以下の処理を義務付け:
1. 定型パターン修正: "あなたと同じ{age}歳のとき、{name}は" で開始
2. スコア欠損補完: 必須スコアの計算と補完
3. 年号範囲検証: birth_year〜death_year範囲内の年号のみ許可（Phase 3追加）
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from scripts.sage.turbo.evaluator import EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class PostProcessResult:
    """後処理結果"""

    success: bool
    episode_text: str
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class YearRangeValidationResult:
    """Phase 3: 年号範囲検証結果"""

    passed: bool
    violations: list[str] = field(default_factory=list)
    detected_years: list[int] = field(default_factory=list)
    birth_year: Optional[int] = None
    death_year: Optional[int] = None


def validate_year_range(
    episode_text: str,
    birth_year: Optional[int],
    death_year: Optional[int],
    age: int,
) -> YearRangeValidationResult:
    """
    Phase 3: エピソードテキスト内の年号がbirth_year〜death_year範囲内かチェック

    Args:
        episode_text: エピソードテキスト
        birth_year: 生年（None可）
        death_year: 没年（None=存命、None可）
        age: 対象年齢

    Returns:
        YearRangeValidationResult: 検証結果
    """
    # 年号パターン（西暦4桁）
    year_pattern = re.compile(r"(1[789]\d{2}|20[0-2]\d)年")
    detected_years = [int(m.group(1)) for m in year_pattern.finditer(episode_text)]

    if not detected_years:
        # 年号なしは別のチェックで対応（具体性チェック）
        return YearRangeValidationResult(
            passed=True,
            violations=[],
            detected_years=[],
            birth_year=birth_year,
            death_year=death_year,
        )

    violations = []

    # 対象年（birth_year + age）を計算
    target_year = None
    if birth_year is not None:
        target_year = birth_year + age

    for year in detected_years:
        # 1. 没年以降チェック
        if death_year is not None and year > death_year:
            violations.append(f"没年({death_year})以降の年号を検出: {year}年")

        # 2. 生年以前チェック
        if birth_year is not None and year < birth_year:
            violations.append(f"生年({birth_year})以前の年号を検出: {year}年")

        # 3. 対象年との大きな乖離チェック（±20年以上は警告）
        if target_year is not None:
            diff = abs(year - target_year)
            if diff > 20:
                # 警告レベル（棄却はしない）
                logger.warning(f"年号乖離警告: 対象年{target_year}に対して{year}年は±{diff}年の差異")

    return YearRangeValidationResult(
        passed=len(violations) == 0,
        violations=violations,
        detected_years=detected_years,
        birth_year=birth_year,
        death_year=death_year,
    )


class EpisodePostProcessor:
    """エピソード後処理器"""

    # 正規パターン: 「あなたと同じ{age}歳のとき、{person_name}は/の」
    VALID_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、(.+?)(は|の)")

    # Markdownヘッダーパターン
    MARKDOWN_HEADER = re.compile(r"^\*\*[^*]+\*\*\s*\n*")

    # 引用符パターン
    QUOTE_START = re.compile(r"^[「『]")

    # 年号開始パターン
    YEAR_START = re.compile(r"^(\d{4})年")

    # 重複した人物名パターン（例: "坂本龍馬は...坂本龍馬は"）
    DUPLICATE_NAME_PATTERN = re.compile(r"は(.{0,20})(\S+)は")

    # 1文目の年号パターン（新ルール: 1文目に年号禁止）
    YEAR_IN_FIRST_PATTERNS = [
        (re.compile(r"(は)((?:19|20)\d{2})年([、,])"), "year_comma"),
        (re.compile(r"(は)((?:19|20)\d{2})年(に)"), "year_ni"),
        (re.compile(r"(は)((?:19|20)\d{2})年(の)"), "year_no"),
    ]

    # 年号検出パターン
    YEAR_DETECT_PATTERN = re.compile(r"((?:19|20)\d{2})年")

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: Trueの場合、修正できない場合はsuccessをFalseにする
        """
        self.strict_mode = strict_mode

    def process(
        self,
        episode_text: str,
        person_name: str,
        age: int,
    ) -> PostProcessResult:
        """
        エピソードテキストを後処理

        Args:
            episode_text: 生成されたエピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            PostProcessResult: 後処理結果
        """
        changes = []
        warnings = []
        text = episode_text

        # 1. 定型パターンの検証と修正
        text, format_changes, format_warnings = self._fix_format_pattern(text, person_name, age)
        changes.extend(format_changes)
        warnings.extend(format_warnings)

        # 2. 重複人物名の修正
        text, dup_changes = self._fix_duplicate_name(text, person_name)
        changes.extend(dup_changes)

        # 3. 1文目の年号修正（EPUP新ルール: 1文目に年号禁止）
        text, year_changes = self._fix_year_in_first_sentence(text)
        changes.extend(year_changes)

        # 4. 末尾の整理（余分な空白、改行）
        text = text.strip()

        # 検証: 最終チェック
        is_valid = self._validate_final(text, person_name, age)

        if not is_valid and self.strict_mode:
            warnings.append("定型パターンの修正に失敗")

        return PostProcessResult(
            success=is_valid or not self.strict_mode,
            episode_text=text,
            changes=changes,
            warnings=warnings,
        )

    def _fix_format_pattern(
        self,
        text: str,
        person_name: str,
        age: int,
    ) -> tuple[str, list[str], list[str]]:
        """定型パターンを修正"""
        changes = []
        warnings = []

        # 既に正しいパターンで始まっているか確認
        match = self.VALID_PATTERN.match(text)
        if match:
            extracted_age = int(match.group(1))
            extracted_name = match.group(2)

            # 年齢の整合性チェック
            if extracted_age != age:
                text = re.sub(
                    r"^あなたと同じ\d+歳のとき",
                    f"あなたと同じ{age}歳のとき",
                    text,
                )
                changes.append(f"年齢修正: {extracted_age} → {age}")

            # 人物名の整合性チェック（部分一致でOK）
            if person_name not in extracted_name:
                # 人物名を置換
                text = re.sub(
                    r"^あなたと同じ(\d+)歳のとき、[^、]+?(は|の)",
                    f"あなたと同じ{age}歳のとき、{person_name}\\2",
                    text,
                )
                changes.append(f"人物名修正: {extracted_name} → {person_name}")

            return text, changes, warnings

        # パターンにマッチしない場合は修正を試みる
        fixed_text = self._create_standard_format(text, person_name, age)
        if fixed_text:
            changes.append("定型パターンで開始するよう修正")
            return fixed_text, changes, warnings

        # 修正できない場合
        warnings.append("定型パターンの自動修正に失敗")
        return text, changes, warnings

    def _create_standard_format(
        self,
        text: str,
        person_name: str,
        age: int,
    ) -> Optional[str]:
        """標準フォーマットに変換"""
        cleaned_text = text

        # Markdownヘッダーを除去
        cleaned_text = self.MARKDOWN_HEADER.sub("", cleaned_text)

        # 引用符を除去
        cleaned_text = self.QUOTE_START.sub("", cleaned_text)

        # 先頭の空白を除去
        cleaned_text = cleaned_text.strip()

        # 既に「あなたと同じ」で始まっているが完全なパターンでない場合
        if cleaned_text.startswith("あなたと同じ"):
            # 壊れたパターンを修正
            partial_match = re.match(r"^あなたと同じ(\d*)歳?の?とき?、?", cleaned_text)
            if partial_match:
                # 既存の部分を除去して再構築
                remaining = cleaned_text[partial_match.end() :]
                return f"あなたと同じ{age}歳のとき、{person_name}は{remaining}"

        # 人物名で始まっている場合
        if cleaned_text.startswith(person_name):
            # "人物名は..." → "あなたと同じ{age}歳のとき、人物名は..."
            return f"あなたと同じ{age}歳のとき、{cleaned_text}"

        # 年号で始まる場合
        year_match = self.YEAR_START.match(cleaned_text)
        if year_match:
            # "1867年、..." → "あなたと同じ{age}歳のとき、{name}は1867年、..."
            return f"あなたと同じ{age}歳のとき、{person_name}は{cleaned_text}"

        # その他の場合、定型を追加
        if cleaned_text:
            # テキストが「は」で続くか「の」で続くか判断
            connector = "は"
            if cleaned_text.startswith(("その", "この", "当時")):
                connector = "の"

            return f"あなたと同じ{age}歳のとき、{person_name}{connector}{cleaned_text}"

        return None

    def _fix_duplicate_name(
        self,
        text: str,
        person_name: str,
    ) -> tuple[str, list[str]]:
        """重複した人物名を修正"""
        changes = []

        # パターン: "あなたと同じX歳のとき、{name}は...{name}は"
        # 2回目の "{name}は" を除去
        dup_pattern = re.compile(
            rf"(あなたと同じ\d+歳のとき、{re.escape(person_name)}は)" rf"(.{{0,50}}?)" rf"({re.escape(person_name)}は)"
        )

        if dup_pattern.search(text):
            # 2回目の人物名+「は」を除去
            text = dup_pattern.sub(r"\1\2", text)
            changes.append(f"重複人物名を除去: {person_name}")

        return text, changes

    def _fix_year_in_first_sentence(self, text: str) -> tuple[str, list[str]]:
        """1文目の年号を修正（年号を削除、括弧追加なし）"""
        changes = []

        # 1文目の範囲を取得
        match = self.VALID_PATTERN.match(text)
        if not match:
            return text, changes

        start_pos = match.end()
        first_period = text.find("。", start_pos)
        if first_period == -1:
            return text, changes

        first_sentence = text[start_pos:first_period]

        # 年号が1文目にあるかチェック
        year_match = self.YEAR_DETECT_PATTERN.search(first_sentence)
        if not year_match:
            return text, changes

        # パターン別に修正（年号削除のみ）
        patterns = [
            (re.compile(r"(は)((?:19|20)\d{2})年([、,])"), "year_comma"),
            (re.compile(r"(は)((?:19|20)\d{2})年(に)"), "year_ni"),
            (re.compile(r"(は)((?:19|20)\d{2})年(の)"), "year_no"),
            (re.compile(r"(は)((?:19|20)\d{2})年(\d{1,2}月)"), "year_month"),
            (re.compile(r"(は)[、,]((?:19|20)\d{2})年(に)"), "comma_before_year"),
            (re.compile(r"(は)((?:19|20)\d{2})年([^\d、,にの。])"), "year_direct"),
            (re.compile(r"(の)((?:19|20)\d{2})年[、,]"), "year_in_middle"),
            (re.compile(r"(翌)((?:19|20)\d{2})年"), "year_yoku"),
            (re.compile(r"[（\(]((?:19|20)\d{2})年[）\)]"), "year_paren"),
        ]

        for pattern, ptype in patterns:
            match_p = pattern.search(text[:first_period])
            if match_p:
                if ptype == "year_paren":
                    year = match_p.group(1)
                    modified_text = text[: match_p.start()] + text[match_p.end() :]
                elif ptype == "year_yoku":
                    year = match_p.group(2)
                    modified_text = text[: match_p.start()] + "翌年" + text[match_p.end() :]
                elif ptype == "year_no":
                    year = match_p.group(2)
                    modified_text = text[: match_p.start()] + match_p.group(1) + "その" + text[match_p.end() :]
                elif ptype == "year_month":
                    year = match_p.group(2)
                    modified_text = (
                        text[: match_p.start()] + match_p.group(1) + match_p.group(3) + text[match_p.end() :]
                    )
                elif ptype == "year_direct":
                    year = match_p.group(2)
                    modified_text = (
                        text[: match_p.start()] + match_p.group(1) + match_p.group(3) + text[match_p.end() :]
                    )
                else:
                    year = match_p.group(2)
                    modified_text = text[: match_p.start()] + match_p.group(1) + text[match_p.end() :]

                changes.append(f"年号削除: {year}年")
                return modified_text, changes

        # 汎用: 残存年号を除去
        year_generic = re.compile(r"((?:19|20)\d{2})年")
        match_generic = year_generic.search(text[:first_period])
        if match_generic:
            year = match_generic.group(1)
            modified_text = text[: match_generic.start()] + text[match_generic.end() :]
            changes.append(f"年号削除(汎用): {year}年")
            return modified_text, changes

        return text, changes

    def _validate_final(
        self,
        text: str,
        person_name: str,
        age: int,
    ) -> bool:
        """最終検証"""
        match = self.VALID_PATTERN.match(text)
        if not match:
            return False

        extracted_age = int(match.group(1))
        extracted_name = match.group(2)

        # 年齢一致
        if extracted_age != age:
            return False

        # 人物名含む
        if person_name not in extracted_name:
            return False

        return True


def validate_scores(
    evaluation: "EvaluationResult",
) -> tuple[bool, list[str]]:
    """
    スコアの妥当性を検証

    Args:
        evaluation: 評価結果

    Returns:
        (valid, warnings)
    """
    warnings = []

    if not evaluation:
        return False, ["評価結果なし"]

    # axis_scores検証
    scores = evaluation.axis_scores
    score_values = [
        scores.memorability,
        scores.empathy,
        scores.surprise,
        scores.generation_quality,
        scores.educational_value,
        scores.story_quality,
        scores.factual_density,
        scores.iconic_score,
    ]

    # 全て0の場合は異常
    if all(v == 0.0 for v in score_values):
        warnings.append("全スコアが0")
        return False, warnings

    # 範囲外の値チェック
    for name, val in [
        ("memorability", scores.memorability),
        ("empathy", scores.empathy),
        ("surprise", scores.surprise),
        ("generation_quality", scores.generation_quality),
        ("educational_value", scores.educational_value),
        ("story_quality", scores.story_quality),
        ("factual_density", scores.factual_density),
        ("iconic_score", scores.iconic_score),
    ]:
        if val < 0 or val > 100:
            warnings.append(f"{name}が範囲外: {val}")

    # composite_score検証
    if evaluation.composite_score <= 0:
        warnings.append("composite_scoreが0以下")

    # super_total_score検証
    if evaluation.super_total_score <= 0:
        warnings.append("super_total_scoreが0以下")

    return len(warnings) == 0, warnings


def apply_post_processing(
    episode_text: str,
    person_name: str,
    age: int,
    strict_mode: bool = True,
) -> tuple[str, list[str]]:
    """
    エピソードテキストに後処理を適用（ユーティリティ関数）

    Args:
        episode_text: 生成されたエピソードテキスト
        person_name: 人物名
        age: 年齢
        strict_mode: 厳格モード

    Returns:
        (修正後テキスト, 変更リスト)
    """
    processor = EpisodePostProcessor(strict_mode=strict_mode)
    result = processor.process(episode_text, person_name, age)

    if result.changes:
        logger.debug(f"PostProcess: {person_name}({age}歳) - {', '.join(result.changes)}")

    return result.episode_text, result.changes


def apply_post_processing_with_year_validation(
    episode_text: str,
    person_name: str,
    age: int,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
    strict_mode: bool = True,
) -> tuple[str, list[str], YearRangeValidationResult]:
    """
    Phase 3: 年号検証付き後処理

    エピソードテキストに後処理を適用し、さらに年号範囲の妥当性を検証。

    Args:
        episode_text: 生成されたエピソードテキスト
        person_name: 人物名
        age: 年齢
        birth_year: 生年（None可）
        death_year: 没年（None可、Noneなら存命扱い）
        strict_mode: 厳格モード

    Returns:
        (修正後テキスト, 変更リスト, 年号検証結果)
    """
    # 1. 通常の後処理
    processor = EpisodePostProcessor(strict_mode=strict_mode)
    result = processor.process(episode_text, person_name, age)

    if result.changes:
        logger.debug(f"PostProcess: {person_name}({age}歳) - {', '.join(result.changes)}")

    # 2. 年号範囲検証
    year_validation = validate_year_range(
        result.episode_text,
        birth_year,
        death_year,
        age,
    )

    if not year_validation.passed:
        for violation in year_validation.violations:
            logger.warning(f"YearRangeViolation: {person_name}({age}歳) - {violation}")

    return result.episode_text, result.changes, year_validation
