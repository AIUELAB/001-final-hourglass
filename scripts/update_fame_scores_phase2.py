#!/usr/bin/env python3
"""
Fame Score v3 Phase 2 - Google検索ヒット数を追加してスコアを再計算。

使用方法:
    # ドライラン（上位100人のみテスト）
    python scripts/update_fame_scores_phase2.py --dry-run

    # 本番実行
    python scripts/update_fame_scores_phase2.py --execute

環境変数:
    GOOGLE_API_KEY: Google Cloud APIキー
    GOOGLE_CSE_ID: Custom Search Engine ID
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.google_search import get_google_search_hits, get_stats, is_google_available, reset_stats
from scripts.fame_score_v3.scorer import FameSignals, assign_ranks, calculate_fame_score

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
CACHE_DB_PATH = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports")

# レート制限（Google API: 100 queries/day free tier）
BATCH_SIZE = 50
BATCH_INTERVAL = 2.0  # 秒


def init_cache_db() -> sqlite3.Connection:
    """キャッシュDBを初期化（google_hits列を追加）"""
    conn = sqlite3.connect(str(CACHE_DB_PATH))

    # google_hits列が存在しなければ追加
    cursor = conn.execute("PRAGMA table_info(fame_cache)")
    columns = [row[1] for row in cursor.fetchall()]
    if "google_hits" not in columns:
        conn.execute("ALTER TABLE fame_cache ADD COLUMN google_hits INTEGER")
        conn.commit()

    return conn


def get_persons_without_google_hits(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Google検索ヒット数が未取得の人物リストを取得"""
    cursor = conn.execute("""
        SELECT person_id, person_name
        FROM fame_cache
        WHERE google_hits IS NULL
        ORDER BY fame_score_v3 DESC
    """)
    return cursor.fetchall()


def run_dry_run() -> None:
    """ドライラン（上位100人のみテスト）"""
    print(f"\n{'='*60}")
    print("Phase 2 ドライラン（上位100人のみ）")
    print(f"{'='*60}\n")

    if not is_google_available():
        print("ERROR: Google API キーが設定されていません")
        print("環境変数を設定してください:")
        print("  export GOOGLE_API_KEY=your_api_key")
        print("  export GOOGLE_CSE_ID=your_cse_id")
        return

    conn = init_cache_db()

    # 上位100人を取得
    cursor = conn.execute("""
        SELECT person_id, person_name, fame_score_v3, multi_lang_pv, sitelinks
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
        ORDER BY fame_score_v3 DESC
        LIMIT 100
    """)
    persons = cursor.fetchall()

    print(f"テスト対象: {len(persons)}人")
    print()

    results = []
    for i, (pid, name, old_score, pv, sitelinks) in enumerate(persons[:10], 1):
        print(f"{i}. {name}...")
        hits = get_google_search_hits(name, person_id=pid)

        if hits:
            # 新スコア計算
            signals = FameSignals(
                multi_lang_pv=pv or 0,
                sitelinks=sitelinks or 0,
                inlinks=0,
                google_hits=hits,
            )
            new_score = calculate_fame_score(signals, pid)

            results.append(
                {
                    "name": name,
                    "old_score": old_score,
                    "new_score": new_score.score,
                    "google_hits": hits,
                }
            )

            print(f"   Google: {hits:,} hits")
            print(f"   スコア: {old_score:.2f} → {new_score.score:.2f}")
        else:
            print("   Google: 取得失敗")

        time.sleep(1.0)  # レート制限

    print()
    print("=== ドライラン完了 ===")
    print("本番実行: python scripts/update_fame_scores_phase2.py --execute")

    conn.close()


