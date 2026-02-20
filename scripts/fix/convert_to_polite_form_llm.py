#!/usr/bin/env python3
"""
常体→丁寧語 LLMバッチ変換スクリプト

マスターCSV内の全エピソードテキストを、Anthropic Batch API を使って
常体（だ・である調）から丁寧語（です・ます調）に変換する。

Usage:
    # パイロット（100件）
    python scripts/fix/convert_to_polite_form_llm.py --pilot --count 100

    # 本番実行
    python scripts/fix/convert_to_polite_form_llm.py --execute --batch-size 500

    # 結果取得
    python scripts/fix/convert_to_polite_form_llm.py --retrieve --batch-id <batch_id>

    # チェックポイントから再開
    python scripts/fix/convert_to_polite_form_llm.py --resume
"""

import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.batch_processor import BatchProcessor, BatchRequest

# ==============================================================================
# 定数
# ==============================================================================

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
CHECKPOINT_FILE = PROJECT_ROOT / "src" / "cache" / "polite_conversion_checkpoint.json"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"

CONVERSION_PROMPT = """以下のエピソードテキストを丁寧語（です・ます調）に変換してください。

【ルール】
1. すべての文末を丁寧語にする（〜した→〜しました、〜である→〜です 等）
2. 引用「」内は変換しない
3. 意味・事実・固有名詞・数値を一切変えない
4. 冒頭「あなたと同じX歳のとき、〜は」はそのまま維持
5. 変換後テキストのみ出力（説明不要）

【テキスト】
{episode_text}"""

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024


# ==============================================================================
# 品質検証
# ==============================================================================

POLITE_ENDINGS = re.compile(
    r"(ました|ません|ています|ていました|でした|です|ます|ございます"
    r"|でしょう|ましょう|ください|いたします|おります|なります)"
    r"[。．.！!？?）)」』】〉》〕]?\s*$"
)

OPENING_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき[、,]")


def validate_conversion(original: str, converted: str) -> dict:
    """変換結果の品質を検証する"""
    issues = []

    # 文字数変化チェック (80%〜130%)
    if original and converted:
        ratio = len(converted) / len(original)
        if ratio < 0.8 or ratio > 1.3:
            issues.append(f"length_ratio_out_of_range: {ratio:.2f}")

    # 冒頭パターン維持チェック
    if OPENING_PATTERN.search(original) and not OPENING_PATTERN.search(converted):
        issues.append("opening_pattern_lost")

    # 丁寧語率チェック
    sentences = re.split(r"[。．.！!？?]", converted)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if sentences:
        polite_count = sum(1 for s in sentences if POLITE_ENDINGS.search(s))
        polite_ratio = polite_count / len(sentences)
        if polite_ratio < 0.85:
            issues.append(f"low_polite_ratio: {polite_ratio:.2f}")

    # 数値保存チェック
    orig_numbers = set(re.findall(r"\d+", original))
    conv_numbers = set(re.findall(r"\d+", converted))
    missing_numbers = orig_numbers - conv_numbers
    if missing_numbers:
        issues.append(f"missing_numbers: {missing_numbers}")

    # 空の変換結果チェック
    if not converted or len(converted.strip()) < 10:
        issues.append("empty_or_too_short")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


# ==============================================================================
# チェックポイント管理
# ==============================================================================


class CheckpointManager:
    """中断再開のためのチェックポイント管理"""

    def __init__(self, checkpoint_path: Path = CHECKPOINT_FILE):
        self.path = checkpoint_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "completed_episode_ids": [],
            "pending_batch_ids": [],
            "failed_episode_ids": [],
            "total_processed": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "started_at": None,
            "last_updated": None,
        }

    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def mark_completed(self, episode_ids: list[str]):
        self.data["completed_episode_ids"].extend(episode_ids)
        self.data["total_processed"] += len(episode_ids)
        self.data["total_succeeded"] += len(episode_ids)
        self.save()

    def mark_failed(self, episode_ids: list[str]):
        self.data["failed_episode_ids"].extend(episode_ids)
        self.data["total_processed"] += len(episode_ids)
        self.data["total_failed"] += len(episode_ids)
        self.save()

    def add_pending_batch(self, batch_id: str):
        self.data["pending_batch_ids"].append(batch_id)
        self.save()

    def remove_pending_batch(self, batch_id: str):
        if batch_id in self.data["pending_batch_ids"]:
            self.data["pending_batch_ids"].remove(batch_id)
        self.save()

    def get_remaining_ids(self, all_ids: list[str]) -> list[str]:
        done = set(self.data["completed_episode_ids"])
        failed = set(self.data["failed_episode_ids"])
        return [eid for eid in all_ids if eid not in done and eid not in failed]

    def summary(self) -> str:
        return (
            f"処理済: {self.data['total_processed']} | "
            f"成功: {self.data['total_succeeded']} | "
            f"失敗: {self.data['total_failed']} | "
            f"保留バッチ: {len(self.data['pending_batch_ids'])}"
        )


