#!/usr/bin/env python3
"""
Post-Batch Processor - 欠損補完オーケストレーター

SAGE Turboバッチ処理後に呼び出され、以下の欠損を補完:
1. episode_type: テキストから推定
2. episode_fame_v6: v6スコアラーで計算
3. fame_tier: fame_score_v3から算出
4. verification_status: 初期値設定
5. generation_timestamp: 表示形式設定

EPUP準拠: 欠損補完ミッション Phase 2

Usage:
    # dry-run
    python scripts/sage/post_batch_processor.py --dry-run

    # 実行
    python scripts/sage/post_batch_processor.py --execute

    # 特定レコードのみ
    python scripts/sage/post_batch_processor.py --execute --filter-missing
"""

import argparse
import json
import logging
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from scripts.sage.gates.episode_type_inferrer import infer_episode_type

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# パス設定
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"
PENDING_QUEUE = PROJECT_ROOT / "src" / "reports" / "pending_episodes.json"

# fame_tier計算閾値（fame_score_v3ベース）
FAME_TIER_THRESHOLDS = {
    5: 800,  # Tier 5: 800+
    4: 600,  # Tier 4: 600-799
    3: 400,  # Tier 3: 400-599
    2: 200,  # Tier 2: 200-399
    1: 0,  # Tier 1: 0-199
}


@dataclass
class ProcessingStats:
    """処理統計"""

    total_records: int = 0
    missing_episode_type: int = 0
    missing_fame_tier: int = 0
    missing_episode_fame_v6: int = 0
    missing_verification_status: int = 0
    missing_generation_timestamp: int = 0

    filled_episode_type: int = 0
    filled_fame_tier: int = 0
    filled_episode_fame_v6: int = 0
    filled_verification_status: int = 0
    filled_generation_timestamp: int = 0

    pending_count: int = 0  # 保留キューに送られた件数
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "missing": {
                "episode_type": self.missing_episode_type,
                "fame_tier": self.missing_fame_tier,
                "episode_fame_v6": self.missing_episode_fame_v6,
                "verification_status": self.missing_verification_status,
                "generation_timestamp": self.missing_generation_timestamp,
            },
            "filled": {
                "episode_type": self.filled_episode_type,
                "fame_tier": self.filled_fame_tier,
                "episode_fame_v6": self.filled_episode_fame_v6,
                "verification_status": self.filled_verification_status,
                "generation_timestamp": self.filled_generation_timestamp,
            },
            "pending_count": self.pending_count,
            "errors": self.errors[:10],
        }


