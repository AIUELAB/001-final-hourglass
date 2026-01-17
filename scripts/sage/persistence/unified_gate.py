#!/usr/bin/env python3
"""
UnifiedGate - DB反映前の最終ゲート

全経路でDB反映前に必須となる統合検証ゲート。
REAL/FICTIONALで検証ルールを分岐し、違反時は不採用（例外発生）またはフラグ付けを行う。

## 統合方法
このクラスは後でSafeCSVWriter._validate_row()に統合される。
単独でも使用可能。

## 使用方法
    gate = UnifiedGate()
    result = gate.validate(row)

    if not result.is_valid:
        if result.auto_fixable:
            # 自動修正可能な場合
            pass
        else:
            raise ValidationError(result.messages)

Author: EPUP Validation Team
Date: 2026-01-17
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# =============================================================================
# 違反タイプ定義
# =============================================================================


class ViolationType(Enum):
    """違反タイプ（プロジェクト共通定義）

    このEnumはプロジェクト全体で共通の違反タイプを定義する。
    csv_writer.py, unified_episode_validator.py等からimportされて使用される。

    Note: 全ての値は snake_case で統一（外部ツール・JSONレポート連携時の一貫性確保）
    """

    # FICTIONAL向け
    META_EXPRESSION = "meta_expression"  # メタ的表現（「原作では」「この作品では」等）
    META_INFO_CONTAMINATION = "meta_info_contamination"  # メタ情報混入
    CANON_VIOLATION = "canon_violation"  # 作品設定違反（キャラ不整合等）
    LLM_CANON_DEVIATION = "llm_canon_deviation"  # LLM創作（カノン逸脱）
    FICTIONAL_AGE_BOUNDARY = "fictional_age_boundary"  # 架空キャラの年齢境界違反
    FICTIONAL_AGE_INCONSISTENCY = "fictional_age_inconsistency"  # 架空キャラ年齢不整合
    ERA_INCONSISTENCY = "era_inconsistency"  # 時代設定不整合（現代年号使用等）
    MODERN_YEAR_IN_FICTIONAL = "modern_year_in_fictional"  # 現代年号使用
    NAME_FORMAT_ERROR = "name_format_error"  # 名前フォーマット違反
    REAL_ENTITY_IN_FICTIONAL = "real_entity_in_fictional"  # 架空世界での現実エンティティ言及
    REAL_INSTITUTION_IN_FICTIONAL = "real_institution_in_fictional"  # 実在機関言及

    # REAL向け
    REAL_AGE_BOUNDARY = "real_age_boundary"  # 実在人物の年齢境界違反
    AGE_EXCEEDS_LIFESPAN = "age_exceeds_lifespan"  # 享年超過
    AGE_EXCEEDS_CURRENT = "age_exceeds_current"  # 現在年齢超過
    BIRTH_AFTER_DEATH = "birth_after_death"  # 生年>没年
    FACT_CHECK_FAIL = "fact_check_fail"  # ファクトチェック失敗
    UNVERIFIED_CLAIM = "unverified_claim"  # 未検証の主張
    DEATH_YEAR_VIOLATION = "death_year_violation"  # 死亡年以降のエピソード
    BIRTH_YEAR_VIOLATION = "birth_year_violation"  # 出生年以前のエピソード

    # 共通
    REQUIRED_FIELD_MISSING = "required_field_missing"  # 必須フィールド欠損
    TEXT_TOO_SHORT = "text_too_short"  # テキスト短すぎ
    DUPLICATE_EPISODE = "duplicate_episode"  # 重複エピソード


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class ValidationResult:
    """検証結果"""

    is_valid: bool
    violations: list[ViolationType] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    auto_fixable: bool = False
    fixed_data: Optional[dict] = None  # 自動修正後のデータ

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "violations": [v.value for v in self.violations],
            "messages": self.messages,
            "auto_fixable": self.auto_fixable,
            "fixed_data": self.fixed_data,
        }

    def add_violation(self, violation_type: ViolationType, message: str) -> None:
        """違反を追加"""
        self.violations.append(violation_type)
        self.messages.append(message)
        self.is_valid = False


class ValidationError(Exception):
    """検証エラー例外"""

    def __init__(self, result: ValidationResult):
        self.result = result
        messages = "; ".join(result.messages)
        super().__init__(f"Validation failed: {messages}")


# =============================================================================
# 検出パターン定義
# =============================================================================

# 年号パターン（西暦）
YEAR_PATTERN = re.compile(r"(19[0-9]{2}|20[0-2][0-9])年")

# メタ的表現パターン
META_EXPRESSION_PATTERNS = [
    r"この(?:作品|アニメ|漫画|マンガ)(?:では|において|の中で)",
    r"(?:原作|漫画版|アニメ版|映画版|実写版)(?:では|において|の中で|と(?:は|の)違い)",
    r"(?:連載|放送)(?:当時|開始時|終了時)",
    r"(?:作者|原作者)(?:が描いた|の意図|によると)",
    r"(?:ストーリー|展開)(?:上の都合|として設定)",
    r"(?:設定|世界観)(?:上は|として)",
    r"(?:読者|視聴者|ファン)(?:に向けて|から見ると|の間で話題)",
    r"(?:伏線|フラグ)(?:が回収|を張)",
    r"(?:ベストセラー|大ヒット作)(?:として|になった)",
    r"(?:アワード|漫画賞|アニメ賞)(?:を受賞|にノミネート)",
]

# 作品タイトルパターン（メタ参照検出用）
WORK_TITLES = [
    "鬼滅の刃",
    "るろうに剣心",
    "進撃の巨人",
    "ONE PIECE",
    "NARUTO",
    "ドラゴンボール",
    "ハリー・ポッター",
    "呪術廻戦",
    "BLEACH",
    "HUNTER×HUNTER",
]

# 名前フォーマット違反パターン（「名（姓）」形式）
NAME_FORMAT_ERROR_PATTERNS = [
    (r"^([ァ-ヶー]{2,})（([ァ-ヶー]{2,})）$", "カタカナ名（姓）"),
    (r"^([ぁ-ん]{2,})（([ぁ-ん]{2,})）$", "ひらがな名（姓）"),
    (r"^(.{1,5})（(.{1,5})）$", "一般名（姓）"),
]

# 歴史作品の時代設定
HISTORICAL_WORK_SETTINGS = {
    "鬼滅の刃": {
        "era_name": "大正時代",
        "era_start": 1912,
        "era_end": 1926,
        "prohibited_years": range(1945, 2030),
    },
    "るろうに剣心": {
        "era_name": "明治時代",
        "era_start": 1868,
        "era_end": 1912,
        "prohibited_years": range(1930, 2030),
    },
    "進撃の巨人": {
        "era_name": "独自年号",
        "era_start": 845,
        "era_end": 860,
        "prohibited_years": range(1000, 2030),
    },
    "ONE PIECE": {
        "era_name": "架空世界",
        "era_start": None,
        "era_end": None,
        "prohibited_years": range(1000, 2030),
    },
    "NARUTO": {
        "era_name": "架空世界",
        "era_start": None,
        "era_end": None,
        "prohibited_years": range(1000, 2030),
    },
}

# 現代カテゴリ（時代錯誤チェック対象）
MODERN_CATEGORIES = {"エンタメ", "芸能", "スポーツ", "アイドル"}

# 定数
MAX_HUMAN_AGE = 120
MODERN_CATEGORY_BIRTH_CUTOFF = 1920
MIN_EPISODE_TEXT_LENGTH = 100


# =============================================================================
# UnifiedGate クラス
# =============================================================================


class UnifiedGate:
    """
    DB反映前の最終ゲート

    全経路でDB反映前に必須となる統合検証ゲート。
    REAL/FICTIONALで検証ルールを分岐する。
    """

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: True の場合、違反時に例外を発生させる
        """
        self.strict_mode = strict_mode

        # 正規表現のコンパイル
        self._meta_pattern = re.compile("|".join(META_EXPRESSION_PATTERNS))
        self._work_title_pattern = re.compile(rf"[「『]({'|'.join(re.escape(t) for t in WORK_TITLES)})[」』]")

    def validate(self, row: dict) -> ValidationResult:
        """
        行を検証し、結果を返す

        Args:
            row: エピソードデータ（dict形式）

        Returns:
            ValidationResult: 検証結果

        Raises:
            ValidationError: strict_modeがTrueで違反がある場合
        """
        result = ValidationResult(is_valid=True)

        # 1. 共通の必須フィールドチェック
        self._validate_required_fields(row, result)
        if not result.is_valid and self.strict_mode:
            raise ValidationError(result)

        # 2. person_typeに基づいて分岐
        person_type = self._normalize_person_type(row.get("person_type", ""))

        if person_type == "FICTIONAL":
            fictional_result = self._validate_fictional(row)
            self._merge_results(result, fictional_result)
        elif person_type == "REAL":
            real_result = self._validate_real(row)
            self._merge_results(result, real_result)

        # strict_modeでは違反時に例外
        if not result.is_valid and self.strict_mode:
            raise ValidationError(result)

        return result

    def _validate_required_fields(self, row: dict, result: ValidationResult) -> None:
        """共通の必須フィールドチェック"""
        required_fields = ["person_id", "person_name", "age", "episode_text"]

        for field_name in required_fields:
            value = row.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                result.add_violation(
                    ViolationType.REQUIRED_FIELD_MISSING,
                    f"必須フィールド '{field_name}' が欠損しています",
                )

        # テキスト長チェック
        episode_text = str(row.get("episode_text", ""))
        if len(episode_text) < MIN_EPISODE_TEXT_LENGTH:
            result.add_violation(
                ViolationType.TEXT_TOO_SHORT,
                f"エピソードテキストが短すぎます（{len(episode_text)}文字 < {MIN_EPISODE_TEXT_LENGTH}文字）",
            )

    def _validate_fictional(self, row: dict) -> ValidationResult:
        """FICTIONAL向け検証"""
        result = ValidationResult(is_valid=True)

        person_name = str(row.get("person_name", ""))
        episode_text = str(row.get("episode_text", ""))
        work_title = str(row.get("work_title", ""))

        # 1. メタ表現チェック
        self._check_meta_expression(episode_text, result)

        # 2. 時代整合性チェック（歴史作品のみ）
        self._check_era_consistency(episode_text, work_title, person_name, result)

        # 3. 名前フォーマットチェック
        self._check_name_format(person_name, result)

        # 4. 作品名直接言及チェック
        self._check_work_title_reference(episode_text, result)

        return result

    def _validate_real(self, row: dict) -> ValidationResult:
        """REAL向け検証"""
        result = ValidationResult(is_valid=True)

        age = self._safe_int(row.get("age"))
        birth_year = self._safe_int(row.get("birth_year"))
        death_year = self._safe_int(row.get("death_year"))
        category = str(row.get("category", ""))

        # 1. 年齢境界チェック（birth_year / death_year がある場合）
        self._check_age_boundary(age, birth_year, death_year, result)

        # 2. 未来年齢チェック（存命人物）
        self._check_future_age(age, birth_year, death_year, result)

        # 3. 超長寿チェック
        self._check_super_longevity(birth_year, death_year, result)

        # 4. 時代錯誤チェック
        self._check_era_mismatch(birth_year, category, result)

        # 5. 生年・没年の時系列チェック
        self._check_birth_death_order(birth_year, death_year, result)

        return result

    def _normalize_person_type(self, value: str) -> str:
        """person_typeを正規化"""
        if not value or (isinstance(value, float) and pd.isna(value)):
            # 空値の場合はUNKNOWN（normalize_person_type.pyと整合性を取る）
            return "UNKNOWN"

        normalized = str(value).upper().strip()

        # バリエーション対応
        if normalized in ("FICTIONAL", "FICTION", "FICTIONARY"):
            return "FICTIONAL"
        if normalized in ("REAL", "REALITY", "HISTORICAL"):
            return "REAL"
        if normalized == "UNKNOWN":
            return "UNKNOWN"
        if "FICTIONAL" in normalized:
            return "FICTIONAL"

        # 不明な値はUNKNOWNとして扱う
        return "UNKNOWN"

    # =========================================================================
    # FICTIONAL向け検証メソッド
    # =========================================================================

    def _check_meta_expression(self, episode_text: str, result: ValidationResult) -> None:
        """メタ的表現チェック"""
        matches = self._meta_pattern.findall(episode_text)
        if matches:
            result.add_violation(
                ViolationType.META_EXPRESSION,
                f"メタ表現を検出: {matches[:3]}",  # 最大3件表示
            )

    def _check_era_consistency(
        self,
        episode_text: str,
        work_title: str,
        person_name: str,
        result: ValidationResult,
    ) -> None:
        """時代整合性チェック"""
        # 作品設定を特定
        era_setting = self._get_era_setting(work_title, person_name)
        if era_setting is None:
            return

        prohibited_years = era_setting.get("prohibited_years", [])
        if not prohibited_years:
            return

        # 年号を抽出
        found_years = YEAR_PATTERN.findall(episode_text)
        for year_str in found_years:
            year = int(year_str)
            if year in prohibited_years:
                result.add_violation(
                    ViolationType.ERA_INCONSISTENCY,
                    f"歴史設定作品に現代年号を検出: {year}年（{era_setting.get('era_name', '不明')}）",
                )

    def _check_name_format(self, person_name: str, result: ValidationResult) -> None:
        """名前フォーマットチェック"""
        for pattern, pattern_name in NAME_FORMAT_ERROR_PATTERNS:
            if re.match(pattern, person_name):
                result.add_violation(
                    ViolationType.NAME_FORMAT_ERROR,
                    f"名前フォーマット違反: {pattern_name}形式（{person_name}）",
                )
                break

    def _check_work_title_reference(self, episode_text: str, result: ValidationResult) -> None:
        """作品名直接言及チェック"""
        matches = self._work_title_pattern.findall(episode_text)
        if matches:
            result.add_violation(
                ViolationType.META_EXPRESSION,
                f"作品名の直接言及を検出: {matches[:3]}",
            )

    def _get_era_setting(self, work_title: str, person_name: str) -> Optional[dict]:
        """作品の時代設定を取得"""
        # 作品タイトルから検索
        if work_title and str(work_title) != "nan":
            for title_key, setting in HISTORICAL_WORK_SETTINGS.items():
                if title_key in work_title:
                    return setting

        # 人物名から推定（鬼滅の刃キャラクター等）
        kimetsu_chars = [
            "竈門炭治郎",
            "竈門禰豆子",
            "我妻善逸",
            "嘴平伊之助",
            "栗花落カナヲ",
            "煉獄杏寿郎",
            "胡蝶しのぶ",
            "冨岡義勇",
            "宇髄天元",
            "甘露寺蜜璃",
            "時透無一郎",
        ]
        if person_name in kimetsu_chars:
            return HISTORICAL_WORK_SETTINGS["鬼滅の刃"]

        return None

    # =========================================================================
    # REAL向け検証メソッド
    # =========================================================================

    def _check_age_boundary(
        self,
        age: Optional[int],
        birth_year: Optional[int],
        death_year: Optional[int],
        result: ValidationResult,
    ) -> None:
        """年齢境界チェック（享年超過）"""
        if age is None or birth_year is None or death_year is None:
            return

        max_age = death_year - birth_year
        if age > max_age:
            result.add_violation(
                ViolationType.REAL_AGE_BOUNDARY,
                f"年齢が享年を超過: age={age} > max_age={max_age}（{birth_year}-{death_year}）",
            )

    def _check_future_age(
        self,
        age: Optional[int],
        birth_year: Optional[int],
        death_year: Optional[int],
        result: ValidationResult,
    ) -> None:
        """未来年齢チェック（存命人物）"""
        # 故人はチェック不要
        if death_year is not None:
            return

        if age is None or birth_year is None:
            return

        current_year = datetime.now().year
        current_age = current_year - birth_year

        if age > current_age:
            result.add_violation(
                ViolationType.REAL_AGE_BOUNDARY,
                f"年齢が現在年齢を超過: age={age} > current_age={current_age}（存命人物）",
            )

    def _check_super_longevity(
        self,
        birth_year: Optional[int],
        death_year: Optional[int],
        result: ValidationResult,
    ) -> None:
        """超長寿チェック（120歳以上で存命扱い）"""
        # 故人はチェック不要
        if death_year is not None:
            return

        if birth_year is None:
            return

        current_year = datetime.now().year
        current_age = current_year - birth_year

        if current_age > MAX_HUMAN_AGE:
            result.add_violation(
                ViolationType.REAL_AGE_BOUNDARY,
                f"超長寿で存命扱い: {current_age}歳（{birth_year}年生まれ、120歳超過）",
            )

    def _check_era_mismatch(
        self,
        birth_year: Optional[int],
        category: str,
        result: ValidationResult,
    ) -> None:
        """時代錯誤チェック（現代カテゴリで1920年以前生まれ）"""
        if birth_year is None or not category:
            return

        if birth_year < MODERN_CATEGORY_BIRTH_CUTOFF and category in MODERN_CATEGORIES:
            result.add_violation(
                ViolationType.FACT_CHECK_FAIL,
                f"時代錯誤: {category}カテゴリなのに{birth_year}年生まれ（1920年以前）",
            )

    def _check_birth_death_order(
        self,
        birth_year: Optional[int],
        death_year: Optional[int],
        result: ValidationResult,
    ) -> None:
        """生年・没年の時系列チェック"""
        if birth_year is None or death_year is None:
            return

        if birth_year > death_year:
            result.add_violation(
                ViolationType.BIRTH_YEAR_VIOLATION,
                f"時系列矛盾: birth_year={birth_year} > death_year={death_year}",
            )

    # =========================================================================
    # ユーティリティ
    # =========================================================================

    def _safe_int(self, value, field_name: str = "") -> Optional[int]:
        """安全にintに変換（変換失敗時はログを残す）"""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError) as e:
            if value and str(value).strip():
                logger.warning(f"Failed to convert '{value}' to int for field '{field_name}': {e}")
            return None

    def _merge_results(self, target: ValidationResult, source: ValidationResult) -> None:
        """検証結果をマージ"""
        if not source.is_valid:
            target.is_valid = False
            target.violations.extend(source.violations)
            target.messages.extend(source.messages)

        if source.auto_fixable:
            target.auto_fixable = True
            target.fixed_data = source.fixed_data


