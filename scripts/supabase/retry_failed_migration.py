#!/usr/bin/env python3
"""
失敗分再実行スクリプト

エラーログJSONファイルから失敗したepisode_idを抽出し、
マスターCSVから該当レコードをフィルタしてSupabaseにupsertします。

Usage:
    python scripts/supabase/retry_failed_migration.py src/reports/logs/migration_errors_YYYYMMDD_HHMMSS.json
    python scripts/supabase/retry_failed_migration.py src/reports/logs/migration_errors_YYYYMMDD_HHMMSS.json --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from postgrest.exceptions import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 既存の移行スクリプトから関数をインポート
from supabase import Client  # 型ヒントで使用

from scripts.supabase.migrate_csv_to_supabase import (
    get_supabase_client,
    load_csv,
    clean_data,
    sanitize_records,
)


# リトライを5回に変更したupsert関数
@retry(
    stop=stop_after_attempt(5),  # 5回リトライ
    wait=wait_exponential(multiplier=1, min=2, max=30),  # 最大30秒まで待機
    retry=retry_if_exception_type(APIError),
)
def upsert_batch_with_retry(supabase: Client, batch_records: list[dict]) -> dict:
    """バッチupsert with 5回リトライ

    Returns:
        dict: {"success_count": int, "data": list}
    """
    result = supabase.table("episodes").upsert(batch_records, on_conflict="episode_id").execute()
    return {"success_count": len(result.data) if result.data else 0, "data": result.data or []}


def extract_failed_episode_ids(error_log_path: Path) -> list[str]:
    """エラーログJSONから失敗したepisode_idを抽出

    Raises:
        ValueError: JSONファイルの形式が不正な場合
        FileNotFoundError: ファイルの読み込みに失敗した場合
    """
    try:
        with open(error_log_path, "r", encoding="utf-8") as f:
            error_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"エラーログのJSON形式が不正です: {error_log_path} - {e}") from e
    except (IOError, OSError) as e:
        raise FileNotFoundError(f"エラーログの読み込みに失敗: {error_log_path} - {e}") from e

    episode_ids: set[str] = set()
    for entry in error_data:
        if "episode_ids" in entry:
            episode_ids.update(entry["episode_ids"])

    return list(episode_ids)


def filter_records_by_ids(df: pd.DataFrame, episode_ids: list[str]) -> pd.DataFrame:
    """episode_idリストで該当レコードをフィルタ"""
    filtered: pd.DataFrame = df[df["episode_id"].isin(episode_ids)]  # type: ignore[assignment]
    return filtered


def retry_migration(error_log_path: Path, dry_run: bool = False, batch_size: int = 100) -> int:
    """失敗分の再移行処理

    Returns:
        int: エラー件数（0なら正常終了）
    """
    # batch_size 妥当性チェック
    if batch_size <= 0:
        raise ValueError("batch_size は1以上の整数を指定してください")
    if batch_size > 10000:
        print("[WARN] batch_sizeが大きすぎます。API制限に注意してください")

    print("=" * 60)
    print("失敗分再実行: CSV -> Supabase")
    print("=" * 60)

    # エラーログ読み込み
    if not error_log_path.exists():
        raise FileNotFoundError(f"エラーログが見つかりません: {error_log_path}")

    failed_ids = extract_failed_episode_ids(error_log_path)
    print(f"[OK] エラーログ読み込み完了: {len(failed_ids):,}件の失敗episode_id")

    if not failed_ids:
        print("[INFO] 失敗したepisode_idがありません。終了します。")
        return 0  # 処理対象なしは成功として扱う

    # マスターCSV読み込み＆クレンジング
    df = load_csv()
    df = clean_data(df)

    # 該当レコードをフィルタ
    filtered_df = filter_records_by_ids(df, failed_ids)
    print(f"[OK] マスターCSVからフィルタ完了: {len(filtered_df):,}件")

    if len(filtered_df) == 0:
        print("[WARN] マスターCSVに該当レコードがありません。終了します。")
        return 0  # 処理対象なしは成功として扱う

    # フィルタ漏れチェック
    found_ids = set(filtered_df["episode_id"].tolist())
    missing_ids = set(failed_ids) - found_ids
    if missing_ids:
        print(f"[WARN] マスターCSVに存在しないepisode_id: {len(missing_ids):,}件")
        if len(missing_ids) <= 10:
            for mid in missing_ids:
                print(f"       - {mid}")

    if dry_run:
        print("\n[DRY-RUN] 実際の書き込みは行いません")
        print(f"   - 対象件数: {len(filtered_df):,}件")
        print(f"   - バッチサイズ: {batch_size}件")
        print(f"   - 予想バッチ数: {(len(filtered_df) + batch_size - 1) // batch_size}")

        # サンプルデータをサニタイズしてテスト
        sample_df = filtered_df.head(5)
        sample_records = sample_df.to_dict(orient="records")
        sanitized_sample = sanitize_records(sample_records)

        print("\n[SAMPLE] サニタイズ後のサンプルデータ（先頭5件）:")
        for i, rec in enumerate(sanitized_sample):
            print(
                f"  {i+1}. episode_id={rec.get('episode_id')}, "
                f"person_name={rec.get('person_name')}, "
                f"age={rec.get('age')}, "
                f"super_total_score={rec.get('super_total_score')}"
            )
        return 0  # dry-runは常に成功

    # Supabase接続
    supabase = get_supabase_client()
    print("[OK] Supabase接続完了")

    # バッチupsert
    total_batches = (len(filtered_df) + batch_size - 1) // batch_size
    success_count = 0
    error_count = 0
    failed_records: list[dict] = []

    print(f"\n[START] 再移行開始: {len(filtered_df):,}件 -> {total_batches}バッチ (バッチサイズ: {batch_size})")
    print("-" * 60)

    for i in tqdm(range(0, len(filtered_df), batch_size), total=total_batches, desc="再移行中", unit="batch", ncols=80):
        batch_df = filtered_df.iloc[i : i + batch_size]
        batch_records = batch_df.to_dict(orient="records")
        batch_records = sanitize_records(batch_records)
        batch_num = i // batch_size + 1

        try:
            result = upsert_batch_with_retry(supabase, batch_records)
            success_count += result["success_count"]
            if result["success_count"] < len(batch_records):
                partial_failed = len(batch_records) - result["success_count"]
                error_count += partial_failed
                print(f"[WARN] 部分成功: {result['success_count']}/{len(batch_records)}件")
        except APIError as e:
            # Supabase API固有エラー（型不一致、制約違反等）
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} APIError: {e.message}")
            failed_records.append(
                {
                    "batch_num": batch_num,
                    "error_type": "APIError",
                    "error_message": str(e.message),
                    "episode_ids": batch_episode_ids,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            # データ変換・構造エラー
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[ERROR] バッチ {batch_num} データ変換エラー ({type(e).__name__}): {e}")
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
            # ネットワークエラー
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
            # 予期しないエラー - 警告を強調
            error_count += len(batch_records)
            batch_episode_ids = [r.get("episode_id", "unknown") for r in batch_records]
            print(f"\n[CRITICAL] バッチ {batch_num} 予期しないエラー ({type(e).__name__}): {e}")
            print("           ※このエラーは想定外です。調査が必要な可能性があります。")
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
            PROJECT_ROOT / "src/reports/logs" / f"retry_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    print("再移行結果")
    print("=" * 60)
    print(f"[OK] 成功: {success_count:,}件")
    print(f"[NG] 失敗: {error_count:,}件")

    # 検証
    try:
        sample_ids = filtered_df["episode_id"].head(10).tolist()
        sample_result = (
            supabase.table("episodes")
            .select("episode_id, person_name, super_total_score")
            .in_("episode_id", sample_ids)
            .execute()
        )
        retrieved = len(sample_result.data) if sample_result.data else 0
        print(f"[CHECK] サンプル検証: {retrieved}/10件取得成功")
    except APIError as e:
        print(f"[ERROR] サンプル検証失敗 (APIError): {e.message}")
    except (TypeError, KeyError) as e:
        print(f"[ERROR] サンプルデータの形式が予期しない: {e}")
    except Exception as e:
        print(f"[ERROR] サンプル検証で予期しないエラー ({type(e).__name__}): {e}")

    return error_count


def main():
    parser = argparse.ArgumentParser(description="失敗分再実行: CSV -> Supabase")
    parser.add_argument("error_log", type=str, help="エラーログJSONファイルのパス")
    parser.add_argument("--dry-run", action="store_true", help="実行確認のみ")
    parser.add_argument("--batch-size", type=int, default=100, help="バッチサイズ（デフォルト: 100）")
    args = parser.parse_args()

    error_log_path = Path(args.error_log)
    if not error_log_path.is_absolute():
        error_log_path = PROJECT_ROOT / error_log_path

    error_count = retry_migration(error_log_path, dry_run=args.dry_run, batch_size=args.batch_size)
    if error_count and error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
