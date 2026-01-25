#!/usr/bin/env python3
"""
Fame Score v3 差分更新スクリプト（Phase 3用）。

使用方法:
    # 新規・期限切れ人物のみ更新
    python scripts/update_fame_scores_incremental.py

    # 強制全更新
    python scripts/update_fame_scores_incremental.py --force-all

    # ドライラン（更新対象の確認のみ）
    python scripts/update_fame_scores_incremental.py --dry-run
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.scorer import FameSignals, assign_ranks, calculate_fame_score
from scripts.fame_score_v3.wikidata import get_wikidata_info
from scripts.fame_score_v3.wikipedia_pv import get_multi_lang_pageviews

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
CACHE_DB_PATH = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports")
LOG_DIR = Path("src/reports/logs")

# キャッシュ有効期限（日）
CACHE_EXPIRY_DAYS = 30

# バッチ設定
BATCH_SIZE = 50
BATCH_INTERVAL = 1.0  # 秒


def init_cache_db() -> sqlite3.Connection:
    """キャッシュDBを初期化"""
    CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fame_cache (
            person_id TEXT PRIMARY KEY,
            person_name TEXT,
            wikidata_id TEXT,
            multi_lang_pv INTEGER,
            sitelinks INTEGER,
            inlinks INTEGER,
            pv_by_lang TEXT,
            fame_score_v3 REAL,
            fame_rank_v3 INTEGER,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn


def get_persons_to_update(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    force_all: bool = False,
) -> list[tuple[str, str]]:
    """
    更新対象の人物リストを取得。

    Args:
        conn: キャッシュDB接続
        df: マスターCSVのDataFrame
        force_all: 全員を対象とするか

    Returns:
        [(person_id, person_name), ...] のリスト
    """
    # 全人物リストを取得
    persons = df.groupby("person_id").agg({"person_name": "first"}).reset_index()
    all_persons = set(persons["person_id"].tolist())

    if force_all:
        return list(persons.itertuples(index=False, name=None))

    # キャッシュ済み人物を取得
    cursor = conn.execute("""
        SELECT person_id, updated_at
        FROM fame_cache
        WHERE multi_lang_pv IS NOT NULL
    """)
    cached = {row[0]: row[1] for row in cursor.fetchall()}

    # 期限切れの閾値
    expiry_threshold = datetime.now() - timedelta(days=CACHE_EXPIRY_DAYS)

    update_targets = []
    for _, row in persons.iterrows():
        person_id = row["person_id"]
        person_name = row["person_name"]

        # 新規人物
        if person_id not in cached:
            update_targets.append((person_id, person_name))
            continue

        # 期限切れチェック
        updated_at_str = cached.get(person_id)
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str)
                if updated_at < expiry_threshold:
                    update_targets.append((person_id, person_name))
            except ValueError:
                update_targets.append((person_id, person_name))

    return update_targets


def fetch_fame_data(
    person_id: str,
    person_name: str,
) -> dict:
    """人物の有名人度データを取得"""
    result = {
        "person_id": person_id,
        "person_name": person_name,
        "wikidata_id": None,
        "multi_lang_pv": 0,
        "sitelinks": 0,
        "inlinks": 0,
        "pv_by_lang": {},
    }

    try:
        # Wikidata情報を取得
        wikidata_info = get_wikidata_info(person_name, include_inlinks=False)
        result["wikidata_id"] = wikidata_info.get("wikidata_id")
        result["sitelinks"] = wikidata_info.get("sitelinks", 0)
        result["inlinks"] = wikidata_info.get("inlinks", 0)

        # Wikipedia多言語PVを取得
        pv_info = get_multi_lang_pageviews(
            person_name,
            wikidata_id=result["wikidata_id"],
        )
        result["multi_lang_pv"] = pv_info.get("total_pv", 0)
        result["pv_by_lang"] = pv_info.get("by_lang", {})

    except Exception as e:
        print(f"    [WARNING] データ取得エラー: {person_name} - {e}")

    return result


def save_to_cache(conn: sqlite3.Connection, data: dict) -> None:
    """キャッシュにデータを保存"""
    conn.execute(
        """
        INSERT OR REPLACE INTO fame_cache
        (person_id, person_name, wikidata_id, multi_lang_pv, sitelinks, inlinks,
         pv_by_lang, fame_score_v3, fame_rank_v3, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data["person_id"],
            data["person_name"],
            data.get("wikidata_id"),
            data.get("multi_lang_pv", 0),
            data.get("sitelinks", 0),
            data.get("inlinks", 0),
            json.dumps(data.get("pv_by_lang", {})),
            data.get("fame_score_v3"),
            data.get("fame_rank_v3"),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()


def update_csv_from_cache(df: pd.DataFrame, conn: sqlite3.Connection) -> pd.DataFrame:
    """キャッシュからCSVを更新"""
    # 全キャッシュデータを取得
    cursor = conn.execute("""
        SELECT person_id, fame_score_v3, fame_rank_v3, multi_lang_pv, sitelinks
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
    """)
    cache_data = {row[0]: row[1:] for row in cursor.fetchall()}

    # カラムが存在しなければ追加
    for col in ["fame_score_v3", "fame_rank_v3", "multi_lang_pv", "sitelinks_count"]:
        if col not in df.columns:
            df[col] = None

    # 更新
    for person_id, (score, rank, pv, sitelinks) in cache_data.items():
        mask = df["person_id"] == person_id
        df.loc[mask, "fame_score_v3"] = score
        df.loc[mask, "fame_rank_v3"] = rank
        df.loc[mask, "multi_lang_pv"] = pv
        df.loc[mask, "sitelinks_count"] = sitelinks

    return df


def run_incremental_update(
    dry_run: bool = False,
    force_all: bool = False,
) -> dict:
    """差分更新を実行"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"fame_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    print(f"\n{'=' * 60}")
    print("Fame Score v3 差分更新")
    print(f"{'=' * 60}\n")

    # CSV読み込み
    df = pd.read_csv(MASTER_CSV_PATH, low_memory=False)
    total_persons = df["person_id"].nunique()
    print(f"総人物数: {total_persons:,}")

    # キャッシュDB初期化
    conn = init_cache_db()

    # 更新対象を取得
    targets = get_persons_to_update(conn, df, force_all=force_all)
    print(f"更新対象: {len(targets):,}人物")

    if dry_run:
        print("\n[ドライラン] 更新は実行しません。")
        if targets[:10]:
            print("\n更新対象（先頭10件）:")
            for pid, pname in targets[:10]:
                print(f"  - {pname} ({pid})")
        conn.close()
        return {"targets": len(targets), "updated": 0, "dry_run": True}

    if not targets:
        print("\n更新対象がありません。")
        conn.close()
        return {"targets": 0, "updated": 0}

    # バッチ処理
    updated_count = 0
    all_results = []
    total_batches = (len(targets) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(targets))
        batch = targets[start_idx:end_idx]

        print(f"\nバッチ {batch_idx + 1}/{total_batches} ({start_idx + 1}-{end_idx}/{len(targets)})")

        for person_id, person_name in batch:
            try:
                data = fetch_fame_data(person_id, person_name)

                # スコア計算
                signals = FameSignals(
                    multi_lang_pv=data["multi_lang_pv"],
                    sitelinks=data["sitelinks"],
                    inlinks=data["inlinks"],
                )
                score = calculate_fame_score(signals, person_id)
                data["fame_score_v3"] = score.score

                # キャッシュに保存
                save_to_cache(conn, data)
                all_results.append(data)
                updated_count += 1

            except Exception as e:
                print(f"    [ERROR] {person_name}: {e}")

        # バッチ間の待機
        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

    # 全データの順位を再計算
    print("\n順位を再計算中...")
    cursor = conn.execute("""
        SELECT person_id, fame_score_v3
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
    """)
    all_scores = [(row[0], row[1]) for row in cursor.fetchall()]
    ranks = assign_ranks(all_scores)

    # 順位をキャッシュに反映
    for person_id, rank in ranks.items():
        conn.execute(
            "UPDATE fame_cache SET fame_rank_v3 = ? WHERE person_id = ?",
            (rank, person_id),
        )
    conn.commit()

    # CSVを更新
    print("CSVを更新中...")
    df = update_csv_from_cache(df, conn)
    df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"CSV保存完了: {MASTER_CSV_PATH}")

    # レポート出力
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_persons": total_persons,
        "targets": len(targets),
        "updated": updated_count,
        "force_all": force_all,
    }

    report_path = REPORT_DIR / f"fame_incremental_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"レポート保存: {report_path}")

    print(f"\n{'=' * 60}")
    print(f"完了: {updated_count}/{len(targets)}人物を更新")
    print(f"{'=' * 60}")

    conn.close()
    return result


def main():
    parser = argparse.ArgumentParser(description="Fame Score v3 差分更新")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（更新対象の確認のみ）",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="全人物を強制更新",
    )

    args = parser.parse_args()

    run_incremental_update(
        dry_run=args.dry_run,
        force_all=args.force_all,
    )


if __name__ == "__main__":
    main()
