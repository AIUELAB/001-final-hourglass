#!/usr/bin/env python3
"""
浅田真央のデータベース更新スクリプト
ソチ五輪の感動的エピソードを追加
"""

import json
from datetime import datetime
from pathlib import Path

def update_asada_mao_facts():
    """浅田真央の事実データを更新"""

    # データベース読み込み
    db_path = Path("verified_facts_database_103persons.json")

    with open(db_path, 'r', encoding='utf-8') as f:
        database = json.load(f)

    # 浅田真央のデータを確認
    if "浅田真央" not in database.get('verified_facts', {}):
        print("❌ 浅田真央のデータが見つかりません")
        # 新規作成
        database['verified_facts']['浅田真央'] = {
            "person_id": "P000102",
            "birth_year": 1990,
            "facts": []
        }

    asada_data = database['verified_facts']['浅田真央']

    # 重要な事実を追加（既存のものを残しつつ）
    new_facts = [
        {
            "age": 24,
            "fact": "2014年ソチ五輪、ショートプログラム16位から奇跡の復活。フリーで全6種類8回の3回転ジャンプを完璧に成功させ、涙と笑顔で世界を感動させた",
            "sources": ["IOC公式", "ISU", "Wikipedia"],
            "confidence": 1.0,
            "emotional_score": 1.0,
            "educational_score": 0.95,
            "keywords": [
                "ソチ五輪", "2014年", "復活", "伝説",
                "涙", "感動", "16位", "6種類8回",
                "トリプルアクセル", "142.71点"
            ],
            "ownership_type": "individual",
            "importance_score": 2.5
        },
        {
            "age": 20,
            "fact": "2010年バンクーバー五輪で銀メダル獲得、女子初のオリンピックでトリプルアクセルを成功、1大会3回成功でギネス世界記録",
            "sources": ["IOC公式", "ギネス記録", "Wikipedia"],
            "confidence": 1.0,
            "emotional_score": 0.95,
            "educational_score": 0.92,
            "keywords": [
                "バンクーバー五輪", "2010年", "銀メダル",
                "トリプルアクセル", "女子初", "ギネス記録",
                "3回成功", "歴史的快挙"
            ],
            "ownership_type": "individual",
            "importance_score": 2.2
        },
        {
            "age": 15,
            "fact": "2005年、GPファイナル優勝、史上最年少での優勝記録",
            "sources": ["ISU", "Wikipedia"],
            "confidence": 1.0,
            "emotional_score": 0.88,
            "educational_score": 0.85,
            "keywords": [
                "GPファイナル", "2005年", "史上最年少",
                "15歳", "優勝"
            ],
            "ownership_type": "individual",
            "importance_score": 1.8
        },
        {
            "age": 26,
            "fact": "2017年4月10日、現役引退を表明、21年間の競技生活に幕",
            "sources": ["日本スケート連盟", "Wikipedia"],
            "confidence": 1.0,
            "emotional_score": 0.9,
            "educational_score": 0.8,
            "keywords": [
                "引退", "2017年", "21年間", "競技生活"
            ],
            "ownership_type": "individual",
            "importance_score": 1.5
        },
        {
            "age": 34,
            "fact": "2024年11月11日、MAO RINK TACHIKAWA TACHIHIをオープン、日本初の個人名を冠したスケートリンク",
            "sources": ["立飛HD", "Wikipedia"],
            "confidence": 1.0,
            "emotional_score": 0.75,
            "educational_score": 0.8,
            "keywords": [
                "MAO RINK", "2024年", "立川", "日本初",
                "個人名", "スケートリンク"
            ],
            "ownership_type": "individual",
            "importance_score": 1.2
        }
    ]

    # 既存のfactsに追加（重複チェック）
    existing_ages = {f.get('age') for f in asada_data.get('facts', [])}

    for fact in new_facts:
        if fact['age'] not in existing_ages:
            asada_data['facts'].append(fact)
            print(f"✅ 追加: {fact['age']}歳 - {fact['fact'][:50]}...")
        else:
            # 既存のものを更新（ソチ五輪を優先）
            for i, existing_fact in enumerate(asada_data['facts']):
                if existing_fact.get('age') == fact['age']:
                    if fact.get('importance_score', 0) > existing_fact.get('importance_score', 0):
                        asada_data['facts'][i] = fact
                        print(f"🔄 更新: {fact['age']}歳 - {fact['fact'][:50]}...")

    # ソート（importance_scoreの高い順）
    asada_data['facts'].sort(
        key=lambda x: x.get('importance_score', 0),
        reverse=True
    )

    # 更新日時を記録
    database['metadata']['last_updated'] = datetime.now().isoformat()
    database['metadata']['update_note'] = "浅田真央のソチ五輪エピソード追加・感動価値重視"

    # 保存
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print(f"\n📊 浅田真央のデータ更新完了")
    print(f"   事実数: {len(asada_data['facts'])}件")
    print(f"   最重要: {asada_data['facts'][0]['fact'][:60]}...")

    return asada_data

if __name__ == "__main__":
    update_asada_mao_facts()