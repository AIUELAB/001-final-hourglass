#!/usr/bin/env python3
"""
データ整合性チェックシステム
データの妥当性、一貫性、完全性を検証

作成日: 2025-08-31
Ultra Think Mode対応
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd


class IntegrityChecker:
    """
    データ整合性チェックシステム
    - データ妥当性検証
    - 一貫性チェック
    - 完全性確認
    - 自動修復機能
    """

    def __init__(self, rules_file: str = "integrity_rules.json"):
        self.rules_file = Path(rules_file)
        self.logger = logging.getLogger(__name__)

        # ルール定義
        self.rules = self._load_rules()

        # チェック結果
        self.check_results = []
        self.error_count = 0
        self.warning_count = 0

        # 修復履歴
        self.repair_history = []

        self.logger.info("✅ IntegrityChecker初期化完了")

    def _load_rules(self) -> Dict[str, Any]:
        """整合性ルールを読み込み"""
        default_rules = {
            "required_columns": ["person_id", "person_name", "person_name_display", "person_name_ja", "birth_year"],
            "unique_columns": ["person_id"],
            "patterns": {"person_id": r"^P\d{6}$", "birth_year": r"^\d{4}$|^$"},
            "value_constraints": {
                "birth_year": {"min": 1900, "max": 2025},
                "recognition_score": {"min": 0, "max": 100},
            },
            "duplicate_checks": {
                "parentheses": r"^([^(]+)\s*\(\1\)$",
                "spaces": r"\s{2,}",
                "special_chars": r"[<>\"'\\]",
            },
            "consistency_rules": {
                "name_match": "person_name と person_name_display の整合性",
                "group_consistency": "グループメンバーの整合性",
                "date_format": "日付形式の統一性",
            },
        }

        if self.rules_file.exists():
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    loaded_rules = json.load(f)
                    default_rules.update(loaded_rules)
            except Exception as e:
                self.logger.warning(f"ルール読み込みエラー、デフォルトを使用: {e}")

        return default_rules

    def check_data_integrity(
        self, df: pd.DataFrame, auto_repair: bool = False, detailed_report: bool = True
    ) -> Dict[str, Any]:
        """データ整合性を包括的にチェック"""
        self.check_results = []
        self.error_count = 0
        self.warning_count = 0

        # 1. 構造チェック
        structure_ok = self._check_structure(df)

        # 2. データ型チェック
        types_ok = self._check_data_types(df)

        # 3. 必須フィールドチェック
        required_ok = self._check_required_fields(df)

        # 4. 一意性チェック
        unique_ok = self._check_uniqueness(df)

        # 5. パターンマッチングチェック
        patterns_ok = self._check_patterns(df)

        # 6. 値の制約チェック
        constraints_ok = self._check_value_constraints(df)

        # 7. 重複・異常パターンチェック
        duplicates_ok = self._check_duplicate_patterns(df)

        # 8. 一貫性チェック
        consistency_ok = self._check_consistency(df)

        # 9. データ完全性チェック
        completeness = self._check_completeness(df)

        # 自動修復
        if auto_repair and (self.error_count > 0 or self.warning_count > 0):
            df = self._auto_repair(df)

        # レポート生成
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_rows": len(df),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "checks": {
                "structure": structure_ok,
                "data_types": types_ok,
                "required_fields": required_ok,
                "uniqueness": unique_ok,
                "patterns": patterns_ok,
                "constraints": constraints_ok,
                "duplicates": duplicates_ok,
                "consistency": consistency_ok,
                "completeness": completeness,
            },
            "is_valid": self.error_count == 0,
            "details": self.check_results if detailed_report else [],
        }

        return report

    def _check_structure(self, df: pd.DataFrame) -> bool:
        """データ構造をチェック"""
        is_valid = True

        # 必須カラムの存在確認
        for col in self.rules["required_columns"]:
            if col not in df.columns:
                self._add_error(f"必須カラム '{col}' が存在しません")
                is_valid = False

        # カラム名の妥当性チェック
        invalid_chars = re.compile(r"[^\w\s_]")
        for col in df.columns:
            if invalid_chars.search(col):
                self._add_warning(f"カラム名 '{col}' に無効な文字が含まれています")

        return is_valid

    def _check_data_types(self, df: pd.DataFrame) -> bool:
        """データ型をチェック"""
        is_valid = True

        # 数値型であるべきカラム
        numeric_columns = ["birth_year", "recognition_score", "episode_count"]
        for col in numeric_columns:
            if col in df.columns:
                non_numeric = df[col].apply(lambda x: not pd.isna(x) and not str(x).replace(".", "").isdigit())
                if non_numeric.any():
                    count = non_numeric.sum()
                    self._add_error(f"カラム '{col}' に非数値データが{count}件あります")
                    is_valid = False

        return is_valid

    def _check_required_fields(self, df: pd.DataFrame) -> bool:
        """必須フィールドの存在をチェック"""
        is_valid = True

        # person_idは必須
        if "person_id" in df.columns:
            null_count = df["person_id"].isna().sum()
            if null_count > 0:
                self._add_error(f"person_idがNULLのレコードが{null_count}件あります")
                is_valid = False

        # person_nameも必須
        if "person_name" in df.columns:
            null_count = df["person_name"].isna().sum()
            empty_count = (df["person_name"] == "").sum()
            if null_count + empty_count > 0:
                self._add_error(f"person_nameが空のレコードが{null_count + empty_count}件あります")
                is_valid = False

        return is_valid

    def _check_uniqueness(self, df: pd.DataFrame) -> bool:
        """一意性制約をチェック"""
        is_valid = True

        for col in self.rules["unique_columns"]:
            if col in df.columns:
                duplicates = df[col].duplicated()
                if duplicates.any():
                    dup_count = duplicates.sum()
                    dup_values = df[duplicates][col].unique()[:10]  # 最初の10件
                    self._add_error(f"カラム '{col}' に重複が{dup_count}件あります: {list(dup_values)}")
                    is_valid = False

        return is_valid

    def _check_patterns(self, df: pd.DataFrame) -> bool:
        """パターンマッチングチェック"""
        is_valid = True

        for col, pattern in self.rules["patterns"].items():
            if col in df.columns:
                pattern_re = re.compile(pattern)
                invalid = df[col].apply(lambda x: not pd.isna(x) and x != "" and not pattern_re.match(str(x)))
                if invalid.any():
                    count = invalid.sum()
                    examples = df[invalid][col].head(5).tolist()
                    self._add_warning(f"カラム '{col}' のパターン違反が{count}件: {examples}")

        return is_valid

    def _check_value_constraints(self, df: pd.DataFrame) -> bool:
        """値の制約をチェック"""
        is_valid = True

        for col, constraints in self.rules["value_constraints"].items():
            if col in df.columns:
                # 数値として変換可能な値のみチェック
                numeric_mask = pd.to_numeric(df[col], errors="coerce").notna()
                numeric_values = pd.to_numeric(df[col], errors="coerce")

                if "min" in constraints:
                    below_min = numeric_mask & (numeric_values < constraints["min"])
                    if below_min.any():
                        count = below_min.sum()
                        self._add_warning(f"カラム '{col}' に最小値({constraints['min']})未満が{count}件")

                if "max" in constraints:
                    above_max = numeric_mask & (numeric_values > constraints["max"])
                    if above_max.any():
                        count = above_max.sum()
                        self._add_warning(f"カラム '{col}' に最大値({constraints['max']})超過が{count}件")

        return is_valid

    def _check_duplicate_patterns(self, df: pd.DataFrame) -> bool:
        """重複・異常パターンをチェック"""
        is_valid = True

        # 括弧の重複チェック
        if "person_name_display" in df.columns:
            pattern = re.compile(self.rules["duplicate_checks"]["parentheses"])
            duplicates = df["person_name_display"].apply(
                lambda x: bool(pattern.match(str(x))) if pd.notna(x) else False
            )
            if duplicates.any():
                count = duplicates.sum()
                examples = df[duplicates]["person_name_display"].head(5).tolist()
                self._add_error(f"括弧内重複が{count}件検出: {examples}")
                is_valid = False

        # 連続スペースチェック
        space_pattern = re.compile(self.rules["duplicate_checks"]["spaces"])
        for col in ["person_name", "person_name_display", "person_name_ja"]:
            if col in df.columns:
                has_spaces = df[col].apply(lambda x: bool(space_pattern.search(str(x))) if pd.notna(x) else False)
                if has_spaces.any():
                    count = has_spaces.sum()
                    self._add_warning(f"カラム '{col}' に連続スペースが{count}件")

        return is_valid

    def _check_consistency(self, df: pd.DataFrame) -> bool:
        """データの一貫性をチェック"""
        is_valid = True

        # person_nameとperson_name_displayの整合性
        if "person_name" in df.columns and "person_name_display" in df.columns:
            # 基本的に関連性があるべき
            completely_different = df.apply(
                lambda row: (
                    pd.notna(row["person_name"])
                    and pd.notna(row["person_name_display"])
                    and len(str(row["person_name"])) > 0
                    and len(str(row["person_name_display"])) > 0
                    and not any(part in str(row["person_name_display"]) for part in str(row["person_name"]).split())
                ),
                axis=1,
            )
            if completely_different.any():
                count = completely_different.sum()
                self._add_warning(f"名前の不整合が{count}件検出されました")

        return is_valid

    def _check_completeness(self, df: pd.DataFrame) -> float:
        """データの完全性をチェック（完全性スコアを返す）"""
        total_cells = len(df) * len(df.columns)
        non_null_cells = df.notna().sum().sum()
        completeness = (non_null_cells / total_cells) * 100 if total_cells > 0 else 0

        # カラムごとの完全性
        for col in df.columns:
            null_ratio = df[col].isna().sum() / len(df) * 100
            if null_ratio > 50:
                self._add_warning(f"カラム '{col}' の欠損率が{null_ratio:.1f}%です")

        return completeness

    def _auto_repair(self, df: pd.DataFrame) -> pd.DataFrame:
        """自動修復を実行"""
        df_repaired = df.copy()
        repairs_made = []

        # 括弧の重複を修正
        if "person_name_display" in df_repaired.columns:
            pattern = re.compile(r"^([^(]+)\s*\(\1\)$")
            mask = df_repaired["person_name_display"].apply(
                lambda x: bool(pattern.match(str(x))) if pd.notna(x) else False
            )
            if mask.any():
                df_repaired.loc[mask, "person_name_display"] = df_repaired.loc[mask, "person_name_display"].str.replace(
                    pattern, r"\1", regex=True
                )
                repairs_made.append(f"括弧内重複を{mask.sum()}件修正")

        # 連続スペースを修正
        space_pattern = re.compile(r"\s{2,}")
        for col in ["person_name", "person_name_display", "person_name_ja"]:
            if col in df_repaired.columns:
                df_repaired[col] = df_repaired[col].apply(
                    lambda x: space_pattern.sub(" ", str(x)).strip() if pd.notna(x) else x
                )

        # 特殊文字を除去
        special_pattern = re.compile(r"[<>\"\'\\]")
        for col in df_repaired.columns:
            if df_repaired[col].dtype == object:
                df_repaired[col] = df_repaired[col].apply(
                    lambda x: special_pattern.sub("", str(x)) if pd.notna(x) else x
                )

        # 修復履歴を記録
        if repairs_made:
            self.repair_history.append(
                {"timestamp": datetime.now().isoformat(), "repairs": repairs_made, "rows_affected": len(df_repaired)}
            )

            self.logger.info(f"✅ 自動修復完了: {', '.join(repairs_made)}")

        return df_repaired

    def _add_error(self, message: str):
        """エラーを追加"""
        self.check_results.append({"level": "ERROR", "message": message})
        self.error_count += 1
        self.logger.error(f"❌ {message}")

    def _add_warning(self, message: str):
        """警告を追加"""
        self.check_results.append({"level": "WARNING", "message": message})
        self.warning_count += 1
        self.logger.warning(f"⚠️ {message}")

    def validate_before_sync(self, df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        """同期前の検証と修復"""
        # 整合性チェック
        report = self.check_data_integrity(df, auto_repair=True)

        # エラーがある場合は同期を中止
        if report["errors"] > 0:
            self.logger.error("❌ 重大なエラーのため同期を中止します")
            return False, df

        # 警告のみの場合は修復済みデータで続行
        if report["warnings"] > 0:
            self.logger.warning(f"⚠️ {report['warnings']}件の警告がありましたが修復済みです")

        return True, df

    def generate_integrity_report(self, df: pd.DataFrame) -> str:
        """整合性レポートを生成"""
        report = self.check_data_integrity(df, detailed_report=True)

        report_text = f"""
