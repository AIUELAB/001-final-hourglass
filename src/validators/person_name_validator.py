#!/usr/bin/env python3
"""
PersonNameValidator - 人物名バリデーション

機能:
1. グループ名検出
2. 連結名パターン検出
3. 表記ゆれ検出
4. 自動修正提案
"""

import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.group_master import (
    GROUP_ENTITIES,
    GROUP_MEMBER_MAP,
    DISPERSION_RULES,
    DispersionStrategy,
)


class IssueType(Enum):
    """検出された問題の種類"""

    GROUP_AS_PERSON = "group_as_person"
    CONCATENATED_NAME = "concatenated_name"
    VARIANT_NAME = "variant_name"
    UNKNOWN_GROUP = "unknown_group"
    ORG_TITLE_CONTAMINATION = "org_title_contamination"  # 組織名・肩書き混入
    INVALID_NAME = "invalid_name"  # 不正な人物名（道具名・アイテム名等）


class Severity(Enum):
    """問題の重大度"""

    ERROR = "error"  # 即時修正必要
    WARNING = "warning"  # 修正推奨
    INFO = "info"  # 情報のみ


@dataclass
class ValidationIssue:
    """バリデーション問題"""

    issue_type: IssueType
    severity: Severity
    person_name: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fixed_value: Optional[str] = None


