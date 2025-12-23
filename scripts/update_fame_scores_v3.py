#!/usr/bin/env python3
"""
Fame Score v3 - 有名人度スコア更新スクリプト

使用方法:
    # ドライラン（変更なし、効果確認のみ）
    python scripts/update_fame_scores_v3.py --dry-run

    # 特定人物のみテスト
    python scripts/update_fame_scores_v3.py --test-persons "大谷翔平,スティーブ・ジョブズ,マイケル・ジョーダン,小泉八雲"

    # 本番実行
    python scripts/update_fame_scores_v3.py --execute
"""

import argparse
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

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


def get_cached_data(conn: sqlite3.Connection, person_id: str) -> Optional[dict]:
    """キャッシュからデータを取得"""
    cursor = conn.execute("SELECT * FROM fame_cache WHERE person_id = ?", (person_id,))
    row = cursor.fetchone()
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None


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


def fetch_fame_data(
    person_id: str,
    person_name: str,
    conn: sqlite3.Connection,
    use_cache: bool = True,
    include_inlinks: bool = True,
) -> dict:
    """
    人物の有名人度データを取得。

    Args:
        person_id: 人物ID
        person_name: 人物名
        conn: キャッシュDB接続
        use_cache: キャッシュを使用するか
        include_inlinks: 被リンク数も取得するか

    Returns:
        有名人度データの辞書
    """
    # キャッシュを確認
    if use_cache:
        cached = get_cached_data(conn, person_id)
        if cached and cached.get("multi_lang_pv") is not None:
            return cached

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
        wikidata_info = get_wikidata_info(
            person_name,
            include_inlinks=include_inlinks,
        )
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


def run_test_persons(test_persons: list[str]) -> None:
    """特定人物のみテスト実行"""
    print(f"\n{'='*60}")
    print("テスト実行モード")
    print(f"{'='*60}\n")

    conn = init_cache_db()

    results = []
    for name in test_persons:
        print(f"取得中: {name}...")
        data = fetch_fame_data(
            person_id=f"TEST_{name}",
            person_name=name,
            conn=conn,
            use_cache=False,
            include_inlinks=True,
        )

        # スコア計算
        signals = FameSignals(
            multi_lang_pv=data["multi_lang_pv"],
            sitelinks=data["sitelinks"],
            inlinks=data["inlinks"],
        )
        score = calculate_fame_score(signals, data["person_id"])
        data["fame_score_v3"] = score.score

        results.append(data)

        print(f"  Wikidata ID: {data['wikidata_id']}")
        print(f"  多言語PV合計: {data['multi_lang_pv']:,}")
        print(f"  言語版数: {data['sitelinks']}")
        print(f"  被リンク数: {data['inlinks']}")
        print(f"  PV内訳: {data['pv_by_lang']}")
        print(f"  新スコア: {score.score:.2f}")
        print()

    # 順位を計算
    scores = [(r["person_name"], r["fame_score_v3"]) for r in results]
    ranks = assign_ranks(scores)

    print("=== 新順位 ===")
    for name, _ in sorted(scores, key=lambda x: ranks[x[0]]):
        result = next(r for r in results if r["person_name"] == name)
        print(f"  {ranks[name]}位: {name} (スコア: {result['fame_score_v3']:.2f})")

    conn.close()


def run_dry_run() -> None:
    """ドライラン（変更なし、効果確認のみ）"""
    print(f"\n{'='*60}")
    print("ドライラン実行モード（変更なし）")
    print(f"{'='*60}\n")

    # CSVを読み込み
    df = pd.read_csv(MASTER_CSV_PATH, low_memory=False)
    print(f"CSVレコード数: {len(df):,}")

    # 人物リストを取得
    persons = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
                "wikipedia_pv": "first",
                "fame_score": "first",
                "fame_rank": "first",
            }
        )
        .reset_index()
    )
    print(f"ユニーク人物数: {len(persons):,}")

    # 現在の上位10人を表示
    print("\n=== 現在の上位10人 ===")
    top10_current = persons.nsmallest(10, "fame_rank")
    for _, row in top10_current.iterrows():
        print(
            f"  {int(row['fame_rank'])}位: {row['person_name']} "
            f"(PV: {row['wikipedia_pv']:,.0f}, スコア: {row['fame_score']})"
        )

    # サンプル10人で新スコアを計算
    print("\n=== サンプル10人の新スコア計算 ===")
    conn = init_cache_db()

    sample_persons = [
        "大谷翔平",
        "スティーブ・ジョブズ",
        "マイケル・ジョーダン",
        "小泉八雲",
        "高市早苗",
        "北川景子",
        "井上尚弥",
        "尾崎豊",
        "宇多田ヒカル",
        "ベートーヴェン",
    ]

    results = []
    for name in sample_persons:
        person_row = persons[persons["person_name"] == name]
        if len(person_row) == 0:
            print(f"  {name}: CSVに見つかりません")
            continue

        person_id = person_row.iloc[0]["person_id"]
        current_rank = person_row.iloc[0]["fame_rank"]
        current_pv = person_row.iloc[0]["wikipedia_pv"]

        print(f"\n取得中: {name} (現在{int(current_rank)}位)...")
        data = fetch_fame_data(
            person_id=person_id,
            person_name=name,
            conn=conn,
            use_cache=True,
            include_inlinks=False,  # 時間短縮
        )

        signals = FameSignals(
            multi_lang_pv=data["multi_lang_pv"],
            sitelinks=data["sitelinks"],
            inlinks=data["inlinks"],
        )
        score = calculate_fame_score(signals, person_id)
        data["fame_score_v3"] = score.score
        data["current_rank"] = current_rank
        data["current_pv"] = current_pv

        results.append(data)

        print(f"  現在: 順位={int(current_rank)}, PV(日本語のみ)={current_pv:,.0f}")
        print(f"  新: 多言語PV={data['multi_lang_pv']:,}, 言語版数={data['sitelinks']}")
        print(f"  新スコア: {score.score:.2f}")

    # 新順位を計算
    if results:
        scores = [(r["person_name"], r["fame_score_v3"]) for r in results]
        ranks = assign_ranks(scores)

        print("\n=== サンプル10人の新順位（相対比較） ===")
        for name, _ in sorted(scores, key=lambda x: ranks[x[0]]):
            result = next(r for r in results if r["person_name"] == name)
            print(
                f"  {ranks[name]}位: {name} "
                f"(現在{int(result['current_rank'])}位 → 新スコア{result['fame_score_v3']:.2f})"
            )

    conn.close()


