#!/usr/bin/env python3
"""
Episode Fame Score v2 計算スクリプト

感銘重視のエピソードランキングを生成
"""

import csv
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.score.episode_fame_v2 import (
    calculate_episode_fame_v2,
    rank_episodes,
)

# パス
CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
CACHE_DB = Path("data/cache/fame_score.db")
REPORT_DIR = Path("src/reports")


def get_celebrity_scores() -> dict:
    """fame_cacheからcelebrity_scoreを取得"""
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.execute("""
        SELECT person_id, fame_score_v3
        FROM fame_cache
        WHERE fame_score_v3 IS NOT NULL
    """)
    scores = {row[0]: row[1] for row in cursor}
    conn.close()
    return scores


def load_episodes() -> list:
    """CSVからエピソードを読み込み"""
    episodes = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def calculate_all_v2_scores(
    episodes: list, celebrity_scores: dict, verbose: bool = False, use_llm: bool = False
) -> list:
    """全エピソードのv2スコアを計算"""
    results = []

    for i, ep in enumerate(episodes):
        if verbose and i % 1000 == 0:
            print(f"  処理中: {i}/{len(episodes)}")

        person_id = ep.get("person_id", "")
        text = ep.get("episode_text", "") or ""

        # LLMスコア取得（正しいカラム名を使用）
        llm_scores = {
            "memorability": float(ep.get("llm_memorability_score") or 0),
            "story_quality": float(ep.get("llm_story_quality") or 0),
            "factual_density": float(ep.get("llm_factual_density") or 0),
            "educational_value": float(ep.get("llm_educational_value") or 0),
            "empathy": float(ep.get("llm_empathy_score") or 0),
        }

        # 人物知名度
        celebrity_score = celebrity_scores.get(person_id, 0)

        # 年齢情報
        try:
            episode_age = int(ep.get("age") or 0)
        except (ValueError, TypeError):
            episode_age = None

        try:
            birth_year = int(ep.get("birth_year") or 0)
        except (ValueError, TypeError):
            birth_year = None

        try:
            death_year = int(ep.get("death_year") or 0) if ep.get("death_year") else None
        except (ValueError, TypeError):
            death_year = None

        # v2スコア計算
        v2_result = calculate_episode_fame_v2(
            text=text,
            llm_scores=llm_scores,
            celebrity_score=celebrity_score,
            episode_age=episode_age,
            birth_year=birth_year,
            death_year=death_year,
            person_name=ep.get("person_name", ""),
            category=ep.get("category", ""),
            use_llm_inspiration=use_llm,
        )

        # 結果をエピソードに追加
        ep["episode_fame_v2"] = v2_result["total"]
        ep["episode_fame_tier_v2"] = v2_result["tier"]
        ep["v2_inspiration"] = v2_result["components"]["inspiration"]
        ep["v2_quality"] = v2_result["components"]["quality"]
        ep["v2_historical"] = v2_result["components"]["historical"]
        ep["v2_person_fame"] = v2_result["components"]["person_fame"]
        ep["v2_exclude"] = v2_result["exclude"]
        ep["v2_details"] = v2_result["details"]

        results.append(ep)

    return results


