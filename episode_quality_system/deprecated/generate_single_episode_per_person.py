#!/usr/bin/env python3
"""
エピソードデータベース生成スクリプト（修正版）
各人物に最適な年齢で1エピソードずつ生成
"""

import csv
import json
import random
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent))
from episode_factory import EpisodeFactory, EpisodeRequest


def get_optimal_age(person_name: str, facts: dict) -> int:
    """
    人物の事実データから最適な年齢を決定

    Args:
        person_name: 人物名
        facts: 事実データ

    Returns:
        最適な年齢
    """
    # 事実から年齢のヒントを探す
    age_hints = []

    # すべての事実をチェック
    for category, fact_list in facts.items():
        for fact in fact_list:
            # 年齢が含まれる事実を探す
            import re
            age_matches = re.findall(r'(\d+)歳', fact)
            for age_str in age_matches:
                age = int(age_str)
                if 20 <= age <= 50:  # 妥当な範囲
                    age_hints.append(age)

    # 特定の人物の既知の重要年齢
    known_ages = {
        "大谷翔平": 29,      # 2023年のMVP時
        "イチロー": 27,      # MLB新人王・MVP
        "松井秀喜": 35,      # ワールドシリーズMVP
        "羽生結弦": 23,      # ソチ五輪金メダル
        "錦織圭": 24,        # 全米準優勝
        "村上春樹": 30,      # 「羊をめぐる冒険」発表
        "黒澤明": 40,        # 「羅生門」監督時
        "宮崎駿": 47,        # 「となりのトトロ」公開
        "HIKAKIN": 28,       # YouTube日本一達成頃
        "松山英樹": 29,      # マスターズ優勝
        "孫正義": 37,        # Yahoo! JAPAN設立
        "安倍晋三": 52,      # 首相就任（第2次）
        "織田信長": 26,      # 桶狭間の戦い
        "豊臣秀吉": 45,      # 天下統一
        "徳川家康": 60,      # 江戸幕府開府
        "坂本龍馬": 31,      # 薩長同盟
        "山中伸弥": 50,      # ノーベル賞受賞
        "本庶佑": 76,        # ノーベル賞受賞
        "北野武": 50,        # 「HANA-BI」でヴェネツィア金獅子賞
        "渡辺謙": 44,        # 「ラストサムライ」アカデミー賞ノミネート
        "羽生善治": 25,      # 七冠達成
        "藤井聡太": 19,      # 最年少二冠
        "吉田沙保里": 30,    # ロンドン五輪金メダル
        "伊調馨": 32,        # リオ五輪金メダル（4連覇）
        "内村航平": 27,      # リオ五輪個人総合金メダル
        "北島康介": 21,      # アテネ五輪2冠
        "萩野公介": 22,      # リオ五輪金メダル
        "浅田真央": 23,      # ソチ五輪フリー最高演技
    }

    # 既知の年齢があればそれを使用
    if person_name in known_ages:
        return known_ages[person_name]

    # 事実から抽出した年齢があれば、その中央値を使用
    if age_hints:
        return sorted(age_hints)[len(age_hints)//2]

    # カテゴリーに基づくデフォルト年齢
    category_defaults = {
        "sports": 28,        # アスリートの全盛期
        "entertainment": 35, # 芸能界での成熟期
        "business": 40,      # ビジネスでの成功期
        "politics": 45,      # 政治的影響力のピーク
        "science": 42,       # 研究成果の結実期
        "art": 38,          # 芸術的円熟期
        "music": 32,        # 音楽的成熟期
        "culture": 35,      # 文化的影響力のピーク
        "technology": 35,   # 技術革新の時期
        "intellectual": 40  # 知的成果の結実期
    }

    # カテゴリーが判明していればそれに基づく
    for cat in category_defaults:
        if cat in str(facts).lower():
            return category_defaults[cat]

    # デフォルトは30歳（多くの人が何かを成し遂げる年齢）
    return 30


def generate_episode_database():
    """エピソードデータベースを生成（1人1エピソード）"""

    # EpisodeFactory初期化
    factory = EpisodeFactory()

    # person_facts.jsonを読み込み
    facts_path = Path(__file__).parent / "data" / "person_facts.json"
    with open(facts_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        persons = data.get("persons", {})

    # エピソードデータベース
    episode_database = []

    print(f"エピソード生成開始: {len(persons)}人（各1エピソード）")
    print("="*60)

    total_episodes = 0
    success_count = 0
    total_score = 0
    age_distribution = {}

    for person_name, person_data in persons.items():
        category = person_data.get("category", "unknown")
        facts = person_data.get("facts", {})

        # 最適な年齢を決定
        optimal_age = get_optimal_age(person_name, facts)

        # 年齢分布を記録
        age_distribution[optimal_age] = age_distribution.get(optimal_age, 0) + 1

        # エピソード生成リクエスト
        request = EpisodeRequest(
            person_name=person_name,
            age=optimal_age,
            category=category
        )

        # エピソード生成
        try:
            response = factory.generate_episode(request)

            # データベースに追加
            episode_database.append({
                "person_id": f"{person_name}_{optimal_age}",
                "person_name": person_name,
                "age": optimal_age,
                "category": category,
                "episode": response.episode,
                "character_count": len(response.episode),
                "quality_score": response.quality_score,
                "quality_level": response.quality_level,
                "generation_time": round(response.generation_time, 3),
                "template_check": "PASS" if response.final_validation["checks"]["template_blocker"]["passed"] else "FAIL",
                "realtime_check": "PASS" if response.final_validation["checks"]["realtime_validator"]["passed"] else "FAIL",
                "has_facts": "あり" if any(char.isdigit() for char in response.episode) else "なし",
                "age_reason": "最適年齢",  # 年齢選択の理由
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            total_episodes += 1
            total_score += response.quality_score
            if response.quality_score >= 70:
                success_count += 1

            # 進捗表示
            if total_episodes % 10 == 0:
                print(f"進捗: {total_episodes}/{len(persons)} エピソード生成完了")

        except Exception as e:
            print(f"エラー: {person_name} ({optimal_age}歳) - {e}")
            # エラーの場合もデータベースに記録
            episode_database.append({
                "person_id": f"{person_name}_{optimal_age}",
                "person_name": person_name,
                "age": optimal_age,
                "category": category,
                "episode": "生成エラー",
                "character_count": 0,
                "quality_score": 0,
                "quality_level": "error",
                "generation_time": 0,
                "template_check": "ERROR",
                "realtime_check": "ERROR",
                "has_facts": "エラー",
                "age_reason": "エラー",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            total_episodes += 1

    # CSVに出力（UTF-8 BOM付き）
    output_path = Path(__file__).parent / f"episode_database_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
        if episode_database:
            fieldnames = episode_database[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(episode_database)

    print("\n" + "="*60)
    print("エピソードデータベース生成完了")
    print(f"出力ファイル: {output_path}")
    print(f"総エピソード数: {total_episodes}（1人1エピソード）")
    print(f"成功数: {success_count} ({success_count/total_episodes*100:.1f}%)")
    print(f"平均品質スコア: {total_score/total_episodes:.1f}")

    # 年齢分布を表示
    print("\n年齢分布:")
    for age in sorted(age_distribution.keys()):
        print(f"  {age}歳: {age_distribution[age]}人")

    # 年齢統計
    ages = list(age_distribution.keys())
    if ages:
        print(f"\n年齢統計:")
        print(f"  最小年齢: {min(ages)}歳")
        print(f"  最大年齢: {max(ages)}歳")
        print(f"  平均年齢: {sum(age * count for age, count in age_distribution.items()) / total_episodes:.1f}歳")

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
                "total_chars": 0,
                "ages": []
            }
        categories[cat]["count"] += 1
        categories[cat]["total_score"] += episode["quality_score"]
        if episode["quality_score"] >= 70:
            categories[cat]["success"] += 1
        categories[cat]["total_chars"] += episode["character_count"]
        categories[cat]["ages"].append(episode["age"])

    for cat, stats in categories.items():
        summary_data.append({
            "カテゴリ": cat,
            "人数": stats["count"],
            "平均スコア": round(stats["total_score"] / stats["count"], 1) if stats["count"] > 0 else 0,
            "成功率": f"{stats['success']/stats['count']*100:.1f}%" if stats["count"] > 0 else "0%",
            "平均文字数": round(stats["total_chars"] / stats["count"], 1) if stats["count"] > 0 else 0,
            "平均年齢": round(sum(stats["ages"]) / len(stats["ages"]), 1) if stats["ages"] else 0
        })

    # サマリーCSV出力
    summary_path = Path(__file__).parent / f"episode_database_single_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

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