def run_execute(batch_size: int = 50, max_persons: int = 0) -> None:
    """本番実行（CSV更新）"""
    print(f"\n{'='*60}")
    print("本番実行モード")
    print(f"{'='*60}\n")

    # バックアップ作成
    backup_path = MASTER_CSV_PATH.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy(MASTER_CSV_PATH, backup_path)
    print(f"バックアップ作成: {backup_path}")

    # CSVを読み込み
    df = pd.read_csv(MASTER_CSV_PATH, low_memory=False)
    print(f"CSVレコード数: {len(df):,}")

    # 人物リストを取得
    persons = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
            }
        )
        .reset_index()
    )
    person_list = list(persons.itertuples(index=False))
    print(f"ユニーク人物数: {len(person_list):,}")

    if max_persons > 0:
        person_list = person_list[:max_persons]
        print(f"処理対象: 先頭{max_persons}人に制限")

    # キャッシュDB初期化
    conn = init_cache_db()

    # バッチ処理
    all_results = []
    total_batches = (len(person_list) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(person_list))
        batch = person_list[start_idx:end_idx]

        print(f"\nバッチ {batch_idx + 1}/{total_batches} " f"({start_idx + 1}-{end_idx}/{len(person_list)})")

        for person in batch:
            person_id = person.person_id
            person_name = person.person_name

            try:
                data = fetch_fame_data(
                    person_id=person_id,
                    person_name=person_name,
                    conn=conn,
                    use_cache=True,
                    include_inlinks=False,  # Phase 1では省略
                )

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

            except Exception as e:
                print(f"    [ERROR] {person_name}: {e}")

        # バッチ間の待機
        if batch_idx < total_batches - 1:
            time.sleep(1.0)

    print(f"\n処理完了: {len(all_results)}人")

    # 順位を計算
    scores = [(r["person_id"], r["fame_score_v3"]) for r in all_results]
    ranks = assign_ranks(scores)

    # ランクをデータに追加
    for result in all_results:
        result["fame_rank_v3"] = ranks.get(result["person_id"], 0)
        save_to_cache(conn, result)

    # CSVを更新
    print("\nCSV更新中...")

    # 新しいカラムを追加
    if "fame_score_v3" not in df.columns:
        df["fame_score_v3"] = None
    if "fame_rank_v3" not in df.columns:
        df["fame_rank_v3"] = None
    if "multi_lang_pv" not in df.columns:
        df["multi_lang_pv"] = None
    if "sitelinks_count" not in df.columns:
        df["sitelinks_count"] = None

    # 結果を反映
    for result in all_results:
        mask = df["person_id"] == result["person_id"]
        df.loc[mask, "fame_score_v3"] = result["fame_score_v3"]
        df.loc[mask, "fame_rank_v3"] = result["fame_rank_v3"]
        df.loc[mask, "multi_lang_pv"] = result["multi_lang_pv"]
        df.loc[mask, "sitelinks_count"] = result["sitelinks"]

    # CSV保存
    df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"CSV保存完了: {MASTER_CSV_PATH}")

    # レポート出力
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_persons": len(all_results),
        "backup_path": str(backup_path),
        "top_20": [],
    }

    # 上位20人
    sorted_results = sorted(all_results, key=lambda x: x["fame_rank_v3"])[:20]
    for r in sorted_results:
        report["top_20"].append(
            {
                "rank": r["fame_rank_v3"],
                "person_id": r["person_id"],
                "person_name": r["person_name"],
                "score": r["fame_score_v3"],
                "multi_lang_pv": r["multi_lang_pv"],
                "sitelinks": r["sitelinks"],
            }
        )

    report_path = REPORT_DIR / f"fame_score_v3_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"レポート保存: {report_path}")

    # 結果サマリー
    print("\n=== 新システムの上位20人 ===")
    for r in sorted_results:
        print(
            f"  {r['fame_rank_v3']}位: {r['person_name']} "
            f"(スコア: {r['fame_score_v3']:.2f}, 多言語PV: {r['multi_lang_pv']:,})"
        )

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Fame Score v3 - 有名人度スコア更新")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（変更なし、効果確認のみ）",
    )
    parser.add_argument(
        "--test-persons",
        type=str,
        help="特定人物のみテスト（カンマ区切り）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="本番実行（CSV更新）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="バッチサイズ（デフォルト: 50）",
    )
    parser.add_argument(
        "--max-persons",
        type=int,
        default=0,
        help="処理する最大人数（0=全員）",
    )

    args = parser.parse_args()

    if args.test_persons:
        test_persons = [p.strip() for p in args.test_persons.split(",")]
        run_test_persons(test_persons)
    elif args.dry_run:
        run_dry_run()
    elif args.execute:
        run_execute(
            batch_size=args.batch_size,
            max_persons=args.max_persons,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
