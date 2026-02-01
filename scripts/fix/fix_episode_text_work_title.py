#!/usr/bin/env python3
"""
EPUP: episode_text冒頭フォーマット違反修正スクリプト

episode_textの冒頭「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」の
work_title部分を、CSVのwork_titleカラムの値に置換する。

## 修正対象
1. 冒頭の『』内がwork_titleと異なるエピソード
2. 冒頭フォーマットが欠落しているエピソード

## 使用方法
    # ドライラン（検出のみ）
    python scripts/fix/fix_episode_text_work_title.py --dry-run

    # 実行
    python scripts/fix/fix_episode_text_work_title.py --execute

    # 検証
    python scripts/fix/fix_episode_text_work_title.py --verify

Author: EPUP Fix Team
Date: 2026-02-01
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/backups"
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
class FixResult:
    """修正結果"""

    episode_id: str
    person_name: str
    age: int
    work_title: str
    fix_type: str
    old_text: str
    new_text: str
    confidence: float  # 修正の確信度（0.0-1.0）


# =============================================================================
# 修正ロジック
# =============================================================================


class EpisodeTextWorkTitleFixer:
    """
    episode_text冒頭のwork_title修正器

    冒頭フォーマット: あなたと同じ{age}歳のとき、{person_name}『{work_title}』は
    """

    # 冒頭パターン（『』内をキャプチャ）
    LEAD_PATTERN = re.compile(r"^(あなたと同じ)(\d+)(歳のとき、)([^『]+)(『)([^』]*)(』)(は)")

    # 正しい冒頭パターン
    CORRECT_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は")

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                logger.info(f"マスターCSV読み込み: {self.master_csv}")
                self._master_df = pd.read_csv(
                    self.master_csv,
                    encoding="utf-8-sig",
                    low_memory=False,
                )
            else:
                logger.error(f"マスターCSVが見つかりません: {self.master_csv}")
                self._master_df = pd.DataFrame()
        return self._master_df

    def create_backup(self) -> Path:
        """バックアップ作成"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_before_worktitle_fix_{timestamp}.csv"
        shutil.copy2(self.master_csv, backup_path)
        return backup_path

    def check_needs_fix(
        self,
        episode_text: str,
        person_name: str,
        age: int,
        work_title: str,
    ) -> bool:
        """
        修正が必要か判定

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢
            work_title: 正しいwork_title

        Returns:
            修正が必要か
        """
        if not episode_text or pd.isna(episode_text):
            return True

        if not work_title or pd.isna(work_title):
            return False  # work_titleが空の場合は修正不可

        episode_text = str(episode_text)
        work_title = str(work_title)

        # 期待される冒頭
        expected_prefix = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は"

        # 完全一致ならOK
        if episode_text.startswith(expected_prefix):
            return False

        # パターンマッチで確認
        match = self.LEAD_PATTERN.match(episode_text)
        if match:
            matched_age = int(match.group(2))
            matched_name = match.group(4).strip()
            matched_work = match.group(6)

            # 年齢、名前、work_titleすべて一致ならOK
            if matched_age == age and matched_name == person_name and matched_work == work_title:
                return False

        return True

    def fix_episode_text(
        self,
        episode_text: str,
        person_name: str,
        age: int,
        work_title: str,
    ) -> tuple[str, str, float]:
        """
        episode_textを修正

        Args:
            episode_text: 元のエピソードテキスト
            person_name: 人物名
            age: 年齢
            work_title: 正しいwork_title

        Returns:
            (修正後テキスト, 修正タイプ, 確信度)
        """
        if not episode_text or pd.isna(episode_text):
            return str(episode_text), "空テキスト", 0.0

        if not work_title or pd.isna(work_title):
            return str(episode_text), "work_title欠損", 0.0

        episode_text = str(episode_text)
        work_title = str(work_title).strip()
        person_name = str(person_name).strip()

        # 期待される冒頭
        expected_prefix = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は"

        # 既に正しい形式
        if episode_text.startswith(expected_prefix):
            return episode_text, "既に正常", 1.0

        # パターン1: 冒頭形式はあるがwork_titleが誤っている
        match = self.LEAD_PATTERN.match(episode_text)
        if match:
            # グループ:
            # 1: "あなたと同じ"
            # 2: 年齢（数字）
            # 3: "歳のとき、"
            # 4: 人物名
            # 5: "『"
            # 6: 現在のwork_title（誤り）
            # 7: "』"
            # 8: "は"
            current_name = match.group(4).strip()
            current_work = match.group(6)
            rest = episode_text[match.end() :]

            # work_titleを置換
            new_text = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は{rest}"

            # 名前も変わった場合
            if current_name != person_name:
                return (
                    new_text,
                    f"work_title置換+名前修正（{current_work}→{work_title}, {current_name}→{person_name}）",
                    0.9,
                )

            return new_text, f"work_title置換（{current_work}→{work_title}）", 1.0

        # パターン2: 「あなたと同じ」で始まるが『』がない
        pattern_no_bracket = re.compile(
            r"^(あなたと同じ)(\d+)(歳のとき、)([^、は]+)(は)(.+)",
            re.DOTALL,
        )
        match2 = pattern_no_bracket.match(episode_text)
        if match2:
            current_name = match2.group(4).strip()
            rest = match2.group(6)

            new_text = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は{rest}"
            return new_text, f"work_title挿入（{current_name}）", 0.9

        # パターン3: 冒頭フォーマットが完全に欠落
        # 「あなたと同じ」で始まらない場合
        if not episode_text.startswith("あなたと同じ"):
            # テキスト先頭に正しい冒頭を追加
            new_text = f"{expected_prefix}{episode_text}"
            return new_text, "冒頭フォーマット追加", 0.7

        # パターン4: その他の異常パターン
        # 「あなたと同じ」で始まるが解析できない場合
        # 可能な限り正しい形式に修正を試みる
        pattern_partial = re.compile(r"^あなたと同じ(\d+)歳のとき、(.+)", re.DOTALL)
        match3 = pattern_partial.match(episode_text)
        if match3:
            # matched_age = int(match3.group(1))  # 使用しないためコメントアウト
            rest_content = match3.group(2)

            # 「は」で始まる部分を探す
            if rest_content.startswith(f"{person_name}『"):
                # 名前はあるが『』の形式が崩れている
                new_text = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は{rest_content.split('は', 1)[-1] if 'は' in rest_content else rest_content}"
                return new_text, "形式再構築", 0.6

            # 名前が含まれているか確認
            if person_name in rest_content:
                # 名前の後ろの内容を取得
                parts = rest_content.split(person_name, 1)
                if len(parts) > 1:
                    after_name = parts[1].lstrip("『」は の")
                    new_text = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は{after_name}"
                    return new_text, "名前基準再構築", 0.6

        # 修正不可
        return episode_text, "パターン不一致（保留）", 0.0

    def scan_and_fix(
        self,
        dry_run: bool = True,
        min_confidence: float = 0.6,
    ) -> list[FixResult]:
        """
        全FICTIONALエピソードをスキャンして修正

        Args:
            dry_run: Trueの場合、実際の保存を行わない
            min_confidence: 修正を適用する最小確信度

        Returns:
            修正結果のリスト
        """
        if self.master_df.empty:
            logger.error("マスターデータが空です")
            return []

        # FICTIONALエピソードを抽出
        df = self.master_df.copy()
        fictional_mask = df["person_type"].str.upper().str.contains("FICTIONAL", na=False)
        fictional_df = df[fictional_mask].copy()

        logger.info(f"FICTIONALエピソード数: {len(fictional_df):,}件")

        results: list[FixResult] = []
        fix_count = 0
        skip_count = 0

        for idx, row in fictional_df.iterrows():
            episode_id = str(row.get("episode_id", ""))
            person_name = str(row.get("person_name", ""))
            work_title = str(row.get("work_title", ""))
            episode_text = str(row.get("episode_text", ""))

            age_raw = row.get("age", 0)
            try:
                age = int(age_raw) if age_raw and str(age_raw).replace(".", "").isdigit() else 0
            except (ValueError, TypeError):
                age = 0

            # 修正不要チェック
            if not self.check_needs_fix(episode_text, person_name, age, work_title):
                continue

            # 修正を試行
            new_text, fix_type, confidence = self.fix_episode_text(episode_text, person_name, age, work_title)

            result = FixResult(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                work_title=work_title,
                fix_type=fix_type,
                old_text=episode_text[:100],
                new_text=new_text[:100],
                confidence=confidence,
            )
            results.append(result)

            # 確信度が閾値以上なら修正を適用
            if confidence >= min_confidence and new_text != episode_text:
                if not dry_run:
                    df.at[idx, "episode_text"] = new_text
                fix_count += 1
            else:
                skip_count += 1

        # 保存
        if not dry_run and fix_count > 0:
            df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")
            logger.info(f"修正を保存しました: {self.master_csv}")

        logger.info(f"修正対象: {fix_count}件, スキップ: {skip_count}件")
        return results


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="EPUP: episode_text冒頭フォーマット違反修正スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（検出のみ）
  python scripts/fix/fix_episode_text_work_title.py --dry-run

  # 実行
  python scripts/fix/fix_episode_text_work_title.py --execute

  # 検証
  python scripts/fix/fix_episode_text_work_title.py --verify
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（検出のみ）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="修正を実行",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="修正後の検証",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="修正を適用する最小確信度（デフォルト: 0.6）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    args = parser.parse_args()

    # デフォルトはdry-run
    if not args.execute and not args.verify:
        args.dry_run = True

    # ログレベル設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ヘッダー表示
    print("=" * 70)
    print("EPUP: episode_text冒頭フォーマット違反修正スクリプト")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'dry-run' if args.dry_run else 'execute' if args.execute else 'verify'}")
    print("=" * 70)

    # 修正器初期化
    fixer = EpisodeTextWorkTitleFixer()

    if fixer.master_df.empty:
        logger.error("マスターCSVが読み込めません")
        return 2

    print(f"\n📂 マスターCSV: {MASTER_CSV}")
    print(f"📊 総エピソード数: {len(fixer.master_df):,}件")

    if args.verify:
        # 検証モード: 残存違反をカウント
        from scripts.validation.detect_fictional_name_violations import FictionalNameViolationDetector

        detector = FictionalNameViolationDetector()
        result = detector.scan_all()

        print("\n" + "=" * 60)
        print("検証結果")
        print("=" * 60)
        print(f"冒頭フォーマット違反: {len(result.format_violations)}件")

        if len(result.format_violations) == 0:
            print("\n✅ 全FICTIONALエピソードが冒頭フォーマットに準拠しています")
            return 0
        else:
            print("\n⚠️ 一部違反が残っています")
            for v in result.format_violations[:10]:
                print(f"  [{v.episode_id}] 期待: {v.expected_prefix}")
            return 1

    # バックアップ作成（executeモードのみ）
    if args.execute:
        backup_path = fixer.create_backup()
        print(f"\n💾 バックアップ作成: {backup_path}")

    # 修正実行
    print("\nスキャン中...")
    results = fixer.scan_and_fix(
        dry_run=args.dry_run,
        min_confidence=args.min_confidence,
    )

    # 結果サマリー
    print("\n" + "=" * 60)
    print("修正サマリー")
    print("=" * 60)

    # 修正タイプ別集計
    by_type: dict[str, int] = {}
    for r in results:
        fix_type = r.fix_type.split("（")[0]  # パラメータ部分を除去
        by_type[fix_type] = by_type.get(fix_type, 0) + 1

    for fix_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {fix_type}: {count}件")

    # 確信度別集計
    high_conf = [r for r in results if r.confidence >= 0.9]
    mid_conf = [r for r in results if 0.6 <= r.confidence < 0.9]
    low_conf = [r for r in results if r.confidence < 0.6]

    print("\n確信度別:")
    print(f"  高（>=0.9）: {len(high_conf)}件")
    print(f"  中（0.6-0.9）: {len(mid_conf)}件")
    print(f"  低（<0.6）: {len(low_conf)}件")

    # 修正可能件数
    fixable = [r for r in results if r.confidence >= args.min_confidence]
    print(f"\n修正対象（確信度>={args.min_confidence}）: {len(fixable)}件")

    if args.dry_run:
        # サンプル表示
        print("\n" + "-" * 60)
        print("修正サンプル（最大15件）")
        print("-" * 60)
        for r in fixable[:15]:
            print(f"\n[{r.episode_id}] {r.person_name}『{r.work_title}』")
            print(f"  タイプ: {r.fix_type}")
            print(f"  確信度: {r.confidence:.1f}")
            print(f"  Before: {r.old_text[:70]}...")
            print(f"  After:  {r.new_text[:70]}...")

        if low_conf:
            print("\n" + "-" * 60)
            print("保留サンプル（確信度<0.6、最大5件）")
            print("-" * 60)
            for r in low_conf[:5]:
                print(f"\n[{r.episode_id}] {r.person_name}")
                print(f"  タイプ: {r.fix_type}")
                print(f"  文頭: {r.old_text[:80]}...")

        print("\n💡 実行するには --execute フラグを付けてください")
        return 0

    if args.execute:
        print("\n" + "=" * 60)
        print("✅ 修正完了")
        print("=" * 60)
        print(f"修正件数: {len(fixable)}件")
        print(f"保留件数: {len(low_conf)}件")

        # 検証実行
        print("\n検証中...")
        try:
            from scripts.validation.detect_fictional_name_violations import FictionalNameViolationDetector

            # 新しいインスタンスで再読み込み（キャッシュなし）
            detector = FictionalNameViolationDetector()
            result = detector.scan_all()

            print(f"\n残存違反: {len(result.format_violations)}件")

            if len(result.format_violations) == 0:
                print("🎉 全FICTIONALエピソードが冒頭フォーマットに準拠しました")
            else:
                print("⚠️ 一部違反が残っています（手動対応が必要）")
                for v in result.format_violations[:5]:
                    print(f"  [{v.episode_id}] {v.person_name}")
        except ImportError:
            print("検証スクリプトが見つかりません。手動で検証してください。")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
