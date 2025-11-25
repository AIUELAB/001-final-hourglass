#!/usr/bin/env python3
"""
厳選された感銘を与える有名人物データベース
現代の10代〜50代が本当に「自分も頑張ろう」と思える人物を厳選
"""

import json
from datetime import datetime
from typing import Dict, List

import pandas as pd


def create_curated_inspirational_database():
    """厳選された感銘を与える人物データベースを作成"""

    people = []

    # ===== エンターテインメント（バランス良く）=====

    # 日本のお笑い芸人
    comedians_jp = [
        {
            'name': 'ダウンタウン・松本人志',
            'birth_year': 1963,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'お笑い芸人',
            'inspirational_points': 'NSC第1期生から日本のお笑い界のトップへ',
            'target_age': '20-50代',
            'key_achievement': 'ガキの使い、ごっつええ感じ等の革新的番組'
        },
        {
            'name': '明石家さんま',
            'birth_year': 1955,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'お笑い芸人',
            'inspirational_points': '落語から漫才へ転向し大成功',
            'target_age': '30-50代',
            'key_achievement': '40年以上第一線で活躍'
        },
        {
            'name': 'サンドウィッチマン',
            'birth_year': 1974,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'お笑い芸人',
            'inspirational_points': '10年の下積みからM-1優勝',
            'target_age': '20-40代',
            'key_achievement': '東日本大震災復興支援活動'
        }
    ]

    # YouTuber・インフルエンサー
    youtubers = [
        {
            'name': 'HIKAKIN',
            'birth_year': 1989,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'YouTuber',
            'inspirational_points': 'スーパーの店員からYouTube界のトップへ',
            'target_age': '10-30代',
            'key_achievement': 'チャンネル登録者数1000万人突破'
        },
        {
            'name': 'はじめしゃちょー',
            'birth_year': 1993,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'YouTuber',
            'inspirational_points': '大学生から日本トップYouTuberへ',
            'target_age': '10-20代',
            'key_achievement': '実験系動画のパイオニア'
        },
        {
            'name': 'MrBeast（ジミー・ドナルドソン）',
            'birth_year': 1998,
            'nationality': 'アメリカ',
            'category': 'エンターテインメント',
            'subcategory': 'YouTuber',
            'inspirational_points': '収益を全て動画制作に再投資する姿勢',
            'target_age': '10-30代',
            'key_achievement': '世界最大規模のYouTubeチャンネル'
        }
    ]

    # アイドル・音楽アーティスト
    musicians = [
        {
            'name': '米津玄師',
            'birth_year': 1991,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'ミュージシャン',
            'inspirational_points': 'ニコニコ動画から国民的アーティストへ',
            'target_age': '10-30代',
            'key_achievement': 'Lemon、パプリカ等のヒット曲'
        },
        {
            'name': 'BTS（防弾少年団）',
            'birth_year': 1997,  # 平均
            'nationality': '韓国',
            'category': 'エンターテインメント',
            'subcategory': 'アイドル',
            'inspirational_points': '小事務所から世界的スターへ',
            'target_age': '10-30代',
            'key_achievement': 'ビルボード1位、国連スピーチ'
        },
        {
            'name': 'Billie Eilish',
            'birth_year': 2001,
            'nationality': 'アメリカ',
            'category': 'エンターテインメント',
            'subcategory': '歌手',
            'inspirational_points': '10代で世界的成功、メンタルヘルス啓発',
            'target_age': '10-20代',
            'key_achievement': 'グラミー賞最年少受賞'
        },
        {
            'name': 'あいみょん',
            'birth_year': 1995,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': 'シンガーソングライター',
            'inspirational_points': '路上ライブから紅白出場へ',
            'target_age': '10-30代',
            'key_achievement': 'マリーゴールド等のヒット曲'
        }
    ]

    # 俳優・女優
    actors = [
        {
            'name': '新垣結衣',
            'birth_year': 1988,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': '女優',
            'inspirational_points': 'モデルから国民的女優へ',
            'target_age': '20-40代',
            'key_achievement': '逃げ恥、コード・ブルー等'
        },
        {
            'name': '菅田将暉',
            'birth_year': 1993,
            'nationality': '日本',
            'category': 'エンターテインメント',
            'subcategory': '俳優',
            'inspirational_points': '仮面ライダーから演技派俳優へ',
            'target_age': '10-30代',
            'key_achievement': '多彩な役柄、音楽活動も成功'
        },
        {
            'name': 'Zendaya',
            'birth_year': 1996,
            'nationality': 'アメリカ',
            'category': 'エンターテインメント',
            'subcategory': '女優',
            'inspirational_points': '子役から映画スターへ、社会問題への発言',
            'target_age': '10-20代',
            'key_achievement': 'スパイダーマン、DUNE等'
        }
    ]

    # ===== 文化・芸術（日本の強みを活かす）=====

    # 漫画家
    manga_artists = [
        {
            'name': '尾田栄一郎',
            'birth_year': 1975,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': '漫画家',
            'inspirational_points': 'ONE PIECEで25年以上連載継続',
            'target_age': '全世代',
            'key_achievement': 'ギネス記録、世界的人気'
        },
        {
            'name': '諫山創',
            'birth_year': 1986,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': '漫画家',
            'inspirational_points': '新人賞落選から世界的ヒット作へ',
            'target_age': '20-30代',
            'key_achievement': '進撃の巨人で世界現象'
        },
        {
            'name': '吾峠呼世晴',
            'birth_year': 1989,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': '漫画家',
            'inspirational_points': '短期間で社会現象を起こす',
            'target_age': '10-30代',
            'key_achievement': '鬼滅の刃で歴代興行収入1位'
        }
    ]

    # アニメ・映画監督
    directors = [
        {
            'name': '新海誠',
            'birth_year': 1973,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': 'アニメ監督',
            'inspirational_points': '個人制作から世界的監督へ',
            'target_age': '10-40代',
            'key_achievement': '君の名は。、天気の子'
        },
        {
            'name': '細田守',
            'birth_year': 1967,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': 'アニメ監督',
            'inspirational_points': 'スタジオジブリ退社から独立成功',
            'target_age': '20-40代',
            'key_achievement': 'サマーウォーズ、竜とそばかすの姫'
        },
        {
            'name': 'クリストファー・ノーラン',
            'birth_year': 1970,
            'nationality': 'イギリス',
            'category': '文化・芸術',
            'subcategory': '映画監督',
            'inspirational_points': '独自の映像表現で革新',
            'target_age': '20-50代',
            'key_achievement': 'インセプション、インターステラー'
        }
    ]

    # ゲームクリエイター
    game_creators = [
        {
            'name': '宮本茂',
            'birth_year': 1952,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': 'ゲームクリエイター',
            'inspirational_points': 'マリオ、ゼルダの生みの親',
            'target_age': '全世代',
            'key_achievement': '世界のゲーム文化を創造'
        },
        {
            'name': '小島秀夫',
            'birth_year': 1963,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': 'ゲームクリエイター',
            'inspirational_points': '独立後も世界的成功',
            'target_age': '20-40代',
            'key_achievement': 'メタルギアシリーズ、デス・ストランディング'
        },
        {
            'name': 'ヨコオタロウ',
            'birth_year': 1970,
            'nationality': '日本',
            'category': '文化・芸術',
            'subcategory': 'ゲームクリエイター',
            'inspirational_points': '独特の世界観で熱狂的ファン獲得',
            'target_age': '20-30代',
            'key_achievement': 'NieR:Automataで世界的評価'
        }
    ]

    # ===== スポーツ（努力と成功の象徴）=====

    athletes = [
        {
            'name': '大谷翔平',
            'birth_year': 1994,
            'nationality': '日本',
            'category': 'スポーツ',
            'subcategory': '野球選手',
            'inspirational_points': '二刀流という不可能への挑戦',
            'target_age': '全世代',
            'key_achievement': 'MLB MVP受賞、WBC優勝'
        },
        {
            'name': '藤井聡太',
            'birth_year': 2002,
            'nationality': '日本',
            'category': 'スポーツ',
            'subcategory': '棋士',
            'inspirational_points': '最年少記録を次々更新',
            'target_age': '10-30代',
            'key_achievement': '史上最年少八冠達成'
        },
        {
            'name': '大坂なおみ',
            'birth_year': 1997,
            'nationality': '日本/アメリカ',
            'category': 'スポーツ',
            'subcategory': 'テニス選手',
            'inspirational_points': 'メンタルヘルスの重要性を発信',
            'target_age': '10-30代',
            'key_achievement': '全米・全豪オープン優勝'
        },
        {
            'name': 'イリア・マリニン',
            'birth_year': 2004,
            'nationality': 'アメリカ',
            'category': 'スポーツ',
            'subcategory': 'フィギュアスケート',
            'inspirational_points': '4回転アクセル成功',
            'target_age': '10-20代',
            'key_achievement': '技術革新への挑戦'
        }
    ]

    # ===== ビジネス・テクノロジー（起業家精神）=====

    entrepreneurs = [
        {
            'name': 'イーロン・マスク',
            'birth_year': 1971,
            'nationality': 'アメリカ',
            'category': 'ビジネス',
            'subcategory': '起業家',
            'inspirational_points': '複数の革新的企業を創業',
            'target_age': '20-40代',
            'key_achievement': 'Tesla、SpaceX、X（Twitter）'
        },
        {
            'name': '前澤友作',
            'birth_year': 1975,
            'nationality': '日本',
            'category': 'ビジネス',
            'subcategory': '起業家',
            'inspirational_points': 'バンドマンから起業家へ',
            'target_age': '20-40代',
            'key_achievement': 'ZOZO創業、宇宙旅行'
        },
        {
            'name': '山田進太郎',
            'birth_year': 1977,
            'nationality': '日本',
            'category': 'ビジネス',
            'subcategory': '起業家',
            'inspirational_points': '楽天退社後にメルカリ創業',
            'target_age': '20-40代',
            'key_achievement': 'フリマアプリ文化を創造'
        },
        {
            'name': 'Brian Chesky',
            'birth_year': 1981,
            'nationality': 'アメリカ',
            'category': 'ビジネス',
            'subcategory': '起業家',
            'inspirational_points': 'エアマットレスから世界的企業へ',
            'target_age': '20-30代',
            'key_achievement': 'Airbnb創業'
        }
    ]

    # ===== 政治・社会（若い世代の活動家）=====

    activists = [
        {
            'name': 'グレタ・トゥーンベリ',
            'birth_year': 2003,
            'nationality': 'スウェーデン',
            'category': '政治・社会',
            'subcategory': '環境活動家',
            'inspirational_points': '15歳で世界的ムーブメント',
            'target_age': '10-20代',
            'key_achievement': '気候変動対策を世界に訴え'
        },
        {
            'name': 'マララ・ユスフザイ',
            'birth_year': 1997,
            'nationality': 'パキスタン',
            'category': '政治・社会',
            'subcategory': '人権活動家',
            'inspirational_points': '命の危険を乗り越え教育の権利を訴え',
            'target_age': '10-30代',
            'key_achievement': '史上最年少ノーベル平和賞'
        },
        {
            'name': '今井紀明',
            'birth_year': 1985,
            'nationality': '日本',
            'category': '政治・社会',
            'subcategory': 'NPO創設者',
            'inspirational_points': 'イラク人質事件から社会起業家へ',
            'target_age': '20-40代',
            'key_achievement': '認定NPO法人D×P創設'
        },
        {
            'name': 'Alexandria Ocasio-Cortez',
            'birth_year': 1989,
            'nationality': 'アメリカ',
            'category': '政治・社会',
            'subcategory': '政治家',
            'inspirational_points': 'ウェイトレスから最年少下院議員へ',
            'target_age': '20-30代',
            'key_achievement': 'グリーン・ニューディール提唱'
        }
    ]

    # すべての人物をリストに追加
    all_categories = [
        comedians_jp, youtubers, musicians, actors,
        manga_artists, directors, game_creators,
        athletes, entrepreneurs, activists
    ]

    for category_list in all_categories:
        people.extend(category_list)

    return people

