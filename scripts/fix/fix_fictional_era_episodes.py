#!/usr/bin/env python3
"""
EPUP: 架空キャラクター 時代設定違反エピソード修正スクリプト

時代設定に違反するエピソード（歴史作品に現代年号を含むなど）を検出し、
Batch APIで再生成して修正する。

機能:
1. detect: 違反エピソードを検出してレポート生成
2. submit: 違反エピソードの再生成バッチを送信
3. apply: バッチ結果をマスターCSVに適用

使用方法:
    # 違反検出（ドライラン）
    python scripts/fix/fix_fictional_era_episodes.py --detect-only

    # Batch API送信
    python scripts/fix/fix_fictional_era_episodes.py --submit

    # バッチ結果適用
    python scripts/fix/fix_fictional_era_episodes.py --apply --batch-id msgbatch_xxx

    # 一括実行（検出→送信→完了待ち→適用）
    python scripts/fix/fix_fictional_era_episodes.py --full

Author: EPUP Fix Team
Date: 2026-01-15
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.fictional_episode_validator import (
    CHARACTER_WORK_MAP,
    WORK_ERA_SETTINGS,
    FictionalEpisodeValidator,
    ValidationResult,
    ViolationType,
)

_has_batch_api = False
BatchProcessor: type | None = None
BatchRequest: type | None = None
HybridConfig: type | None = None

try:
    from scripts.sage.batch_processor import BatchProcessor, BatchRequest
    from scripts.sage.config import HybridConfig

    _has_batch_api = True
except ImportError:
    pass

HAS_BATCH_API: bool = _has_batch_api

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"
BATCH_JOBS_DIR = PROJECT_ROOT / "src/cache/batch_jobs"


# =============================================================================
# 再生成プロンプトテンプレート
# =============================================================================

# 時代設定を考慮した再生成プロンプト
ERA_AWARE_PROMPT_TEMPLATE = """あなたは{work_title}の世界観を深く理解するストーリーテラーです。

{person_name}（{work_title}のキャラクター）が{age}歳の時点での作品内エピソードを生成してください。

【重要な時代設定】
- この作品は「{era_name}」を舞台としています（{era_range}）
- 現代の年号（西暦1945年以降）は絶対に使用しないでください
- 作品世界内の時間軸・設定を尊重してください

【出力フォーマット】
必ず以下の形式で開始してください:
「あなたと同じ{age}歳のとき、{person_name}は〜」

【禁止事項】
- 現代の年号（西暦1945年以降）の使用
- メタ的言及（「架空のキャラクター」「フィクションの」等）
- 作品名の直接言及（「鬼滅の刃の世界で」等）
- 原作に存在しない出来事の創作

【作品固有の注意事項】
{work_specific_notes}

【生成方針】
- 原作/アニメで{age}歳時点の描写がある場合のみ、それを活用
- キャラクターの性格・口癖・行動パターンを維持
- 作品内の地名、イベント、関係キャラクターのみを活用
- 200-250文字で生成

出力:
"""

# 作品固有の注意事項
WORK_SPECIFIC_NOTES = {
    "鬼滅の刃": """
- 大正時代の日本が舞台
- 鬼殺隊、鬼、呼吸法などの設定を活用
- キャラクターが登場する編（アーク）を確認
  - 炭治郎・禰豆子: 全編に登場
  - カナヲ: 最終選別、蝶屋敷、柱稽古、無限城に登場（無限列車・遊郭には登場しない）
  - 煉獄: 柱合会議、無限列車のみ（無限列車で死亡）
""",
    "るろうに剣心": """
- 明治時代の日本が舞台
- 飛天御剣流、新選組などの設定を活用
- 緋村剣心は人斬り抜刀斎としての過去を持つ
""",
    "進撃の巨人": """
- 独自の年号体系（845年など作品内年号）を使用
- 西暦は一切使用しない
- 壁内世界と壁外世界の区別に注意
""",
    "ONE PIECE": """
- 架空の海賊世界が舞台
- 西暦は使用しない
- 大海賊時代、グランドラインなどの設定を活用
""",
    "NARUTO": """
