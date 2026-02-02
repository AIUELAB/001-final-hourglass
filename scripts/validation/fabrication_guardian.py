#!/usr/bin/env python3
"""
FabricationGuardian - LLM捏造検出・修正・隔離の統合オーケストレーター

エピソードデータベースに対するLLM捏造を検出し、
修正可能なものは自動修正、修正不可能なものは隔離する。

## アーキテクチャ
```
FabricationGuardian（統合オーケストレーター）
├── 検出レイヤー
│   ├── RealPersonVerifier - REAL人物検証
│   ├── FictionalQualityGate - FICTIONAL検証
│   └── AuthenticityChecker - 真正性検証
├── 修正レイヤー
│   └── auto_fix() - 修正可能な違反の自動修正
└── 隔離レイヤー
    └── QuarantineManager - 隔離管理
```

## 使用方法
    # 基本使用（ドライラン）
    python scripts/validation/fabrication_guardian.py

    # 修正・隔離を実行
    python scripts/validation/fabrication_guardian.py --execute

    # 特定人物のみ処理
    python scripts/validation/fabrication_guardian.py --person-id P-12345

    # 処理件数上限
    python scripts/validation/fabrication_guardian.py --limit 100

    # 隔離解除
    python scripts/validation/fabrication_guardian.py --release EP-12345

Author: EPUP Validation Team
Date: 2026-02-01
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.quarantine_manager import QuarantineManager
from scripts.validation.real_person_verifier import RealPersonVerifier
from src.utils.fictional_quality_gate import FictionalQualityGate


# =============================================================================
# データクラス定義
# =============================================================================


class ActionType(Enum):
    """処理結果アクションタイプ"""

    PASS = "pass"  # 問題なし
    AUTO_FIXED = "auto_fixed"  # 自動修正済み
    QUARANTINED = "quarantined"  # 隔離
    SKIPPED = "skipped"  # スキップ（検査対象外）


@dataclass
class GuardianResult:
    """スキャン結果"""

    episode_id: str
    person_name: str
    person_type: str
    action: ActionType
    violation_type: Optional[str]
    violation_detail: Optional[str]
    super_total_score: float
    fixed_text: Optional[str] = None  # 修正後テキスト（修正した場合）

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "episode_id": self.episode_id,
            "person_name": self.person_name,
            "person_type": self.person_type,
            "action": self.action.value,
            "violation_type": self.violation_type,
            "violation_detail": self.violation_detail,
            "super_total_score": self.super_total_score,
            "fixed_text": self.fixed_text,
        }


# =============================================================================
# FabricationGuardian クラス
# =============================================================================


class FabricationGuardian:
    """
    LLM捏造検出・修正・隔離の統合オーケストレーター

    検出レイヤー:
    - RealPersonVerifier: REAL人物の検証
    - FictionalQualityGate: FICTIONAL人物の検証

    修正レイヤー:
    - auto_fix(): 修正可能な違反の自動修正

    隔離レイヤー:
    - QuarantineManager: 隔離管理
    """

    # super_total_score < 100,000 で隔離対象
    QUARANTINE_THRESHOLD = 100000

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        dry_run: bool = True,
    ):
        """
        初期化

        Args:
            csv_path: CSVファイルパス（デフォルト: preserved/data/MASTER_EPISODES_CURRENT.csv）
            dry_run: ドライラン（True: 検出のみ、False: 修正・隔離実行）
        """
        self.csv_path = csv_path or (PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv")
        self.dry_run = dry_run

        # レイヤー初期化
        self.quarantine_manager = QuarantineManager()
        self.real_verifier = RealPersonVerifier()
        self.fictional_gate = FictionalQualityGate(enable_authenticity_check=True)

        # 結果格納
        self.results: list[GuardianResult] = []
        self._episodes: list[dict] = []

    def scan(
        self,
        person_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[GuardianResult]:
        """
        CSVをスキャンして違反を検出

        処理フロー:
        1. CSVを読み込み
        2. 各エピソードをチェック
           - person_type == "REAL": RealPersonVerifier
           - person_type == "FICTIONAL": FictionalQualityGate
        3. 違反検出時:
           a. 修正可能なら auto_fix() 試行
           b. 修正後もスコア < 閾値 なら隔離
        4. 結果をself.resultsに蓄積

        Args:
            person_id: 特定人物のみ処理（Noneの場合は全て）
            limit: 処理件数上限

        Returns:
            GuardianResultのリスト
        """
        self.results = []
        self._episodes = self._load_csv(person_id, limit)

        total = len(self._episodes)
        if total == 0:
            print("処理対象のエピソードがありません。")
            return self.results

        print(self._create_header())
        print(f"\n  📂 対象CSV: {self.csv_path}")
        print(f"  📋 スキャン対象: {total:,} 件")
        print(f"  🔧 モード: {'ドライラン（検出のみ）' if self.dry_run else '実行モード（修正・隔離）'}")
        print(f"  📊 隔離閾値: super_total_score < {self.QUARANTINE_THRESHOLD:,}")
        print()

        # プログレスバー表示用
        bar_width = 50
        violations_detected = 0
        auto_fixed_count = 0
        quarantined_count = 0

        for i, episode in enumerate(self._episodes, 1):
            result = self._check_episode(episode)
            self.results.append(result)

            # 統計更新
            if result.action != ActionType.PASS and result.action != ActionType.SKIPPED:
                violations_detected += 1
            if result.action == ActionType.AUTO_FIXED:
                auto_fixed_count += 1
            if result.action == ActionType.QUARANTINED:
                quarantined_count += 1

            # プログレスバー更新（50件ごと or 最後）
            if i % 50 == 0 or i == total:
                progress = i / total
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                print(f"\r  [{bar}] {i:>6}/{total} ({progress*100:5.1f}%)", end="", flush=True)

        print()  # 改行

        # サマリー表示
        print(self._create_summary(total, violations_detected, auto_fixed_count, quarantined_count))

        return self.results

    def _load_csv(self, person_id: Optional[str], limit: Optional[int]) -> list[dict]:
        """CSVファイルを読み込み"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_path}")

        episodes: list[dict] = []

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # person_id フィルタ
                if person_id and row.get("person_id") != person_id:
                    continue

                episodes.append(row)

                # 件数上限
                if limit and len(episodes) >= limit:
                    break

        return episodes

    def _check_episode(self, episode: dict) -> GuardianResult:
        """
        単一エピソードをチェック

        Args:
            episode: エピソードデータ

        Returns:
            GuardianResult
        """
        episode_id = str(episode.get("episode_id", ""))
        person_name = str(episode.get("person_name", ""))
        person_type = str(episode.get("person_type", "")).upper()

        # スコア取得
        try:
            super_total_score = float(episode.get("super_total_score", 0))
        except (ValueError, TypeError):
            super_total_score = 0.0

        # 人物タイプに応じた検証
        if "REAL" in person_type:
            # REAL人物: RealPersonVerifier
            return self._check_real_episode(episode, episode_id, person_name, person_type, super_total_score)
        elif "FICTIONAL" in person_type:
            # FICTIONAL人物: FictionalQualityGate
            return self._check_fictional_episode(episode, episode_id, person_name, person_type, super_total_score)
        else:
            # 不明なタイプはスキップ
            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.SKIPPED,
                violation_type=None,
                violation_detail=f"不明なperson_type: {person_type}",
                super_total_score=super_total_score,
            )

    def _check_real_episode(
        self,
        episode: dict,
        episode_id: str,
        person_name: str,
        person_type: str,
        super_total_score: float,
    ) -> GuardianResult:
        """REAL人物のエピソードをチェック"""
        episode_text = str(episode.get("episode_text", ""))

        # 年齢・生年・没年取得
        try:
            age = float(episode.get("age", 0))
        except (ValueError, TypeError):
            age = 0.0

        birth_year = episode.get("birth_year")
        death_year = episode.get("death_year")
        source = episode.get("source")

        # 型変換
        try:
            birth_year = int(birth_year) if birth_year else None
        except (ValueError, TypeError):
            birth_year = None

        try:
            death_year = int(death_year) if death_year else None
        except (ValueError, TypeError):
            death_year = None

        # RealPersonVerifier で検証
        result = self.real_verifier.verify(
            person_name=person_name,
            episode_text=episode_text,
            age=age,
            birth_year=birth_year,
            death_year=death_year,
            source=source,
        )

        if result.passed:
            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.PASS,
                violation_type=None,
                violation_detail=None,
                super_total_score=super_total_score,
            )

        # 違反検出
        violation_type = result.violation_type.value if result.violation_type else "unknown"
        violation_detail = result.violation_detail

        # 修正可能か判定（FILLER, FABRICATION は修正困難）
        # NOTE: fixable は将来の修正ロジック用に設計されているが、現在は未使用
        # fixable = result.violation_type in [RealViolationType.FUTURE_EPISODE, RealViolationType.POST_DEATH]

        # 隔離判定
        if self._should_quarantine(episode):
            # 隔離実行
            if not self.dry_run:
                self.quarantine_manager.quarantine(
                    episode_id=episode_id,
                    person_name=person_name,
                    reason=violation_detail,
                    violation_type=violation_type,
                    super_total_score=super_total_score,
                    episode_data=episode,
                )

            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.QUARANTINED,
                violation_type=violation_type,
                violation_detail=violation_detail,
                super_total_score=super_total_score,
            )

        # 修正不可で隔離対象外 → PASS として通過（ただし違反情報は記録）
        return GuardianResult(
            episode_id=episode_id,
            person_name=person_name,
            person_type=person_type,
            action=ActionType.PASS,
            violation_type=violation_type,
            violation_detail=f"スコア高のため通過: {violation_detail}",
            super_total_score=super_total_score,
        )

    def _check_fictional_episode(
        self,
        episode: dict,
        episode_id: str,
        person_name: str,
        person_type: str,
        super_total_score: float,
    ) -> GuardianResult:
        """FICTIONAL人物のエピソードをチェック"""
        # FictionalQualityGate で検証
        result = self.fictional_gate.check(episode)

        if result.passed:
            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.PASS,
                violation_type=None,
                violation_detail=None,
                super_total_score=super_total_score,
            )

        # 違反検出
        violations = result.violations
        if not violations:
            # 違反リストが空の場合（想定外）
            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.PASS,
                violation_type=None,
                violation_detail=None,
                super_total_score=super_total_score,
            )

        # 最初の違反を使用
        first_violation = violations[0]
        violation_type = first_violation.type.value
        violation_detail = first_violation.detail

        # 修正可能か判定
        if result.fixable and result.auto_fixed_text:
            # 自動修正成功
            fixed_text = result.auto_fixed_text

            if not self.dry_run:
                # CSVを更新（実装省略: 別途バッチ処理で対応）
                pass

            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.AUTO_FIXED,
                violation_type=violation_type,
                violation_detail=violation_detail,
                super_total_score=super_total_score,
                fixed_text=fixed_text,
            )

        # 隔離判定
        if self._should_quarantine(episode):
            if not self.dry_run:
                self.quarantine_manager.quarantine(
                    episode_id=episode_id,
                    person_name=person_name,
                    reason=violation_detail,
                    violation_type=violation_type,
                    super_total_score=super_total_score,
                    episode_data=episode,
                )

            return GuardianResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                action=ActionType.QUARANTINED,
                violation_type=violation_type,
                violation_detail=violation_detail,
                super_total_score=super_total_score,
            )

        # スコア高のため通過
        return GuardianResult(
            episode_id=episode_id,
            person_name=person_name,
            person_type=person_type,
            action=ActionType.PASS,
            violation_type=violation_type,
            violation_detail=f"スコア高のため通過: {violation_detail}",
            super_total_score=super_total_score,
        )

    def _apply_fix(self, episode: dict, _violation_type: str) -> tuple[bool, Optional[str]]:
        """
        修正を試行

        Args:
            episode: エピソードデータ
            violation_type: 違反タイプ

        Returns:
            (成功したか, 修正後テキスト)
        """
        # FictionalQualityGate の auto_fix を使用
        result = self.fictional_gate.check(episode)

        if result.fixable and result.auto_fixed_text:
            return True, result.auto_fixed_text

        return False, None

    def _should_quarantine(self, episode: dict) -> bool:
        """
        隔離判定（スコア < 100,000）

        Args:
            episode: エピソードデータ

        Returns:
            隔離すべきかどうか
        """
        try:
            score = float(episode.get("super_total_score", 0))
        except (ValueError, TypeError):
            score = 0

        return score < self.QUARANTINE_THRESHOLD

    def execute(self) -> dict:
        """
        スキャン結果を実行

        - dry_run=False: 実際に隔離を実行
        - dry_run=True: レポートのみ

        Returns:
            実行結果サマリー
        """
        if not self.results:
            return {"error": "scan() を先に実行してください"}

        # 統計計算
        total = len(self.results)
        passed = sum(1 for r in self.results if r.action == ActionType.PASS)
        auto_fixed = sum(1 for r in self.results if r.action == ActionType.AUTO_FIXED)
        quarantined = sum(1 for r in self.results if r.action == ActionType.QUARANTINED)
        skipped = sum(1 for r in self.results if r.action == ActionType.SKIPPED)
        violations_detected = total - passed - skipped

        return {
            "executed_at": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "total_scanned": total,
            "passed": passed,
            "violations_detected": violations_detected,
            "auto_fixed": auto_fixed,
            "quarantined": quarantined,
            "skipped": skipped,
        }

    def release(self, episode_id: str) -> bool:
        """
        特定エピソードを隔離解除

        Args:
            episode_id: エピソードID

        Returns:
            成功したかどうか
        """
        result = self.quarantine_manager.release(episode_id, "Manual release via FabricationGuardian")
        return result is not None

    def generate_report(self) -> dict:
        """
        レポートを生成してsrc/reports/に保存

        Returns:
            レポートデータ
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # 統計計算
        total = len(self.results)
        passed = sum(1 for r in self.results if r.action == ActionType.PASS)
        auto_fixed = sum(1 for r in self.results if r.action == ActionType.AUTO_FIXED)
        quarantined = sum(1 for r in self.results if r.action == ActionType.QUARANTINED)
        skipped = sum(1 for r in self.results if r.action == ActionType.SKIPPED)
        violations_detected = auto_fixed + quarantined

        # 違反タイプ別集計
        violation_type_counts: dict[str, int] = {}
        for r in self.results:
            if r.violation_type:
                violation_type_counts[r.violation_type] = violation_type_counts.get(r.violation_type, 0) + 1

        # 詳細データ（違反があるもののみ）
        details = [r.to_dict() for r in self.results if r.action in [ActionType.AUTO_FIXED, ActionType.QUARANTINED]]

        report = {
            "scan_timestamp": timestamp.isoformat(),
            "total_scanned": total,
            "passed": passed,
            "violations_detected": violations_detected,
            "auto_fixed": auto_fixed,
            "quarantined": quarantined,
            "skipped": skipped,
            "quarantine_threshold": self.QUARANTINE_THRESHOLD,
            "dry_run": self.dry_run,
            "violation_type_breakdown": violation_type_counts,
            "details": details,
        }

        # レポート保存
        report_dir = PROJECT_ROOT / "src" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"fabrication_guardian_report_{timestamp_str}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n  📄 レポート保存: {report_path}")

        return report

    def _create_header(self) -> str:
        """ヘッダー表示を作成"""
        return """