# =============================================================================
# ユーティリティ関数
# =============================================================================


def validate_episode_row(row: dict, strict: bool = True) -> ValidationResult:
    """
    エピソード行を検証（シンプルAPI）

    Args:
        row: エピソードデータ
        strict: True の場合、違反時に例外を発生させる

    Returns:
        ValidationResult: 検証結果
    """
    gate = UnifiedGate(strict_mode=strict)
    return gate.validate(row)


def check_and_raise(row: dict) -> None:
    """
    エピソード行を検証し、違反があれば例外を発生

    Args:
        row: エピソードデータ

    Raises:
        ValidationError: 違反がある場合
    """
    gate = UnifiedGate(strict_mode=True)
    gate.validate(row)


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UnifiedGate - DB反映前の最終ゲート")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="デモモードで実行",
    )

    args = parser.parse_args()

    if args.demo:
        # デモエピソード
        demo_episodes = [
            {
                "person_id": "P001",
                "person_name": "竈門炭治郎",
                "age": 15,
                "episode_text": "2019年、竈門炭治郎は「鬼滅の刃」の主人公として原作では大活躍した。" * 3,
                "person_type": "FICTIONAL",
                "work_title": "鬼滅の刃",
            },
            {
                "person_id": "P002",
                "person_name": "手塚治虫",
                "age": 200,  # 違反
                "episode_text": "漫画の神様として知られる手塚治虫は、多くの作品を生み出した。" * 3,
                "person_type": "REAL",
                "birth_year": 1928,
                "death_year": 1989,
                "category": "文化",
            },
            {
                "person_id": "P003",
                "person_name": "正常なREAL人物",
                "age": 50,
                "episode_text": "50歳の時、彼は重要な決断を下した。その決断は後の人生を大きく変えることになった。" * 3,
                "person_type": "REAL",
                "birth_year": 1970,
                "category": "経済",
            },
        ]

        print("=" * 70)
        print("UnifiedGate デモ")
        print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        gate = UnifiedGate(strict_mode=False)

        for i, episode in enumerate(demo_episodes, 1):
            print(f"\n[Episode {i}] {episode['person_name']}")
            print(f"Type: {episode['person_type']}")

            result = gate.validate(episode)

            print(f"Valid: {result.is_valid}")
            if result.violations:
                print("Violations:")
                for v, msg in zip(result.violations, result.messages):
                    print(f"  - [{v.value}] {msg}")

        print("\n" + "=" * 70)
        print("デモ完了")