class PersonNameValidator:
    """人物名バリデータ"""

    # グループ名＋個人名の区切りパターン
    SEPARATORS = ["・", "（", "(", "／", "/", "　", " "]

    # 誤検出除外パターン（グループ名と同名だが個人名として正しいもの）
    EXCLUDE_PERSON_NAMES = {
        # お笑いコンビ「オードリー」と同名の女優
        "オードリー・ヘプバーン",
        "オードリー・タトゥ",
    }

    def __init__(self):
        """初期化"""
        self.group_entities = GROUP_ENTITIES
        self.group_member_map = GROUP_MEMBER_MAP
        self.dispersion_rules = DISPERSION_RULES

        # ブラックリスト読み込み
        self.blacklist = self._load_blacklist()

        # 組織名・肩書き混入検出用のnormalizer（遅延初期化）
        self._normalizer = None

    def validate(self, person_name: str) -> list[ValidationIssue]:
        """
        人物名をバリデーション

        Args:
            person_name: 検証対象の人物名

        Returns:
            検出された問題のリスト
        """
        issues: list[ValidationIssue] = []

        if not person_name:
            return issues

        # 除外パターンをチェック
        if person_name in self.EXCLUDE_PERSON_NAMES:
            return issues

        # 1. グループ名が直接登録されていないか
        group_issue = self._check_group_as_person(person_name)
        if group_issue:
            issues.append(group_issue)

        # 2. グループ名＋個人名の連結パターンか
        concat_issue = self._check_concatenated_name(person_name)
        if concat_issue:
            issues.append(concat_issue)

        # 3. 組織名・肩書き混入チェック（新規）
        org_title_issue = self._check_org_title_contamination(person_name)
        if org_title_issue:
            issues.append(org_title_issue)

        # 4. 別名・通称チェック（2025-12-15追加）★NEW
        alias_issue = self._check_alias_usage(person_name)
        if alias_issue:
            issues.append(alias_issue)

        # 5. ブラックリストチェック（2025-12-15追加）★NEW
        blacklist_issue = self._check_blacklist(person_name)
        if blacklist_issue:
            issues.append(blacklist_issue)

        # 6. 道具名・アイテム名チェック（2025-12-15追加）★NEW
        item_issue = self._check_item_name_pattern(person_name)
        if item_issue:
            issues.append(item_issue)

        # 7. 後置詞型パターンチェック（2025-12-16追加）★NEW
        suffix_issue = self._check_suffix_patterns(person_name)
        if suffix_issue:
            issues.append(suffix_issue)

        return issues

    def _check_group_as_person(self, person_name: str) -> Optional[ValidationIssue]:
        """
        グループ名が人物名として登録されていないかチェック

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        if person_name in self.group_entities:
            # DISPERSION_RULESにルールがあるか確認
            if person_name in self.dispersion_rules:
                rule = self.dispersion_rules[person_name]
                if rule.strategy == DispersionStrategy.ALL:
                    suggestion = f"全メンバーに分散: {rule.members}"
                else:
                    suggestion = f"代表メンバーに変換: {rule.members[0]}"
                fixed_value = rule.members[0] if rule.members else None
            else:
                suggestion = "DISPERSION_RULESにルール追加が必要"
                fixed_value = None

            return ValidationIssue(
                issue_type=IssueType.GROUP_AS_PERSON,
                severity=Severity.ERROR,
                person_name=person_name,
                message=f"グループ名 '{person_name}' が人物名として登録されています",
                suggestion=suggestion,
                auto_fixable=fixed_value is not None,
                fixed_value=fixed_value,
            )

        return None

    def _check_concatenated_name(self, person_name: str) -> Optional[ValidationIssue]:
        """
        グループ名＋個人名の連結パターンをチェック

        例: "ビートルズ・ジョン・レノン" → "ジョン・レノン"

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        for group in self.group_entities:
            for sep in self.SEPARATORS:
                prefix = f"{group}{sep}"
                if person_name.startswith(prefix):
                    individual = person_name[len(prefix) :]

                    # 閉じ括弧を除去
                    individual = individual.rstrip("）)")

                    if individual:
                        return ValidationIssue(
                            issue_type=IssueType.CONCATENATED_NAME,
                            severity=Severity.ERROR,
                            person_name=person_name,
                            message=f"グループ名 '{group}' と個人名 '{individual}' が連結されています",
                            suggestion=f"個人名 '{individual}' のみに分離",
                            auto_fixable=True,
                            fixed_value=individual,
                        )

        return None

    def _get_normalizer(self):
        """PersonNameNormalizerを遅延初期化して取得"""
        if self._normalizer is None:
            # 循環インポート回避のため、ここでインポート
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from scripts.normalize_person_names import PersonNameNormalizer

            self._normalizer = PersonNameNormalizer(min_confidence=0.85)
        return self._normalizer

    def _check_org_title_contamination(self, person_name: str) -> Optional[ValidationIssue]:
        """
        組織名・肩書き混入をチェック

        例:
        - 「日本人実業家の稲盛和夫」 → 「稲盛和夫」
        - 「辻調 辻芳樹」 → 「辻芳樹」
        - 「維新松井一郎」 → 「松井一郎」
        - 「お笑い・とんねるず石橋貴明」 → 「石橋貴明」

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        normalizer = self._get_normalizer()
        result = normalizer.normalize(person_name)

        if result:
            # 正規化が必要 = 組織名・肩書き混入あり
            detail = f"パターン: {result.pattern_type}"
            if result.title:
                detail += f", 肩書: {result.title}"
            if result.affiliation:
                detail += f", 所属: {result.affiliation}"

            return ValidationIssue(
                issue_type=IssueType.ORG_TITLE_CONTAMINATION,
                severity=Severity.ERROR,
                person_name=person_name,
                message=f"人物名に組織名・肩書きが混入: '{person_name}' → '{result.normalized_name}' ({detail})",
                suggestion=f"正規化後の名前 '{result.normalized_name}' を使用してください",
                auto_fixable=True,
                fixed_value=result.normalized_name,
            )

        return None

    def _check_alias_usage(self, person_name: str) -> Optional[ValidationIssue]:
        """
        別名・通称の使用を検出

        例: 「山中教授」→「山中伸弥」を使用すべき

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        # normalize_person_names.pyのALIAS_KEYWORDSを参照
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from scripts.normalize_person_names import ALIAS_KEYWORDS

        if person_name in ALIAS_KEYWORDS:
            canonical = ALIAS_KEYWORDS[person_name]
            return ValidationIssue(
                issue_type=IssueType.VARIANT_NAME,
                severity=Severity.WARNING,
                person_name=person_name,
                message=f"別名「{person_name}」が使用されています",
                suggestion=f"正規表記「{canonical}」を使用してください",
                auto_fixable=True,
                fixed_value=canonical,
            )

        return None

    def _check_item_name_pattern(self, person_name: str) -> Optional[ValidationIssue]:
        """
        道具名・アイテム名パターンの検出（ERR-005）

        検出パターン:
        - 道具接尾辞: ギプス、マシン、装置、道具
        - 物品接尾辞: アイテム、グッズ、ツール
        - 機械接尾辞: ロボット、メカ、システム

        Args:
            person_name: 検証対象の人物名

        Returns:
            問題が検出された場合はValidationIssue、なければNone
        """
        ITEM_SUFFIXES = [
            "ギプス",
            "マシン",
            "装置",
            "道具",
            "アイテム",
            "グッズ",
            "ツール",
            "ロボット",
            "メカ",
            "システム",
            "デバイス",
            "マスク",
            "スーツ",
        ]

        # 接尾辞チェック
        for suffix in ITEM_SUFFIXES:
            if person_name.endswith(suffix):
                return ValidationIssue(
                    issue_type=IssueType.INVALID_NAME,
                    severity=Severity.ERROR,
                    person_name=person_name,
                    message=f"道具名・アイテム名の可能性: 「{person_name}」は「{suffix}」で終わっています（ERR-005）",
                    suggestion="実在する人物名であることを確認してください",
                    auto_fixable=False,
                    fixed_value=None,
                )

        # 完全一致パターン（明らかな道具名・架空アイテム）
        OBVIOUS_ITEMS = ["秘密道具", "必殺技", "魔法", "呪文", "スキル"]

        for item in OBVIOUS_ITEMS:
            if item in person_name:
                return ValidationIssue(
                    issue_type=IssueType.INVALID_NAME,
                    severity=Severity.ERROR,
                    person_name=person_name,
                    message=f"架空アイテムの可能性: 「{person_name}」に「{item}」が含まれています（ERR-005）",
                    suggestion="実在する人物名であることを確認してください",
                    auto_fixable=False,
                    fixed_value=None,
                )

        return None

    def _check_suffix_patterns(self, person_name: str) -> Optional[ValidationIssue]:
        """
        後置詞型パターンの検出（役職/敬称/学術/関係）

        検出パターン:
        - 役職: 監督、議員、社長、CEO等
        - 敬称: 氏、さん、様、殿、君
        - 学術: 博士、教授、准教授等
        - 関係: 夫人（個人名不明確なケースのみエラー）

        Args:
            person_name: 検証対象の人物名

        Returns:
            問題が検出された場合はValidationIssue、なければNone
        """
        SUFFIX_KEYWORDS = {
            "役職": [
                "監督",
                "コーチ",
                "議員",
                "上院議員",
                "下院議員",
                "代議士",
                "大統領",
                "首相",
                "総理",
                "知事",
                "市長",
                "区長",
                "大臣",
                "長官",
                "部長",
                "課長",
                "主任",
                "会長",
                "社長",
                "副社長",
                "CEO",
                "CTO",
                "CFO",
                "リーダー",
                "キャプテン",
                "選手",
                "プレーヤー",
            ],
            "敬称": ["氏", "さん", "様", "殿", "君"],
            "学術": ["博士", "教授", "准教授", "助教授", "名誉教授", "先生", "師範", "師匠", "名人", "博士号"],
            "関係": [
                "夫人",  # 注：「夫」「子」は日本人名に頻出するため除外
            ],
        }

        for category, suffixes in SUFFIX_KEYWORDS.items():
            for suffix in suffixes:
                if person_name.endswith(suffix):
                    base_name = person_name[: -len(suffix)]

                    # base_nameが短すぎる場合はスキップ（誤検出防止）
                    if len(base_name) < 2:
                        continue

                    # 優先度と重大度の判定
                    severity = Severity.INFO
                    message = ""
                    suggestion = None

                    if category == "関係":
                        severity = Severity.ERROR
                        message = f"{category}語「{suffix}」が含まれています: 個人名が不明確です。本文から個人名を特定してください。"
                        suggestion = f"本文から個人名を特定して「{base_name}」を正しい個人名に変更してください"
                    elif len(base_name) <= 3 and category == "役職":
                        severity = Severity.WARNING
                        message = f"{category}語「{suffix}」が含まれています: 姓のみ+役職、同姓別人のリスクがあります"
                        suggestion = f"フルネーム+役職（例: 「{base_name}[名] {suffix}」）に変更することを推奨します"
                    elif category == "敬称":
                        severity = Severity.INFO
                        message = (
                            f"{category}「{suffix}」が含まれています: 許容されますが、フルネームの確認を推奨します"
                        )
                        suggestion = None
                    else:
                        severity = Severity.INFO
                        message = f"{category}語「{suffix}」が含まれています: フルネーム+後置詞で識別が明確であれば維持できます"
                        suggestion = None

                    return ValidationIssue(
                        issue_type=IssueType.ORG_TITLE_CONTAMINATION,
                        severity=severity,
                        person_name=person_name,
                        message=message,
                        suggestion=suggestion,
                        auto_fixable=False,
                        fixed_value=None,
                    )

        return None

    def _load_blacklist(self) -> dict[str, list]:
        """
        ブラックリストの読み込み

        Returns:
            ブラックリスト辞書（blacklist, patterns）
        """
        blacklist_path = Path(__file__).parent.parent.parent / "config" / "blacklist_names.json"
        if blacklist_path.exists():
            try:
                with open(blacklist_path, "r", encoding="utf-8") as f:
                    data: dict[str, list] = json.load(f)
                    return data
            except (json.JSONDecodeError, OSError):
                # ファイルが壊れている場合は空のブラックリストを返す
                return {"blacklist": [], "patterns": []}
        return {"blacklist": [], "patterns": []}

    def _check_blacklist(self, person_name: str) -> Optional[ValidationIssue]:
        """
        ブラックリストチェック

        Args:
            person_name: 検証対象の人物名

        Returns:
            問題が検出された場合はValidationIssue、なければNone
        """
        # 完全一致チェック
        for entry in self.blacklist.get("blacklist", []):
            if person_name == entry["name"]:
                return ValidationIssue(
                    issue_type=IssueType.INVALID_NAME,
                    severity=Severity.ERROR,
                    person_name=person_name,
                    message=f"ブラックリスト該当: {entry['reason']}",
                    suggestion="この名前は使用できません",
                    auto_fixable=False,
                    fixed_value=None,
                )

        # パターンマッチ
        for pattern in self.blacklist.get("patterns", []):
            if re.match(pattern, person_name):
                return ValidationIssue(
                    issue_type=IssueType.INVALID_NAME,
                    severity=Severity.WARNING,
                    person_name=person_name,
                    message=f"ブラックリストパターンに該当: {pattern}",
                    suggestion="この名前パターンは注意が必要です",
                    auto_fixable=False,
                    fixed_value=None,
                )

        return None

    def validate_batch(self, person_names: list[str]) -> dict:
        """
        複数の人物名をバリデーション

        Args:
            person_names: 人物名リスト

        Returns:
            {
                "total": 検証数,
                "valid": 問題なし数,
                "invalid": 問題あり数,
                "issues": 問題リスト,
                "auto_fixable": 自動修正可能数,
            }
        """
        all_issues = []

        for name in person_names:
            issues = self.validate(name)
            all_issues.extend(issues)

        auto_fixable = [i for i in all_issues if i.auto_fixable]

        return {
            "total": len(person_names),
            "valid": len(person_names) - len(set(i.person_name for i in all_issues)),
            "invalid": len(set(i.person_name for i in all_issues)),
            "issues": all_issues,
            "auto_fixable": len(auto_fixable),
        }

    def auto_fix(self, person_name: str) -> tuple[str, Optional[ValidationIssue]]:
        """
        人物名を自動修正

        Args:
            person_name: 人物名

        Returns:
            (修正後の名前, 修正した問題) のタプル
            修正不要/不可能な場合は (元の名前, None)
        """
        issues = self.validate(person_name)

        for issue in issues:
            if issue.auto_fixable and issue.fixed_value:
                return issue.fixed_value, issue

        return person_name, None

    def get_canonical_info(self, person_name: str) -> dict:
        """
        人物名から正規化された情報を取得

        Args:
            person_name: 人物名

        Returns:
            {
                "canonical_name": 正規化された個人名,
                "group_name": グループ名（所属があれば）,
                "is_group_member": グループメンバーかどうか,
                "needs_correction": 修正が必要かどうか,
                "original_name": 元の名前,
            }
        """
        result: dict[str, str | bool | None] = {
            "canonical_name": person_name,
            "group_name": None,
            "is_group_member": None,
            "needs_correction": False,
            "original_name": person_name,
        }

        # 自動修正を試行
        fixed_name, issue = self.auto_fix(person_name)

        if issue:
            result["canonical_name"] = fixed_name
            result["needs_correction"] = True

            # 連結パターンの場合はグループ名を抽出
            if issue.issue_type == IssueType.CONCATENATED_NAME:
                # グループ名を取得（メッセージからパース）
                for group in self.group_entities:
                    for sep in self.SEPARATORS:
                        if person_name.startswith(f"{group}{sep}"):
                            result["group_name"] = group
                            result["is_group_member"] = True
                            break

        # グループマスタから情報を補完
        canonical_name = result["canonical_name"]
        if isinstance(canonical_name, str) and canonical_name in self.group_member_map:
            result["group_name"] = self.group_member_map[canonical_name]
            result["is_group_member"] = True

        return result