# ==============================================================================
# メイン変換クラス
# ==============================================================================


class PoliteFormConverter:
    """常体→丁寧語 LLMバッチ変換器"""

    def __init__(self, csv_path: Path = MASTER_CSV, batch_size: int = 500):
        self.csv_path = csv_path
        self.batch_size = batch_size
        self.checkpoint = CheckpointManager()
        self.processor = BatchProcessor()

    def _load_csv(self) -> pd.DataFrame:
        return pd.read_csv(self.csv_path, encoding="utf-8-sig")

    def _create_backup(self) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"pre_polite_conversion_{timestamp}.csv"
        df = self._load_csv()
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"バックアップ作成: {backup_path}")
        return backup_path

    def prepare_requests(self, df: pd.DataFrame, episode_ids: list[str] | None = None) -> list[BatchRequest]:
        """バッチリクエストを準備"""
        requests = []

        if episode_ids:
            target_df = df[df["episode_id"].astype(str).isin(episode_ids)]
        else:
            target_df = df

        for _, row in target_df.iterrows():
            episode_id = str(row["episode_id"])
            text = str(row.get("episode_text", ""))

            if not text or len(text.strip()) < 10:
                continue

            prompt = CONVERSION_PROMPT.format(episode_text=text)

            custom_id = f"polite_{episode_id}"
            if len(custom_id) > 64:
                hash_id = hashlib.sha256(episode_id.encode()).hexdigest()[:16]
                custom_id = f"polite_{hash_id}"
                # ハッシュ化IDのマッピングを保存（結果取得時の逆引き用）
                self.checkpoint.data.setdefault("id_mapping", {})[custom_id] = episode_id
                self.checkpoint.save()

            req = BatchRequest(
                custom_id=custom_id,
                person_name=str(row.get("person_name", "")),
                age=int(row.get("age", 0)),
                category=str(row.get("category", "")),
                prompt=prompt,
                model=MODEL,
                max_tokens=MAX_TOKENS,
            )
            requests.append(req)

        return requests

    async def submit_batch(self, requests: list[BatchRequest]) -> str:
        """バッチを送信してbatch_idを返す"""
        job = await self.processor.submit_batch(requests)
        self.checkpoint.add_pending_batch(job.batch_id)
        print(f"バッチ送信完了: {job.batch_id} ({len(requests)}件)")
        return job.batch_id

    async def submit_all(
        self,
        pilot: bool = False,
        count: int = 100,
    ) -> list[str]:
        """全エピソードをバッチ送信"""
        self._create_backup()

        df = self._load_csv()
        all_ids = df["episode_id"].astype(str).tolist()

        remaining_ids = self.checkpoint.get_remaining_ids(all_ids)
        print(f"総エピソード数: {len(all_ids)}")
        print(f"未処理数: {len(remaining_ids)}")

        if pilot:
            remaining_ids = remaining_ids[:count]
            print(f"パイロットモード: {len(remaining_ids)}件")

        if not remaining_ids:
            print("全エピソード処理済み")
            return []

        if not self.checkpoint.data["started_at"]:
            self.checkpoint.data["started_at"] = datetime.now().isoformat()
            self.checkpoint.save()

        batch_ids = []
        for i in range(0, len(remaining_ids), self.batch_size):
            chunk_ids = remaining_ids[i : i + self.batch_size]
            requests = self.prepare_requests(df, chunk_ids)

            if not requests:
                continue

            batch_id = await self.submit_batch(requests)
            batch_ids.append(batch_id)

            if i + self.batch_size < len(remaining_ids):
                print("  次のバッチまで5秒待機...")
                await asyncio.sleep(5)

        print(f"\n送信完了: {len(batch_ids)}バッチ")
        print("バッチID一覧:")
        for bid in batch_ids:
            print(f"  - {bid}")

        return batch_ids

    async def retrieve_and_apply(self, batch_id: str) -> dict:
        """バッチ結果を取得してCSVに適用"""
        job = await self.processor.check_status(batch_id)
        print(f"バッチ {batch_id}: status={job.status}")

        if job.status != "ended":
            print(f"  まだ完了していません (status={job.status})")
            print(f"  成功: {job.succeeded_count} / 失敗: {job.failed_count}")
            return {"status": job.status, "applied": 0}

        results = await self.processor.get_results(batch_id)
        print(f"  結果取得: {len(results)}件")

        df = self._load_csv()
        applied = 0
        failed_ids = []
        validation_failures = []

        id_mapping = self.checkpoint.data.get("id_mapping", {})

        for result in results:
            custom_id = result["custom_id"]
            # ハッシュ化IDの場合はマッピングから逆引き
            episode_id = id_mapping.get(custom_id, custom_id.replace("polite_", ""))

            if result["result_type"] != "succeeded":
                failed_ids.append(episode_id)
                print(f"  失敗: {episode_id} - {result.get('error', 'unknown')}")
                continue

            converted_text = result["text"].strip()

            mask = df["episode_id"].astype(str) == episode_id
            if mask.sum() == 0:
                continue

            original_text = str(df.loc[mask, "episode_text"].iloc[0])

            validation = validate_conversion(original_text, converted_text)
            if not validation["passed"]:
                validation_failures.append({"episode_id": episode_id, "issues": validation["issues"]})
                print(f"  品質警告: {episode_id} - {validation['issues']}")
                failed_ids.append(episode_id)
                continue  # 品質NGはスキップ

            df.loc[mask, "episode_text"] = converted_text
            applied += 1

        if applied > 0:
            df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            print(f"  CSV更新: {applied}件適用")

        applied_ids = [r["custom_id"].replace("polite_", "") for r in results if r["result_type"] == "succeeded"]
        self.checkpoint.mark_completed(applied_ids)
        if failed_ids:
            self.checkpoint.mark_failed(failed_ids)
        self.checkpoint.remove_pending_batch(batch_id)

        report = {
            "batch_id": batch_id,
            "status": "completed",
            "applied": applied,
            "failed": len(failed_ids),
            "validation_warnings": len(validation_failures),
            "validation_details": validation_failures[:20],
        }

        report_path = REPORT_DIR / f"polite_conversion_{batch_id[:20]}.json"
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nレポート: {report_path}")
        print(self.checkpoint.summary())

        return report

    async def retrieve_all_pending(self):
        """全保留バッチの結果を取得・適用"""
        pending = list(self.checkpoint.data["pending_batch_ids"])
        if not pending:
            print("保留中のバッチはありません")
            return

        print(f"保留バッチ: {len(pending)}件")
        for batch_id in pending:
            print(f"\n--- {batch_id} ---")
            await self.retrieve_and_apply(batch_id)


