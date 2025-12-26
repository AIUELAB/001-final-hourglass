#!/usr/bin/env python3
"""
Celebrity Score v2 算出パイプライン

使用方法:
    # ドライラン（Top100のみ表示、保存なし）
    python scripts/update_celebrity_score_v2.py --dry-run

    # 本番実行（全人物を計算・保存）
    python scripts/update_celebrity_score_v2.py --execute

    # 特定人物のみ（デバッグ用）
    python scripts/update_celebrity_score_v2.py --person-id P12345678
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.scorer_v2 import (
    CelebritySignals,
    assign_ranks_v2,
    calculate_celebrity_score_v2,
)
from scripts.fame_score_v3.pv_history import detect_japan_buzz

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
CACHE_DB_PATH = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports")


def ensure_v2_columns(conn: sqlite3.Connection) -> None:
    """v2カラムが存在しなければ追加"""
    cursor = conn.execute("PRAGMA table_info(fame_cache)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("celebrity_score_v2", "REAL"),
        ("celebrity_rank_v2", "INTEGER"),
        ("v2_confidence", "REAL"),
        ("v2_updated_at", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            conn.execute(f"ALTER TABLE fame_cache ADD COLUMN {col_name} {col_type}")
            print(f"  カラム追加: {col_name}")

    conn.commit()


def load_episode_counts() -> dict[str, int]:
    """CSVからperson_idごとのエピソード数を集計"""
    if not MASTER_CSV_PATH.exists():
        return {}

    df = pd.read_csv(MASTER_CSV_PATH, usecols=["person_id"], low_memory=False)
    counts = df["person_id"].value_counts().to_dict()
    return counts


def load_person_categories() -> dict[str, str]:
    """CSVからperson_idごとのカテゴリを取得"""
    if not MASTER_CSV_PATH.exists():
        return {}

    df = pd.read_csv(
        MASTER_CSV_PATH,
        usecols=["person_id", "category"],
        low_memory=False,
    )
    # 重複を除去（最初のカテゴリを使用）
    df = df.drop_duplicates(subset=["person_id"], keep="first")
    return dict(zip(df["person_id"], df["category"]))


def load_llm_quality_scores() -> dict[str, float]:
    """CSVからperson_idごとのLLM品質スコアを集計（平均）"""
    if not MASTER_CSV_PATH.exists():
        return {}

    # LLM品質関連カラムを読み込み
    quality_cols = [
        "person_id",
        "llm_generation_quality_score",
        "llm_memorability_score",
        "impressiveness_score",
    ]

    try:
        df = pd.read_csv(MASTER_CSV_PATH, usecols=quality_cols, low_memory=False)
    except ValueError:
        # カラムがない場合は空を返す
        return {}

    # 数値変換
    for col in quality_cols[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 人物ごとの平均を計算
    grouped = df.groupby("person_id")[quality_cols[1:]].mean()

    # 全カラムの平均を取ってLLM品質スコアとする
    result = {}
    for person_id, row in grouped.iterrows():
        values = [v for v in row.values if pd.notna(v)]
        if values:
            result[person_id] = sum(values) / len(values)
        else:
            result[person_id] = 0.0

    return result


def load_japanese_info() -> tuple[dict[str, bool], dict[str, float]]:
    """CSVからperson_idごとの日本人フラグとfame_score_japanを取得"""
    if not MASTER_CSV_PATH.exists():
        return {}, {}

    try:
        df = pd.read_csv(
            MASTER_CSV_PATH,
            usecols=["person_id", "is_japanese", "fame_score_japan"],
            low_memory=False,
        )
    except ValueError:
        # カラムがない場合は空を返す
        return {}, {}

    # 重複を除去
    df = df.drop_duplicates(subset=["person_id"], keep="first")

    # is_japaneseをboolに変換
    is_japanese_map = {}
    for _, row in df.iterrows():
        pid = row["person_id"]
        val = row.get("is_japanese", False)
        is_japanese_map[pid] = val is True or val == "True" or val == "TRUE"

    # fame_score_japanを数値に変換
    fame_japan_map = {}
    for _, row in df.iterrows():
        pid = row["person_id"]
        val = row.get("fame_score_japan", 0)
        try:
            fame_japan_map[pid] = float(val) if pd.notna(val) else 0.0
        except (ValueError, TypeError):
            fame_japan_map[pid] = 0.0

    return is_japanese_map, fame_japan_map


def load_ja_pv_from_db(conn: sqlite3.Connection) -> dict[str, int]:
    """DBからperson_idごとの日本語PVを取得"""
    cursor = conn.execute("SELECT person_id, pv_by_lang FROM fame_cache")
    ja_pv_map = {}

    for person_id, pv_by_lang in cursor.fetchall():
        if not pv_by_lang:
            ja_pv_map[person_id] = 0
            continue

        try:
            # JSON多重エスケープ対応（最大10回）
            pv_data = pv_by_lang
            for _ in range(10):
                if isinstance(pv_data, str):
                    pv_data = json.loads(pv_data)
                else:
                    break

            if isinstance(pv_data, dict):
                ja_pv_map[person_id] = pv_data.get("ja", 0) or 0
            else:
                ja_pv_map[person_id] = 0
        except (json.JSONDecodeError, TypeError, ValueError):
            ja_pv_map[person_id] = 0

    return ja_pv_map


def run_dry_run(limit: int = 100) -> None:
    """ドライラン（Top100のみ表示）"""
    print(f"\n{'='*60}")
    print("Celebrity Score v2 ドライラン")
    print(f"{'='*60}\n")

    if not CACHE_DB_PATH.exists():
        print("ERROR: キャッシュDBが見つかりません")
        return

    # データ読み込み
    print("データ読み込み中...")
    episode_counts = load_episode_counts()
    categories = load_person_categories()
    llm_quality_scores = load_llm_quality_scores()
    is_japanese_map, fame_japan_map = load_japanese_info()
    print(f"  エピソード数: {len(episode_counts)}人")
    print(f"  カテゴリ: {len(categories)}人")
    print(f"  LLM品質: {len(llm_quality_scores)}人")
    print(f"  日本人: {sum(is_japanese_map.values())}人")

    conn = sqlite3.connect(str(CACHE_DB_PATH))

    # 日本語PV読み込み
    print("日本語PV読み込み中...")
    ja_pv_map = load_ja_pv_from_db(conn)
    print(f"  日本語PV: {len(ja_pv_map)}人")

    # バズ検出（日本語版PV比率が異常に高い人物）
    print("バズ検出中...")
    buzz_adjustments, buzz_details = detect_japan_buzz(conn)
    print(f"  バズ検出: {len(buzz_details)}人")
    for b in buzz_details:
        print(f"    - {b['person_name']}: 補正係数 {b['adjustment']:.2f}")

    # 全人物のシグナルを取得
    cursor = conn.execute("""
        SELECT person_id, person_name, multi_lang_pv, sitelinks, inlinks, google_hits
        FROM fame_cache
        ORDER BY fame_score_v3 DESC
    """)
    rows = cursor.fetchall()
    print(f"  人物数: {len(rows)}人")
    print()

    # スコア計算
    print("スコア計算中...")
    all_scores = []
    details = []

    for row in rows:
        person_id, person_name, pv, sitelinks, inlinks, google_hits = row

        signals = CelebritySignals(
            multi_lang_pv=pv or 0,
            sitelinks=sitelinks or 0,
            inlinks=inlinks or 0,
            google_hits=google_hits,
            episode_count=episode_counts.get(person_id, 1),
            llm_quality=llm_quality_scores.get(person_id, 0.0),
            category=categories.get(person_id, ""),
            disambiguation_confidence=1.0,  # TODO: 曖昧性解決結果を連携
            is_japanese=is_japanese_map.get(person_id, False),
            fame_score_japan=fame_japan_map.get(person_id, 0.0),
            ja_pv=ja_pv_map.get(person_id, 0),
            buzz_adjustment=buzz_adjustments.get(person_id, 1.0),
            person_name=person_name,  # 政治家・天皇判定用
        )

        result = calculate_celebrity_score_v2(signals, person_id)
        all_scores.append((person_id, result.score))

        details.append(
            {
                "person_id": person_id,
                "person_name": person_name,
                "score": result.score,
                "raw_score": result.raw_score,
                "category": signals.category,
                "episode_count": signals.episode_count,
                "category_cap_applied": result.category_cap_applied,
                "japan_pv_bonus_applied": result.japan_pv_bonus_applied,
                "buzz_adjustment_applied": result.buzz_adjustment_applied,
                "is_japanese": signals.is_japanese,
            }
        )

    # 順位計算
    ranks = assign_ranks_v2(all_scores)

    # Top100を表示
    print(f"\n=== Celebrity Score v2 Top {min(limit, len(details))} ===\n")

    sorted_details = sorted(details, key=lambda x: x["score"], reverse=True)[:limit]

    for i, d in enumerate(sorted_details, 1):
        cap_mark = " [CAP]" if d["category_cap_applied"] else ""
        jp_mark = " 🇯🇵" if d.get("is_japanese") else ""
        bonus_mark = " [JP+]" if d.get("japan_pv_bonus_applied") else ""
        buzz_mark = " [BUZZ]" if d.get("buzz_adjustment_applied") else ""
        print(
            f"{i:3d}. {d['person_name'][:15]:<15s} "
            f"スコア:{d['score']:6.1f} "
            f"カテゴリ:{d['category'][:8]:<8s} "
            f"EP:{d['episode_count']:2d}{cap_mark}{jp_mark}{bonus_mark}{buzz_mark}"
        )

    # カテゴリ分布
    print("\n=== カテゴリ分布（Top100） ===")
    category_counts = {}
    for d in sorted_details:
        cat = d["category"] or "(未分類)"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}人")

    # 政治家占有率
    politics_count = category_counts.get("政治・社会", 0)
    print(f"\n政治家占有率: {politics_count}% (目標: 20%以下)")

    # 日本人占有率
    jp_count = sum(1 for d in sorted_details if d.get("is_japanese"))
    jp_bonus_count = sum(1 for d in sorted_details if d.get("japan_pv_bonus_applied"))
    print(f"日本人: {jp_count}人 (うち{jp_bonus_count}人がJP PVボーナス適用)")

    conn.close()

    print("\n本番実行: python scripts/update_celebrity_score_v2.py --execute")


def run_execute() -> int:
    """本番実行（全人物を計算・保存）"""
    print(f"\n{'='*60}")
    print("Celebrity Score v2 本番実行")
    print(f"{'='*60}\n")

    if not CACHE_DB_PATH.exists():
        print("ERROR: キャッシュDBが見つかりません")
        return 1

    # データ読み込み
    print("データ読み込み中...")
    episode_counts = load_episode_counts()
    categories = load_person_categories()
    llm_quality_scores = load_llm_quality_scores()
    is_japanese_map, fame_japan_map = load_japanese_info()
    print(f"  日本人: {sum(is_japanese_map.values())}人")

    conn = sqlite3.connect(str(CACHE_DB_PATH))

    # v2カラム追加
    print("スキーマ確認...")
    ensure_v2_columns(conn)

    # 日本語PV読み込み
    print("日本語PV読み込み中...")
    ja_pv_map = load_ja_pv_from_db(conn)
    print(f"  日本語PV: {len(ja_pv_map)}人")

    # バズ検出（日本語版PV比率が異常に高い人物）
    print("バズ検出中...")
    buzz_adjustments, buzz_details = detect_japan_buzz(conn)
    print(f"  バズ検出: {len(buzz_details)}人")
    for b in buzz_details:
        print(f"    - {b['person_name']}: 補正係数 {b['adjustment']:.2f}")

    # 全人物のシグナルを取得
    cursor = conn.execute("""
        SELECT person_id, person_name, multi_lang_pv, sitelinks, inlinks, google_hits
        FROM fame_cache
    """)
    rows = cursor.fetchall()
    print(f"  対象人物: {len(rows)}人")

    # スコア計算
    print("\nスコア計算中...")
    all_scores = []
    japan_pv_bonus_count = 0
    buzz_adjustment_count = 0
    now = datetime.now().isoformat()

    for row in rows:
        person_id, person_name, pv, sitelinks, inlinks, google_hits = row

        signals = CelebritySignals(
            multi_lang_pv=pv or 0,
            sitelinks=sitelinks or 0,
            inlinks=inlinks or 0,
            google_hits=google_hits,
            episode_count=episode_counts.get(person_id, 1),
            llm_quality=llm_quality_scores.get(person_id, 0.0),
            category=categories.get(person_id, ""),
            disambiguation_confidence=1.0,
            is_japanese=is_japanese_map.get(person_id, False),
            fame_score_japan=fame_japan_map.get(person_id, 0.0),
            ja_pv=ja_pv_map.get(person_id, 0),
            buzz_adjustment=buzz_adjustments.get(person_id, 1.0),
            person_name=person_name,  # 政治家・天皇判定用
        )

        result = calculate_celebrity_score_v2(signals, person_id)
        all_scores.append((person_id, result.score))
        if result.japan_pv_bonus_applied:
            japan_pv_bonus_count += 1
        if result.buzz_adjustment_applied:
            buzz_adjustment_count += 1

        # DB更新
        conn.execute(
            """
            UPDATE fame_cache
            SET celebrity_score_v2 = ?, v2_confidence = ?, v2_updated_at = ?
            WHERE person_id = ?
            """,
            (result.score, signals.disambiguation_confidence, now, person_id),
        )

    # 順位計算・更新
    print("順位計算中...")
    ranks = assign_ranks_v2(all_scores)

    for person_id, rank in ranks.items():
        conn.execute(
            "UPDATE fame_cache SET celebrity_rank_v2 = ? WHERE person_id = ?",
            (rank, person_id),
        )

    conn.commit()
    print(f"  DB更新完了: {len(all_scores)}人")

    # CSV更新
    print("\nCSV更新中...")
    df = pd.read_csv(MASTER_CSV_PATH, low_memory=False)

    # カラム追加
    if "celebrity_score_v2" not in df.columns:
        df["celebrity_score_v2"] = None
    if "celebrity_rank_v2" not in df.columns:
        df["celebrity_rank_v2"] = None

    # DBからスコア・順位を取得してCSVに反映
    cursor = conn.execute("""
        SELECT person_id, celebrity_score_v2, celebrity_rank_v2
        FROM fame_cache
    """)

    for row in cursor.fetchall():
        person_id, score, rank = row
        mask = df["person_id"] == person_id
        df.loc[mask, "celebrity_score_v2"] = score
        df.loc[mask, "celebrity_rank_v2"] = rank

    df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  CSV保存: {MASTER_CSV_PATH}")

    # レポート出力
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"celebrity_score_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Top100抽出
    cursor = conn.execute("""
        SELECT person_name, celebrity_score_v2, celebrity_rank_v2
        FROM fame_cache
        ORDER BY celebrity_score_v2 DESC
        LIMIT 100
    """)
    top100 = [{"name": r[0], "score": r[1], "rank": r[2]} for r in cursor.fetchall()]

    report = {
        "timestamp": now,
        "total_persons": len(all_scores),
        "japan_pv_bonus_count": japan_pv_bonus_count,
        "buzz_adjustment_count": buzz_adjustment_count,
        "buzz_targets": [b["person_name"] for b in buzz_details],
        "top100": top100,
        "stats": {
            "max_score": max(s[1] for s in all_scores),
            "min_score": min(s[1] for s in all_scores),
            "avg_score": sum(s[1] for s in all_scores) / len(all_scores),
        },
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  レポート: {report_path}")

    conn.close()

    print("\n=== 完了 ===")
    print(f"  計算人物数: {len(all_scores)}")
    print(f"  JP PVボーナス適用: {japan_pv_bonus_count}人")
    print(f"  バズ補正適用: {buzz_adjustment_count}人")
    print(f"  最高スコア: {report['stats']['max_score']:.2f}")
    print(f"  平均スコア: {report['stats']['avg_score']:.2f}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Celebrity Score v2 算出")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（Top100のみ）")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    parser.add_argument("--limit", type=int, default=100, help="ドライラン時の表示件数")

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run(args.limit)
    elif args.execute:
        sys.exit(run_execute())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
