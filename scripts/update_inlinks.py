#!/usr/bin/env python3
"""
inlinks（被リンク数）一括更新スクリプト。

fame_cache内のWikidata IDを持つ全エントリに対して、
Wikipedia APIでinlinksを取得・更新する。
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path

from fame_score_v3.wikidata import get_inlinks_hybrid
from fame_score_v3.scorer import calculate_fame_score, FameSignals

# パス
CACHE_DB = Path("data/cache/fame_score.db")


def get_entries_needing_inlinks(conn: sqlite3.Connection) -> list:
    """inlinks更新が必要なエントリを取得"""
    cursor = conn.execute("""
        SELECT person_id, person_name, wikidata_id, sitelinks, multi_lang_pv, google_hits
        FROM fame_cache
        WHERE wikidata_id IS NOT NULL
          AND wikidata_id != ''
          AND (inlinks IS NULL OR inlinks = 0)
        ORDER BY fame_score_v3 DESC
    """)
    return list(cursor)


def get_all_entries_with_wikidata(conn: sqlite3.Connection) -> list:
    """Wikidata IDを持つ全エントリを取得"""
    cursor = conn.execute("""
        SELECT person_id, person_name, wikidata_id, sitelinks, multi_lang_pv, google_hits, inlinks
        FROM fame_cache
        WHERE wikidata_id IS NOT NULL AND wikidata_id != ''
        ORDER BY fame_score_v3 DESC
    """)
    return list(cursor)


def update_inlinks(
    conn: sqlite3.Connection,
    person_id: str,
    inlinks: int,
    recalculate_score: bool = False,
    sitelinks: int = 0,
    multi_lang_pv: int = 0,
    google_hits: int = None,
) -> None:
    """inlinksを更新"""
    if recalculate_score:
        # スコア再計算
        signals = FameSignals(
            multi_lang_pv=multi_lang_pv,
            sitelinks=sitelinks,
            inlinks=inlinks,
            google_hits=google_hits,
        )
        new_score = calculate_fame_score(signals)

        conn.execute(
            """
            UPDATE fame_cache
            SET inlinks = ?, fame_score_v3 = ?, updated_at = ?
            WHERE person_id = ?
            """,
            (inlinks, new_score, datetime.now().isoformat(), person_id),
        )
    else:
        conn.execute(
            "UPDATE fame_cache SET inlinks = ? WHERE person_id = ?",
            (inlinks, person_id),
        )


def main():
    import sys

    # オプション解析
    only_missing = "--only-missing" in sys.argv
    recalculate = "--recalculate" in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    print("=== inlinks一括更新 ===\n")
    print("オプション:")
    print(f"  --only-missing: {only_missing}")
    print(f"  --recalculate: {recalculate}")
    print(f"  --limit: {limit}")
    print()

    conn = sqlite3.connect(str(CACHE_DB))

    # 対象エントリ取得
    if only_missing:
        entries = get_entries_needing_inlinks(conn)
        print(f"inlinks未取得エントリ: {len(entries)}")
    else:
        entries = get_all_entries_with_wikidata(conn)
        print(f"Wikidata ID保持エントリ: {len(entries)}")

    if limit:
        entries = entries[:limit]
        print(f"処理対象（limit適用後）: {len(entries)}")

    print()

    # 統計
    success_count = 0
    skip_count = 0
    error_count = 0
    total_inlinks = 0

    start_time = time.time()

    for i, entry in enumerate(entries, 1):
        person_id = entry[0]
        person_name = entry[1]
        wikidata_id = entry[2]
        sitelinks = entry[3] or 0
        multi_lang_pv = entry[4] or 0
        google_hits = entry[5]
        current_inlinks = entry[6] if len(entry) > 6 else 0

        # 進捗表示
        if i % 100 == 0 or i == len(entries):
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(entries) - i) / rate if rate > 0 else 0
            print(f"進捗: {i}/{len(entries)} ({i/len(entries)*100:.1f}%) " f"- {rate:.1f}/sec - ETA: {eta/60:.1f}分")

        # 既存inlinksがある場合はスキップ（only_missingの場合）
        if only_missing and current_inlinks and current_inlinks > 0:
            skip_count += 1
            continue

        try:
            # inlinks取得（Wikipedia API優先）
            inlinks = get_inlinks_hybrid(wikidata_id, lang="ja", use_sparql_fallback=False)

            if inlinks > 0:
                success_count += 1
                total_inlinks += inlinks

                update_inlinks(
                    conn,
                    person_id,
                    inlinks,
                    recalculate_score=recalculate,
                    sitelinks=sitelinks,
                    multi_lang_pv=multi_lang_pv,
                    google_hits=google_hits,
                )

                # 50件ごとにコミット
                if success_count % 50 == 0:
                    conn.commit()
            else:
                skip_count += 1

        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {person_name} ({wikidata_id}): {e}")

    # 最終コミット
    conn.commit()
    conn.close()

    # 結果サマリー
    elapsed = time.time() - start_time
    print(f"\n{'=' * 50}")
    print("処理完了")
    print(f"  処理時間: {elapsed/60:.1f}分")
    print(f"  成功: {success_count}")
    print(f"  スキップ: {skip_count}")
    print(f"  エラー: {error_count}")
    print(f"  平均inlinks: {total_inlinks/success_count:.1f}" if success_count > 0 else "")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
