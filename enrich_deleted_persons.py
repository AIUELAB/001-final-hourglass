#!/usr/bin/env python3
"""
削除された人物リストにoccupationとdescriptionを追加するスクリプト
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Tuple

def get_person_info(name: str, person_id: str) -> Tuple[str, str]:
    """
    人物名から職業と説明を推定する
    
    Returns:
        tuple: (occupation, description)
    """
    
    # K-POPアーティストの判定
    kpop_members = {
        'Beomgyu': ('K-POPアーティスト', 'TOMORROW X TOGETHER (TXT)のメンバー'),
        'Cha Eun-woo': ('K-POPアーティスト・俳優', 'ASTROのメンバー、俳優としても活動'),
        'Chaeryeong': ('K-POPアーティスト', 'ITZYのメンバー'),
        'Chaeyoung': ('K-POPアーティスト', 'TWICEのメンバー'),
        'Changbin': ('K-POPアーティスト', 'Stray Kidsのメンバー、ラッパー'),
        'Chenle': ('K-POPアーティスト', 'NCT DREAMのメンバー'),
        'Dahyun': ('K-POPアーティスト', 'TWICEのメンバー'),
        'Felix Lee': ('K-POPアーティスト', 'Stray Kidsのメンバー'),
        'G-Dragon': ('K-POPアーティスト', 'BIGBANGのリーダー、ソロアーティスト'),
        'Haechan': ('K-POPアーティスト', 'NCT 127/NCT DREAMのメンバー'),
        'Han': ('K-POPアーティスト', 'Stray Kidsのメンバー'),
        'Heeseung': ('K-POPアーティスト', 'ENHYPENのメンバー'),
        'Hongjoong': ('K-POPアーティスト', 'ATEEZのリーダー'),
        'Hoshi': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Jeonghan': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Jongho': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Kang Daniel': ('K-POPアーティスト', '元Wanna Oneメンバー、ソロアーティスト'),
        'Karina': ('K-POPアーティスト', 'aespaのリーダー'),
        'Lee Know': ('K-POPアーティスト', 'Stray Kidsのメンバー'),
        'Mingi': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Mingyu': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Nayeon': ('K-POPアーティスト', 'TWICEのメンバー'),
        'Ningning': ('K-POPアーティスト', 'aespaのメンバー'),
        'Rosé': ('K-POPアーティスト', 'BLACKPINKのメンバー'),
        'S.Coups': ('K-POPアーティスト', 'SEVENTEENのリーダー'),
        'San': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Seonghwa': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Seungkwan': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Seungmin': ('K-POPアーティスト', 'Stray Kidsのメンバー'),
        'Sunghoon': ('K-POPアーティスト', 'ENHYPENのメンバー'),
        'Taeyong': ('K-POPアーティスト', 'NCTのメンバー'),
        'Vernon': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Winter': ('K-POPアーティスト', 'aespaのメンバー'),
        'Wonwoo': ('K-POPアーティスト', 'SEVENTEENのメンバー'),
        'Wooyoung': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Woozi': ('K-POPアーティスト', 'SEVENTEENのメンバー、プロデューサー'),
        'Yeji': ('K-POPアーティスト', 'ITZYのリーダー'),
        'Yeosang': ('K-POPアーティスト', 'ATEEZのメンバー'),
        'Yunho': ('K-POPアーティスト', 'ATEEZのメンバー'),
    }
    
    # ラテン音楽アーティスト
    latin_artists = {
        'オズナ': ('レゲトンアーティスト', 'プエルトリコのレゲトン・ラテントラップアーティスト'),
        'ルイス・フォンシ': ('歌手', 'プエルトリコの歌手、「Despacito」で世界的に有名'),
        'マルマ': ('レゲトンアーティスト', 'コロンビアのレゲトンアーティスト'),
        'ラウ・アレハンドロ': ('レゲトンアーティスト', 'プエルトリコのレゲトンアーティスト'),
        'ミスター・イージー': ('レゲエアーティスト', 'パナマのレゲエ・ダンスホールアーティスト'),
    }
    
    # インド・パキスタン音楽アーティスト
    south_asian_artists = {
        'ラハット・ファテ・アリ・ハーン': ('カッワーリー歌手', 'パキスタンのカッワーリー歌手'),
        'ソヌ・ニガム': ('歌手', 'インドのボリウッド歌手'),
        'アーシャ・ボースレー': ('歌手', 'インドの伝説的プレイバックシンガー'),
        'アーティフ・アスラム': ('歌手', 'パキスタンの歌手'),
        'アリジット・シン': ('歌手', 'インドのボリウッド歌手'),
    }
    
    # アフリカ音楽アーティスト
    african_artists = {
        'イエミ・アラデ': ('歌手', 'ナイジェリアのアフロポップ歌手'),
        'ダイヤモンド・プラトナムズ': ('歌手', 'タンザニアのボンゴ・フラーヴァアーティスト'),
        'ファイアーボーイ・DML': ('歌手', 'ナイジェリアのアフロビーツアーティスト'),
        'サウティ・ソル': ('音楽グループ', 'ケニアのアフロポップバンド'),
        'CKay': ('歌手', 'ナイジェリアのアフロビーツアーティスト'),
        'レマ': ('歌手', 'ナイジェリアのアフロビーツアーティスト'),
        'マスターKG': ('音楽プロデューサー', '南アフリカのハウスミュージックプロデューサー'),
    }
    
    # アラブ音楽アーティスト
    arab_artists = {
        'カーディム・アッ＝サーヒル': ('歌手', 'イラクの歌手、作曲家'),
    }
    
    # 学者・研究者
    scholars = {
        'ジョシュア・アングリスト': ('経済学者', 'ノーベル経済学賞受賞者'),
        'ナルゲス・モハンマディ': ('人権活動家', 'イランの人権活動家、ノーベル平和賞受賞者'),
    }
    
    # 日本人の一般的な名前（職業不明）
    japanese_common_names = [
        '鈴木', '高橋', '田中', '渡辺', '伊藤', '山本', '中村', '小林', '加藤', '吉田',
        '山田', '佐々木', '山口', '松本', '井上', '木村', '林', '斎藤', '清水', '山崎'
    ]
    
    # 職業と説明を決定
    if name in kpop_members:
        return kpop_members[name]
    elif name in latin_artists:
        return latin_artists[name]
    elif name in south_asian_artists:
        return south_asian_artists[name]
    elif name in african_artists:
        return african_artists[name]
    elif name in arab_artists:
        return arab_artists[name]
    elif name in scholars:
        return scholars[name]
    else:
        # 日本人の一般的な名前かチェック
        for surname in japanese_common_names:
            if name.startswith(surname):
                return ('一般人', f'{surname}姓の一般的な日本人名')
        
        # その他の外国人名
        if any(c.isalpha() and ord(c) < 128 for c in name):
            # アルファベットが含まれる場合
            return ('不明', '職業・活動内容不明の人物')
        else:
            # 日本語のみの場合
            return ('一般人', '特定の有名人ではない一般的な名前')

def main():
    """メイン処理"""
    
    input_file = 'deleted_persons_score_under_4_summary_20250910_123007.csv'
    output_file = f'deleted_persons_enriched_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    # CSVファイルを読み込む
    persons = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            persons.append(row)
    
    print(f"読み込んだ人物数: {len(persons)}")
    
    # 各人物に職業と説明を追加
    occupation_stats = {}
    for person in persons:
        name = person['name']
        person_id = person['person_id']
        
        occupation, description = get_person_info(name, person_id)
        person['occupation'] = occupation
        person['description'] = description
        
        # 統計情報を収集
        if occupation not in occupation_stats:
            occupation_stats[occupation] = 0
        occupation_stats[occupation] += 1
    
    # 新しいCSVファイルに書き込む
    fieldnames = ['person_id', 'name', 'score', 'reason', 'wikipedia_found', 'occupation', 'description']
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(persons)
    
    print(f"\n職業と説明を追加したファイルを作成しました: {output_file}")
    
    # 統計情報を表示
    print("\n職業別の人数:")
    for occupation, count in sorted(occupation_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {occupation}: {count}人")
    
    # サンプルを表示
    print("\n追加された情報のサンプル（最初の10件）:")
    for person in persons[:10]:
        print(f"  {person['name']}: {person['occupation']} - {person['description']}")

if __name__ == '__main__':
    main()