class PostBatchProcessor:
    """バッチ処理後の欠損補完オーケストレーター"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = ProcessingStats()
        self.pending_episodes: list[dict] = []
        self._df: Optional[pd.DataFrame] = None

    def load_csv(self) -> bool:
        """マスターCSV読み込み"""
        if not MASTER_CSV.exists():
            logger.error(f"Master CSV not found: {MASTER_CSV}")
            return False

        self._df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
        self.stats.total_records = len(self._df)
        logger.info(f"Loaded {self.stats.total_records} records from master CSV")
        return True

    def _is_missing(self, value: Any) -> bool:
        """値が欠損かチェック"""
        if value is None:
            return True
        if pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (int, float)) and value == 0:
            return True
        return False

    def detect_missing(self) -> dict:
        """欠損を検出"""
        if self._df is None:
            return {}

        # episode_type欠損
        mask_type = self._df["episode_type"].isna() | (self._df["episode_type"] == "")
        self.stats.missing_episode_type = mask_type.sum()

        # fame_tier欠損
        if "fame_tier" in self._df.columns:
            mask_tier = self._df["fame_tier"].isna() | (self._df["fame_tier"] == 0)
            self.stats.missing_fame_tier = mask_tier.sum()

        # episode_fame_v6欠損
        if "episode_fame_v6" in self._df.columns:
            mask_fame = self._df["episode_fame_v6"].isna() | (self._df["episode_fame_v6"] == 0)
            self.stats.missing_episode_fame_v6 = mask_fame.sum()

        # verification_status欠損
        if "verification_status" in self._df.columns:
            mask_verify = self._df["verification_status"].isna() | (self._df["verification_status"] == "")
            self.stats.missing_verification_status = mask_verify.sum()

        # generation_timestamp欠損
        if "generation_timestamp" in self._df.columns:
            mask_ts = self._df["generation_timestamp"].isna() | (self._df["generation_timestamp"] == "")
            self.stats.missing_generation_timestamp = mask_ts.sum()

        return {
            "episode_type": self.stats.missing_episode_type,
            "fame_tier": self.stats.missing_fame_tier,
            "episode_fame_v6": self.stats.missing_episode_fame_v6,
            "verification_status": self.stats.missing_verification_status,
            "generation_timestamp": self.stats.missing_generation_timestamp,
        }

    def fill_episode_type(self) -> int:
        """episode_typeを推定・補完"""
        if self._df is None:
            return 0

        filled = 0
        mask = self._df["episode_type"].isna() | (self._df["episode_type"] == "")
        missing_idx = self._df[mask].index

        for idx in missing_idx:
            episode_text = str(self._df.at[idx, "episode_text"] or "")
            result = infer_episode_type(episode_text)

            if result.episode_type:
                if not self.dry_run:
                    self._df.at[idx, "episode_type"] = result.episode_type
                filled += 1
                logger.debug(f"Filled episode_type: {self._df.at[idx, 'episode_id']} → {result.episode_type}")
            else:
                # 推定不能 → 保留キューへ
                self.pending_episodes.append(
                    {
                        "episode_id": self._df.at[idx, "episode_id"],
                        "person_name": self._df.at[idx, "person_name"],
                        "reason": "episode_type推定不能",
                        "episode_text_preview": episode_text[:100],
                    }
                )

        self.stats.filled_episode_type = filled
        self.stats.pending_count = len(self.pending_episodes)
        return filled

    def fill_fame_tier(self) -> int:
        """fame_tierをfame_score_v3から算出"""
        if self._df is None:
            return 0

        if "fame_tier" not in self._df.columns:
            self._df["fame_tier"] = ""

        if "fame_score_v3" not in self._df.columns:
            logger.warning("fame_score_v3 column not found, skipping fame_tier fill")
            return 0

        filled = 0
        mask = self._df["fame_tier"].isna() | (self._df["fame_tier"] == "") | (self._df["fame_tier"] == 0)
        missing_idx = self._df[mask].index

        for idx in missing_idx:
            fame_score = self._df.at[idx, "fame_score_v3"]
            if pd.isna(fame_score) or fame_score == 0:
                continue

            # fame_score_v3 → tier変換
            tier = 1
            for t, threshold in FAME_TIER_THRESHOLDS.items():
                if fame_score >= threshold:
                    tier = t
                    break

            if not self.dry_run:
                self._df.at[idx, "fame_tier"] = tier
            filled += 1

        self.stats.filled_fame_tier = filled
        return filled

    def fill_episode_fame_v6(self) -> int:
        """
        episode_fame_v6を計算

        Note: 完全なv6計算には全エピソードの正規化パラメータが必要なため、
        ここでは簡易版として7軸スコアの加重平均を使用する。
        本格的な再計算は scripts/calculate_episode_fame_v6.py を使用する。
        """
        if self._df is None:
            return 0

        if "episode_fame_v6" not in self._df.columns:
            self._df["episode_fame_v6"] = 0.0

        filled = 0
        mask = self._df["episode_fame_v6"].isna() | (self._df["episode_fame_v6"] == 0)
        missing_idx = self._df[mask].index

        # 7軸スコア列
        score_cols = [
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
        ]

        for idx in missing_idx:
            # 7軸の平均を基準にv6を推定
            scores = []
            for col in score_cols:
                if col in self._df.columns:
                    val = self._df.at[idx, col]
                    if not pd.isna(val) and val > 0:
                        scores.append(float(val))

            if not scores:
                continue

            # 簡易v6計算: (7軸平均 * 10) を基準に調整
            avg_score = sum(scores) / len(scores)
            v6_estimate = avg_score * 10  # 0-100スケールへ

            # fame_score_v3があればボーナス
            if "fame_score_v3" in self._df.columns:
                fame_score = self._df.at[idx, "fame_score_v3"]
                if not pd.isna(fame_score) and fame_score > 0:
                    # fame_scoreの正規化ボーナス（最大20点）
                    fame_bonus = min(fame_score / 50, 20)
                    v6_estimate += fame_bonus

            if not self.dry_run:
                self._df.at[idx, "episode_fame_v6"] = round(v6_estimate, 2)

                # episode_fame_scoreも同期
                if "episode_fame_score" in self._df.columns:
                    self._df.at[idx, "episode_fame_score"] = round(v6_estimate, 2)

                # episode_fame_tier_v6も設定
                if "episode_fame_tier_v6" in self._df.columns:
                    tier_v6 = 1
                    if v6_estimate >= 80:
                        tier_v6 = 5
                    elif v6_estimate >= 60:
                        tier_v6 = 4
                    elif v6_estimate >= 40:
                        tier_v6 = 3
                    elif v6_estimate >= 20:
                        tier_v6 = 2
                    self._df.at[idx, "episode_fame_tier_v6"] = tier_v6

            filled += 1

        self.stats.filled_episode_fame_v6 = filled
        return filled

    def fill_verification_status(self) -> int:
        """verification_statusを初期値設定"""
        if self._df is None:
            return 0

        if "verification_status" not in self._df.columns:
            self._df["verification_status"] = ""

        filled = 0
        mask = self._df["verification_status"].isna() | (self._df["verification_status"] == "")
        missing_idx = self._df[mask].index

        for idx in missing_idx:
            if not self.dry_run:
                self._df.at[idx, "verification_status"] = "unverified"
            filled += 1

        self.stats.filled_verification_status = filled
        return filled

    def fill_generation_timestamp(self) -> int:
        """generation_timestampを表示形式で設定"""
        if self._df is None:
            return 0

        if "generation_timestamp" not in self._df.columns:
            self._df["generation_timestamp"] = ""

        filled = 0
        mask = self._df["generation_timestamp"].isna() | (self._df["generation_timestamp"] == "")
        missing_idx = self._df[mask].index

        # generated_at から変換、なければ現在日時
        today = datetime.now().strftime("%Y.%m.%d")

        for idx in missing_idx:
            if "generated_at" in self._df.columns:
                generated_at = self._df.at[idx, "generated_at"]
                if not pd.isna(generated_at) and generated_at:
                    try:
                        # ISO形式からYYYY.MM.DDへ変換
                        dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                        timestamp = dt.strftime("%Y.%m.%d")
                    except (ValueError, TypeError):
                        timestamp = today
                else:
                    timestamp = today
            else:
                timestamp = today

            if not self.dry_run:
                self._df.at[idx, "generation_timestamp"] = timestamp
            filled += 1

        self.stats.filled_generation_timestamp = filled
        return filled

    def save_pending_queue(self) -> None:
        """保留キューを保存"""
        if not self.pending_episodes:
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # 既存キューと統合
        existing = []
        if PENDING_QUEUE.exists():
            with open(PENDING_QUEUE, encoding="utf-8") as f:
                existing = json.load(f)

        # 重複除外して追加
        existing_ids = {ep.get("episode_id") for ep in existing}
        for ep in self.pending_episodes:
            if ep["episode_id"] not in existing_ids:
                existing.append(ep)

        with open(PENDING_QUEUE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(self.pending_episodes)} episodes to pending queue: {PENDING_QUEUE}")

    def create_backup(self) -> Optional[Path]:
        """バックアップ作成"""
        if not MASTER_CSV.exists():
            return None

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_post_batch_{timestamp}.csv"
        shutil.copy2(MASTER_CSV, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path

    def save_csv(self) -> bool:
        """CSV保存"""
        if self._df is None or self.dry_run:
            return False

        self._df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(self._df)} records to master CSV")
        return True

    def process(self) -> dict:
        """
        メイン処理

        Returns:
            dict: 処理結果
        """
        logger.info("=" * 60)
        logger.info("Post-Batch Processor" + (" [DRY-RUN]" if self.dry_run else ""))
        logger.info("=" * 60)

        # 1. CSV読み込み
        if not self.load_csv():
            return {"success": False, "error": "CSV load failed"}

        # 2. 欠損検出
        missing = self.detect_missing()
        logger.info(f"Missing detection: {missing}")

        # 3. バックアップ作成
        if not self.dry_run:
            self.create_backup()

        # 4. 補完処理
        logger.info("\n--- Filling missing values ---")

        # episode_type
        filled_type = self.fill_episode_type()
        logger.info(f"episode_type: {filled_type}/{self.stats.missing_episode_type} filled")

        # fame_tier
        filled_tier = self.fill_fame_tier()
        logger.info(f"fame_tier: {filled_tier}/{self.stats.missing_fame_tier} filled")

        # episode_fame_v6
        filled_fame = self.fill_episode_fame_v6()
        logger.info(f"episode_fame_v6: {filled_fame}/{self.stats.missing_episode_fame_v6} filled")

        # verification_status
        filled_verify = self.fill_verification_status()
        logger.info(f"verification_status: {filled_verify}/{self.stats.missing_verification_status} filled")

        # generation_timestamp
        filled_ts = self.fill_generation_timestamp()
        logger.info(f"generation_timestamp: {filled_ts}/{self.stats.missing_generation_timestamp} filled")

        # 5. 保留キュー保存
        if self.pending_episodes and not self.dry_run:
            self.save_pending_queue()

        # 6. CSV保存
        if not self.dry_run:
            self.save_csv()

        # 7. 結果レポート
        result = {
            "success": True,
            "dry_run": self.dry_run,
            "stats": self.stats.to_dict(),
        }

        logger.info("\n" + "=" * 60)
        logger.info("Processing Complete")
        logger.info("=" * 60)
        logger.info(f"Total records: {self.stats.total_records}")
        logger.info(f"Pending episodes: {self.stats.pending_count}")

        return result


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(description="Post-Batch Processor - 欠損補完オーケストレーター")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行モード（変更を保存）")
    parser.add_argument("--json", action="store_true", help="JSON形式で結果出力")
    args = parser.parse_args()

    # dry-runがデフォルト
    dry_run = not args.execute

    processor = PostBatchProcessor(dry_run=dry_run)
    result = processor.process()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 60)
        print("処理結果サマリー")
        print("=" * 60)
        stats = result.get("stats", {})
        print(f"総レコード数: {stats.get('total_records', 0)}")
        print(f"欠損検出: {stats.get('missing', {})}")
        print(f"補完件数: {stats.get('filled', {})}")
        print(f"保留件数: {stats.get('pending_count', 0)}")
        print("=" * 60)


if __name__ == "__main__":
    main()