def generate_top100_comparison(episodes: list) -> dict:
    """Top100のv1/v2比較を生成"""
    # v2でランキング
    ranked = rank_episodes(episodes, apply_bias=True)

    # v1でソート
    v1_sorted = sorted(
        [ep for ep in episodes if not ep.get("v2_exclude", False)],
        key=lambda x: float(x.get("episode_fame_score_v4") or 0),
        reverse=True,
    )

    # v2 Top100（bias_excluded除外）
    v2_top100 = [ep for ep in ranked if ep.get("rank_v2") is not None][:100]

    # v1 Top100
    v1_top100 = v1_sorted[:100]

    # 人物別カウント（v2）
    v2_person_counts = {}
    for ep in v2_top100:
        pname = ep.get("person_name", "Unknown")
        v2_person_counts[pname] = v2_person_counts.get(pname, 0) + 1

    # 人物別カウント（v1）
    v1_person_counts = {}
    for ep in v1_top100:
        pname = ep.get("person_name", "Unknown")
        v1_person_counts[pname] = v1_person_counts.get(pname, 0) + 1

    return {
        "v2_top100": [
            {
                "rank": i + 1,
                "person_name": ep.get("person_name", ""),
                "age": ep.get("age", ""),
                "episode_fame_v2": ep.get("episode_fame_v2", 0),
                "tier_v2": ep.get("episode_fame_tier_v2", 0),
                "inspiration": ep.get("v2_inspiration", 0),
                "quality": ep.get("v2_quality", 0),
                "historical": ep.get("v2_historical", 0),
                "person_fame": ep.get("v2_person_fame", 0),
                "episode_summary": (ep.get("episode_text", "") or "")[:100] + "...",
            }
            for i, ep in enumerate(v2_top100)
        ],
        "v1_top100": [
            {
                "rank": i + 1,
                "person_name": ep.get("person_name", ""),
                "age": ep.get("age", ""),
                "episode_fame_v4": float(ep.get("episode_fame_score_v4") or 0),
                "tier_v4": ep.get("episode_fame_tier_v4", ""),
                "episode_summary": (ep.get("episode_text", "") or "")[:100] + "...",
            }
            for i, ep in enumerate(v1_top100)
        ],
        "v2_person_distribution": dict(sorted(v2_person_counts.items(), key=lambda x: -x[1])[:20]),
        "v1_person_distribution": dict(sorted(v1_person_counts.items(), key=lambda x: -x[1])[:20]),
        "v2_unique_persons": len(v2_person_counts),
        "v1_unique_persons": len(v1_person_counts),
    }


def check_reference_ranking_match(episodes: list, reference_persons: list) -> dict:
    """参考ランキングとの一致をチェック"""
    # v2 Top100の人物リスト
    ranked = rank_episodes(episodes, apply_bias=True)
    v2_top100 = [ep for ep in ranked if ep.get("rank_v2") is not None][:100]
    v2_top100_persons = {ep.get("person_name", ""): ep.get("rank_v2") for ep in v2_top100}

    # 参考ランキングの人物との一致（短縮名でも一致するように）
    matches = []
    misses = []

    # 参考人物の短縮名マッピング
    short_names = {
        "ネルソン・マンデラ": ["マンデラ"],
        "マララ・ユスフザイ": ["マララ"],
        "ベートーヴェン": ["ベートーヴェン", "ベートーベン"],
        "マルティン・ルター・キング": ["キング牧師", "キング・ジュニア", "キング"],
        "マハトマ・ガンディー": ["ガンディー", "ガンジー"],
        "ローザ・パークス": ["パークス"],
        "マザー・テレサ": ["テレサ"],
        "フリーダ・カーロ": ["カーロ", "カロ"],
        "マリー・キュリー": ["キュリー"],
        "アインシュタイン": ["アインシュタイン"],
        "アブラハム・リンカーン": ["リンカーン"],
        "山中伸弥": ["山中伸弥", "山中"],
        "大谷翔平": ["大谷翔平", "大谷"],
        "羽生結弦": ["羽生結弦", "羽生"],
        "大坂なおみ": ["大坂なおみ", "大坂"],
        "ペレ": ["ペレ"],
        "ダーウィン": ["ダーウィン"],
        "宮崎駿": ["宮崎駿", "宮崎"],
        "グレタ・トゥーンベリ": ["グレタ", "トゥーンベリ"],
        "アラン・チューリング": ["チューリング"],
    }

    for ref_person in reference_persons:
        found = False
        search_names = short_names.get(ref_person, [ref_person])

        for v2_person, rank in v2_top100_persons.items():
            for search_name in search_names:
                if search_name in v2_person:
                    matches.append({"reference": ref_person, "matched": v2_person, "rank": rank})
                    found = True
                    break
            if found:
                break

        if not found:
            misses.append(ref_person)

    return {
        "total_reference": len(reference_persons),
        "matched": len(matches),
        "missed": len(misses),
        "match_rate": len(matches) / len(reference_persons) * 100 if reference_persons else 0,
        "matches": sorted(matches, key=lambda x: x.get("rank", 999)),
        "misses": misses,
    }


