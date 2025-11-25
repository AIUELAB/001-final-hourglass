#!/usr/bin/env python3
"""
日本のエンターテイナー（お笑い芸人、YouTuber、アイドル）のデータ収集
"""

import json
from datetime import datetime


def create_japanese_entertainers_database():
    """日本のエンターテイナーデータベースを作成"""

    entertainers = []

    # ========== お笑い芸人 ==========
    comedians = [
        # レジェンド・大御所
        {'name': 'ビートたけし', 'name_ja': 'ビートたけし', 'birth_year': 1947,
         'episodes': [(27, 'ツービート結成'), (32, '漫才ブーム'), (42, '映画監督デビュー'), (50, 'ヴェネツィア映画祭金獅子賞')]},
        {'name': '明石家さんま', 'name_ja': '明石家さんま', 'birth_year': 1955,
         'episodes': [(19, 'NSC入学'), (26, 'ひょうきん族レギュラー'), (32, '恋のから騒ぎ開始'), (60, '還暦')]},
        {'name': '志村けん', 'name_ja': '志村けん', 'birth_year': 1950, 'death_year': 2020,
         'episodes': [(24, 'ドリフターズ加入'), (36, 'だいじょうぶだぁ開始'), (45, 'バカ殿様'), (70, 'コロナ死去')]},
        {'name': 'タモリ', 'name_ja': 'タモリ', 'birth_year': 1945,
         'episodes': [(30, '東京進出'), (37, '笑っていいとも開始'), (69, 'いいとも終了'), (77, 'ブラタモリ')]},

        # ダウンタウン世代
        {'name': '松本人志', 'name_ja': '松本人志', 'birth_year': 1963,
         'episodes': [(19, 'ダウンタウン結成'), (26, 'ガキの使い開始'), (46, '映画監督デビュー'), (60, '還暦')]},
        {'name': '浜田雅功', 'name_ja': '浜田雅功', 'birth_year': 1963,
         'episodes': [(19, 'ダウンタウン結成'), (26, 'ガキの使い開始'), (35, '結婚'), (50, '紅白司会')]},

        # とんねるず
        {'name': '石橋貴明', 'name_ja': '石橋貴明', 'birth_year': 1961,
         'episodes': [(19, 'とんねるず結成'), (27, 'みなさんのおかげです開始'), (37, 'うたばん開始'), (59, 'YouTube開始')]},
        {'name': '木梨憲武', 'name_ja': '木梨憲武', 'birth_year': 1962,
         'episodes': [(18, 'とんねるず結成'), (28, 'みなさんのおかげです'), (48, '個展開催'), (58, 'アート活動本格化')]},

        # ナインティナイン
        {'name': '岡村隆史', 'name_ja': '岡村隆史', 'birth_year': 1970,
         'episodes': [(20, 'ナインティナイン結成'), (27, 'めちゃイケ開始'), (40, '休養'), (50, '結婚')]},
        {'name': '矢部浩之', 'name_ja': '矢部浩之', 'birth_year': 1971,
         'episodes': [(19, 'ナインティナイン結成'), (26, 'めちゃイケ開始'), (36, '結婚'), (50, '青空レストラン')]},

        # M-1王者
        {'name': '中川家・礼二', 'name_ja': '中川家・礼二', 'birth_year': 1972,
         'episodes': [(20, 'コンビ結成'), (29, 'M-1優勝'), (40, 'ものまね番組'), (50, 'ベテラン芸人')]},
        {'name': 'ますだおかだ・岡田圭右', 'name_ja': 'ますだおかだ・岡田', 'birth_year': 1968,
         'episodes': [(20, 'コンビ結成'), (34, 'M-1優勝'), (45, '東京進出'), (54, '司会業')]},
        {'name': 'フットボールアワー・後藤輝基', 'name_ja': '後藤輝基', 'birth_year': 1974,
         'episodes': [(25, 'コンビ結成'), (29, 'M-1優勝'), (40, 'ガキ使レギュラー'), (48, 'MC業')]},
        {'name': 'フットボールアワー・岩尾望', 'name_ja': '岩尾望', 'birth_year': 1975,
         'episodes': [(24, 'コンビ結成'), (28, 'M-1優勝'), (35, '俳優業'), (47, 'フジモン')]},

        # 人気芸人
        {'name': '有吉弘行', 'name_ja': '有吉弘行', 'birth_year': 1974,
         'episodes': [(20, '猿岩石デビュー'), (22, '電波少年'), (33, '再ブレイク'), (47, '結婚')]},
        {'name': 'マツコ・デラックス', 'name_ja': 'マツコ・デラックス', 'birth_year': 1972,
         'episodes': [(28, 'ゲイ雑誌編集'), (35, 'タレントデビュー'), (39, '月曜から夜ふかし'), (50, '冠番組多数')]},
        {'name': '千鳥・大悟', 'name_ja': '千鳥・大悟', 'birth_year': 1980,
         'episodes': [(20, '千鳥結成'), (33, '東京進出'), (37, 'ダイアン'), (42, '相席食堂')]},
        {'name': '千鳥・ノブ', 'name_ja': '千鳥・ノブ', 'birth_year': 1979,
         'episodes': [(21, '千鳥結成'), (34, '東京進出'), (38, 'クセがすごい'), (43, '相席食堂')]},
        {'name': 'サンドウィッチマン・伊達みきお', 'name_ja': '伊達みきお', 'birth_year': 1974,
         'episodes': [(24, 'コンビ結成'), (33, 'M-1優勝'), (37, '震災復興支援'), (48, '冠番組')]},
        {'name': 'サンドウィッチマン・富澤たけし', 'name_ja': '富澤たけし', 'birth_year': 1974,
         'episodes': [(24, 'コンビ結成'), (33, 'M-1優勝'), (40, 'カロリーゼロ理論'), (48, '冠番組')]},
    ]

    # ========== YouTuber ==========
    youtubers = [
        # トップYouTuber
        {'name': 'HIKAKIN', 'name_ja': 'HIKAKIN', 'birth_year': 1989,
         'episodes': [(17, 'YouTube開始'), (21, 'ビートボックス'), (24, 'UUUM設立'), (32, '登録者1000万人')]},
        {'name': 'はじめしゃちょー', 'name_ja': 'はじめしゃちょー', 'birth_year': 1993,
         'episodes': [(19, 'YouTube開始'), (21, '100万人突破'), (24, 'UUUM加入'), (29, '登録者1000万人')]},
        {'name': 'ヒカル', 'name_ja': 'ヒカル', 'birth_year': 1991,
         'episodes': [(19, '起業'), (25, 'YouTube開始'), (26, '炎上'), (31, 'ブランド設立')]},
        {'name': 'フィッシャーズ・シルク', 'name_ja': 'シルクロード', 'birth_year': 1994,
         'episodes': [(18, 'Fischer\'s結成'), (20, '100万人'), (25, 'UUUM'), (28, '登録者700万人')]},

        # ゲーム実況者
        {'name': 'キヨ', 'name_ja': 'キヨ', 'birth_year': 1993,
         'episodes': [(16, '実況開始'), (20, '最終兵器俺達'), (25, '400万人'), (29, 'ゲーム実況者')]},
        {'name': '牛沢', 'name_ja': '牛沢', 'birth_year': 1987,
         'episodes': [(22, 'ニコニコ動画'), (26, 'YouTube開始'), (30, '100万人'), (35, 'ゲーム実況')]},
        {'name': 'もこう', 'name_ja': 'もこう', 'birth_year': 1990,
         'episodes': [(20, 'ニコニコ開始'), (23, 'ポケモン実況'), (28, 'YouTube'), (32, '厨ポケ狩り')]},
        {'name': '加藤純一', 'name_ja': '加藤純一', 'birth_year': 1985,
         'episodes': [(24, 'ニコ生開始'), (30, 'オワコン'), (33, 'YouTube'), (37, '結婚配信')]},

        # VTuber
        {'name': 'キズナアイ', 'name_ja': 'キズナアイ', 'birth_year': 2016,  # デビュー年
         'episodes': [(0, 'デビュー'), (1, '100万人'), (2, '200万人'), (6, '活動終了')]},
        {'name': '月ノ美兎', 'name_ja': '月ノ美兎', 'birth_year': 1994,  # キャラ年齢16歳設定
         'episodes': [(16, 'にじさんじデビュー'), (17, '清楚系'), (18, '100万人'), (20, '委員長')]},
        {'name': '兎田ぺこら', 'name_ja': '兎田ぺこら', 'birth_year': 1995,  # キャラ年齢111歳設定
         'episodes': [(111, 'ホロライブ3期生'), (112, 'ぺこぺこ'), (113, '100万人'), (114, '世界的人気')]},
        {'name': 'さくらみこ', 'name_ja': 'さくらみこ', 'birth_year': 1996,  # エリート巫女設定
         'episodes': [(18, 'デビュー'), (19, 'みこち'), (20, 'FAQ'), (22, 'エリート')]},

        # 教育系
        {'name': '中田敦彦', 'name_ja': '中田敦彦', 'birth_year': 1982,
         'episodes': [(21, 'オリラジ結成'), (30, '武勇伝'), (37, 'YouTube大学'), (40, 'シンガポール移住')]},
        {'name': 'QuizKnock・伊沢拓司', 'name_ja': '伊沢拓司', 'birth_year': 1994,
         'episodes': [(16, '高校生クイズ優勝'), (22, '東大卒業'), (23, 'QuizKnock設立'), (28, 'クイズ王')]},
        {'name': 'ヨビノリたくみ', 'name_ja': 'ヨビノリたくみ', 'birth_year': 1993,
         'episodes': [(24, 'YouTube開始'), (25, '予備校講師'), (27, '100万人'), (29, '教育系')]},
    ]

    # ========== アイドル ==========
    idols = [
        # ジャニーズ
        {'name': '木村拓哉', 'name_ja': '木村拓哉', 'birth_year': 1972,
         'episodes': [(15, 'ジャニーズ入所'), (16, 'SMAP結成'), (24, 'ロンバケ'), (28, '結婚'), (44, 'SMAP解散')]},
        {'name': '中居正広', 'name_ja': '中居正広', 'birth_year': 1972,
         'episodes': [(15, 'ジャニーズ入所'), (16, 'SMAP結成'), (44, 'SMAP解散'), (48, 'ジャニーズ退所')]},
        {'name': '嵐・大野智', 'name_ja': '大野智', 'birth_year': 1980,
         'episodes': [(13, 'ジャニーズ入所'), (19, '嵐結成'), (40, '活動休止'), (42, '個人活動')]},
        {'name': '嵐・櫻井翔', 'name_ja': '櫻井翔', 'birth_year': 1982,
         'episodes': [(13, 'ジャニーズ入所'), (17, '嵐結成'), (31, 'NEWS ZERO'), (38, '活動休止')]},
        {'name': 'King & Prince・平野紫耀', 'name_ja': '平野紫耀', 'birth_year': 1997,
         'episodes': [(15, 'ジャニーズ入所'), (21, 'キンプリデビュー'), (26, '脱退'), (26, 'Number_i')]},
        {'name': 'Snow Man・目黒蓮', 'name_ja': '目黒蓮', 'birth_year': 1997,
         'episodes': [(13, 'ジャニーズ入所'), (23, 'Snow Manデビュー'), (25, 'silent'), (26, '俳優活動')]},

        # 女性アイドル
        {'name': 'AKB48・前田敦子', 'name_ja': '前田敦子', 'birth_year': 1991,
         'episodes': [(14, 'AKB加入'), (18, 'センター'), (21, '卒業'), (28, '結婚')]},
        {'name': 'AKB48・大島優子', 'name_ja': '大島優子', 'birth_year': 1988,
         'episodes': [(7, '子役'), (18, 'AKB加入'), (22, '総選挙1位'), (26, '卒業')]},
        {'name': '乃木坂46・白石麻衣', 'name_ja': '白石麻衣', 'birth_year': 1992,
         'episodes': [(19, '乃木坂加入'), (21, 'センター'), (28, '卒業'), (30, 'ソロ活動')]},
        {'name': '乃木坂46・西野七瀬', 'name_ja': '西野七瀬', 'birth_year': 1994,
         'episodes': [(17, '乃木坂加入'), (20, 'センター'), (24, '卒業'), (27, '女優')]},
        {'name': 'NiziU・マコ', 'name_ja': 'マコ', 'birth_year': 2001,
         'episodes': [(15, 'JYP練習生'), (18, '虹プロ'), (19, 'NiziUデビュー'), (21, 'リーダー')]},
        {'name': 'TWICE・サナ', 'name_ja': '湊崎紗夏', 'birth_year': 1996,
         'episodes': [(13, 'JYP練習生'), (19, 'TWICEデビュー'), (23, '日本活動'), (26, 'ソロ活動')]},
    ]

    # 声優
    voice_actors = [
        {'name': '花澤香菜', 'name_ja': '花澤香菜', 'birth_year': 1989,
         'episodes': [(14, '子役'), (17, '声優デビュー'), (21, '化物語'), (31, '結婚')]},
        {'name': '神谷浩史', 'name_ja': '神谷浩史', 'birth_year': 1975,
         'episodes': [(19, '声優デビュー'), (31, '化物語'), (37, '声優アワード'), (41, '結婚発表')]},
        {'name': '梶裕貴', 'name_ja': '梶裕貴', 'birth_year': 1985,
         'episodes': [(19, '声優デビュー'), (24, '進撃の巨人'), (34, '結婚'), (37, '声優アワード')]},
        {'name': '竹達彩奈', 'name_ja': '竹達彩奈', 'birth_year': 1989,
         'episodes': [(20, '声優デビュー'), (21, 'けいおん!'), (30, '結婚'), (32, '出産')]},
    ]

    # 全データを統合
    for person_data in comedians:
        person = create_person_entry(person_data, 'お笑い芸人', 'エンターテインメント')
        entertainers.append(person)

    for person_data in youtubers:
        person = create_person_entry(person_data, 'YouTuber', 'インターネット')
        entertainers.append(person)

    for person_data in idols:
        person = create_person_entry(person_data, 'アイドル', 'エンターテインメント')
        entertainers.append(person)

    for person_data in voice_actors:
        person = create_person_entry(person_data, '声優', 'エンターテインメント')
        entertainers.append(person)

    return entertainers

