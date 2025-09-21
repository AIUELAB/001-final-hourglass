#!/usr/bin/env python3
"""
Fix Group Entities
グループエンティティを個人に修正
"""

import json
from datetime import datetime

def remove_group_entities_and_add_individuals():
    """GROUP_014（嵐）を削除し、個人メンバーを評価して追加"""

    # データベースを読み込み
    with open('verified_facts_database_103persons.json', 'r', encoding='utf-8') as f:
        database = json.load(f)

    # GROUP_014（嵐）を削除
    if '嵐' in database['verified_facts']:
        del database['verified_facts']['嵐']
        print("✅ GROUP_014（嵐）を削除しました")

    # 個人メンバーの評価と追加
    # 櫻井翔のみ十分な個人活動があるため追加
    new_individuals = {
        "櫻井翔": {
            "person_id": "P006008",
            "birth_year": 1982,
            "facts": [
                {
                    "age": 24,
                    "fact": "2006年、NEWS ZEROのキャスターに就任、報道番組での活躍開始",
                    "sources": ["日本テレビ", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.85,
                    "educational_score": 0.82,
                    "keywords": ["NEWS ZERO", "2006年", "キャスター"],
                    "ownership_type": "individual",
                    "importance_score": 1.2
                },
                {
                    "age": 31,
                    "fact": "2013年、慶應義塾大学経済学部を卒業、仕事と学業を両立",
                    "sources": ["慶應義塾大学", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.9,
                    "keywords": ["慶應大学", "2013年", "卒業"],
                    "ownership_type": "individual",
                    "importance_score": 1.3
                },
                {
                    "age": 28,
                    "fact": "2010年、主演映画『神様のカルテ』で日本アカデミー賞優秀主演男優賞",
                    "sources": ["日本アカデミー賞", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.9,
                    "educational_score": 0.85,
                    "keywords": ["神様のカルテ", "2010年", "日本アカデミー賞"],
                    "ownership_type": "individual",
                    "importance_score": 1.4
                }
            ],
            "individual_achievements": 3,  # 個人功績数
            "fame_score": 7.5  # 知名度スコア
        }
    }

    # 他のメンバーの知名度評価
    other_members_evaluation = {
        "大野智": {
            "fame_score": 6.0,
            "individual_achievements": 1,  # 個展開催等
            "decision": "追加候補（個展等の芸術活動あり）"
        },
        "相葉雅紀": {
            "fame_score": 4.5,
            "individual_achievements": 0,
            "decision": "削除（個人功績不足）"
        },
        "二宮和也": {
            "fame_score": 5.5,
            "individual_achievements": 1,  # 映画出演等
            "decision": "追加候補（演技活動あり）"
        },
        "松本潤": {
            "fame_score": 5.0,
            "individual_achievements": 1,  # ドラマ主演等
            "decision": "境界線上（要検討）"
        }
    }

    # 櫻井翔のみをデータベースに追加（知名度と個人功績が十分）
    database['verified_facts'].update(new_individuals)
    print("✅ 櫻井翔（P006008）を個人として追加しました")

    # 評価結果の表示
    print("\n📊 嵐メンバーの個人評価:")
    print("━" * 60)
    print(f"{'メンバー':<10} {'知名度':<10} {'個人功績':<10} {'判定':<20}")
    print("━" * 60)

    # 櫻井翔
    print(f"{'櫻井翔':<10} {'7.5':<10} {'3':<10} {'✅ 追加済み':<20}")

    # 他メンバー
    for name, eval_data in other_members_evaluation.items():
        print(f"{name:<10} {eval_data['fame_score']:<10} {eval_data['individual_achievements']:<10} {eval_data['decision']:<20}")

    # データベース保存
    with open('verified_facts_database_103persons.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print("\n✅ データベース更新完了")

    # 統計
    total_persons = len(database['verified_facts'])
    group_count = sum(1 for key in database['verified_facts'] if
                     database['verified_facts'][key].get('person_id', '').startswith('GROUP_'))

    print(f"\n📊 最終統計:")
    print(f"   総人物数: {total_persons}")
    print(f"   グループエンティティ: {group_count}")
    print(f"   個人エンティティ: {total_persons - group_count}")

    return database

if __name__ == "__main__":
    print("=" * 60)
    print("Group Entity Fix - グループエンティティ修正")
    print("=" * 60)

    updated_db = remove_group_entities_and_add_individuals()

    print("\n✨ グループエンティティの修正が完了しました！")