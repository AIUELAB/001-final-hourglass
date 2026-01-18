#!/usr/bin/env python3
"""
91歳以上エピソード生成スクリプト

91-100歳のエピソードを重点的に生成する
"""

import os
import sys
import random
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.episode_generation_bridge import EpisodeGenerationBridge

TEMPLATE_PATH = Path(__file__).parent.parent / "config/person_sources/senior_91plus_batch1.csv"
MASTER_PATH = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "generated/senior_91plus_episodes.csv"
CURRENT_YEAR = 2025


def load_candidates(min_age: int = 91, max_age: int = 100) -> list[dict]:
    """91歳以上の候補を読み込む"""
    df = pd.read_csv(TEMPLATE_PATH, encoding="utf-8-sig")
    candidates = []

    for _, row in df.iterrows():
        person_name = str(row["person_name"])
        birth_year = row.get("birth_year")
        death_year = row.get("death_year")

        if pd.isna(birth_year):
            continue

        birth_year = int(birth_year)

        # 最大到達年齢を計算
        if pd.notna(death_year):
            max_lived_age = int(death_year) - birth_year
        else:
            max_lived_age = CURRENT_YEAR - birth_year

        # 91歳以上に到達可能か
        if max_lived_age < min_age:
            continue

        # 有効な年齢範囲
        valid_ages = [a for a in range(min_age, min(max_age, max_lived_age) + 1)]
        if not valid_ages:
            continue

        candidates.append(
            {
                "person_name": person_name,
                "category": str(row.get("category", "その他")),
                "person_type": str(row.get("person_type", "REAL")),
                "birth_year": birth_year,
                "death_year": int(death_year) if pd.notna(death_year) else None,
                "valid_ages": valid_ages,
                "tier": str(row.get("tier", "A")),
            }
        )

    return candidates


def generate_episodes(candidates: list[dict], limit: int = 50) -> list[dict]:
    """エピソードを生成"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    bridge = EpisodeGenerationBridge(api_key=api_key)
    episodes = []

    # 候補をシャッフル
    random.shuffle(candidates)

    for i, candidate in enumerate(candidates):
        if len(episodes) >= limit:
            break

        person_name = candidate["person_name"]
        valid_ages = candidate["valid_ages"]

        # ランダムに年齢を選択
        selected_age = random.choice(valid_ages)

        print(f"\n[{i+1}/{min(limit, len(candidates))}] {person_name} ({selected_age}歳)")

        try:
            person_data = {
                "person_name": person_name,
                "category": candidate["category"],
                "person_type": candidate["person_type"],
                "birth_year": candidate["birth_year"],
                "death_year": candidate["death_year"],
            }

            result = bridge.generate_for_person(person_data, episodes_count=1)

            if result:
                ep = result[0]
                ep["age"] = selected_age
                ep["tier"] = candidate["tier"]
                episodes.append(ep)
                print(f"   ✅ {len(ep.get('episode_text', ''))}字")
            else:
                print("   ❌ 生成失敗")

        except Exception as e:
            print(f"   ❌ エラー: {e}")

    return episodes


def save_episodes(episodes: list[dict]):
    """エピソードをCSVに保存"""
    if not episodes:
        print("❌ 保存するエピソードがありません")
        return

    df = pd.DataFrame(episodes)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n✅ {len(episodes)}件のエピソードを保存: {OUTPUT_PATH}")


def integrate_to_master(episodes: list[dict]):
    """マスターCSVに統合"""
    if not episodes:
        return

    master_df = pd.read_csv(MASTER_PATH, encoding="utf-8-sig")
    episodes_df = pd.DataFrame(episodes)

    # 必要なカラムを追加
    timestamp = datetime.now().isoformat()
    episodes_df["generation_timestamp"] = timestamp

    # マスターにないカラムは追加
    for col in master_df.columns:
        if col not in episodes_df.columns:
            episodes_df[col] = ""

    # 統合
    combined = pd.concat([master_df, episodes_df[master_df.columns]], ignore_index=True)
    combined.to_csv(MASTER_PATH, index=False, encoding="utf-8-sig")

    print(f"✅ マスターCSVに統合完了: {len(master_df)} → {len(combined)} (+{len(episodes)})")


def main():
    parser = argparse.ArgumentParser(description="91歳以上エピソード生成")
    parser.add_argument("--limit", type=int, default=50, help="生成件数")
    parser.add_argument("--min-age", type=int, default=91, help="最小年齢")
    parser.add_argument("--max-age", type=int, default=100, help="最大年齢")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    print("=" * 60)
    print("🎯 91歳以上エピソード生成")
    print("=" * 60)
    print(f"  年齢範囲: {args.min_age}-{args.max_age}歳")
    print(f"  生成件数: {args.limit}")
    print(f"  モード: {'本番実行' if args.execute else 'ドライラン'}")
    print()

    # 候補を読み込み
    candidates = load_candidates(min_age=args.min_age, max_age=args.max_age)
    print(f"📋 候補数: {len(candidates)}名")

    if not candidates:
        print("❌ 候補がいません")
        return

    for c in candidates[:10]:
        print(f"   - {c['person_name']} (有効年齢: {min(c['valid_ages'])}-{max(c['valid_ages'])}歳)")

    if args.dry_run or not args.execute:
        print("\n⚠️ ドライランモード - 実際の生成は行いません")
        return

    # エピソード生成
    episodes = generate_episodes(candidates, limit=args.limit)

    print(f"\n📊 生成結果: {len(episodes)}件")

    if episodes:
        # 保存
        save_episodes(episodes)

        # マスターに統合
        integrate_to_master(episodes)


if __name__ == "__main__":
    main()
