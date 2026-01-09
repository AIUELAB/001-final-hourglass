#!/usr/bin/env python3
"""
EPUP準拠エピソード品質修正エンジン

全エピソードを対象に以下の品質問題を検知・修正:
1. 冒頭1文目の年号禁止ルール違反
2. 丁寧語（です・ます調）統一
3. 冒頭定型パターン遵守

Usage:
    # 検知のみ（スキャン）
    python scripts/fix/fix_episode_quality.py --scan

    # dry-run（修正プレビュー）
    python scripts/fix/fix_episode_quality.py --dry-run

    # 実行（バックアップ作成後に修正）
    python scripts/fix/fix_episode_quality.py --execute
"""

import argparse
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"

sys.path.insert(0, str(PROJECT_ROOT))

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """品質問題"""

    episode_id: str
    person_name: str
    age: float
    issue_type: str  # year_in_first_sentence, polite_form, format_pattern
    description: str
    original_text: str
    fixed_text: Optional[str] = None
    can_auto_fix: bool = True
    risk_level: str = "low"  # low, medium, high


@dataclass
class ScanResult:
    """スキャン結果"""

    total_episodes: int
    issues: list[QualityIssue] = field(default_factory=list)
    issues_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class FixResult:
    """修正結果"""

    total_episodes: int
    scanned: int
    fixed: int
    skipped: int
    manual_review: int
    backup_path: Optional[Path] = None
    report_path: Optional[Path] = None


