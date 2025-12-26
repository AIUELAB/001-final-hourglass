#!/usr/bin/env python3
"""
Fame Score v3 Phase 2 - Google検索ヒット数を追加してスコアを再計算。

使用方法:
    # ドライラン（上位10人のみテスト）
    python scripts/update_fame_scores_phase2.py --dry-run

    # 本番実行（日次上限まで）
    python scripts/update_fame_scores_phase2.py --execute

    # 最大10クエリに制限
    python scripts/update_fame_scores_phase2.py --execute --max-queries 10

    # 自動実行モード（スケジューラ用）
    python scripts/update_fame_scores_phase2.py --execute --auto

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
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.google_search import (
    get_search_hits,
    get_stats,
    is_google_available,
    is_serpapi_available,
    reset_stats,
)
from scripts.fame_score_v3.quota_manager import GoogleQuotaManager
from scripts.fame_score_v3.scorer import FameSignals, assign_ranks, calculate_fame_score

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
CACHE_DB_PATH = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports")

# レート制限（Google API: 100 queries/day free tier）
BATCH_SIZE = 50
BATCH_INTERVAL = 2.0  # 秒

# 人物メタ情報キャッシュ（category, person_type）
_person_meta_cache: dict[str, dict] = {}


def load_person_meta() -> dict[str, dict]:
    """
    CSVから人物のカテゴリ・person_type情報を読み込み。
    曖昧性対策用（Google検索クエリにカテゴリを付加）。
    """
    global _person_meta_cache
    if _person_meta_cache:
        return _person_meta_cache

    if not MASTER_CSV_PATH.exists():
        return {}

    try:
        df = pd.read_csv(MASTER_CSV_PATH, encoding="utf-8-sig")
        for _, row in df.iterrows():
            pid = row.get("person_id", "")
            if pid and pid not in _person_meta_cache:
                _person_meta_cache[pid] = {
                    "category": row.get("category", ""),
                    "person_type": row.get("person_type", "REAL"),
                }
    except Exception as e:
        print(f"警告: 人物メタ情報の読み込み失敗: {e}")

    return _person_meta_cache


# 短名スキップリスト（一般語と衝突するため検索結果が汚染される）
SKIP_SHORT_NAMES = {
    "ken",
    "ONE",
    "UA",
    "IU",
    "SZA",
    "hide",
    "AI",
    "DJ",
    "MC",
    "Eve",
    "May",
    "Rio",
    "Jun",
    "Rei",
    "Yui",
    "Ryu",
    "Kai",
}


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
    """Google検索ヒット数が未取得の人物リストを取得（スコア降順）"""
    cursor = conn.execute("""
        SELECT person_id, person_name
        FROM fame_cache
        WHERE google_hits IS NULL
        ORDER BY fame_score_v3 DESC
    """)
    return cursor.fetchall()


def run_dry_run() -> None:
    """ドライラン（上位10人のみテスト）"""
    print(f"\n{'='*60}")
    print("Phase 2 ドライラン（上位10人のみ）")
    print(f"{'='*60}\n")

    if not is_google_available() and not is_serpapi_available():
        print("ERROR: 検索API キーが設定されていません")
        print("以下のいずれかを設定してください:")
        print("  export SERPAPI_API_KEY=your_api_key  (推奨)")
        print("  または")
        print("  export GOOGLE_API_KEY=your_api_key")
        print("  export GOOGLE_CSE_ID=your_cse_id")
        return

    api_type = "SerpAPI" if is_serpapi_available() else "Google"
    print(f"使用API: {api_type}")

    # クォータ確認
    quota_mgr = GoogleQuotaManager(CACHE_DB_PATH)
    status = quota_mgr.get_status()
    print(f"今日のクォータ: {status.total_queries}/{status.quota_limit} (残り: {status.remaining})")
    print()

    conn = init_cache_db()

    # 上位10人を取得
    cursor = conn.execute("""
        SELECT person_id, person_name, fame_score_v3, multi_lang_pv, sitelinks
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
        ORDER BY fame_score_v3 DESC
        LIMIT 10
    """)
    persons = cursor.fetchall()

    print(f"テスト対象: {len(persons)}人")
    print()

    # 人物メタ情報を読み込み（曖昧性対策用）
    person_meta = load_person_meta()

    results = []
    for i, (pid, name, old_score, pv, sitelinks) in enumerate(persons, 1):
        start_time = time.time()

        # メタ情報取得（曖昧性対策: カテゴリ付加検索）
        meta = person_meta.get(pid, {})
        category = meta.get("category", "")
        person_type = meta.get("person_type", "REAL")

        print(f"{i}. {name} ({category})...")
        hits = get_search_hits(name, person_id=pid, category=category, person_type=person_type)
        elapsed_ms = int((time.time() - start_time) * 1000)

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

            # ログ記録
            quota_mgr.log_search(
                person_id=pid,
                query=name,
                google_hits=hits,
                status="success",
                processing_time_ms=elapsed_ms,
            )
        else:
            print("   Google: 取得失敗")
            quota_mgr.log_search(
                person_id=pid,
                query=name,
                google_hits=None,
                status="error",
                error_message="API call failed",
                processing_time_ms=elapsed_ms,
            )

        time.sleep(1.0)  # レート制限

    print()
    print("=== ドライラン完了 ===")
    print("本番実行: python scripts/update_fame_scores_phase2.py --execute")

    conn.close()


def run_execute(max_queries: int = 0, auto_mode: bool = False) -> int:
    """
    本番実行

    Args:
        max_queries: 最大クエリ数（0=クォータ上限まで）
        auto_mode: 自動実行モード（ログ出力を抑制）

    Returns:
        終了コード（0=正常、1=エラー）
    """
    if not auto_mode:
        print(f"\n{'='*60}")
        print("Phase 2 本番実行")
        print(f"{'='*60}\n")

    if not is_google_available() and not is_serpapi_available():
        if not auto_mode:
            print("ERROR: 検索API キーが設定されていません")
        return 1

    if not auto_mode:
        api_type = "SerpAPI" if is_serpapi_available() else "Google"
        print(f"使用API: {api_type}")

    # クォータマネージャー初期化
    quota_mgr = GoogleQuotaManager(CACHE_DB_PATH)
    status = quota_mgr.get_status()

    if not auto_mode:
        print(f"今日のクォータ: {status.total_queries}/{status.quota_limit} (残り: {status.remaining})")

    # 残りクエリがない場合
    if not quota_mgr.can_make_request():
        if not auto_mode:
            print("日次上限に到達しています。明日再実行してください。")
        return 0  # 自動モードでは正常終了扱い

    conn = init_cache_db()

    # Google検索未取得の人物を取得
    persons = get_persons_without_google_hits(conn)
    total_unsearched = len(persons)

    if not auto_mode:
        print(f"Google検索未取得: {total_unsearched}人")

    if not persons:
        if not auto_mode:
            print("全員取得済みです")
        quota_mgr.set_status(None, "completed")
        conn.close()
        return 0

    # 処理数を決定
    remaining_quota = quota_mgr.get_remaining_quota()
    if max_queries > 0:
        limit = min(max_queries, remaining_quota, len(persons))
    else:
        limit = min(remaining_quota, len(persons))

    persons = persons[:limit]

    if not auto_mode:
        print(f"処理対象: {len(persons)}人（クォータ残: {remaining_quota}）")
        print()

    # 人物メタ情報を読み込み（曖昧性対策用）
    person_meta = load_person_meta()

    # バッチ処理
    updated = 0
    errors = 0
    skipped = 0
    total_batches = (len(persons) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        # クォータ再確認
        if not quota_mgr.can_make_request():
            if not auto_mode:
                print("\n日次上限に到達しました。処理を中断します。")
            break

        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(persons))
        batch = persons[start_idx:end_idx]

        if not auto_mode:
            print(f"\nバッチ {batch_idx + 1}/{total_batches} ({start_idx + 1}-{end_idx}/{len(persons)})")

        for pid, name in batch:
            # クォータ再確認（バッチ内でも）
            if not quota_mgr.can_make_request():
                break

            # 短名スキップ（一般語汚染防止）
            if name in SKIP_SHORT_NAMES:
                if not auto_mode:
                    print(f"  ⊘ {name}: スキップ（短名）")
                skipped += 1
                continue

            start_time = time.time()

            # メタ情報取得（曖昧性対策: カテゴリ付加検索）
            meta = person_meta.get(pid, {})
            category = meta.get("category", "")
            person_type = meta.get("person_type", "REAL")

            # キャッシュ優先（既にgoogle_hitsがあればスキップ）
            hits = get_search_hits(name, person_id=pid, category=category, person_type=person_type)
            elapsed_ms = int((time.time() - start_time) * 1000)

            if hits is not None:
                updated += 1
                # クォータをインクリメント
                quota_mgr.increment_quota()
                # ログ記録
                quota_mgr.log_search(
                    person_id=pid,
                    query=name,
                    google_hits=hits,
                    status="success",
                    processing_time_ms=elapsed_ms,
                )
                if not auto_mode:
                    print(f"  ✓ {name}: {hits:,} hits")
            else:
                errors += 1
                # 統計情報からクォータ超過を検知
                stats = get_stats()
                if stats.get("quota_exceeded"):
                    quota_mgr.log_search(
                        person_id=pid,
                        query=name,
                        google_hits=None,
                        status="error",
                        error_message="HTTP 429: Quota exceeded",
                        processing_time_ms=elapsed_ms,
                    )
                    if not auto_mode:
                        print(f"  ✗ {name}: クォータ超過 (HTTP 429)")
                        print("\n⚠️ Google API日次クォータを超過しました。処理を中断します。")
                    break
                else:
                    quota_mgr.log_search(
                        person_id=pid,
                        query=name,
                        google_hits=None,
                        status="error",
                        error_message="API call failed",
                        processing_time_ms=elapsed_ms,
                    )
                    if not auto_mode:
                        print(f"  ✗ {name}: エラー")

        conn.commit()

        # クォータ超過フラグをチェック（外側ループの中断）
        stats = get_stats()
        if stats.get("quota_exceeded"):
            break

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

    if not auto_mode:
        print(f"\n取得完了: {updated}人 (エラー: {errors})")

    # 全スコアを再計算
    if not auto_mode:
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
    if not auto_mode:
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

    if not auto_mode:
        print(f"CSV保存: {MASTER_CSV_PATH}")

    # 進捗レポート
    final_status = quota_mgr.get_status()
    remaining_unsearched = conn.execute(
        "SELECT COUNT(*) FROM fame_cache WHERE google_hits IS NULL AND fame_score_v3 IS NOT NULL"
    ).fetchone()[0]

    estimated_days = (remaining_unsearched + 99) // 100  # 切り上げ

    report = {
        "timestamp": datetime.now().isoformat(),
        "date": final_status.date,
        "updated": updated,
        "errors": errors,
        "quota": {
            "used": final_status.total_queries,
            "remaining": final_status.remaining,
            "limit": final_status.quota_limit,
            "status": final_status.status,
        },
        "progress": {
            "total_with_google": conn.execute(
                "SELECT COUNT(*) FROM fame_cache WHERE google_hits IS NOT NULL"
            ).fetchone()[0],
            "remaining_unsearched": remaining_unsearched,
            "estimated_days_to_complete": estimated_days,
        },
    }

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"fame_phase2_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if not auto_mode:
        print(f"レポート: {report_path}")

    # サマリー表示
    if not auto_mode:
        print()
        print("=== 進捗サマリー ===")
        print(f"  今日の処理: {updated}件")
        print(f"  Google検索済み合計: {report['progress']['total_with_google']}人")
        print(f"  未検索残り: {remaining_unsearched}人")
        print(f"  完了予定: 約{estimated_days}日後")

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
    return 0


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
        help="ドライラン（上位10人のみテスト）",
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
        help="最大クエリ数（0=クォータ上限まで）",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自動実行モード（スケジューラ用、出力抑制）",
    )

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
        sys.exit(0)
    elif args.execute:
        exit_code = run_execute(max_queries=args.max_queries, auto_mode=args.auto)
        sys.exit(exit_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