def create_person_entry(data, occupation, category):
    """人物エントリーを作成"""

    # エピソードを年齢ベースの辞書形式に変換
    episodes_dict = {}
    if 'episodes' in data:
        for age, event in data['episodes']:
            episodes_dict[str(age)] = event

    # 死亡年齢を計算
    death_age = None
    if 'death_year' in data and data['death_year'] and 'birth_year' in data:
        death_age = data['death_year'] - data['birth_year']

    return {
        'id': f"jp_{data['name'].replace(' ', '_').replace('・', '_').lower()}",
        'name': data['name'],
        'name_ja': data['name_ja'],
        'birth_year': str(data['birth_year']) if data['birth_year'] else '',
        'death_year': str(data.get('death_year', '')) if data.get('death_year') else '',
        'death_age': str(death_age) if death_age else '',
        'nationality': '日本',
        'occupation': occupation,
        'main_category': '日本サブカルチャー',
        'subcategory': occupation,
        'special_tags': category,
        'source': '手動入力',
        'wikidata_id': '',
        'description': f"日本の{occupation}",
        'key_ages': json.dumps(episodes_dict, ensure_ascii=False)
    }

def main():
    """メイン処理"""

    print("🎌 日本のエンターテイナーデータベースを作成中...")

    entertainers = create_japanese_entertainers_database()

    # CSVファイルに出力
    import csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"japanese_entertainers_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
            'nationality', 'occupation', 'main_category', 'subcategory',
            'special_tags', 'source', 'wikidata_id', 'description', 'key_ages'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(entertainers)

    # 統計を表示
    categories = {}
    for person in entertainers:
        cat = person['subcategory']
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n✅ {len(entertainers)}人のエンターテイナーを追加しました")
    print("\nカテゴリ別内訳:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}人")

    print(f"\n📄 ファイル出力: {output_file}")

    return output_file

if __name__ == "__main__":
    main()