# ==============================================================================
# CLI
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(description="常体→丁寧語 LLMバッチ変換")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pilot", action="store_true", help="パイロット実行")
    group.add_argument("--execute", action="store_true", help="本番実行")
    group.add_argument("--retrieve", action="store_true", help="結果取得・適用")
    group.add_argument("--resume", action="store_true", help="保留バッチの結果取得")
    group.add_argument("--status", action="store_true", help="チェックポイント状態表示")

    parser.add_argument("--count", type=int, default=100, help="パイロット件数 (default: 100)")
    parser.add_argument("--batch-size", type=int, default=500, help="バッチサイズ (default: 500)")
    parser.add_argument("--batch-id", type=str, help="取得するバッチID")

    args = parser.parse_args()

    converter = PoliteFormConverter(batch_size=args.batch_size)

    if args.status:
        print("=== チェックポイント状態 ===")
        print(converter.checkpoint.summary())
        return

    if args.pilot:
        batch_ids = asyncio.run(converter.submit_all(pilot=True, count=args.count))
        if batch_ids:
            print("\nパイロット送信完了。結果取得:")
            print(f"  python scripts/fix/convert_to_polite_form_llm.py --retrieve --batch-id {batch_ids[0]}")

    elif args.execute:
        batch_ids = asyncio.run(converter.submit_all(pilot=False))
        if batch_ids:
            print("\n本番送信完了。結果取得:")
            print("  python scripts/fix/convert_to_polite_form_llm.py --resume")

    elif args.retrieve:
        if not args.batch_id:
            print("--batch-id を指定してください")
            sys.exit(1)
        asyncio.run(converter.retrieve_and_apply(args.batch_id))

    elif args.resume:
        asyncio.run(converter.retrieve_all_pending())


if __name__ == "__main__":
    main()