class EpisodeQualityFixer:
    """エピソード品質修正エンジン"""

    # 定型パターン
    VALID_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、(.+?)(は|の)")

    # 1文目の年号パターン（検出用）
    YEAR_IN_FIRST_SENTENCE_PATTERNS = [
        # 「は{年}年、」形式 - 最も一般的
        (r"(は)((?:19|20)\d{2})年([、,])", "year_comma"),
        # 「は{年}年に」形式
        (r"(は)((?:19|20)\d{2})年(に)", "year_ni"),
        # 「は{年}年の」形式
        (r"(は)((?:19|20)\d{2})年(の)", "year_no"),
        # 「は{年}年{月}月」形式（日付）
        (r"(は)((?:19|20)\d{2})年(\d{1,2}月)", "year_month"),
        # 「は、{年}年に」形式（カンマ後）
        (r"(は)[、,]((?:19|20)\d{2})年(に)", "comma_before_year"),
        # 「は{年}年{イベント}」形式（平昌五輪等）
        (r"(は)((?:19|20)\d{2})年([^\d、,にの。])", "year_direct"),
        # 「の{年}年、」形式（「...最中の1909年、」等）
        (r"(の)((?:19|20)\d{2})年[、,]", "year_in_middle"),
        # 「、{年}年に」形式（稀）
        (r"([、,])((?:19|20)\d{2})年(に)", "comma_year_ni"),
        # 「、{年}年、」形式（稀）
        (r"([、,])((?:19|20)\d{2})年([、,])", "comma_year_comma"),
    ]

    # 自動修正可能パターン
    AUTO_FIX_PATTERNS = [
        "year_comma",
        "year_ni",
        "year_no",
        "year_month",
        "comma_before_year",
        "year_direct",
        "year_in_middle",
    ]

    # 年号パターン（一般検出用）
    YEAR_PATTERN = re.compile(r"((?:19|20)\d{2})年")

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path
        self.issues: list[QualityIssue] = []

    def _get_first_sentence(self, text: str) -> tuple[str, int]:
        """1文目を取得（開始句の後から最初の句点まで）"""
        # 開始句を除いた位置から
        match = self.VALID_PATTERN.match(text)
        if not match:
            return text, -1

        start_pos = match.end()
        first_period = text.find("。", start_pos)

        if first_period == -1:
            return text[start_pos:], len(text)

        return text[start_pos:first_period], first_period

    def _detect_year_in_first_sentence(
        self, text: str, episode_id: str, person_name: str, age: float
    ) -> Optional[QualityIssue]:
        """1文目の年号違反を検出"""
        first_sentence, first_period_pos = self._get_first_sentence(text)

        if first_period_pos == -1:
            return None

        # 年号を検出
        year_match = self.YEAR_PATTERN.search(first_sentence)
        if not year_match:
            return None

        # どのパターンに該当するか確認
        pattern_type = None
        for pattern, ptype in self.YEAR_IN_FIRST_SENTENCE_PATTERNS:
            if re.search(pattern, text[:first_period_pos]):
                pattern_type = ptype
                break

        year_value = year_match.group(1)

        return QualityIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="year_in_first_sentence",
            description=f"1文目に年号あり: {year_value}年 (パターン: {pattern_type})",
            original_text=text[: first_period_pos + 1] if first_period_pos > 0 else text[:100],
            can_auto_fix=pattern_type in self.AUTO_FIX_PATTERNS,
            risk_level="low" if pattern_type in self.AUTO_FIX_PATTERNS else "medium",
        )

    def _fix_year_in_first_sentence(self, text: str) -> tuple[str, list[str]]:
        """1文目の年号を修正（年号を削除、括弧追加なし）"""
        changes = []
        first_sentence, first_period_pos = self._get_first_sentence(text)

        if first_period_pos == -1:
            return text, changes

        # パターン別に修正（年号削除のみ）
        modified_text = text

        # パターン1: 「は{年}年、」→「は」に変更
        pattern1 = re.compile(r"(は)((?:19|20)\d{2})年([、,])")
        match1 = pattern1.search(text[:first_period_pos])
        if match1:
            year = match1.group(2)
            modified_text = text[: match1.start()] + match1.group(1) + text[match1.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン2: 「は{年}年に」→「は」に変更
        pattern2 = re.compile(r"(は)((?:19|20)\d{2})年(に)")
        match2 = pattern2.search(text[:first_period_pos])
        if match2:
            year = match2.group(2)
            modified_text = text[: match2.start()] + match2.group(1) + text[match2.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン3: 「は{年}年の」→「はその」に変更
        pattern3 = re.compile(r"(は)((?:19|20)\d{2})年(の)")
        match3 = pattern3.search(text[:first_period_pos])
        if match3:
            year = match3.group(2)
            modified_text = text[: match3.start()] + match3.group(1) + "その" + text[match3.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン4: 「は{年}年{月}月」→「は{月}月」に変更
        pattern4 = re.compile(r"(は)((?:19|20)\d{2})年(\d{1,2}月)")
        match4 = pattern4.search(text[:first_period_pos])
        if match4:
            year = match4.group(2)
            month = match4.group(3)
            modified_text = text[: match4.start()] + match4.group(1) + month + text[match4.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン5: 「は、{年}年に」→「は」に変更（カンマ後の年号）
        pattern5 = re.compile(r"(は)[、,]((?:19|20)\d{2})年(に)")
        match5 = pattern5.search(text[:first_period_pos])
        if match5:
            year = match5.group(2)
            modified_text = text[: match5.start()] + match5.group(1) + text[match5.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン6: 「は{年}年{イベント名}」→「は{イベント名}」に変更（平昌五輪等）
        pattern6 = re.compile(r"(は)((?:19|20)\d{2})年([^\d、,にの。])")
        match6 = pattern6.search(text[:first_period_pos])
        if match6:
            year = match6.group(2)
            modified_text = text[: match6.start()] + match6.group(1) + match6.group(3) + text[match6.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン7: 「の{年}年、」→「の」に変更（「...最中の1909年、」等）
        pattern7 = re.compile(r"(の)((?:19|20)\d{2})年[、,]")
        match7 = pattern7.search(text[:first_period_pos])
        if match7:
            year = match7.group(2)
            modified_text = text[: match7.start()] + match7.group(1) + text[match7.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン8: 「翌{年}年」→「翌年」に変更
        pattern8 = re.compile(r"(翌)((?:19|20)\d{2})年")
        match8 = pattern8.search(text[:first_period_pos])
        if match8:
            year = match8.group(2)
            modified_text = text[: match8.start()] + "翌年" + text[match8.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン9: 「(YYYY年)」または「（YYYY年）」→除去
        pattern9 = re.compile(r"[（\(]((?:19|20)\d{2})年[）\)]")
        match9 = pattern9.search(text[:first_period_pos])
        if match9:
            year = match9.group(1)
            modified_text = text[: match9.start()] + text[match9.end() :]
            changes.append(f"年号削除: ({year}年)")
            return modified_text, changes

        # パターン10: 「YYYY年にかけて」→「にかけて」に変更
        pattern10 = re.compile(r"((?:19|20)\d{2})年(にかけて)")
        match10 = pattern10.search(text[:first_period_pos])
        if match10:
            year = match10.group(1)
            modified_text = text[: match10.start()] + match10.group(2) + text[match10.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン11: 「、YYYY年に」→「、」に変更（文中の年号）
        pattern11 = re.compile(r"([、,])((?:19|20)\d{2})年(に)")
        match11 = pattern11.search(text[:first_period_pos])
        if match11:
            year = match11.group(2)
            modified_text = text[: match11.start()] + match11.group(1) + text[match11.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン12: 「として{年}年に」→「として」に変更
        pattern12 = re.compile(r"(として)((?:19|20)\d{2})年(に)")
        match12 = pattern12.search(text[:first_period_pos])
        if match12:
            year = match12.group(2)
            modified_text = text[: match12.start()] + match12.group(1) + text[match12.end() :]
            changes.append(f"年号削除: {year}年")
            return modified_text, changes

        # パターン13: 汎用 - 残存年号を除去（最終手段）
        year_generic = re.compile(r"((?:19|20)\d{2})年")
        match_generic = year_generic.search(text[:first_period_pos])
        if match_generic:
            year = match_generic.group(1)
            # 年号のみを除去（年号の前後の文脈は保持）
            modified_text = text[: match_generic.start()] + text[match_generic.end() :]
            changes.append(f"年号削除(汎用): {year}年")
            return modified_text, changes

        return text, changes

    def scan(self, limit: Optional[int] = None) -> ScanResult:
        """全件スキャン"""
        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)

        result = ScanResult(total_episodes=len(df))

        for idx, row in df.iterrows():
            if limit and idx >= limit:
                break

            episode_id = str(row.get("episode_id", ""))
            person_name = str(row.get("person_name", ""))
            age = row.get("age", 0)
            text = str(row.get("episode_text", "") or "")

            if not text:
                continue

            # 1. 年号違反チェック
            year_issue = self._detect_year_in_first_sentence(text, episode_id, person_name, age)
            if year_issue:
                result.issues.append(year_issue)
                result.issues_by_type["year_in_first_sentence"] = (
                    result.issues_by_type.get("year_in_first_sentence", 0) + 1
                )

        return result

    def execute(
        self,
        dry_run: bool = True,
        max_risk: str = "low",
        limit: Optional[int] = None,
    ) -> FixResult:
        """修正実行"""
        # バックアップ作成
        backup_path = None
        if not dry_run:
            backup_path = self._create_backup()

        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)

        result = FixResult(
            total_episodes=len(df),
            scanned=0,
            fixed=0,
            skipped=0,
            manual_review=0,
            backup_path=backup_path,
        )

        changes_log = []

        for idx, row in df.iterrows():
            if limit and idx >= limit:
                break

            result.scanned += 1

            episode_id = str(row.get("episode_id", ""))
            person_name = str(row.get("person_name", ""))
            text = str(row.get("episode_text", "") or "")

            if not text:
                continue

            original_text = text
            all_changes = []

            # 1. 年号修正
            text, year_changes = self._fix_year_in_first_sentence(text)
            all_changes.extend(year_changes)

            # 変更があった場合
            if all_changes:
                if not dry_run:
                    df.at[idx, "episode_text"] = text
                    result.fixed += 1
                else:
                    result.fixed += 1

                changes_log.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "changes": all_changes,
                        "original": original_text[:100],
                        "fixed": text[:100],
                    }
                )

        # 保存
        if not dry_run and result.fixed > 0:
            df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            logger.info(f"保存完了: {self.csv_path}")

        # レポート保存
        result.report_path = self._save_report(result, changes_log, dry_run)

        return result

    def _create_backup(self) -> Path:
        """バックアップ作成"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_BACKUP_quality_{timestamp}.csv"
        shutil.copy(self.csv_path, backup_path)
        logger.info(f"バックアップ作成: {backup_path}")
        return backup_path

    def _save_report(self, result: FixResult, changes_log: list[dict], dry_run: bool) -> Path:
        """レポート保存"""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "dryrun" if dry_run else "execute"
        report_path = REPORTS_DIR / f"quality_fix_{mode}_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "summary": {
                "total_episodes": result.total_episodes,
                "scanned": result.scanned,
                "fixed": result.fixed,
                "skipped": result.skipped,
                "manual_review": result.manual_review,
            },
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "changes_sample": changes_log[:50],  # 最大50件
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"レポート保存: {report_path}")
        return report_path


def main():
    parser = argparse.ArgumentParser(description="EPUP準拠エピソード品質修正")
    parser.add_argument("--scan", action="store_true", help="スキャンのみ（検知）")
    parser.add_argument("--dry-run", action="store_true", help="dry-run（修正プレビュー）")
    parser.add_argument("--execute", action="store_true", help="実行（実際に修正）")
    parser.add_argument("--force", action="store_true", help="確認プロンプトをスキップ")
    parser.add_argument("--limit", type=int, help="処理件数上限")
    parser.add_argument("--max-risk", default="low", choices=["low", "medium", "high"], help="許容リスクレベル")
    args = parser.parse_args()

    fixer = EpisodeQualityFixer()

    print("=" * 60)
    print("EPUP準拠エピソード品質修正エンジン")
    print("=" * 60)

    if args.scan:
        print("\n【スキャンモード】")
        result = fixer.scan(limit=args.limit)

        print(f"\n総エピソード数: {result.total_episodes}")
        print(f"問題検出数: {len(result.issues)}")
        print("\n問題の内訳:")
        for issue_type, count in sorted(result.issues_by_type.items(), key=lambda x: -x[1]):
            print(f"  {issue_type}: {count}件")

        print("\n代表例（10件）:")
        for issue in result.issues[:10]:
            print(f"  [{issue.issue_type}] {issue.person_name}({issue.age}歳)")
            print(f"    {issue.description}")
            print(f"    本文: {issue.original_text[:60]}...")

    elif args.dry_run or args.execute:
        dry_run = not args.execute

        if dry_run:
            print("\n【dry-runモード】変更は保存されません")
        else:
            print("\n【実行モード】変更を保存します")
            if not args.force:
                response = input("続行しますか？ (y/N): ")
                if response.lower() != "y":
                    print("中止しました")
                    return

        result = fixer.execute(
            dry_run=dry_run,
            max_risk=args.max_risk,
            limit=args.limit,
        )

        print("\n【結果サマリー】")
        print(f"  総エピソード数: {result.total_episodes}")
        print(f"  スキャン: {result.scanned}")
        print(f"  修正: {result.fixed}")
        print(f"  スキップ: {result.skipped}")
        print(f"  要手動確認: {result.manual_review}")

        if result.backup_path:
            print(f"\n  バックアップ: {result.backup_path}")
        if result.report_path:
            print(f"  レポート: {result.report_path}")

        if dry_run:
            print("\n実行するには: python scripts/fix/fix_episode_quality.py --execute")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
