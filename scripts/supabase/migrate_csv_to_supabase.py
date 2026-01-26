#!/usr/bin/env python3
"""
CSV → Supabase 初期移行スクリプト

Usage:
    python scripts/supabase/migrate_csv_to_supabase.py --dry-run   # 実行確認のみ
    python scripts/supabase/migrate_csv_to_supabase.py             # 実際に移行
"""

import argparse
import json
import logging
import math
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

# ロガー設定（スクリプト単体実行時にも警告を表示）
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.WARNING)

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import create_client, Client
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# PostgreSQLでINTEGER型のカラム一覧
INTEGER_COLUMNS = {
    "episode_count",
    "age",
    "wikipedia_pv",
    "fame_rank_v3",
    "multi_lang_pv",
    "sitelinks_count",
    "google_hits",
    "celebrity_rank_v2",
    "episode_fame_tier_v6",
    "birth_year",
    "death_year",
}


# フォールバック出力の最大レコード数
MAX_FALLBACK_RECORDS = 100


# エラータイプの列挙
ErrorType = Literal[
    "PartialFailure",
    "APIError",
    "ConnectionError",
    "JSONDecodeError",
    "ValueError",
    "TypeError",
    "KeyError",
    "UnexpectedError",
]


class FailedRecord(TypedDict):
    """失敗レコードの型定義"""

    batch_num: int
    error_type: ErrorType
    error_message: str
    episode_ids: list[str]
    timestamp: str
    unexpected: NotRequired[bool]


