#!/usr/bin/env python3
"""
Add missing 7 people to database
データベースに不足している7名を追加
"""

import json
from datetime import datetime

def add_missing_people():
    """不足している7名の人物データを追加"""

    # データベースを読み込み
    with open('verified_facts_database_103persons.json', 'r', encoding='utf-8') as f:
        database = json.load(f)

    # 追加する7名のデータ
    new_people = {
        "スティーブ・ジョブズ": {
            "person_id": "P006001",
            "birth_year": 1955,
            "death_year": 2011,
            "facts": [
                {
                    "age": 29,
                    "fact": "1984年、初代Macintoshを発表し、パーソナルコンピュータの革命を起こす",
                    "sources": ["Apple公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.95,
                    "educational_score": 0.95,
                    "keywords": ["Macintosh", "1984年", "革命"],
                    "ownership_type": "individual",
                    "importance_score": 1.8
                },
                {
                    "age": 52,
                    "fact": "2007年、iPhoneを発表し、スマートフォン時代の幕開けをもたらす",
                    "sources": ["Apple公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 1.0,
                    "educational_score": 1.0,
                    "keywords": ["iPhone", "2007年", "スマートフォン", "革新"],
                    "ownership_type": "individual",
                    "importance_score": 2.0
                },
                {
                    "age": 21,
                    "fact": "1976年、Apple Computerを共同創業、ガレージから世界的企業への第一歩",
                    "sources": ["Apple公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.9,
                    "educational_score": 0.88,
                    "keywords": ["Apple", "1976年", "創業"],
                    "ownership_type": "collaborative",
                    "importance_score": 1.5
                }
            ]
        },
        "ヘレン・ケラー": {
            "person_id": "P006002",
            "birth_year": 1880,
            "death_year": 1968,
            "facts": [
                {
                    "age": 24,
                    "fact": "1904年、ラドクリフ大学を卒業、盲聾者として初の学士号取得",
                    "sources": ["Harvard Archives", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.98,
                    "educational_score": 0.95,
                    "keywords": ["ラドクリフ大学", "1904年", "初", "学士号"],
                    "ownership_type": "individual",
                    "importance_score": 1.9
                },
                {
                    "age": 7,
                    "fact": "1887年、サリバン先生と出会い、「水」の概念を理解する奇跡の瞬間",
                    "sources": ["伝記", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 1.0,
                    "educational_score": 0.9,
                    "keywords": ["サリバン", "1887年", "水", "奇跡"],
                    "ownership_type": "individual",
                    "importance_score": 1.7
                },
                {
                    "age": 23,
                    "fact": "1903年、自伝『私の生涯』を出版、世界的ベストセラーとなる",
                    "sources": ["出版記録", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.85,
                    "keywords": ["私の生涯", "1903年", "ベストセラー"],
                    "ownership_type": "individual",
                    "importance_score": 1.4
                }
            ]
        },
        "孫正義": {
            "person_id": "P006003",
            "birth_year": 1957,
            "facts": [
                {
                    "age": 24,
                    "fact": "1981年、ソフトバンクを創業、パソコンソフトの卸売から始まる",
                    "sources": ["ソフトバンク公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.85,
                    "keywords": ["ソフトバンク", "1981年", "創業"],
                    "ownership_type": "individual",
                    "importance_score": 1.6
                },
                {
                    "age": 39,
                    "fact": "1996年、Yahoo! JAPANを設立し、日本のインターネット革命を牽引",
                    "sources": ["Yahoo公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.92,
                    "educational_score": 0.9,
                    "keywords": ["Yahoo! JAPAN", "1996年", "インターネット"],
                    "ownership_type": "individual",
                    "importance_score": 1.8
                },
                {
                    "age": 59,
                    "fact": "2016年、英ARM社を約3.3兆円で買収、IoT時代への大型投資",
                    "sources": ["ソフトバンク公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.9,
                    "educational_score": 0.88,
                    "keywords": ["ARM", "2016年", "買収", "3.3兆円"],
                    "ownership_type": "individual",
                    "importance_score": 1.7
                }
            ]
        },
        "本庶佑": {
            "person_id": "P006004",
            "birth_year": 1942,
            "facts": [
                {
                    "age": 76,
                    "fact": "2018年、ノーベル生理学・医学賞を受賞、がん免疫療法の開発に貢献",
                    "sources": ["ノーベル財団", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 1.0,
                    "educational_score": 1.0,
                    "keywords": ["ノーベル賞", "2018年", "がん免疫療法", "PD-1"],
                    "ownership_type": "individual",
                    "importance_score": 2.0
                },
                {
                    "age": 50,
                    "fact": "1992年、PD-1分子を発見、後のがん治療薬開発の基礎となる",
                    "sources": ["京都大学", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.95,
                    "educational_score": 0.98,
                    "keywords": ["PD-1", "1992年", "発見"],
                    "ownership_type": "individual",
                    "importance_score": 1.9
                },
                {
                    "age": 72,
                    "fact": "2014年、PD-1抗体薬「オプジーボ」が承認、がん治療に革命",
                    "sources": ["医薬品医療機器総合機構", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.92,
                    "educational_score": 0.95,
                    "keywords": ["オプジーボ", "2014年", "承認"],
                    "ownership_type": "collaborative",
                    "importance_score": 1.7
                }
            ]
        },
        "三木谷浩史": {
            "person_id": "P006005",
            "birth_year": 1965,
            "facts": [
                {
                    "age": 32,
                    "fact": "1997年、楽天を創業し、日本最大級のECサイトへと成長させる",
                    "sources": ["楽天公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.9,
                    "educational_score": 0.88,
                    "keywords": ["楽天", "1997年", "創業", "EC"],
                    "ownership_type": "individual",
                    "importance_score": 1.7
                },
                {
                    "age": 35,
                    "fact": "2000年、楽天をJASDAQに上場、時価総額6000億円を達成",
                    "sources": ["東証", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.85,
                    "keywords": ["上場", "2000年", "JASDAQ"],
                    "ownership_type": "individual",
                    "importance_score": 1.5
                },
                {
                    "age": 39,
                    "fact": "2004年、プロ野球参入を発表、東北楽天ゴールデンイーグルス設立",
                    "sources": ["楽天野球団", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.85,
                    "educational_score": 0.8,
                    "keywords": ["プロ野球", "2004年", "東北楽天"],
                    "ownership_type": "individual",
                    "importance_score": 1.4
                }
            ]
        },
        "柳井正": {
            "person_id": "P006006",
            "birth_year": 1949,
            "facts": [
                {
                    "age": 35,
                    "fact": "1984年、ユニクロ1号店を広島にオープン、ファストファッションの先駆け",
                    "sources": ["ファーストリテイリング", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.85,
                    "keywords": ["ユニクロ", "1984年", "1号店"],
                    "ownership_type": "individual",
                    "importance_score": 1.6
                },
                {
                    "age": 49,
                    "fact": "1998年、フリース1900円で大ヒット、ユニクロブームの火付け役",
                    "sources": ["ファーストリテイリング", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.9,
                    "educational_score": 0.82,
                    "keywords": ["フリース", "1998年", "1900円"],
                    "ownership_type": "individual",
                    "importance_score": 1.5
                },
                {
                    "age": 60,
                    "fact": "2009年、ヒートテックが世界的ヒット商品となり、機能性衣料の革新",
                    "sources": ["ファーストリテイリング", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.92,
                    "educational_score": 0.88,
                    "keywords": ["ヒートテック", "2009年", "革新"],
                    "ownership_type": "collaborative",
                    "importance_score": 1.7
                }
            ]
        },
        "羽生結弦": {
            "person_id": "P006007",
            "birth_year": 1994,
            "facts": [
                {
                    "age": 19,
                    "fact": "2014年、ソチ五輪で日本男子フィギュアスケート初の金メダルを獲得",
                    "sources": ["IOC公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 1.0,
                    "educational_score": 0.95,
                    "keywords": ["ソチ五輪", "2014年", "金メダル", "日本男子初"],
                    "ownership_type": "individual",
                    "importance_score": 2.1
                },
                {
                    "age": 23,
                    "fact": "2018年、平昌五輪で連覇達成、66年ぶりの男子フィギュア五輪連覇",
                    "sources": ["IOC公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 1.0,
                    "educational_score": 0.98,
                    "keywords": ["平昌五輪", "2018年", "連覇", "66年ぶり"],
                    "ownership_type": "individual",
                    "importance_score": 2.2
                },
                {
                    "age": 16,
                    "fact": "2010年、世界ジュニア選手権優勝、史上最年少での優勝",
                    "sources": ["ISU公式", "Wikipedia"],
                    "confidence": 1.0,
                    "emotional_score": 0.88,
                    "educational_score": 0.85,
                    "keywords": ["世界ジュニア", "2010年", "最年少"],
                    "ownership_type": "individual",
                    "importance_score": 1.4
                }
            ]
        }
    }

    # データベースに追加
    database['verified_facts'].update(new_people)

    # 保存
    with open('verified_facts_database_103persons.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print("✅ 7名の人物データを追加しました:")
    for name in new_people.keys():
        print(f"   - {name}")

    return new_people

if __name__ == "__main__":
    added_people = add_missing_people()
    print(f"\n📊 追加完了: {len(added_people)}名")