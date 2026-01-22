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
    # None/pandas NA
    if value is None or pd.isna(value):
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
def upsert_batch(supabase: Client, batch_records: list[dict]) -> None:
    """バッチupsert with リトライ"""
    supabase.table("episodes").upsert(batch_records, on_conflict="episode_id").execute()


def migrate(dry_run: bool = False, batch_size: int = 500):
    """メイン移行処理"""
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

        return

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
            upsert_batch(supabase, batch_records)
            success_count += len(batch_records)
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
        except Exception as e:
            # その他の予期しないエラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} 予期しないエラー ({type(e).__name__}): {e}")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
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
            print(f"\n[WARN] ログ保存失敗: {e}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("移行結果")
    print("=" * 60)
    print(f"[OK] 成功: {success_count:,}件")
    print(f"[NG] 失敗: {error_count:,}件")

    # 検証（件数取得）
    try:
        result = supabase.table("episodes").select("episode_id", count="exact", head=True).execute()  # type: ignore[arg-type]
        db_count = result.count if result.count else 0
        print(f"\n[CHECK] Supabase件数確認: {db_count:,}件")
    except APIError as e:
        print(f"\n[WARN] 件数検証に失敗しました: {e.message}")
        db_count = -1

    # 件数整合性チェック
    if db_count != success_count:
        print(f"[WARN] 件数不一致: 成功={success_count:,}, DB={db_count:,}")

    # サンプルデータ検証
    sample_ids = df["episode_id"].head(10).tolist()
    sample_result = (
        supabase.table("episodes")
        .select("episode_id, person_name, super_total_score")
        .in_("episode_id", sample_ids)
        .execute()
    )
    print(f"[CHECK] サンプル検証: {len(sample_result.data)}/10件取得成功")


def main():
    parser = argparse.ArgumentParser(description="CSV -> Supabase 移行")
    parser.add_argument("--dry-run", action="store_true", help="実行確認のみ")
    parser.add_argument("--batch-size", type=int, default=500, help="バッチサイズ")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
