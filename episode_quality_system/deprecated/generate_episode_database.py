#!/usr/bin/env python3
"""
エピソードデータベース生成スクリプト
person_facts.jsonの全人物に対してエピソードを生成し、CSVに出力
"""

import csv
import json
import time
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent))
from episode_factory import EpisodeFactory, EpisodeRequest


def generate_episode_database():
    """エピソードデータベースを生成"""

    # EpisodeFactory初期化
    factory = EpisodeFactory()

    # person_facts.jsonを読み込み
    facts_path = Path(__file__).parent / "data" / "person_facts.json"
    with open(facts_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        persons = data.get("persons", {})

    # エピソードデータベース
    episode_database = []

    # 各年齢でエピソード生成（25, 30, 35, 40歳）
    ages = [25, 30, 35, 40]

    print(f"エピソード生成開始: {len(persons)}人 × {len(ages)}年齢 = {len(persons) * len(ages)}エピソード")
    print("="*60)

    total_episodes = 0
    success_count = 0
    total_score = 0

    for person_name, person_data in persons.items():
        category = person_data.get("category", "unknown")

        for age in ages:
            # エピソード生成リクエスト
            request = EpisodeRequest(
                person_name=person_name,
                age=age,
                category=category
            )

            # エピソード生成
            try:
                response = factory.generate_episode(request)

                # データベースに追加
                episode_database.append({
                    "person_id": f"{person_name}_{age}",
                    "person_name": person_name,
                    "age": age,
                    "category": category,
                    "episode": response.episode,
                    "character_count": len(response.episode),
                    "quality_score": response.quality_score,
                    "quality_level": response.quality_level,
                    "generation_time": round(response.generation_time, 3),
                    "template_check": "PASS" if response.final_validation["checks"]["template_blocker"]["passed"] else "FAIL",
                    "realtime_check": "PASS" if response.final_validation["checks"]["realtime_validator"]["passed"] else "FAIL",
                    "has_facts": "あり" if any(char.isdigit() for char in response.episode) else "なし",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                total_episodes += 1
                total_score += response.quality_score
                if response.quality_score >= 70:
                    success_count += 1

                # 進捗表示
                if total_episodes % 10 == 0:
                    print(f"進捗: {total_episodes}/{len(persons) * len(ages)} エピソード生成完了")

            except Exception as e:
                print(f"エラー: {person_name} ({age}歳) - {e}")
                # エラーの場合もデータベースに記録
                episode_database.append({
                    "person_id": f"{person_name}_{age}",
                    "person_name": person_name,
                    "age": age,
                    "category": category,
                    "episode": "生成エラー",
                    "character_count": 0,
                    "quality_score": 0,
                    "quality_level": "error",
                    "generation_time": 0,
                    "template_check": "ERROR",
                    "realtime_check": "ERROR",
                    "has_facts": "エラー",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                total_episodes += 1

    # CSVに出力（UTF-8 BOM付き）
    output_path = Path(__file__).parent / f"episode_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
        if episode_database:
            fieldnames = episode_database[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(episode_database)

    print("\n" + "="*60)
    print("エピソードデータベース生成完了")
    print(f"出力ファイル: {output_path}")
    print(f"総エピソード数: {total_episodes}")
    print(f"成功数: {success_count} ({success_count/total_episodes*100:.1f}%)")
    print(f"平均品質スコア: {total_score/total_episodes:.1f}")

    # サマリーCSVも生成
    summary_data = []

    # カテゴリ別統計
    categories = {}
    for episode in episode_database:
        cat = episode["category"]
        if cat not in categories:
            categories[cat] = {
                "count": 0,
                "total_score": 0,
                "success": 0,
                "total_chars": 0
            }
        categories[cat]["count"] += 1
        categories[cat]["total_score"] += episode["quality_score"]
        if episode["quality_score"] >= 70:
            categories[cat]["success"] += 1
        categories[cat]["total_chars"] += episode["character_count"]

    for cat, stats in categories.items():
        summary_data.append({
            "カテゴリ": cat,
            "エピソード数": stats["count"],
            "平均スコア": round(stats["total_score"] / stats["count"], 1) if stats["count"] > 0 else 0,
            "成功率": f"{stats['success']/stats['count']*100:.1f}%" if stats["count"] > 0 else "0%",
            "平均文字数": round(stats["total_chars"] / stats["count"], 1) if stats["count"] > 0 else 0
        })

    # サマリーCSV出力
    summary_path = Path(__file__).parent / f"episode_database_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(summary_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
        if summary_data:
            fieldnames = summary_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_data)

    print(f"サマリーファイル: {summary_path}")

    return output_path, summary_path


if __name__ == "__main__":
    generate_episode_database()