========================================
データ整合性レポート
========================================
生成日時: {report["timestamp"]}
総レコード数: {report["total_rows"]:,}

【サマリー】
- エラー: {report["errors"]}件
- 警告: {report["warnings"]}件
- 検証結果: {"✅ 合格" if report["is_valid"] else "❌ 不合格"}

【チェック項目】
"""

        for check, result in report["checks"].items():
            status = "✅" if result else "❌"
            report_text += f"  {status} {check}: {result}\n"

        if report["details"]:
            report_text += "\n【詳細】\n"
            for detail in report["details"][:20]:  # 最初の20件
                report_text += f"  [{detail['level']}] {detail['message']}\n"

        report_text += "\n========================================"

        return report_text


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)

    checker = IntegrityChecker()

    # テストデータ（問題のあるデータ）
    test_df = pd.DataFrame(
        {
            "person_id": ["P000399", "P000399", "P000002"],  # 重複あり
            "person_name": ["Kajisac", None, "Test  User"],  # NULL、連続スペース
            "person_name_display": ["カジサック (カジサック)", "テスト", "テストユーザー"],  # 括弧重複
            "birth_year": ["1980", "2030", "invalid"],  # 無効な値
        }
    )

    print("【整合性チェック前】")
    print(test_df)

    # 整合性チェックと自動修復
    is_valid, repaired_df = checker.validate_before_sync(test_df)

    print("\n【整合性チェック後】")
    print(repaired_df)

    # レポート生成
    report = checker.generate_integrity_report(repaired_df)
    print(report)