def run_execute(max_queries: int = 0) -> None:
    """本番実行"""
    print(f"\n{'='*60}")
    print("Phase 2 本番実行")
    print(f"{'='*60}\n")

    if not is_google_available():
        print("ERROR: Google API キーが設定されていません")
        return

    conn = init_cache_db()

    # Google検索未取得の人物を取得
    persons = get_persons_without_google_hits(conn)
    print(f"Google検索未取得: {len(persons)}人")

    if max_queries > 0:
        persons = persons[:max_queries]
        print(f"処理対象: {len(persons)}人（制限）")

    if not persons:
        print("全員取得済みです")
        conn.close()
        return

    # バッチ処理
    updated = 0
    errors = 0
    total_batches = (len(persons) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(persons))
        batch = persons[start_idx:end_idx]

        print(f"\nバッチ {batch_idx + 1}/{total_batches} ({start_idx + 1}-{end_idx}/{len(persons)})")

        for pid, name in batch:
            # キャッシュ優先（既にgoogle_hitsがあればスキップ）
            hits = get_google_search_hits(name, person_id=pid)

            if hits is not None:
                updated += 1
            else:
                errors += 1

        conn.commit()

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

    print(f"\n取得完了: {updated}人 (エラー: {errors})")

    # 全スコアを再計算
    print("\nスコア再計算中...")
    cursor = conn.execute("""
        SELECT person_id, multi_lang_pv, sitelinks, inlinks, google_hits
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
    """)

    all_scores = []
    for row in cursor.fetchall():
        pid, pv, sitelinks, inlinks, google_hits = row
        signals = FameSignals(
            multi_lang_pv=pv or 0,
            sitelinks=sitelinks or 0,
            inlinks=inlinks or 0,
            google_hits=google_hits,  # None の場合は Phase 1 の重みが適用される
        )
        score = calculate_fame_score(signals, pid)
        all_scores.append((pid, score.score))

        conn.execute("UPDATE fame_cache SET fame_score_v3 = ? WHERE person_id = ?", (score.score, pid))

    # 順位を再計算
    ranks = assign_ranks(all_scores)
    for pid, rank in ranks.items():
        conn.execute("UPDATE fame_cache SET fame_rank_v3 = ? WHERE person_id = ?", (rank, pid))

    conn.commit()

    # CSVを更新
    print("CSV更新中...")
    df = pd.read_csv(MASTER_CSV_PATH, low_memory=False)

    if "google_hits" not in df.columns:
        df["google_hits"] = None

    cursor = conn.execute("""
        SELECT person_id, fame_score_v3, fame_rank_v3, google_hits
        FROM fame_cache
    """)

    for row in cursor.fetchall():
        pid, score, rank, hits = row
        mask = df["person_id"] == pid
        df.loc[mask, "fame_score_v3"] = score
        df.loc[mask, "fame_rank_v3"] = rank
        if hits is not None:
            df.loc[mask, "google_hits"] = hits

    df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"CSV保存: {MASTER_CSV_PATH}")

    # レポート
    report = {
        "timestamp": datetime.now().isoformat(),
        "updated": updated,
        "errors": errors,
        "total_with_google": conn.execute("SELECT COUNT(*) FROM fame_cache WHERE google_hits IS NOT NULL").fetchone()[
            0
        ],
    }

    report_path = REPORT_DIR / f"fame_phase2_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"レポート: {report_path}")

    # 上位10人を表示
    print("\n=== Phase 2 新ランキング Top 10 ===")
    cursor = conn.execute("""
        SELECT fame_rank_v3, person_name, fame_score_v3, google_hits
        FROM fame_cache
        ORDER BY fame_rank_v3
        LIMIT 10
    """)
    for rank, name, score, hits in cursor.fetchall():
        hits_str = f"{hits:,}" if hits else "N/A"
        print(f"  {rank}位: {name} (スコア: {score:.2f}, Google: {hits_str})")

    conn.close()


def main():
    # 環境変数をファイルから読み込み（存在すれば）
    key_dir = Path("/Users/admin/Documents/key")
    api_key_file = key_dir / "EP-Google-Count-API-Key.txt"
    cse_id_file = key_dir / "EP_GOOGLE_COUNT_CSE_ID.txt"

    if api_key_file.exists() and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key_file.read_text().strip()
    if cse_id_file.exists() and not os.environ.get("GOOGLE_CSE_ID"):
        os.environ["GOOGLE_CSE_ID"] = cse_id_file.read_text().strip()

    parser = argparse.ArgumentParser(description="Fame Score v3 Phase 2 - Google検索追加")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（上位100人のみテスト）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="本番実行",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=0,
        help="最大クエリ数（0=無制限、API無料枠は100/日）",
    )

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
    elif args.execute:
        run_execute(max_queries=args.max_queries)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