def generate_balanced_report(people: List[Dict]) -> str:
    """バランスレポートを生成"""

    # カテゴリ別集計
    categories = {}
    for person in people:
        cat = person['category']
        categories[cat] = categories.get(cat, 0) + 1

    # 世代別集計
    age_groups = {'10代': 0, '20代': 0, '30代': 0, '40代': 0, '50代': 0}
    for person in people:
        target = person.get('target_age', '')
        for age in age_groups.keys():
            if age[:-1] in target or '全世代' in target:
                age_groups[age] += 1

    report = []
    report.append("=" * 60)
    report.append("🌟 厳選された感銘を与える有名人物")
    report.append("=" * 60)
    report.append(f"\n✅ 総人数: {len(people)}人")

    report.append("\n📊 カテゴリバランス:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(people) * 100
        bar = '█' * int(pct)
        report.append(f"  {cat:20} {count:3}人 ({pct:5.1f}%) {bar}")

    report.append("\n🎯 世代カバレッジ:")
    for age, count in age_groups.items():
        report.append(f"  {age}向け: {count}人")

    report.append("\n💡 主な感銘ポイント:")
    report.append("  • 下積み時代からの成功")
    report.append("  • 挫折からの復活")
    report.append("  • 新しい分野の開拓")
    report.append("  • 社会への貢献")
    report.append("  • 若くしての成功")
    report.append("  • 継続的な努力")

    report.append("\n" + "=" * 60)

    return "\n".join(report)

def export_to_csv(people: List[Dict], filename: str):
    """CSVエクスポート"""
    df = pd.DataFrame(people)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"📄 CSVエクスポート: {filename}")

def main():
    """メイン処理"""
    print("🌟 厳選版・感銘を与える有名人物データベース作成")
    print("=" * 60)

    # データベース作成
    people = create_curated_inspirational_database()

    # レポート生成
    report = generate_balanced_report(people)
    print(report)

    # CSVエクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"curated_inspirational_{timestamp}.csv"
    export_to_csv(people, csv_filename)

    # 人物例を表示
    print("\n📋 収録人物例:")
    for i, person in enumerate(people[:10], 1):
        print(f"  {i:2}. {person['name']} ({person['birth_year']}年生)")
        print(f"      {person['inspirational_points']}")

    print("\n✅ 厳選データベース作成完了！")
    print("  • 日本人多数収録")
    print("  • 10代〜50代全世代カバー")
    print("  • バランスの取れたカテゴリ分布")

if __name__ == "__main__":
    main()
