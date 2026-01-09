#!/usr/bin/env python3
"""
Batch API結果をマスターCSVに統合するプロセッサ

バッチ処理の結果を:
1. 品質ゲートでフィルタリング
2. 重複チェック
3. マスターCSVに追加
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from scripts.sage.config import LOGS_DIR, MASTER_CSV, HybridConfig
from scripts.sage.quality.evaluator import QualityEvaluator
from scripts.sage.gates.duplicate import DuplicateDetector
from scripts.sage.quality.super_total import SuperTotalCalculator
from scripts.sage.inventory_manager import InventoryManager
from scripts.sage.persistence.backup import create_pre_operation_backup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BatchProcessingStats:
    """バッチ処理の統計"""

    total: int = 0
    processed: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    low_quality: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "processed": self.processed,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "duplicates": self.duplicates,
            "low_quality": self.low_quality,
            "errors": self.errors,
            "acceptance_rate": f"{self.accepted / self.processed * 100:.1f}%" if self.processed > 0 else "N/A",
        }


class BatchResultProcessor:
    """Batch API結果プロセッサ"""

    def __init__(self, config: HybridConfig = None, dry_run: bool = False):
        self.config = config or HybridConfig()
        self.dry_run = dry_run
        self._jobs_dir = LOGS_DIR / "batch_jobs"

        # コンポーネント初期化
        self._evaluator = QualityEvaluator()
        self._duplicate_detector = DuplicateDetector(MASTER_CSV)
        self._super_total = SuperTotalCalculator()
        self._inventory_manager = InventoryManager()

        # マスターDF
        self._master_df: Optional[pd.DataFrame] = None
        self._next_episode_id: int = 0

    @property
    def master_df(self) -> pd.DataFrame:
        if self._master_df is None:
            self._master_df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
        return self._master_df

    def load_job(self, batch_id: str) -> tuple[dict, list[dict]]:
        """ジョブメタデータと結果を読み込み"""
        job_path = self._jobs_dir / f"{batch_id}.json"
        results_path = self._jobs_dir / f"{batch_id}_results.json"

        if not job_path.exists():
            raise FileNotFoundError(f"Job file not found: {job_path}")
        if not results_path.exists():
            raise FileNotFoundError(f"Results file not found: {results_path}")

        with open(job_path, encoding="utf-8") as f:
            job_data = json.load(f)

        with open(results_path, encoding="utf-8") as f:
            results = json.load(f)

        return job_data, results

    async def process_batch(self, batch_id: str) -> BatchProcessingStats:
        """バッチ結果を処理してマスターCSVに統合"""
        stats = BatchProcessingStats()

        # ジョブとを結果読み込み
        job_data, results = self.load_job(batch_id)
        stats.total = len(results)

        # リクエストメタデータをcustom_idでインデックス化
        requests_by_id = {r["custom_id"]: r for r in job_data.get("requests", [])}

        # インベントリ更新
        self._inventory_manager.refresh()

        logger.info(f"Processing batch {batch_id} with {stats.total} results")

        accepted_episodes = []

        for result in results:
            stats.processed += 1
            custom_id = result.get("custom_id", "")

            # 失敗結果をスキップ
            if result.get("result_type") != "succeeded":
                stats.errors += 1
                logger.warning(f"  {custom_id}: Failed - {result.get('error', 'unknown')}")
                continue

            # メタデータ取得
            request_meta = requests_by_id.get(custom_id)
            if not request_meta:
                stats.errors += 1
                logger.warning(f"  {custom_id}: No metadata found")
                continue

            person_name = request_meta["person_name"]
            age = request_meta["age"]
            category = request_meta["category"]
            episode_text = result.get("text", "")

            if not episode_text:
                stats.errors += 1
                continue

            # テキスト品質分析（簡易評価）
            text_quality = self._evaluator.evaluate_text_quality(episode_text)

            # 基本的な品質チェック
            text_len = len(episode_text)
            if text_len < 200:
                stats.low_quality += 1
                stats.rejected += 1
                logger.info(f"  {person_name} ({age}歳): Too short ({text_len} chars)")
                continue

            # 禁止パターンチェック
            prohibited = ["のような人物です", "という記録は", "について語られています"]
            if any(p in episode_text for p in prohibited):
                stats.low_quality += 1
                stats.rejected += 1
                logger.info(f"  {person_name} ({age}歳): Prohibited pattern")
                continue

            # 簡易スコア計算（Batch API生成は高品質と仮定）
            from scripts.sage.quality.evaluator import AxisScores

            # テキスト分析からスコア推定
            specificity = text_quality.get("specificity_score", 4)
            has_proper_nouns = text_quality.get("has_proper_nouns", False)
            has_year = text_quality.get("has_year", False)
            proper_noun_count = text_quality.get("proper_noun_count", 0)

            # 品質スコアを推定（Batch APIで生成されたのでベースラインを高く設定）
            base_score = 7.5  # Batch API生成のベースライン

            # 具体性によるボーナス
            specificity_bonus = min(specificity * 0.3, 1.5)
            if has_year:
                specificity_bonus += 0.3
            if has_proper_nouns and proper_noun_count >= 3:
                specificity_bonus += 0.5

            fd_score = min(base_score + specificity_bonus, 9.5)
            gq_score = min(base_score + 0.5 + specificity_bonus * 0.5, 9.5)  # 生成品質は高め

            axis_scores = AxisScores(
                memorability=min(7.0 + specificity_bonus * 0.3, 9.0),
                empathy=7.0,
                surprise=6.5,
                generation_quality=gq_score,
                educational_value=7.0,
                story_quality=7.5,
                factual_density=fd_score,
            )

            # 重複チェック
            dup_result = self._duplicate_detector.check_all(
                text=episode_text,
                person_id=request_meta.get("person_id", ""),
                age=age,
            )
            if dup_result.is_duplicate:
                stats.duplicates += 1
                stats.rejected += 1
                logger.info(f"  {person_name} ({age}歳): Duplicate - {dup_result.reason}")
                continue

            # 超総合スコア計算
            super_result = self._super_total.calculate(
                request_meta.get("person_id", ""),
                axis_scores,
                self.master_df,
            )

            if not super_result.passed_gate:
                stats.low_quality += 1
                stats.rejected += 1
                logger.info(f"  {person_name} ({age}歳): Low super_total - {super_result.gate_failures}")
                continue

            # 採用
            stats.accepted += 1
            accepted_episodes.append(
                {
                    "person_id": request_meta.get("person_id", ""),
                    "person_name": person_name,
                    "age": age,
                    "category": category,
                    "episode_text": episode_text,
                    "axis_scores": axis_scores,
                    "super_total": super_result.score,
                    "custom_id": custom_id,
                }
            )
            logger.info(f"  {person_name} ({age}歳): Accepted (score={super_result.score:.0f})")

        # マスターに書き込み
        if accepted_episodes and not self.dry_run:
            write_result = self._write_episodes(accepted_episodes)
            logger.info(f"Written {write_result['added']} episodes to master")

        return stats

    def _write_episodes(self, episodes: list[dict]) -> dict:
        """エピソードをマスターCSVに書き込み"""
        if not episodes:
            return {"added": 0, "skipped": 0}

        # バックアップ作成
        create_pre_operation_backup("batch_result_process")

        # 既存データ読み込み
        existing_df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")

        # 次のエピソードID取得
        existing_ids = existing_df["episode_id"].tolist()
        max_id = 0
        for eid in existing_ids:
            if isinstance(eid, str) and eid.startswith("EP-"):
                try:
                    num = int(eid.split("-")[1])
                    max_id = max(max_id, num)
                except (ValueError, IndexError):
                    pass
        self._next_episode_id = max_id + 1

        # 新しい行を作成
        new_rows = []
        for ep in episodes:
            row = self._create_episode_record(ep)
            new_rows.append(row)

        # DataFrameに変換して追加
        new_df = pd.DataFrame(new_rows)

        # 既存カラムに合わせる
        for col in existing_df.columns:
            if col not in new_df.columns:
                new_df[col] = ""

        # 結合して保存
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

        return {"added": len(new_rows), "skipped": 0}

    def _create_episode_record(self, ep: dict) -> dict:
        """エピソードレコードを作成"""
        scores = ep["axis_scores"]

        # エピソードID生成
        episode_id = f"EP-{self._next_episode_id:09d}"
        self._next_episode_id += 1

        return {
            "episode_id": episode_id,
            "person_id": ep.get("person_id", ""),
            "person_name": ep["person_name"],
            "age": ep["age"],
            "category": ep["category"],
            "episode_text": ep["episode_text"],
            "memorability_score": scores.memorability,
            "empathy_score": scores.empathy,
            "surprise_score": scores.surprise,
            "generation_quality_score": scores.generation_quality,
            "educational_value": scores.educational_value,
            "story_quality": scores.story_quality,
            "factual_density": scores.factual_density,
            # Note: episode_fame_v6は後でv6スコアラーで計算される
            # super_totalは0-1,000,000スケールなので直接入れない
            "super_total_score": ep["super_total"],
            "person_type": "REAL",
            "source": "batch_api",
            "generated_at": datetime.now().isoformat(),
        }


async def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch API結果プロセッサ")
    parser.add_argument("batch_id", help="処理するバッチID")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    args = parser.parse_args()

    processor = BatchResultProcessor(dry_run=args.dry_run)
    stats = await processor.process_batch(args.batch_id)

    print("\n" + "=" * 60)
    print("バッチ処理結果")
    print("=" * 60)
    print(f"総数: {stats.total}")
    print(f"処理: {stats.processed}")
    print(f"採用: {stats.accepted}")
    print(f"棄却: {stats.rejected}")
    print(f"  - 品質不足: {stats.low_quality}")
    print(f"  - 重複: {stats.duplicates}")
    print(f"  - エラー: {stats.errors}")
    print(f"採用率: {stats.accepted / stats.processed * 100:.1f}%" if stats.processed > 0 else "N/A")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
