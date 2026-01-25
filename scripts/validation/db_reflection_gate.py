#!/usr/bin/env python3
"""
DB反映前ゲート（EPUP準拠）

エピソードがマスターCSVに反映される前に必ず通過すべき検証を実行。
以下の条件を全て満たす場合のみ反映を許可:

1. 定型パターン: 「あなたと同じ{age}歳のとき、{person_name}は/の」で開始
2. 必須スコア: 8軸スコア、composite_score、super_total_score が欠損なし
3. 禁止パターン: 一人称「私は」、メタ表現などを含まない
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class GateResult:
    """ゲート検証結果"""

    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_fixed: dict[str, Any] = field(default_factory=dict)


class DBReflectionGate:
    """DB反映前ゲート"""

    # 定型パターン: 「あなたと同じ{age}歳のとき、{person_name}は/の」
    VALID_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、(.+?)(は|の)")

    # 禁止パターン
    PROHIBITED_PATTERNS = [
        (r"^あなたと同じ\d+歳のとき.*私は", "一人称「私は」パターン"),
        (r"^\*\*.*\*\*\s*\n", "Markdownヘッダーで開始"),
        (r"^「あなたと同じ", "引用符で開始"),
        (r"^[\d]{4}年", "年号で開始"),
        (r"のような人物です", "メタ表現"),
        (r"という記録は", "メタ表現"),
        (r"について語られています", "メタ表現"),
    ]

    # 必須スコアカラム（8軸）
    REQUIRED_SCORE_COLUMNS = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
        "iconic_score",
    ]

    # LLMスコアカラム（バックアップ参照用）
    LLM_SCORE_MAPPING = {
        "memorability_score": "llm_memorability_score",
        "empathy_score": "llm_empathy_score",
        "surprise_score": "llm_surprise_score",
        "generation_quality_score": "llm_generation_quality_score",
        "educational_value": "llm_educational_value",
        "story_quality": "llm_storytelling_quality",
        "factual_density": "llm_factual_density",
    }

    # 統合スコアカラム
    REQUIRED_COMPOSITE_COLUMNS = [
        "composite_score",
        "super_total_score",
    ]

    def __init__(self, auto_fix: bool = False):
        """
        Args:
            auto_fix: Trueの場合、修正可能な問題を自動修正
        """
        self.auto_fix = auto_fix

    def validate_row(self, row: dict) -> GateResult:
        """
        単一行を検証

        Args:
            row: エピソードデータ（辞書形式）

        Returns:
            GateResult: 検証結果
        """
        failures = []
        warnings = []
        auto_fixed = {}

        episode_text = str(row.get("episode_text", "") or "")
        person_name = str(row.get("person_name", "") or "")
        age = row.get("age")

        # 1. 定型パターン検証
        format_result = self._check_format(episode_text, person_name, age)
        if not format_result["passed"]:
            if self.auto_fix and format_result.get("fixable"):
                fixed_text = format_result.get("fixed_text")
                if fixed_text:
                    auto_fixed["episode_text"] = fixed_text
                    warnings.append(f"定型パターンを自動修正: {format_result['issue']}")
            else:
                failures.append(f"定型パターン違反: {format_result['issue']}")

        # 2. 禁止パターン検証
        for pattern, description in self.PROHIBITED_PATTERNS:
            if re.search(pattern, episode_text):
                failures.append(f"禁止パターン検出: {description}")

        # 3. 必須スコア検証（8軸）
        for col in self.REQUIRED_SCORE_COLUMNS:
            val = row.get(col)
            if pd.isna(val) or val == "":
                # LLMカラムからの補完を試みる
                llm_col = self.LLM_SCORE_MAPPING.get(col)
                if llm_col:
                    llm_val = row.get(llm_col)
                    if pd.notna(llm_val) and llm_val != "":
                        if self.auto_fix:
                            auto_fixed[col] = float(llm_val)
                            warnings.append(f"{col}: llm_{col}から補完")
                        else:
                            warnings.append(f"{col}: 欠損（llm_{col}から補完可能）")
                    else:
                        failures.append(f"必須スコア欠損: {col}")
                else:
                    failures.append(f"必須スコア欠損: {col}")

        # 4. 統合スコア検証
        for col in self.REQUIRED_COMPOSITE_COLUMNS:
            val = row.get(col)
            if pd.isna(val) or val == "":
                failures.append(f"統合スコア欠損: {col}")

        return GateResult(
            passed=len(failures) == 0,
            failures=failures,
            warnings=warnings,
            auto_fixed=auto_fixed,
        )

    def _check_format(self, text: str, person_name: str, age: Any) -> dict[str, Any]:
        """定型パターンを検証"""
        match = self.VALID_PATTERN.match(text)

        if match:
            # パターンにマッチ
            extracted_age = int(match.group(1))
            extracted_name = match.group(2)

            # 年齢の整合性チェック
            if age and int(age) != extracted_age:
                return {
                    "passed": False,
                    "issue": f"年齢不一致（本文:{extracted_age}, メタ:{int(age)}）",
                    "fixable": True,
                    "fixed_text": self._fix_age_in_text(text, int(age)),
                }

            # 人物名の部分一致チェック
            if person_name and person_name not in extracted_name:
                return {
                    "passed": False,
                    "issue": f"人物名不一致（本文:{extracted_name}, メタ:{person_name}）",
                    "fixable": True,
                    "fixed_text": self._fix_name_in_text(text, person_name, int(age)),
                }

            return {"passed": True}

        # パターンにマッチしない場合
        # 修正可能かチェック
        if text.startswith(("**", "「", "『")):
            # Markdownヘッダーや引用符で始まる場合
            return {
                "passed": False,
                "issue": "特殊文字で開始",
                "fixable": True,
                "fixed_text": self._create_standard_format(text, person_name, age),
            }

        if re.match(r"^\d{4}年", text):
            # 年号で始まる場合
            return {
                "passed": False,
                "issue": "年号で開始",
                "fixable": True,
                "fixed_text": self._create_standard_format(text, person_name, age),
            }

        return {
            "passed": False,
            "issue": "定型パターンで開始していない",
            "fixable": True if person_name and age else False,
            "fixed_text": self._create_standard_format(text, person_name, age) if person_name and age else None,
        }

    def _fix_age_in_text(self, text: str, correct_age: int) -> str:
        """テキスト内の年齢を修正"""
        return re.sub(
            r"^あなたと同じ\d+歳のとき",
            f"あなたと同じ{correct_age}歳のとき",
            text,
        )

    def _fix_name_in_text(self, text: str, correct_name: str, age: int) -> str:
        """テキスト内の人物名を修正"""
        # 既存の定型部分を置換
        return re.sub(
            r"^あなたと同じ\d+歳のとき、[^、]+は",
            f"あなたと同じ{age}歳のとき、{correct_name}は",
            text,
        )

    def _create_standard_format(self, text: str, person_name: str, age: Any) -> Optional[str]:
        """標準フォーマットに変換"""
        if not person_name or not age:
            return None

        # 先頭の特殊文字やMarkdownを除去
        cleaned_text = re.sub(r"^\*\*.*?\*\*\s*\n?", "", text)
        cleaned_text = re.sub(r"^[「『]", "", cleaned_text)
        cleaned_text = cleaned_text.strip()

        # 年号で始まる場合、その部分を本文に組み込む
        if cleaned_text:
            return f"あなたと同じ{int(age)}歳のとき、{person_name}は{cleaned_text}"

        return None

    def validate_dataframe(self, df: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
        """
        DataFrame全体を検証

        Args:
            df: 検証対象のDataFrame
            verbose: 詳細ログを出力するか

        Returns:
            (修正後のDataFrame, 検証サマリー)
        """
        results = {
            "total": len(df),
            "passed": 0,
            "failed": 0,
            "auto_fixed": 0,
            "failures_by_type": {},
        }

        df_fixed = df.copy()

        for idx, row in df.iterrows():
            result = self.validate_row(row.to_dict())

            if result.passed or (self.auto_fix and result.auto_fixed):
                results["passed"] += 1

                # 自動修正を適用
                if result.auto_fixed:
                    results["auto_fixed"] += 1
                    for col, val in result.auto_fixed.items():
                        df_fixed.at[idx, col] = val

            else:
                results["failed"] += 1
                for failure in result.failures:
                    key = failure.split(":")[0]
                    results["failures_by_type"][key] = results["failures_by_type"].get(key, 0) + 1

                if verbose:
                    ep_id = row.get("episode_id", "unknown")
                    print(f"❌ {ep_id}: {', '.join(result.failures)}")

        return df_fixed, results


def validate_episodes_for_reflection(
    episodes: list[dict], auto_fix: bool = False
) -> tuple[list[dict], list[dict], dict]:
    """
    エピソードリストを検証し、反映可能なものと不可能なものを分離

    Args:
        episodes: エピソードデータのリスト
        auto_fix: 自動修正を有効にするか

    Returns:
        (反映可能リスト, 不可リスト, サマリー)
    """
    gate = DBReflectionGate(auto_fix=auto_fix)
    passed = []
    failed = []
    summary = {"total": len(episodes), "passed": 0, "failed": 0, "auto_fixed": 0}

    for ep in episodes:
        result = gate.validate_row(ep)

        if result.passed:
            passed.append(ep)
            summary["passed"] += 1
        elif result.auto_fixed:
            # 自動修正を適用
            ep_fixed = {**ep, **result.auto_fixed}
            passed.append(ep_fixed)
            summary["passed"] += 1
            summary["auto_fixed"] += 1
        else:
            ep["_gate_failures"] = result.failures
            failed.append(ep)
            summary["failed"] += 1

    return passed, failed, summary


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="DB反映前ゲート検証")
    parser.add_argument(
        "--csv",
        default=str(PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"),
        help="検証対象のCSVファイル",
    )
    parser.add_argument("--auto-fix", action="store_true", help="自動修正を有効にする")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード（変更を保存しない）")
    parser.add_argument("--verbose", action="store_true", help="詳細ログを出力")
    args = parser.parse_args()

    print("=" * 60)
    print("DB反映前ゲート検証")
    print("=" * 60)

    # CSV読み込み
    df = pd.read_csv(args.csv, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    # 検証実行
    gate = DBReflectionGate(auto_fix=args.auto_fix)
    df_fixed, summary = gate.validate_dataframe(df, verbose=args.verbose)

    # サマリー出力
    print()
    print("=" * 60)
    print("検証サマリー")
    print("=" * 60)
    print(f"総数: {summary['total']}")
    print(f"合格: {summary['passed']} ({summary['passed'] / summary['total'] * 100:.1f}%)")
    print(f"不合格: {summary['failed']} ({summary['failed'] / summary['total'] * 100:.1f}%)")
    if args.auto_fix:
        print(f"自動修正: {summary['auto_fixed']}")

    if summary["failures_by_type"]:
        print()
        print("不合格の内訳:")
        for failure_type, count in sorted(summary["failures_by_type"].items(), key=lambda x: -x[1]):
            print(f"  {failure_type}: {count}件")

    # 保存（dry-runでない場合）
    if args.auto_fix and not args.dry_run and summary["auto_fixed"] > 0:
        print()
        print(f"修正を保存中... {args.csv}")
        df_fixed.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print("保存完了")


if __name__ == "__main__":
    main()