def get_supabase_client() -> Client:
    """Supabaseクライアント取得（service_role使用）"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY が必要です")

    return create_client(url, key)


def load_csv() -> pd.DataFrame:
    """マスターCSV読み込み"""
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"マスターCSVが見つかりません: {csv_path}")
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError as e:
        # S-4: エンコーディングエラーを追加
        raise ValueError(f"CSVエンコーディングエラー: {e}") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"CSV解析エラー: {e}") from e
    except (IOError, PermissionError) as e:
        # S-4: ファイルアクセスエラーを追加
        raise ValueError(f"CSVファイルアクセスエラー: {e}") from e
    logger.info("CSV読み込み完了: %d件", len(df))  # S-3: logger追加
    print(f"[OK] CSV読み込み完了: {len(df):,}件")
    return df


@dataclass
class MigrationContext:
    """移行処理のコンテキスト情報を保持"""

    complex_object_count: int = 0
    boolean_conversion_failures: int = 0  # W-1: Boolean変換失敗カウント

    def increment_complex_object_count(self) -> None:
        self.complex_object_count += 1

    def increment_boolean_conversion_failures(self) -> None:
        """Boolean変換失敗をカウント"""
        self.boolean_conversion_failures += 1

    def reset(self) -> None:
        self.complex_object_count = 0
        self.boolean_conversion_failures = 0


# モジュールレベルのコンテキスト（後方互換性のため）
_migration_ctx = MigrationContext()


def create_failed_record(
    batch_num: int,
    error_type: ErrorType,
    error_message: str,
    episode_ids: list[str],
    unexpected: bool = False,
) -> FailedRecord:
    """FailedRecordを生成（バリデーション付き）

    Args:
        batch_num: バッチ番号（1以上）
        error_type: エラータイプ
        error_message: エラーメッセージ
        episode_ids: 影響を受けたepisode_idのリスト
        unexpected: 予期しないエラーかどうか

    Returns:
        FailedRecord: 失敗レコード

    Raises:
        ValueError: batch_numが1未満の場合
    """
    if batch_num < 1:
        raise ValueError(f"batch_num must be >= 1, got {batch_num}")

    record: FailedRecord = {
        "batch_num": batch_num,
        "error_type": error_type,
        "error_message": error_message,
        "episode_ids": episode_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if unexpected:
        record["unexpected"] = True
    return record


def sanitize_value(value: Any, column_name: str = "") -> Any:
    """
    個々の値をJSONシリアライズ可能な形式に変換

    - NaN/Inf/-Inf -> None
    - numpy型 -> Python標準型
    - pandas NAType -> None
    - INTEGERカラムの場合はint型に変換
    """
    # None/pandas NA/NaT の明示的な処理（最初に判定）
    if value is None:
        return None
    if value is pd.NA:
        return None
    if isinstance(value, type(pd.NA)):
        return None

    # 複合オブジェクト（dict, list, set, tuple）は早期にNoneに変換
    # JSONシリアライズ不能なため、APIエラーを防ぐ
    if isinstance(value, (dict, list, set, tuple)):
        _migration_ctx.increment_complex_object_count()
        logger.warning(
            "Complex object detected column=%s, value_type=%s - converting to None",
            column_name,
            type(value).__name__,
        )
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError) as e:
        # その他の複合オブジェクト（予期しない型）
        logger.error(
            "TypeError/ValueError in pd.isna() column=%s, value=%r, value_type=%s: %s",
            column_name,
            repr(value)[:100],  # S-1: 長すぎる場合は切り詰め
            type(value).__name__,
            e,
        )
        # 安全のためNoneを返す
        return None

    # numpy/pandas整数型
    if isinstance(value, (np.integer,)):
        return int(value)

    # numpy/pandas浮動小数点型
    if isinstance(value, (np.floating, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        # INTEGERカラムの場合はintに変換（例: 1890.0 -> 1890）
        if column_name in INTEGER_COLUMNS:
            return int(value)
        return float(value)

    # numpy bool
    if isinstance(value, (np.bool_,)):
        return bool(value)

    # numpy文字列
    if isinstance(value, (np.str_,)):
        return str(value)

    # 文字列で数値が入っているINTEGERカラムの場合
    if column_name in INTEGER_COLUMNS and isinstance(value, str):
        try:
            return int(float(value))
        except (ValueError, TypeError) as e:
            logger.warning("INTEGER conversion failed %s='%s': %s", column_name, value, e)
            return None

    return value


def sanitize_records(records: list[dict]) -> list[dict]:
    """
    レコードリスト全体をサニタイズ
    NaN/Inf/numpy型をすべてJSON互換型に変換
    """
    sanitized = []
    for record in records:
        sanitized_record = {key: sanitize_value(val, column_name=key) for key, val in record.items()}
        sanitized.append(sanitized_record)
    return sanitized


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """データクレンジング（DataFrame段階での前処理）"""
    # INTEGERカラムをNullable Integer型（Int64）に変換
    for col in INTEGER_COLUMNS:
        if col in df.columns:
            series: pd.Series = pd.to_numeric(df[col], errors="coerce")  # type: ignore[assignment]
            df[col] = series.astype("Int64")

    # Boolean型変換（文字列 "FALSE"/"TRUE" を正しく処理）
    def _to_bool(x: Any, column_name: str = "") -> bool | None:
        """Boolean型変換（文字列対応・堅牢版）"""
        # 複合オブジェクトは先に除外（M-2対策）
        if isinstance(x, (dict, list, set, tuple)):
            logger.warning(
                "Complex object in boolean column %s: type=%s - returning None",
                column_name,
                type(x).__name__,
            )
            return None

        # pd.isna()の例外対策（M-2対策）
        try:
            if pd.isna(x) or x == "":
                return None
        except (TypeError, ValueError) as e:
            logger.warning(
                "pd.isna() failed for column %s, type=%s: %s - returning None",
                column_name,
                type(x).__name__,
                e,
            )
            return None

        if isinstance(x, bool):
            return x
        if isinstance(x, str):
            lower_x = x.lower()
            if lower_x in ("true", "1", "yes"):
                return True
            if lower_x in ("false", "0", "no"):  # S-1: 明示的Falseリスト
                return False
            # 不明な文字列は警告してNone
            logger.warning(
                "Unknown boolean string in column %s: '%s' - returning None",
                column_name,
                x,
            )
            return None
        if isinstance(x, (int, float)):
            # 数値型は明示的にbool変換（0/0.0 -> False, それ以外 -> True）
            return bool(x)

        # その他の予期しない型は警告（M-1対策）
        logger.warning(
            "Unexpected type in boolean conversion for column %s: type=%s, value=%r - returning None",
            column_name,
            type(x).__name__,
            x,
        )
        return None

    bool_cols = ["is_group_member", "is_japanese"]
    for col in bool_cols:
        if col in df.columns:
            try:  # H-1: 例外キャッチ追加, C-1: 例外型を限定
                df[col] = df[col].apply(lambda x, c=col: _to_bool(x, column_name=c))
            except (TypeError, ValueError) as e:
                logger.error(
                    "Boolean conversion failed for column '%s': %s (%s) - column set to None",
                    col,
                    e,
                    type(e).__name__,
                )
                # W-2: print→logger.warning に移行
                logger.warning("Boolean変換失敗: カラム '%s' を全てNoneに設定しました", col)
                df[col] = None
                # W-1: Boolean変換失敗をコンテキストに記録
                _migration_ctx.increment_boolean_conversion_failures()

    return df


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, ConnectionError)),  # S-1: ConnectionErrorもリトライ対象
    before_sleep=before_sleep_log(logger, logging.WARNING),  # S-5: リトライ前にログ出力
)
def upsert_batch(supabase: Client, batch_records: list[dict]) -> dict:
    """バッチupsert with リトライ

    Returns:
        dict: {"success_count": int, "data": list}
    """
    result = supabase.table("episodes").upsert(batch_records, on_conflict="episode_id").execute()

    return {"success_count": len(result.data) if result.data else 0, "data": result.data or []}


def migrate(dry_run: bool = False, batch_size: int = 500) -> int:
    """メイン移行処理

    Returns:
        int: エラー件数（0なら正常終了）
    """
    # batch_size 妥当性チェック
    if batch_size <= 0:
        raise ValueError("batch_size は1以上の整数を指定してください")
    if batch_size > 10000:
        logger.warning("batch_size too large (%d). Be aware of API limits", batch_size)

    print("=" * 60)
    print("CSV -> Supabase 移行開始")
    print("=" * 60)

    # データ読み込み
    df = load_csv()
    df = clean_data(df)

    if dry_run:
        print("\n[DRY-RUN] 実際の書き込みは行いません")
        print(f"   - 対象件数: {len(df):,}件")
        print(f"   - バッチサイズ: {batch_size}件")
        print(f"   - 予想バッチ数: {(len(df) + batch_size - 1) // batch_size}")

        # サンプルデータをサニタイズしてテスト
        sample_df = df.head(5)
        sample_records = sample_df.to_dict(orient="records")
        sanitized_sample = sanitize_records(sample_records)

        print("\n[SAMPLE] サニタイズ後のサンプルデータ（先頭5件）:")
        for i, rec in enumerate(sanitized_sample):
            print(
                f"  {i + 1}. episode_id={rec.get('episode_id')}, "
                f"person_name={rec.get('person_name')}, "
                f"age={rec.get('age')} (type={type(rec.get('age')).__name__}), "
                f"birth_year={rec.get('birth_year')} (type={type(rec.get('birth_year')).__name__}), "
                f"super_total_score={rec.get('super_total_score')}"
            )

        # W-3: NaN/Inf検出テスト（dry-runでも本番失敗を示唆するためエラー扱い）
        try:
            json.dumps(sanitized_sample)
            print("\n[OK] JSONシリアライズテスト: 成功")
        except (ValueError, TypeError) as e:
            logger.error("JSON serialize test: FAILED (dry-run) - %s. Actual execution will likely fail.", e)
            return 1  # dry-runでもシリアライズ失敗はエラー終了

        # INTEGERカラムの型検証
        print("\n[CHECK] INTEGERカラムの型検証:")
        for col in INTEGER_COLUMNS:
            if col in sanitized_sample[0]:
                val = sanitized_sample[0][col]
                val_type = type(val).__name__ if val is not None else "NoneType"
                status = "OK" if val is None or isinstance(val, int) else "NG"
                print(f"   - {col}: {val} ({val_type}) [{status}]")

        return 0  # dry-runは常に成功

    # Supabase接続
    supabase = get_supabase_client()
    print("[OK] Supabase接続完了")

    # バッチupsert
    total_batches = (len(df) + batch_size - 1) // batch_size
    success_count = 0
    error_count = 0

    print(f"\n[START] 移行開始: {len(df):,}件 -> {total_batches}バッチ")
    print("-" * 60)

    failed_records: list[FailedRecord] = []  # 失敗レコード詳細

    for i in tqdm(range(0, len(df), batch_size), total=total_batches, desc="移行中", unit="batch", ncols=80):
        batch_df = df.iloc[i : i + batch_size]
        batch_records = batch_df.to_dict(orient="records")

        # NaN/Inf/numpy型をサニタイズ
        batch_records = sanitize_records(batch_records)
        batch_num = i // batch_size + 1

        try:
            result = upsert_batch(supabase, batch_records)
            success_count += result["success_count"]
            if result["success_count"] < len(batch_records):
                partial_failed = len(batch_records) - result["success_count"]
                error_count += partial_failed
                # 成功したIDを特定し、失敗したIDを推定
                success_ids = {r.get("episode_id") for r in (result.get("data") or [])}
                failed_ids = [
                    r.get("episode_id", "unknown") for r in batch_records if r.get("episode_id") not in success_ids
                ]
                logger.warning(
                    "Partial success: %d/%d records (failed: %d) - failed episode_ids: %s",
                    result["success_count"],
                    len(batch_records),
                    partial_failed,
                    failed_ids[:5],
                )
                failed_records.append(
                    create_failed_record(
                        batch_num=batch_num,
                        error_type="PartialFailure",
                        error_message=f"{partial_failed}件が部分的に失敗",
                        episode_ids=failed_ids,
                    )
                )
        except APIError as e:
            # Supabase API固有エラー（型不一致、制約違反等）
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            logger.error("Batch %d APIError: %s", batch_num, e.message)
            logger.error("        target episode_ids: %s... (first 5)", batch_episode_ids[:5])
            failed_records.append(
                create_failed_record(
                    batch_num=batch_num,
                    error_type="APIError",
                    error_message=str(e.message),
                    episode_ids=batch_episode_ids,
                )
            )
        except (json.JSONDecodeError, ValueError) as e:
            # JSON/値変換エラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            logger.error("Batch %d data conversion error: %s", batch_num, e)
            failed_records.append(
                create_failed_record(
                    batch_num=batch_num,
                    error_type="JSONDecodeError" if isinstance(e, json.JSONDecodeError) else "ValueError",
                    error_message=str(e),
                    episode_ids=batch_episode_ids,
                )
            )
        except (TypeError, KeyError) as e:
            # 型エラー、キー欠損
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            logger.error("Batch %d data structure error (%s): %s", batch_num, type(e).__name__, e)
            failed_records.append(
                create_failed_record(
                    batch_num=batch_num,
                    error_type="TypeError" if isinstance(e, TypeError) else "KeyError",
                    error_message=str(e),
                    episode_ids=batch_episode_ids,
                )
            )
        except ConnectionError as e:
            # ネットワーク接続エラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            logger.error("Batch %d connection error: %s", batch_num, e)
            failed_records.append(
                create_failed_record(
                    batch_num=batch_num,
                    error_type="ConnectionError",
                    error_message=str(e),
                    episode_ids=batch_episode_ids,
                )
            )
        except (SystemExit, KeyboardInterrupt):
            # ユーザー意図の中断は再送出
            raise
        except Exception as e:
            # その他の予期しないエラー（ログに明示的に記録）
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            logger.error(
                "Batch %d unexpected error (%s): %s - investigation may be required\n%s",
                batch_num,
                type(e).__name__,
                e,
                traceback.format_exc(),
            )
            failed_records.append(
                create_failed_record(
                    batch_num=batch_num,
                    error_type="UnexpectedError",
                    error_message=str(e),
                    episode_ids=batch_episode_ids,
                    unexpected=True,
                )
            )

    # 失敗レコードをJSONファイルに保存
    if failed_records:
        log_path = (
            PROJECT_ROOT / "src/reports/logs" / f"migration_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(failed_records, f, ensure_ascii=False, indent=2)
            print(f"\n[LOG] 失敗詳細を保存: {log_path}")
        except (IOError, OSError) as e:
            logger.error(
                "Failed to save log to %s: %s (errno=%s)",
                log_path,
                e,
                getattr(e, "errno", "N/A"),
            )
            logger.critical("Log file save failed: %s - falling back to console output", log_path)
            print(f"[CRITICAL] ログファイル保存失敗: {log_path}")
            print(f"           エラー: {e}")
            total_records = len(failed_records)
            print(f"[FALLBACK] 失敗したepisode_idをコンソールに出力 ({total_records}件):")
            for record in failed_records[:MAX_FALLBACK_RECORDS]:
                print(f"  バッチ{record['batch_num']} ({record['error_type']}): {record['episode_ids']}")
            if total_records > MAX_FALLBACK_RECORDS:
                print(f"  ... 他 {total_records - MAX_FALLBACK_RECORDS} 件（上限{MAX_FALLBACK_RECORDS}件まで表示）")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("移行結果")
    print("=" * 60)
    print(f"[OK] 成功: {success_count:,}件")
    print(f"[NG] 失敗: {error_count:,}件")

    # 複合オブジェクト検出サマリー
    if _migration_ctx.complex_object_count > 0:
        print(f"[INFO] Complex objects detected and converted to None: {_migration_ctx.complex_object_count:,}")

    # W-1: Boolean変換失敗をerror_countに反映
    if _migration_ctx.boolean_conversion_failures > 0:
        logger.warning(
            "Boolean conversion failures detected: %d columns affected",
            _migration_ctx.boolean_conversion_failures,
        )
        error_count += _migration_ctx.boolean_conversion_failures

    _migration_ctx.reset()

    # 検証（件数取得）
    db_count: int | None = None
    try:
        count_result = supabase.table("episodes").select("episode_id", count="exact", head=True).execute()  # type: ignore[arg-type]
        # S-2: getattrで安全にアクセス（type:ignore回避）
        count_value = getattr(count_result, "count", None)
        db_count = count_value if count_value is not None else 0
        print(f"\n[CHECK] Supabase件数確認: {db_count:,}件")
    except APIError as e:
        logger.error("Count verification failed: %s", e.message)
        db_count = None  # 不明を明示
        error_count += 1  # W-2: 検証失敗をエラーとしてカウント

    # 件数整合性チェック
    if db_count is None:
        logger.warning("Skipping count verification - please verify migration data integrity manually")
    elif db_count != success_count:
        logger.error(
            "Count mismatch: DB=%d, current success=%d - please verify data integrity", db_count, success_count
        )
        error_count += 1  # S-6: 件数不一致をerror_countに反映

    # サンプルデータ検証
    sample_ids = df["episode_id"].head(10).tolist()
    try:
        sample_result = (
            supabase.table("episodes")
            .select("episode_id, person_name, super_total_score")
            .in_("episode_id", sample_ids)
            .execute()
        )
        retrieved = len(sample_result.data) if sample_result.data else 0
        print(f"[CHECK] サンプル検証: {retrieved}/10件取得成功")

        # 値の整合性チェック
        for row in sample_result.data or []:
            if isinstance(row, dict):
                if row.get("super_total_score") is None:
                    logger.warning("super_total_score missing: %s", row.get("episode_id"))
    except APIError as e:
        logger.error("Sample verification failed (APIError): %s", e.message)
        error_count += 1  # W-3: 検証失敗をエラーとしてカウント
    except (TypeError, KeyError) as e:
        logger.error("Unexpected sample data format: %s", e)
        error_count += 1  # W-3: 検証失敗をエラーとしてカウント
    except (SystemExit, KeyboardInterrupt):
        # ユーザー意図の中断は再送出
        raise
    except Exception as e:
        logger.error("Unexpected error in sample verification (%s): %s", type(e).__name__, e)
        error_count += 1  # W-3: 検証失敗をエラーとしてカウント

    return error_count


def main():
    parser = argparse.ArgumentParser(description="CSV -> Supabase 移行")
    parser.add_argument("--dry-run", action="store_true", help="実行確認のみ")
    parser.add_argument("--batch-size", type=int, default=500, help="バッチサイズ")
    args = parser.parse_args()

    error_count = migrate(dry_run=args.dry_run, batch_size=args.batch_size)
    # W-3: 冗長な条件式を簡素化
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