- 架空の忍者世界が舞台
- 西暦は使用しない
- 木ノ葉隠れの里、忍術などの設定を活用
""",
}


def get_work_specific_notes(work_title: str) -> str:
    """作品固有の注意事項を取得"""
    for key, notes in WORK_SPECIFIC_NOTES.items():
        if key in work_title:
            return notes
    return "- 作品世界観を尊重し、現代の概念・年号を使用しない"


# =============================================================================
# 修正クラス
# =============================================================================


class FictionalEraEpisodeFixer:
    """
    架空キャラクター時代設定違反エピソード修正器

    Batch APIを使用して違反エピソードを再生成する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV, dry_run: bool = False):
        self.master_csv = master_csv
        self.dry_run = dry_run
        self._master_df: Optional[pd.DataFrame] = None
        self.validator = FictionalEpisodeValidator(master_csv)

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def reload_master(self) -> None:
        """マスターデータを再読み込み"""
        self._master_df = None
        _ = self.master_df

    def detect_violations(
        self,
        violation_types: Optional[list[ViolationType]] = None,
    ) -> list[ValidationResult]:
        """
        違反エピソードを検出

        Args:
            violation_types: 検出する違反タイプ（Noneで全て）

        Returns:
            違反エピソードのリスト
        """
        # デフォルトで時代設定関連の違反のみ
        if violation_types is None:
            violation_types = [
                ViolationType.ERA_INCONSISTENCY,
                ViolationType.MODERN_YEAR_IN_HISTORICAL,
                ViolationType.WORK_FACT_ERROR,
            ]

        # 全スキャン
        all_results = self.validator.scan_all_episodes()

        # 指定タイプでフィルタ
        filtered_results = []
        for result in all_results:
            matching_violations = [v for v in result.violations if v.violation_type in violation_types]
            if matching_violations:
                result.violations = matching_violations
                filtered_results.append(result)

        return filtered_results

    def create_batch_requests(self, violations: list[ValidationResult]) -> list:
        """
        違反エピソードからBatch APIリクエストを作成

        Args:
            violations: 違反エピソードのリスト

        Returns:
            BatchRequestのリスト
        """
        if not HAS_BATCH_API:
            raise ImportError("Batch API not available")

        requests = []

        for result in violations:
            episode_id = result.episode_id
            person_name = result.person_name

            # マスターから追加情報を取得
            row = self.master_df[self.master_df["episode_id"] == episode_id]
            if row.empty:
                continue

            row = row.iloc[0]
            age = int(row.get("age", 0) or 0)
            work_title = str(row.get("work_title", ""))

            # 作品情報を取得
            era_setting = self._get_era_setting(work_title, person_name)
            if era_setting is None:
                continue

            era_name = era_setting.get("era_name", "不明")
            era_start = era_setting.get("era_start", "?")
            era_end = era_setting.get("era_end", "?")
            era_range = f"{era_start}-{era_end}" if era_start and era_end else "不明"

            work_specific_notes = get_work_specific_notes(work_title or era_setting.get("work_title", ""))

            # プロンプト生成
            prompt = ERA_AWARE_PROMPT_TEMPLATE.format(
                person_name=person_name,
                age=age,
                work_title=work_title or era_setting.get("work_title", "作品"),
                era_name=era_name,
                era_range=era_range,
                work_specific_notes=work_specific_notes,
            )

            # custom_id形式: FIX_ERA_{episode_id}
            custom_id = f"FIX_ERA_{episode_id}"

            assert BatchRequest is not None
            requests.append(
                BatchRequest(
                    custom_id=custom_id,
                    person_name=person_name,
                    age=age,
                    category="FICTIONAL",
                    prompt=prompt,
                    model="claude-sonnet-4-20250514",
                    max_tokens=512,
                )
            )

        return requests

    async def submit_batch(self, requests: list) -> dict:
        """
        Batch APIにリクエストを送信

        Args:
            requests: BatchRequestのリスト

        Returns:
            バッチジョブ情報
        """
        if not HAS_BATCH_API:
            raise ImportError("Batch API not available")

        if self.dry_run:
            print(f"[DRY RUN] Would submit {len(requests)} requests to Batch API")
            return {"dry_run": True, "request_count": len(requests)}

        assert BatchProcessor is not None and HybridConfig is not None
        processor = BatchProcessor(config=HybridConfig())
        job = await processor.submit_batch(requests)

        # ジョブ情報をファイルに保存
        BATCH_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        job_path = BATCH_JOBS_DIR / f"fix_era_{job.batch_id}.json"

        job_info = {
            "batch_id": job.batch_id,
            "created_at": job.created_at,
            "status": job.status,
            "request_count": job.request_count,
            "requests": [
                {
                    "custom_id": req.custom_id,
                    "person_name": req.person_name,
                    "age": req.age,
                }
                for req in requests
            ],
        }

        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job_info, f, ensure_ascii=False, indent=2)

        print(f"バッチジョブ保存: {job_path}")

        return job.to_dict()

    async def wait_for_completion(self, batch_id: str, poll_interval: int = 60, max_wait: int = 3600) -> dict:
        """
        バッチ完了を待機

        Args:
            batch_id: バッチID
            poll_interval: ポーリング間隔（秒）
            max_wait: 最大待機時間（秒）

        Returns:
            最終ステータス
        """
        if not HAS_BATCH_API:
            raise ImportError("Batch API not available")

        assert BatchProcessor is not None and HybridConfig is not None
        processor = BatchProcessor(config=HybridConfig())
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                print(f"[TIMEOUT] {max_wait}秒経過しました")
                break

            job = await processor.check_status(batch_id)
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Status: {job.status} | Succeeded: {job.succeeded_count}/{job.request_count}"
            )

            if job.status == "ended":
                print("[COMPLETED] バッチ処理完了")
                return job.to_dict()

            if job.status in ("canceled", "expired"):
                print(f"[{job.status.upper()}] バッチ処理が中断されました")
                return job.to_dict()

            await asyncio.sleep(poll_interval)

        return {"status": "timeout", "batch_id": batch_id}

    async def retrieve_and_apply(self, batch_id: str) -> dict:
        """
        バッチ結果を取得してマスターCSVに適用

        Args:
            batch_id: バッチID

        Returns:
            適用結果
        """
        if not HAS_BATCH_API:
            raise ImportError("Batch API not available")

        assert BatchProcessor is not None and HybridConfig is not None
        processor = BatchProcessor(config=HybridConfig())

        # 結果取得
        job: Any = await processor.get_results(batch_id)  # type: ignore[attr-defined]

        if not job.results:
            return {"error": "No results available", "status": job.status}

        # マスターCSV読み込み
        df = self.master_df.copy()

        applied_count = 0
        failed_count = 0
        results_detail: list[dict[str, Any]] = []

        for result in job.results:
            custom_id = result.get("custom_id", "")
            result_type = result.get("result", {}).get("type", "")

            # FIX_ERA_{episode_id} からepisode_idを抽出
            if not custom_id.startswith("FIX_ERA_"):
                continue

            episode_id = custom_id.replace("FIX_ERA_", "")

            if result_type == "succeeded":
                # 成功結果からテキストを抽出
                message = result.get("result", {}).get("message", {})
                content = message.get("content", [])

                if content and isinstance(content, list):
                    new_text = content[0].get("text", "")

                    if new_text and len(new_text) >= 100:
                        # 再検証: 新しいテキストが時代設定に準拠しているか
                        if self._validate_regenerated_text(episode_id, new_text):
                            # マスターCSVを更新
                            idx = df[df["episode_id"] == episode_id].index
                            if len(idx) > 0:
                                if not self.dry_run:
                                    df.loc[idx[0], "episode_text"] = new_text
                                    df.loc[idx[0], "fact_check_result"] = "FIX_ERA_REGENERATED"

                                applied_count += 1
                                results_detail.append(
                                    {
                                        "episode_id": episode_id,
                                        "status": "applied",
                                        "new_text_preview": new_text[:100] + "...",
                                    }
                                )
                            else:
                                failed_count += 1
                                results_detail.append(
                                    {
                                        "episode_id": episode_id,
                                        "status": "not_found_in_master",
                                    }
                                )
                        else:
                            failed_count += 1
                            results_detail.append(
                                {
                                    "episode_id": episode_id,
                                    "status": "validation_failed",
                                    "reason": "Regenerated text still contains violations",
                                }
                            )
                    else:
                        failed_count += 1
                        results_detail.append(
                            {
                                "episode_id": episode_id,
                                "status": "invalid_text",
                                "reason": "Text too short or empty",
                            }
                        )
            else:
                failed_count += 1
                results_detail.append(
                    {
                        "episode_id": episode_id,
                        "status": f"batch_result_{result_type}",
                    }
                )

        # マスターCSV保存
        if not self.dry_run and applied_count > 0:
            # バックアップ
            backup_path = self.master_csv.with_suffix(
                f".backup_before_era_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            self.master_df.to_csv(backup_path, index=False, encoding="utf-8-sig")
            print(f"バックアップ: {backup_path}")

            # 更新保存
            df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")
            print(f"マスターCSV更新: {self.master_csv}")

        return {
            "batch_id": batch_id,
            "applied_count": applied_count,
            "failed_count": failed_count,
            "dry_run": self.dry_run,
            "results": results_detail,
        }

    def _get_era_setting(self, work_title: str, person_name: str) -> Optional[dict]:
        """作品の時代設定を取得"""
        if work_title and str(work_title) != "nan":
            for title_key, setting in WORK_ERA_SETTINGS.items():
                if title_key in work_title:
                    return {**setting, "work_title": title_key}

        char_info = CHARACTER_WORK_MAP.get(person_name)
        if char_info:
            work = char_info.get("work_title")
            if work and work in WORK_ERA_SETTINGS:
                return {**WORK_ERA_SETTINGS[work], "work_title": work}

        return None

    def _validate_regenerated_text(self, episode_id: str, text: str) -> bool:
        """再生成テキストが時代設定に準拠しているかを検証"""
        # マスターから人物情報を取得
        row = self.master_df[self.master_df["episode_id"] == episode_id]
        if row.empty:
            return False

        row = row.iloc[0]
        person_name = str(row.get("person_name", ""))
        work_title = str(row.get("work_title", ""))

        # 時代設定を取得
        era_setting = self._get_era_setting(work_title, person_name)
        if era_setting is None:
            return True  # 時代設定なしの場合は検証パス

        prohibited_years = era_setting.get("prohibited_years", [])
        if not prohibited_years:
            return True

        # 禁止年号をチェック
        import re

        year_pattern = r"(19\d{2}|20\d{2})年"
        found_years = re.findall(year_pattern, text)

        for year_str in found_years:
            year = int(year_str)
            if year in prohibited_years:
                return False

        return True

    def generate_report(self, violations: list[ValidationResult]) -> str:
        """
        違反レポートを生成

        Args:
            violations: 違反エピソードのリスト

        Returns:
            レポート文字列
        """
        lines = []
        lines.append("=" * 70)
        lines.append("EPUP: 架空キャラクター 時代設定違反レポート")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"検出された違反: {len(violations)}件")
        lines.append("")

        # 作品別集計
        work_counts: dict[str, int] = {}
        for v in violations:
            for vio in v.violations:
                work = vio.details.get("work_title", "不明")
                work_counts[work] = work_counts.get(work, 0) + 1

        if work_counts:
            lines.append("作品別違反件数:")
            for work, count in sorted(work_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {work}: {count}件")
            lines.append("")

        # 詳細
        for i, result in enumerate(violations[:50], 1):  # 上位50件
            lines.append(f"--- [{i}] {result.episode_id} | {result.person_name} ---")
            for vio in result.violations:
                lines.append(f"  [{vio.severity}] {vio.violation_type.value}")
                lines.append(f"  Message: {vio.message}")
                if "detected_year" in vio.details:
                    lines.append(f"  検出年号: {vio.details['detected_year']}")
                if "era_name" in vio.details:
                    lines.append(f"  作品時代: {vio.details['era_name']}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================


async def main_async(args):
    """非同期メイン処理"""
    fixer = FictionalEraEpisodeFixer(dry_run=args.dry_run)

    # 1. 違反検出
    if args.detect_only or args.submit or args.full:
        print("=" * 70)
        print("Step 1: 違反検出")
        print("=" * 70)

        violations = fixer.detect_violations()
        print(f"検出された違反: {len(violations)}件")

        # レポート生成・保存
        report = fixer.generate_report(violations)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"fictional_era_violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"レポート保存: {report_path}")

        if args.detect_only:
            print(report)
            return 0 if len(violations) == 0 else 1

    # 2. Batch送信
    if args.submit or args.full:
        print("\n" + "=" * 70)
        print("Step 2: Batch API送信")
        print("=" * 70)

        if not HAS_BATCH_API:
            print("[ERROR] Batch API not available. Install anthropic package.")
            return 2

        violations = fixer.detect_violations()
        if not violations:
            print("違反なし。Batch送信をスキップします。")
            return 0

        requests = fixer.create_batch_requests(violations)
        print(f"作成されたリクエスト: {len(requests)}件")

        if not requests:
            print("有効なリクエストがありません。")
            return 1

        job_info = await fixer.submit_batch(requests)
        print(f"Batch送信完了: {job_info}")

        batch_id = job_info.get("batch_id")

        # 3. 完了待ち（--fullの場合のみ）
        if args.full and batch_id:
            print("\n" + "=" * 70)
            print("Step 3: 完了待機")
            print("=" * 70)

            status = await fixer.wait_for_completion(batch_id)
            print(f"最終ステータス: {status}")

            # 4. 結果適用
            if status.get("status") == "ended":
                print("\n" + "=" * 70)
                print("Step 4: 結果適用")
                print("=" * 70)

                result = await fixer.retrieve_and_apply(batch_id)
                print(f"適用結果: {result}")

        return 0

    # 3. 結果適用（--applyの場合）
    if args.apply and args.batch_id:
        print("=" * 70)
        print("Step: 結果適用")
        print("=" * 70)

        result = await fixer.retrieve_and_apply(args.batch_id)
        print(f"適用結果: {result}")
        return 0

    return 0


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラクター時代設定違反エピソード修正")
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="違反検出のみ（Batch送信しない）",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="違反検出→Batch API送信",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Batch結果をマスターCSVに適用",
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        help="適用するバッチID",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="一括実行（検出→送信→完了待ち→適用）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（実際の変更を行わない）",
    )

    args = parser.parse_args()

    # 引数チェック
    if args.apply and not args.batch_id:
        parser.error("--apply requires --batch-id")

    if not any([args.detect_only, args.submit, args.apply, args.full]):
        parser.print_help()
        return 1

    # 非同期実行
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
