#!/usr/bin/env python3
"""
データベースにセンセーショナルな事実を追加
ヘレン・ケラーのWater!エピソードと安倍晋三の歴代最長記録
"""

import json
from pathlib import Path


def update_database():
    """データベースを更新"""

    db_path = Path("verified_facts_database_103persons.json")

    # データベース読み込み
    with open(db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # ヘレン・ケラーのWater!エピソード追加
    if "ヘレン・ケラー" in data["verified_facts"]:
        helen_facts = data["verified_facts"]["ヘレン・ケラー"]["facts"]

        # Water!エピソードが存在しない場合のみ追加
        water_episode_exists = any(f.get('age') == 7 for f in helen_facts)

        if not water_episode_exists:
            water_episode = {
                "age": 7,
                "fact": "視覚・聴覚・発話に困難を抱えながら、家庭教師アン・サリヴァンの指導で「Water」という言葉と概念を理解した瞬間",
                "sources": [
                    "The Story of My Life",
                    "Wikipedia",
                    "Helen Keller Foundation"
                ],
                "confidence": 1.0,
                "emotional_score": 1.0,
                "educational_score": 1.0,
                "keywords": [
                    "Water",
                    "アン・サリヴァン",
                    "1887年",
                    "教育史",
                    "転換点",
                    "感動的瞬間"
                ],
                "ownership_type": "individual",
                "importance_score": 3.0,  # 最高の重要度
                "story_elements": {
                    "turning_point": True,
                    "against_odds": True,
                    "human_drama": True,
                    "historical_significance": True
                }
            }
            helen_facts.append(water_episode)
            print("✅ ヘレン・ケラーのWater!エピソードを追加しました")
        else:
            print("ℹ️ ヘレン・ケラーのWater!エピソードは既に存在します")

    # 安倍晋三の歴代最長在職記録追加
    if "安倍晋三" in data["verified_facts"]:
        abe_facts = data["verified_facts"]["安倍晋三"]["facts"]

        # 既存の52歳エピソードを更新（戦後最年少を追加）
        for fact in abe_facts:
            if fact.get('age') == 52 and "総理大臣" in fact.get('fact', ''):
                fact['fact'] = "2006年9月26日、第90代内閣総理大臣に就任、戦後生まれ初かつ戦後最年少（52歳）の総理大臣"
                fact['keywords'].append("戦後最年少")
                fact['emotional_score'] = 0.9
                fact['importance_score'] = 2.0
                print("✅ 安倍晋三の就任時エピソードに戦後最年少を追加しました")
                break

        # 歴代最長在職記録が存在しない場合のみ追加
        longest_record_exists = any("最長" in f.get('fact', '') for f in abe_facts)

        if not longest_record_exists:
            longest_record = {
                "age": 65,
                "fact": "通算在職日数3,188日で歴代最長記録を達成、2019年11月20日に桂太郎を超え、連続在職日数も2,822日で佐藤栄作を超える",
                "sources": [
                    "首相官邸",
                    "Wikipedia",
                    "内閣府公式記録"
                ],
                "confidence": 1.0,
                "emotional_score": 0.95,
                "educational_score": 1.0,
                "keywords": [
                    "歴代最長",
                    "3188日",
                    "2822日",
                    "2019年",
                    "2020年",
                    "記録更新",
                    "在職日数"
                ],
                "ownership_type": "individual",
                "importance_score": 2.5,
                "story_elements": {
                    "historic_record": True,
                    "leadership": True,
                    "endurance": True,
                    "national_significance": True
                }
            }
            abe_facts.append(longest_record)
            print("✅ 安倍晋三の歴代最長在職記録を追加しました")
        else:
            print("ℹ️ 安倍晋三の最長在職記録は既に存在します")

    # データベース保存
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n📊 データベース更新完了")

    # 更新内容の確認
    print("\n🔍 更新内容の確認:")

    # ヘレン・ケラーの事実一覧
    if "ヘレン・ケラー" in data["verified_facts"]:
        print("\nヘレン・ケラーの事実:")
        for fact in data["verified_facts"]["ヘレン・ケラー"]["facts"]:
            print(f"  - {fact['age']}歳: {fact['fact'][:50]}...")

    # 安倍晋三の事実一覧
    if "安倍晋三" in data["verified_facts"]:
        print("\n安倍晋三の事実:")
        for fact in data["verified_facts"]["安倍晋三"]["facts"]:
            print(f"  - {fact['age']}歳: {fact['fact'][:50]}...")


if __name__ == "__main__":
    update_database()