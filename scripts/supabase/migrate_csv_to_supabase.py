#!/usr/bin/env python3
"""
CSV → Supabase 初期移行スクリプト

Usage:
    python scripts/supabase/migrate_csv_to_supabase.py --dry-run   # 実行確認のみ
    python scripts/supabase/migrate_csv_to_supabase.py             # 実際に移行
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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
    except pd.errors.ParserError as e:
        raise ValueError(f"CSV解析エラー: {e}")
    print(f"[OK] CSV読み込み完了: {len(df):,}件")
    return df


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
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        # pd.isna()は一部の型（例: 複合オブジェクト）で例外を発生させる
        # この場合は後続の型判定で適切に処理されるため、ここではpassで継続
        # デバッグ時はlogging.debug()でトレース可能
        pass

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
            print(f"[WARN] INTEGER変換失敗 {column_name}='{value}': {e}")
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

    # Boolean型変換
    bool_cols = ["is_group_member", "is_japanese"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: bool(x) if pd.notnull(x) and x != "" else None)

    return df


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(APIError),
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
        print("[WARN] batch_sizeが大きすぎます。API制限に注意してください")

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
                f"  {i+1}. episode_id={rec.get('episode_id')}, "
                f"person_name={rec.get('person_name')}, "
                f"age={rec.get('age')} (type={type(rec.get('age')).__name__}), "
                f"birth_year={rec.get('birth_year')} (type={type(rec.get('birth_year')).__name__}), "
                f"super_total_score={rec.get('super_total_score')}"
            )

        # NaN/Inf検出テスト
        try:
            json.dumps(sanitized_sample)
            print("\n[OK] JSONシリアライズテスト: 成功")
        except (ValueError, TypeError) as e:
            print(f"\n[ERROR] JSONシリアライズテスト: 失敗 - {e}")

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

    failed_records: list[dict] = []  # 失敗レコード詳細

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
                print(f"[WARN] 部分成功: {result['success_count']}/{len(batch_records)}件 (失敗: {partial_failed}件)")
        except APIError as e:
            # Supabase API固有エラー（型不一致、制約違反等）
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} APIError: {e.message}")
            print(f"        対象episode_id: {batch_episode_ids[:5]}...（先頭5件）")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": "APIError",
                    "error_message": str(e.message),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except (json.JSONDecodeError, ValueError) as e:
            # JSON/値変換エラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} データ変換エラー: {e}")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except (TypeError, KeyError) as e:
            # 型エラー、キー欠損
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} データ構造エラー ({type(e).__name__}): {e}")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except ConnectionError as e:
            # ネットワーク接続エラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} 接続エラー: {e}")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": "ConnectionError",
                    "error_message": str(e),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            # その他の予期しないエラー（ログに明示的に記録）
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} 予期しないエラー ({type(e).__name__}): {e}")
            print("        ※このエラーは想定外です。調査が必要な可能性があります。")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                    "unexpected": True,
                }
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
            print(f"\n[ERROR] ログ保存失敗: {e}")
            print("[FALLBACK] 失敗したepisode_idをコンソールに出力:")
            for record in failed_records[:5]:  # 先頭5件のみ
                ids_preview = record["episode_ids"][:10]
                print(f"  バッチ{record['batch_num']}: {ids_preview}...")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("移行結果")
    print("=" * 60)
    print(f"[OK] 成功: {success_count:,}件")
    print(f"[NG] 失敗: {error_count:,}件")

    # 検証（件数取得）
    db_count: int | None = None
    try:
        result = supabase.table("episodes").select("episode_id", count="exact", head=True).execute()  # type: ignore[arg-type]
        db_count = result.count if result.count else 0
        print(f"\n[CHECK] Supabase件数確認: {db_count:,}件")
    except APIError as e:
        print(f"\n[ERROR] 件数検証に失敗: {e.message}")
        db_count = None  # 不明を明示

    # 件数整合性チェック
    if db_count is None:
        print("[SKIP] 件数検証をスキップ（検証APIエラー）")
    elif db_count != success_count:
        print(f"[INFO] DB件数: {db_count:,}, 今回成功: {success_count:,}")

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
                    print(f"[WARN] super_total_score欠損: {row.get('episode_id')}")
    except APIError as e:
        print(f"[ERROR] サンプル検証失敗 (APIError): {e.message}")
    except (TypeError, KeyError) as e:
        print(f"[ERROR] サンプルデータの形式が予期しない: {e}")
    except Exception as e:
        print(f"[ERROR] サンプル検証で予期しないエラー ({type(e).__name__}): {e}")

    return error_count


def main():
    parser = argparse.ArgumentParser(description="CSV -> Supabase 移行")
    parser.add_argument("--dry-run", action="store_true", help="実行確認のみ")
    parser.add_argument("--batch-size", type=int, default=500, help="バッチサイズ")
    args = parser.parse_args()

    error_count = migrate(dry_run=args.dry_run, batch_size=args.batch_size)
    if error_count and error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