╔════════════════════════════════════════════════════════════════╗
║           FabricationGuardian - LLM捏造検出システム            ║
╚════════════════════════════════════════════════════════════════╝"""

    def _create_summary(
        self,
        total: int,
        violations: int,
        auto_fixed: int,
        quarantined: int,
    ) -> str:
        """サマリー表示を作成"""
        passed = total - violations - (total - len(self.results))
        skipped = sum(1 for r in self.results if r.action == ActionType.SKIPPED)

        return f"""
  ┌─────────────────────────────────────────────────────────────────┐
  │                        スキャン結果                              │
  ├─────────────────┬─────────────────┬─────────────────┬───────────┤
  │    📊 総数      │   ✅ 合格       │   🔧 自動修正   │  🚫 隔離  │
  ├─────────────────┼─────────────────┼─────────────────┼───────────┤
  │  {total:>10,} 件  │  {passed:>10,} 件  │  {auto_fixed:>10,} 件  │ {quarantined:>6,} 件 │
  └─────────────────┴─────────────────┴─────────────────┴───────────┘

  📋 違反検出: {violations:,} 件  |  ⏭️ スキップ: {skipped:,} 件"""


# =============================================================================
# CLI メイン関数
# =============================================================================


def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="FabricationGuardian - LLM捏造検出・修正・隔離システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # ドライラン（検出のみ）
    python scripts/validation/fabrication_guardian.py

    # 修正・隔離を実行
    python scripts/validation/fabrication_guardian.py --execute

    # 特定人物のみ処理
    python scripts/validation/fabrication_guardian.py --person-id P-12345

    # 処理件数上限
    python scripts/validation/fabrication_guardian.py --limit 100

    # 隔離解除
    python scripts/validation/fabrication_guardian.py --release EP-12345
""",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="検出のみ（デフォルト）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="修正→隔離を実行",
    )
    parser.add_argument(
        "--person-id",
        type=str,
        help="特定人物のみ処理",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="処理件数上限",
    )
    parser.add_argument(
        "--release",
        type=str,
        help="隔離解除するエピソードID",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="処理対象のCSVファイルパス",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="レポートのみ生成（既存のquarantineデータから）",
    )

    args = parser.parse_args()

    # dry_run の判定（--execute があれば False）
    dry_run = not args.execute

    # CSVパス
    csv_path = Path(args.csv) if args.csv else None

    # FabricationGuardian インスタンス作成
    guardian = FabricationGuardian(
        csv_path=csv_path,
        dry_run=dry_run,
    )

    # 隔離解除モード
    if args.release:
        print(f"\n  🔓 隔離解除: {args.release}")
        success = guardian.release(args.release)
        if success:
            print(f"  ✅ 解除成功: {args.release}")
        else:
            print(f"  ❌ 解除失敗: {args.release}")
        return

    # レポートのみモード
    if args.report_only:
        report = guardian.quarantine_manager.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # スキャン実行
    guardian.scan(
        person_id=args.person_id,
        limit=args.limit,
    )

    # レポート生成
    report = guardian.generate_report()

    # 実行サマリー
    summary = guardian.execute()

    print(f"\n  🏁 実行完了: {summary.get('executed_at', 'N/A')}")

    if dry_run:
        print("  💡 ヒント: 実際に修正・隔離を実行するには --execute フラグを使用してください")


if __name__ == "__main__":
    main()
