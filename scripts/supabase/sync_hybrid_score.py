#!/usr/bin/env python3
"""
hybrid_score カラム同期スクリプト

CSVからhybrid_scoreカラムのみをSupabaseに同期します。
事前にSupabaseダッシュボードでhybrid_scoreカラムを追加してください。

Usage:
    python scripts/supabase/sync_hybrid_score.py --dry-run   # 実行確認のみ
    python scripts/supabase/sync_hybrid_score.py             # 実際に同期

前提条件:
    Supabaseダッシュボードで以下のSQLを実行済みであること:

    ALTER TABLE episodes ADD COLUMN IF NOT EXISTS hybrid_score DOUBLE PRECISION;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_episodes_hybrid_score'
        ) THEN
            CREATE INDEX idx_episodes_hybrid_score
            ON episodes(hybrid_score DESC NULLS LAST, episode_id ASC);
        END IF;
    END $$;
"""

import argparse
import math
import os
import sys
from datetime import datetime
from pathlib import Path

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


def get_supabase_client() -> Client:
    """Supabaseクライアント取得"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY が必要です")

    return create_client(url, key)


def check_column_exists(supabase: Client) -> bool:
    """hybrid_scoreカラムが存在するか確認"""
    try:
        result = supabase.table("episodes").select("hybrid_score").limit(1).execute()
        return True
    except APIError as e:
        if "PGRST204" in str(e) or "hybrid_score" in str(e):
            return False
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, ConnectionError)),
)
def upsert_batch(supabase: Client, batch_records: list[dict]) -> dict:
    """バッチupsert with リトライ"""
    result = supabase.table("episodes").upsert(batch_records, on_conflict="episode_id").execute()
    return {
        "success_count": len(result.data) if result.data else 0,
        "data": result.data or [],
    }


def sync_hybrid_score(dry_run: bool = False, batch_size: int = 500) -> int:
    """hybrid_scoreを同期

    Returns:
        int: エラー件数（0なら正常終了）
    """
    print("=" * 60)
    print("hybrid_score 同期")
    print("=" * 60)

    # CSV読み込み
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"マスターCSVが見つかりません: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"[OK] CSV読み込み完了: {len(df):,}件")

    # hybrid_scoreカラムの確認
    if "hybrid_score" not in df.columns:
        raise ValueError("CSVにhybrid_scoreカラムがありません")

    # NaN/Infをサニタイズ
    def sanitize_score(value):
        if pd.isna(value):
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)

    # episode_idとhybrid_scoreのみ抽出
    df["hybrid_score"] = df["hybrid_score"].apply(sanitize_score)
    sync_df = df[["episode_id", "hybrid_score"]].copy()

    # NULLを除外（必要なデータのみ同期）
    valid_df = sync_df[sync_df["hybrid_score"].notna()]
    print(f"[OK] 同期対象: {len(valid_df):,}件 (NULLを除外)")

    if dry_run:
        print("\n[DRY-RUN] 実際の書き込みは行いません")
        print(f"   - 対象件数: {len(valid_df):,}件")
        print(f"   - バッチサイズ: {batch_size}件")
        print(f"   - 予想バッチ数: {(len(valid_df) + batch_size - 1) // batch_size}")

        print("\n[SAMPLE] サンプルデータ（先頭10件）:")
        for i, row in valid_df.head(10).iterrows():
            print(f"  {row['episode_id']}: {row['hybrid_score']:.2f}")

        # Supabase接続テスト
        try:
            supabase = get_supabase_client()
            if check_column_exists(supabase):
                print("\n[OK] Supabase hybrid_scoreカラム: 存在")
            else:
                print("\n[ERROR] Supabase hybrid_scoreカラム: 未作成")
                print("        先にダッシュボードでカラムを追加してください")
                return 1
        except Exception as e:
            print(f"\n[ERROR] Supabase接続エラー: {e}")
            return 1

        return 0

    # Supabase接続
    supabase = get_supabase_client()
    print("[OK] Supabase接続完了")

    # カラム存在確認
    if not check_column_exists(supabase):
        print("[ERROR] hybrid_scoreカラムがSupabaseに存在しません")
        print("        先にダッシュボードで以下のSQLを実行してください:")
        print("-" * 60)
        print("ALTER TABLE episodes ADD COLUMN IF NOT EXISTS hybrid_score DOUBLE PRECISION;")
        print("-" * 60)
        return 1

    print("[OK] hybrid_scoreカラム確認完了")

    # バッチupsert
    total_batches = (len(valid_df) + batch_size - 1) // batch_size
    success_count = 0
    error_count = 0

    print(f"\n[START] 同期開始: {len(valid_df):,}件 -> {total_batches}バッチ")
    print("-" * 60)

    for i in tqdm(
        range(0, len(valid_df), batch_size),
        total=total_batches,
        desc="同期中",
        unit="batch",
        ncols=80,
    ):
        batch_df = valid_df.iloc[i : i + batch_size]
        batch_records = batch_df.to_dict(orient="records")

        try:
            result = upsert_batch(supabase, batch_records)
            success_count += result["success_count"]
            if result["success_count"] < len(batch_records):
                partial_failed = len(batch_records) - result["success_count"]
                error_count += partial_failed
        except APIError as e:
            error_count += len(batch_records)
            print(f"\n[ERROR] バッチ {i // batch_size + 1}: {e.message}")
        except Exception as e:
            error_count += len(batch_records)
            print(f"\n[ERROR] バッチ {i // batch_size + 1}: {e}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("同期結果")
    print("=" * 60)
    print(f"[OK] 成功: {success_count:,}件")
    print(f"[NG] 失敗: {error_count:,}件")

    # 検証
    try:
        sample_result = (
            supabase.table("episodes")
            .select("episode_id, person_name, hybrid_score")
            .order("hybrid_score", desc=True)
            .limit(5)
            .execute()
        )
        print("\n[CHECK] hybrid_score TOP 5:")
        for row in sample_result.data or []:
            hs = row.get("hybrid_score")
            hs_str = f"{hs:,.2f}" if hs else "NULL"
            print(f"  {row.get('person_name')}: {hs_str}")
    except Exception as e:
        print(f"[WARN] サンプル検証失敗: {e}")

    return error_count


def main():
    parser = argparse.ArgumentParser(description="hybrid_score 同期")
    parser.add_argument("--dry-run", action="store_true", help="実行確認のみ")
    parser.add_argument("--batch-size", type=int, default=500, help="バッチサイズ")
    args = parser.parse_args()

    error_count = sync_hybrid_score(dry_run=args.dry_run, batch_size=args.batch_size)
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