def main(dry_run: bool = True, verbose: bool = True, use_llm: bool = False):
    """メイン処理"""
    print("=== Episode Fame Score v2 計算 ===")
    mode_str = "ドライラン" if dry_run else "本番適用"
    llm_str = " (LLM評価)" if use_llm else ""
    print(f"実行モード: {mode_str}{llm_str}")
    print()

    # データ読み込み
    print("1. データ読み込み中...")
    episodes = load_episodes()
    celebrity_scores = get_celebrity_scores()
    print(f"   エピソード数: {len(episodes)}")
    print(f"   知名度スコア数: {len(celebrity_scores)}")
    print()

    # v2スコア計算
    print("2. v2スコア計算中...")
    results = calculate_all_v2_scores(episodes, celebrity_scores, verbose=verbose, use_llm=use_llm)
    print(f"   計算完了: {len(results)}件")
    print()

    # Top100比較
    print("3. Top100比較生成中...")
    comparison = generate_top100_comparison(results)
    print(f"   v2 Top100 ユニーク人物数: {comparison['v2_unique_persons']}")
    print(f"   v1 Top100 ユニーク人物数: {comparison['v1_unique_persons']}")
    print()

    # 参考ランキングとの照合
    print("4. 参考ランキングとの照合...")
    reference_persons = [
        "ネルソン・マンデラ",
        "マララ・ユスフザイ",
        "ベートーヴェン",
        "マルティン・ルター・キング",
        "マハトマ・ガンディー",
        "ローザ・パークス",
        "マザー・テレサ",
        "フリーダ・カーロ",
        "マリー・キュリー",
        "宮崎駿",
        "大谷翔平",
        "グレタ・トゥーンベリ",
        "アインシュタイン",
        "アラン・チューリング",
        "アブラハム・リンカーン",
        "ダーウィン",
        "山中伸弥",
        "羽生結弦",
        "大坂なおみ",
        "ペレ",
    ]
    ref_match = check_reference_ranking_match(results, reference_persons)
    print(f"   一致率: {ref_match['match_rate']:.1f}% ({ref_match['matched']}/{ref_match['total_reference']})")
    print()

    # v2 Top20 表示
    print("5. v2 Top20:")
    for item in comparison["v2_top100"][:20]:
        print(
            f"   {item['rank']:>2}. {item['person_name'][:12]:<12} "
            f"({item['age']}歳) v2={item['episode_fame_v2']:.1f} "
            f"T{item['tier_v2']} | "
            f"感={item['inspiration']:.0f} 質={item['quality']:.0f} "
            f"歴={item['historical']:.0f} 名={item['person_fame']:.0f}"
        )
    print()

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"episode_fame_v2_dryrun_{timestamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run" if dry_run else "apply",
        "stats": {
            "total_episodes": len(results),
            "excluded": sum(1 for r in results if r.get("v2_exclude", False)),
        },
        "comparison": {
            "v2_top20": comparison["v2_top100"][:20],
            "v1_top20": comparison["v1_top100"][:20],
            "v2_person_distribution": comparison["v2_person_distribution"],
            "v1_person_distribution": comparison["v1_person_distribution"],
        },
        "reference_match": ref_match,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"レポート保存: {report_path}")

    if not dry_run:
        print()
        print("6. CSVに書き出し中...")

        # v2スコアをdictに変換
        v2_scores = {}
        for ep in results:
            ep_id = ep.get("episode_id", "")
            if ep_id:
                v2_scores[ep_id] = {
                    "episode_fame_v2": ep.get("episode_fame_v2", 0),
                    "episode_fame_tier_v2": ep.get("episode_fame_tier_v2", 1),
                }

        # CSVを読み込んでv2カラムを追加
        output_rows = []
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)

            # 新規カラムを追加（なければ）
            new_cols = ["episode_fame_v2", "episode_fame_tier_v2"]
            for col in new_cols:
                if col not in fieldnames:
                    fieldnames.append(col)

            # データ更新
            for row in reader:
                ep_id = row.get("episode_id", "")
                if ep_id in v2_scores:
                    row["episode_fame_v2"] = v2_scores[ep_id]["episode_fame_v2"]
                    row["episode_fame_tier_v2"] = v2_scores[ep_id]["episode_fame_tier_v2"]
                output_rows.append(row)

        # CSVに書き出し
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        print(f"   完了: {len(output_rows)}件更新")
        print(f"   追加カラム: {new_cols}")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Episode Fame Score v2 計算")
    parser.add_argument("--apply", action="store_true", help="本番適用（CSVに書き出し）")
    parser.add_argument("--use-llm", action="store_true", help="LLM直接評価を使用（v2.4）")
    parser.add_argument("--quiet", action="store_true", help="詳細表示を抑制")
    args = parser.parse_args()

    main(dry_run=not args.apply, verbose=not args.quiet, use_llm=args.use_llm)
