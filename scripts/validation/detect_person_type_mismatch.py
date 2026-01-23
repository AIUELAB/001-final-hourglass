#!/usr/bin/env python3
"""
EPUP: Person Type ミスマッチ検出スクリプト

架空キャラクターなのに person_type = "REAL" に誤分類されているエピソードを検出する。

検出ロジック:
1. MASTER_EPISODES_CURRENT.csv を読み込む
2. 架空キャラクターリスト（ドラゴンボール、ポケモン、マリオ等）と照合
3. person_name が架空キャラなのに person_type = "REAL" のエピソードを検出
4. 年号パターン（1900-2026年）を含むエピソードも補助的に検出

使用方法:
    # 全件スキャン
    python scripts/validation/detect_person_type_mismatch.py

    # 詳細出力
    python scripts/validation/detect_person_type_mismatch.py --verbose

    # JSON出力
    python scripts/validation/detect_person_type_mismatch.py --output report.json

    # CI用（違反があればexit 1）
    python scripts/validation/detect_person_type_mismatch.py --strict

Author: EPUP Validation Team
Date: 2026-01-22
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
SETTINGS_MASTER = PROJECT_ROOT / "preserved/data/fictional_work_settings_master.json"
REPORT_DIR = PROJECT_ROOT / "src/reports"

# 架空キャラクターデータベース（src/utils/fictional_characters.py から移動 - RCA-20260123）
from src.utils.fictional_characters import (
    FICTIONAL_CHARACTERS,
    ALL_FICTIONAL_CHARACTERS,
    BLACKLIST_NAMES,
)


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class MismatchRecord:
    """ミスマッチ記録"""

    episode_id: str
    person_id: str
    person_name: str
    current_person_type: str
    expected_person_type: str
    work_title: str
    matched_work: str
    episode_text_snippet: str
    detection_reason: str
    has_modern_year: bool = False
    detected_years: list[int] = field(default_factory=list)


# =============================================================================
# 検出ロジック
# =============================================================================


class PersonTypeMismatchDetector:
    """
    Person Type ミスマッチ検出器

    架空キャラクターなのに REAL に分類されているエピソードを検出する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None

        # 年号検出パターン（1900-2026年）
        self.year_pattern = re.compile(r"(19\d{2}|20[0-2]\d)年")

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def detect_fictional_character(self, person_name: str) -> tuple[bool, str]:
        """
        人物名が架空キャラクターかどうかを判定（完全一致のみ）

        Args:
            person_name: 人物名

        Returns:
            (is_fictional, matched_work): 架空キャラクターか、マッチした作品名
        """
        # ブラックリストチェック（一般名との混同防止）
        if person_name in BLACKLIST_NAMES:
            return False, ""

        # 完全一致チェックのみ
        if person_name in ALL_FICTIONAL_CHARACTERS:
            for work, characters in FICTIONAL_CHARACTERS.items():
                if person_name in characters:
                    return True, work

        return False, ""

    def detect_modern_years(self, text: str) -> list[int]:
        """
        テキストから現代年号（1900-2026年）を検出

        Args:
            text: エピソードテキスト

        Returns:
            検出された年号のリスト
        """
        if not isinstance(text, str):
            return []

        matches = self.year_pattern.findall(text)
        return [int(year) for year in matches]

    def scan_episode(self, row: dict) -> Optional[MismatchRecord]:
        """
        単一エピソードをスキャン

        Args:
            row: エピソードデータ

        Returns:
            ミスマッチがあればMismatchRecord、なければNone
        """
        episode_id = str(row.get("episode_id", ""))
        person_id = str(row.get("person_id", ""))
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        work_title = str(row.get("work_title", ""))
        episode_text = str(row.get("episode_text", ""))

        # FICTIONALの場合はスキップ（正しい分類）
        if "FICTIONAL" in person_type:
            return None

        # 架空キャラクターかどうかをチェック（完全一致）
        is_fictional, matched_work = self.detect_fictional_character(person_name)

        if not is_fictional:
            return None

        # ミスマッチ検出
        detected_years = self.detect_modern_years(episode_text)
        has_modern_year = len(detected_years) > 0

        # エピソードテキストのスニペット（最初の100文字）
        snippet = episode_text[:100] + "..." if len(episode_text) > 100 else episode_text

        return MismatchRecord(
            episode_id=episode_id,
            person_id=person_id,
            person_name=person_name,
            current_person_type=person_type,
            expected_person_type="FICTIONAL",
            work_title=work_title if work_title and work_title != "nan" else "",
            matched_work=matched_work,
            episode_text_snippet=snippet,
            detection_reason=f"架空キャラクター（{matched_work}）がREALに分類されている",
            has_modern_year=has_modern_year,
            detected_years=detected_years,
        )

    def scan_all(self) -> list[MismatchRecord]:
        """
        全エピソードをスキャン

        Returns:
            ミスマッチレコードのリスト
        """
        if self.master_df.empty:
            return []

        records = []

        for _, row in self.master_df.iterrows():
            record = self.scan_episode(row.to_dict())
            if record:
                records.append(record)

        return records

    def get_summary(self, records: list[MismatchRecord]) -> dict:
        """
        サマリーを生成

        Args:
            records: ミスマッチレコードのリスト

        Returns:
            サマリー辞書
        """
        by_work: dict[str, int] = {}
        by_character: dict[str, int] = {}
        with_modern_year = 0

        for record in records:
            # 作品別
            work = record.matched_work
            by_work[work] = by_work.get(work, 0) + 1

            # キャラクター別
            char = record.person_name
            by_character[char] = by_character.get(char, 0) + 1

            # 現代年号あり
            if record.has_modern_year:
                with_modern_year += 1

        return {
            "total_mismatches": len(records),
            "by_work": dict(sorted(by_work.items(), key=lambda x: -x[1])),
            "by_character": dict(sorted(by_character.items(), key=lambda x: -x[1])),
            "with_modern_year": with_modern_year,
            "unique_characters": len(by_character),
            "unique_works": len(by_work),
        }