# シングルトンインスタンス
_validator = None


def get_validator() -> PersonNameValidator:
    """バリデータのシングルトンインスタンスを取得"""
    global _validator
    if _validator is None:
        _validator = PersonNameValidator()
    return _validator


def validate_before_episode_generation(
    person_name: str, person_type: str = "REAL", group_name: Optional[str] = None
) -> tuple[bool, str, Optional[dict]]:
    """
    エピソード生成前に人物名を検証（簡易版API）

    Args:
        person_name: 人物名
        person_type: 人物タイプ
        group_name: グループ名

    Returns:
        (is_valid, message, suggested_fix)
    """
    validator = get_validator()
    issues = validator.validate(person_name)

    errors = [i for i in issues if i.severity == Severity.ERROR]

    if errors:
        first_error = errors[0]
        suggested_fix: Optional[dict[str, str | bool]] = None
        if first_error.auto_fixable and first_error.fixed_value:
            suggested_fix = {
                "person_name": first_error.fixed_value,
            }
            # グループ名を抽出
            canonical_info = validator.get_canonical_info(person_name)
            group_name = canonical_info.get("group_name")
            if group_name and isinstance(group_name, str):
                suggested_fix["group_name"] = group_name
                suggested_fix["is_group_member"] = True

        return False, first_error.message, suggested_fix

    return True, "OK", None
