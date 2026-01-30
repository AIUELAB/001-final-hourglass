#!/usr/bin/env python3
"""
EPUP: 架空キャラクター名違反検出スクリプト

架空キャラクターのエピソードで以下の違反を検出する:
1. person_name表記揺れ（FICTIONAL_NAME_ALIASESに該当するもの）
2. work_title欠損（空またはNaN）
3. episode_text冒頭フォーマット違反

## 使用方法
    # ドライラン（検出のみ・レポート生成）
    python scripts/validation/detect_fictional_name_violations.py --dry-run

    # CSVパス指定
    python scripts/validation/detect_fictional_name_violations.py --csv path/to/file.csv

    # レポート出力先指定
    python scripts/validation/detect_fictional_name_violations.py --output path/to/report.txt

Author: EPUP Validation Team
Date: 2026-01-28
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.fictional_characters import normalize_fictional_name

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"

# =============================================================================
# ロギング設定
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class NameAliasViolation:
    """person_name表記揺れ違反"""

    episode_id: str
    person_name: str
    canonical_name: str  # 正規名


@dataclass
class WorkTitleMissingViolation:
    """work_title欠損違反"""

    episode_id: str
    person_name: str


@dataclass
class FormatViolation:
    """episode_text冒頭フォーマット違反"""

    episode_id: str
    person_name: str
    age: int
    work_title: str
    current_text: str  # 現在の冒頭テキスト（50文字まで）
    expected_prefix: str  # 期待されるフォーマット


@dataclass
class DetectionResult:
    """検出結果"""

    total_checked: int = 0
    name_alias_violations: list[NameAliasViolation] = field(default_factory=list)
    work_title_missing_violations: list[WorkTitleMissingViolation] = field(default_factory=list)
    format_violations: list[FormatViolation] = field(default_factory=list)


# =============================================================================
# 検出クラス
# =============================================================================


class FictionalNameViolationDetector:
    """
    架空キャラクター名違反検出器

    FICTIONALエピソードから以下を検出:
    1. person_name表記揺れ
    2. work_title欠損
    3. episode_text冒頭フォーマット違反
    """

    # 期待される冒頭フォーマット
    EXPECTED_PREFIX_PATTERN = r"^あなたと同じ(\d+)歳のとき、(.+?)『(.+?)』は"

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                logger.info(f"マスターCSV読み込み: {self.master_csv}")
                try:
                    self._master_df = pd.read_csv(
                        self.master_csv,
                        encoding="utf-8-sig",
                        low_memory=False,
                    )
                except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
                    logger.error(f"CSV解析エラー: {e}")
                    self._master_df = pd.DataFrame()
            else:
                logger.error(f"マスターCSVが見つかりません: {self.master_csv}")
                self._master_df = pd.DataFrame()
        return self._master_df

    def check_name_alias(self, person_name: str) -> tuple[bool, str]:
        """
        person_name表記揺れをチェック

        Args:
            person_name: 人物名

        Returns:
            (違反ありか, 正規名)
        """
        normalized, was_changed = normalize_fictional_name(person_name)
        return was_changed, normalized

    def check_work_title_missing(self, work_title: str) -> bool:
        """
        work_title欠損をチェック

        Args:
            work_title: 作品タイトル

        Returns:
            欠損しているか
        """
        if not work_title:
            return True
        if str(work_title).strip().lower() in ("", "nan", "none", "null"):
            return True
        return False

    def check_format_violation(
        self,
        episode_text: str,
        person_name: str,
        age: int,
        work_title: str,
    ) -> bool:
        """
        episode_text冒頭フォーマット違反をチェック

        期待フォーマット: あなたと同じ{age}歳のとき、{person_name}『{work_title}』は

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢
            work_title: 作品タイトル

        Returns:
            フォーマット違反があるか
        """
        if not episode_text or str(episode_text).strip().lower() in ("", "nan"):
            return True  # 空テキストは違反

        # 期待される冒頭パターン
        expected_prefix = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は"

        # 完全一致チェック（先頭部分）
        if episode_text.startswith(expected_prefix):
            return False  # 正常

        # 正規表現で部分チェック（年齢・名前・作品名が含まれているか）
        match = re.match(self.EXPECTED_PREFIX_PATTERN, episode_text)
        if match:
            matched_age = int(match.group(1))
            matched_name = match.group(2)
            matched_work = match.group(3)

            # 年齢、名前、作品タイトルがすべて一致すれば正常
            if matched_age == age and matched_name == person_name and matched_work == work_title:
                return False  # 正常

        return True  # 違反

    def check_episode(
        self, row: dict
    ) -> tuple[
        Optional[NameAliasViolation],
        Optional[WorkTitleMissingViolation],
        Optional[FormatViolation],
    ]:
        """
        単一エピソードをチェック

        Args:
            row: エピソードデータ

        Returns:
            (表記揺れ違反, work_title欠損違反, フォーマット違反)
        """
        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        work_title = str(row.get("work_title", ""))
        episode_text = str(row.get("episode_text", ""))
        age_raw = row.get("age", 0)
        try:
            age = int(age_raw) if age_raw and str(age_raw).isdigit() else 0
        except (ValueError, TypeError):
            age = 0  # "ageless"等の非数値年齢は0として扱う

        name_violation = None
        work_violation = None
        format_violation = None

        # 1. person_name表記揺れチェック
        is_alias, canonical_name = self.check_name_alias(person_name)
        if is_alias:
            name_violation = NameAliasViolation(
                episode_id=episode_id,
                person_name=person_name,
                canonical_name=canonical_name,
            )

        # 2. work_title欠損チェック
        if self.check_work_title_missing(work_title):
            work_violation = WorkTitleMissingViolation(
                episode_id=episode_id,
                person_name=person_name,
            )

        # 3. episode_text冒頭フォーマット違反チェック
        # work_titleが欠損している場合はフォーマットチェックをスキップ
        if not self.check_work_title_missing(work_title):
            if self.check_format_violation(episode_text, person_name, age, work_title):
                current_text = episode_text[:50] if episode_text else ""
                expected_prefix = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は"
                format_violation = FormatViolation(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=age,
                    work_title=work_title,
                    current_text=current_text,
                    expected_prefix=expected_prefix,
                )

        return name_violation, work_violation, format_violation

    def scan_all(self) -> DetectionResult:
        """
        全FICTIONALエピソードをスキャン

        Returns:
            検出結果
        """
        result = DetectionResult()

        if self.master_df.empty:
            logger.error("マスターデータが空です")
            return result

        # person_type = "FICTIONAL" のエピソードのみ抽出
        df = self.master_df.copy()
        fictional_mask = df["person_type"].str.upper().str.contains("FICTIONAL", na=False)
        df = df[fictional_mask]
        result.total_checked = len(df)

        logger.info(f"検証対象: {result.total_checked}件のFICTIONALエピソード")

        processed = 0
        for _, row in df.iterrows():
            name_v, work_v, format_v = self.check_episode(row.to_dict())

            if name_v:
                result.name_alias_violations.append(name_v)
            if work_v:
                result.work_title_missing_violations.append(work_v)
            if format_v:
                result.format_violations.append(format_v)

            processed += 1
            if processed % 1000 == 0:
                logger.info(f"処理中: {processed}/{result.total_checked}")

        return result


# =============================================================================
# レポート生成
# =============================================================================


def generate_report(result: DetectionResult, csv_path: Path) -> str:
    """
    検出レポートを生成

    Args:
        result: 検出結果
        csv_path: 対象CSVパス

    Returns:
        レポート文字列
    """
    lines: list[str] = []

    lines.append("=== 架空キャラクター名違反レポート ===")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"対象CSV: {csv_path}")
    lines.append("")

    # サマリー
    lines.append("■ サマリー")
    lines.append(f"- 検査対象エピソード数: {result.total_checked}件")
    lines.append(f"- person_name表記揺れ: {len(result.name_alias_violations)}件")
    lines.append(f"- work_title欠損: {len(result.work_title_missing_violations)}件")
    lines.append(f"- 冒頭フォーマット違反: {len(result.format_violations)}件")
    lines.append("")

    # 詳細: person_name表記揺れ
    lines.append("■ 詳細: person_name表記揺れ")
    if result.name_alias_violations:
        for v in result.name_alias_violations:
            lines.append(f"[{v.episode_id}] {v.person_name} → {v.canonical_name}")
    else:
        lines.append("なし")
    lines.append("")

    # 詳細: work_title欠損
    lines.append("■ 詳細: work_title欠損")
    if result.work_title_missing_violations:
        for v in result.work_title_missing_violations:
            lines.append(f"[{v.episode_id}] person_name={v.person_name}, work_title=空")
    else:
        lines.append("なし")
    lines.append("")

    # 詳細: 冒頭フォーマット違反
    lines.append("■ 詳細: 冒頭フォーマット違反")
    if result.format_violations:
        for v in result.format_violations:
            lines.append(f"[{v.episode_id}] 現在: {v.current_text}...")
            lines.append(f"             期待: {v.expected_prefix}")
    else:
        lines.append("なし")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="EPUP: 架空キャラクター名違反検出スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（検出のみ・レポート生成）
  python scripts/validation/detect_fictional_name_violations.py --dry-run

  # CSVパス指定
  python scripts/validation/detect_fictional_name_violations.py --csv path/to/file.csv

  # レポート出力先指定
  python scripts/validation/detect_fictional_name_violations.py --output path/to/report.txt
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="レポート生成のみ（デフォルト）",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help=f"CSVパス指定（デフォルト: {MASTER_CSV}）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="レポート出力先（デフォルト: src/reports/fictional_name_violations_{日付}.txt）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    args = parser.parse_args()

    # ログレベル設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # CSVパス設定
    csv_path = Path(args.csv)

    # 出力先設定
    if args.output:
        output_path = Path(args.output)
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = REPORT_DIR / f"fictional_name_violations_{date_str}.txt"

    # ヘッダー表示
    logger.info("=" * 70)
    logger.info("EPUP: 架空キャラクター名違反検出スクリプト")
    logger.info(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # 検出器初期化
    detector = FictionalNameViolationDetector(master_csv=csv_path)

    if detector.master_df.empty:
        logger.error(f"マスターCSVが見つかりません: {csv_path}")
        return 2

    logger.info(f"マスターCSV: {csv_path}")
    logger.info(f"総エピソード数: {len(detector.master_df):,}")

    # スキャン実行
    logger.info("")
    logger.info("スキャン開始...")
    result = detector.scan_all()

    # レポート生成
    report = generate_report(result, csv_path)

    # 出力
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"レポート保存: {output_path}")

    # 標準出力にもサマリー表示
    print("")
    print(report)

    # 結果サマリー
    total_violations = (
        len(result.name_alias_violations) + len(result.work_title_missing_violations) + len(result.format_violations)
    )
    logger.info("")
    logger.info(f"検証完了: {result.total_checked}件チェック, {total_violations}件違反検出")

    # 終了コード（違反があれば1）
    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