# =============================================================================
# CLI
# =============================================================================


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: Person Type ミスマッチ検出")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="JSON出力先",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="ミスマッチがあればexit 1",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="表示する最大件数（デフォルト: 50）",
    )

    args = parser.parse_args()

    # ヘッダー
    print("=" * 70)
    print("EPUP: Person Type ミスマッチ検出")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 検出器初期化
    detector = PersonTypeMismatchDetector()

    if detector.master_df.empty:
        print(f"\nError: Master CSV not found: {detector.master_csv}")
        return 2

    print(f"\nマスターCSV: {detector.master_csv}")
    print(f"総エピソード数: {len(detector.master_df):,}")
    print(f"登録架空キャラクター数: {len(ALL_FICTIONAL_CHARACTERS)}")
    print(f"ブラックリスト（除外名）: {len(BLACKLIST_NAMES)}")

    # スキャン実行
    print("\nスキャン中...")
    records = detector.scan_all()

    # サマリー
    summary = detector.get_summary(records)

    print(f"\n{'=' * 70}")
    print("検出結果サマリー")
    print(f"{'=' * 70}")
    print(f"ミスマッチ総数: {summary['total_mismatches']}件")
    print(f"ユニークキャラクター数: {summary['unique_characters']}人")
    print(f"ユニーク作品数: {summary['unique_works']}作品")
    print(f"現代年号を含むエピソード: {summary['with_modern_year']}件")

    if summary["by_work"]:
        print("\n作品別ミスマッチ数:")
        for work, count in list(summary["by_work"].items())[:10]:
            print(f"  {work}: {count}件")

    if summary["by_character"]:
        print("\nキャラクター別ミスマッチ数（上位10）:")
        for char, count in list(summary["by_character"].items())[:10]:
            print(f"  {char}: {count}件")

    # 詳細出力
    if records:
        limit = args.limit
        print(f"\n{'=' * 70}")
        print(f"詳細（上位{min(limit, len(records))}件）")
        print(f"{'=' * 70}")

        for i, record in enumerate(records[:limit], 1):
            print(f"\n{i}. {record.episode_id}")
            print(f"   人物名: {record.person_name}")
            print(f"   現在の分類: {record.current_person_type}")
            print(f"   期待される分類: {record.expected_person_type}")
            print(f"   マッチした作品: {record.matched_work}")
            print(f"   理由: {record.detection_reason}")

            if args.verbose:
                print(f"   person_id: {record.person_id}")
                print(f"   work_title: {record.work_title}")
                print(f"   テキスト: {record.episode_text_snippet}")

            if record.has_modern_year:
                print(f"   [警告] 現代年号検出: {record.detected_years}")

    # エピソードID一覧
    if records:
        print(f"\n{'=' * 70}")
        print("修正が必要なエピソードID一覧")
        print(f"{'=' * 70}")
        episode_ids = [r.episode_id for r in records]
        print(f"総数: {len(episode_ids)}件")
        print("\nエピソードID:")
        for eid in episode_ids[:100]:  # 最大100件
            print(f"  {eid}")
        if len(episode_ids) > 100:
            print(f"  ... 他 {len(episode_ids) - 100}件")

    # JSON出力
    if args.output:
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "records": [
                {
                    "episode_id": r.episode_id,
                    "person_id": r.person_id,
                    "person_name": r.person_name,
                    "current_person_type": r.current_person_type,
                    "expected_person_type": r.expected_person_type,
                    "work_title": r.work_title,
                    "matched_work": r.matched_work,
                    "detection_reason": r.detection_reason,
                    "has_modern_year": r.has_modern_year,
                    "detected_years": r.detected_years,
                }
                for r in records
            ],
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nJSONレポート保存: {output_path}")

    # 終了コード
    if args.strict and summary["total_mismatches"] > 0:
        print(f"\n[FAILED] {summary['total_mismatches']}件のミスマッチがあります")
        return 1

    if summary["total_mismatches"] == 0:
        print("\n[OK] ミスマッチは検出されませんでした")
    else:
        print(f"\n[WARNING] {summary['total_mismatches']}件のミスマッチを検出しました")

    return 0


if __name__ == "__main__":
    sys.exit(main())
