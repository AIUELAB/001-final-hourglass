#!/usr/bin/env python3
"""
グループメンバー判定カラムを追加するスクリプト
F列: activity_type（個人/グループメンバー）
G列: group_name（所属グループ名）
"""

import pandas as pd
import re
from datetime import datetime
import json

def create_group_member_mapping():
    """既知のグループメンバーマッピングを作成"""

    mapping = {
        # BTS
        'RM': 'BTS',
        'Jin': 'BTS',
        'SUGA': 'BTS',
        'J-Hope': 'BTS',
        'Jimin': 'BTS',
        'V': 'BTS',
        'Jungkook': 'BTS',

        # 嵐
        '大野智': '嵐',
        '櫻井翔': '嵐',
        '相葉雅紀': '嵐',
        '二宮和也': '嵐',
        '松本潤': '嵐',

        # X JAPAN
        'YOSHIKI': 'X JAPAN',
        'Toshl': 'X JAPAN',
        'hide': 'X JAPAN',
        'PATA': 'X JAPAN',
        'HEATH': 'X JAPAN',

        # GLAY
        'TERU': 'GLAY',
        'TAKURO': 'GLAY',
        'HISASHI': 'GLAY',
        'JIRO': 'GLAY',

        # LUNA SEA
        'RYUICHI': 'LUNA SEA',
        'SUGIZO': 'LUNA SEA',
        'INORAN': 'LUNA SEA',
        'J': 'LUNA SEA',
        '真矢': 'LUNA SEA',

        # ONE OK ROCK
        'Taka': 'ONE OK ROCK',
        'Toru': 'ONE OK ROCK',
        'Ryota': 'ONE OK ROCK',
        'Tomoya': 'ONE OK ROCK',

        # SEKAI NO OWARI
        'Fukase': 'SEKAI NO OWARI',
        'Nakajin': 'SEKAI NO OWARI',
        'Saori': 'SEKAI NO OWARI',
        'DJ LOVE': 'SEKAI NO OWARI',

        # YOASOBI
        'Ayase': 'YOASOBI',
        'ikura': 'YOASOBI',

        # お笑いコンビ - ダウンタウン
        '松本人志': 'ダウンタウン',
        '浜田雅功': 'ダウンタウン',

        # お笑いコンビ - ナインティナイン
        '岡村隆史': 'ナインティナイン',
        '矢部浩之': 'ナインティナイン',

        # お笑いコンビ - 千鳥
        '大悟': '千鳥',
        'ノブ': '千鳥',

        # お笑いコンビ - サンドウィッチマン
        '伊達みきお': 'サンドウィッチマン',
        '富澤たけし': 'サンドウィッチマン',

        # お笑いコンビ - 霜降り明星
        'せいや': '霜降り明星',
        '粗品': '霜降り明星',

        # お笑いコンビ - かまいたち
        '山内健司': 'かまいたち',
        '濱家隆一': 'かまいたち',

        # お笑いコンビ - オードリー
        '若林正恭': 'オードリー',
        '春日俊彰': 'オードリー',

        # お笑いコンビ - 南海キャンディーズ
        '山里亮太': '南海キャンディーズ',
        'しずちゃん': '南海キャンディーズ',

        # お笑いトリオ - 3時のヒロイン
        'かなで': '3時のヒロイン',
        'ゆめっち': '3時のヒロイン',
        '福田麻貴': '3時のヒロイン',

        # お笑いグループ - ぼる塾
        'あんり': 'ぼる塾',
        'きりやはるか': 'ぼる塾',
        '田辺智加': 'ぼる塾',
        '酒寄希望': 'ぼる塾',

        # King & Prince
        '永瀬廉': 'King & Prince',
        '平野紫耀': 'King & Prince',
        '高橋海人': 'King & Prince',
        '岸優太': 'King & Prince',
        '神宮寺勇太': 'King & Prince',

        # Snow Man
        '深澤辰哉': 'Snow Man',
        '佐久間大介': 'Snow Man',
        '渡辺翔太': 'Snow Man',
        '宮舘涼太': 'Snow Man',
        '岩本照': 'Snow Man',
        '阿部亮平': 'Snow Man',
        '向井康二': 'Snow Man',
        '目黒蓮': 'Snow Man',
        'ラウール': 'Snow Man',

        # SixTONES
        'ジェシー': 'SixTONES',
        '京本大我': 'SixTONES',
        '松村北斗': 'SixTONES',
        '髙地優吾': 'SixTONES',
        '森本慎太郎': 'SixTONES',
        '田中樹': 'SixTONES',

        # 乃木坂46（一部メンバー）
        '齋藤飛鳥': '乃木坂46',
        '生田絵梨花': '乃木坂46',
        '白石麻衣': '乃木坂46',
        '西野七瀬': '乃木坂46',
        '橋本奈々未': '乃木坂46',

        # NiziU
        'マコ': 'NiziU',
        'リオ': 'NiziU',
        'マヤ': 'NiziU',
        'リク': 'NiziU',
        'アヤカ': 'NiziU',
        'マユカ': 'NiziU',
        'リマ': 'NiziU',
        'ミイヒ': 'NiziU',
        'ニナ': 'NiziU',
    }

    return mapping

def extract_group_from_display_name(display_name):
    """
    person_name_displayからグループ名を抽出
    例: "Ayase（YOASOBI）" → "YOASOBI"
    """
    if pd.isna(display_name):
        return None

    # カッコ内の文字列を抽出（全角・半角両対応）
    match = re.search(r'[（(](.+?)[）)]', display_name)
    if match:
        return match.group(1)

    return None

def determine_activity_type_and_group(row, known_groups):
    """
    活動形態とグループ名を判定

    Returns:
        tuple: (activity_type, group_name)
    """
    display_name = row['person_name_display']
    person_name = row['person_name']

    # 1. person_name_displayのカッコから判定
    group_from_display = extract_group_from_display_name(display_name)
    if group_from_display:
        return 'group_member', group_from_display

    # 2. 既知のグループメンバーリストから判定
    # display_nameで検索
    if display_name in known_groups:
        return 'group_member', known_groups[display_name]

    # person_nameでも検索
    if person_name in known_groups:
        return 'group_member', known_groups[person_name]

    # 3. 名前の一部でマッチング（姓名分離対応）
    for member_name, group_name in known_groups.items():
        if pd.notna(display_name) and member_name in display_name:
            return 'group_member', group_name

    # 4. デフォルトは個人
    return 'individual', ''

def main():
    print("=" * 60)
    print("グループメンバー判定カラム追加処理")
    print("=" * 60)

    # CSVファイルを読み込み
    input_file = 'ultra_think_with_affiliation_20250915_124801.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # カラム位置を確認
    columns = list(df.columns)
    affiliation_index = columns.index('affiliation')
    print(f"✅ affiliation列の位置: {affiliation_index + 1}番目")

    # F列とG列を追加（affiliationの直後）
    new_columns = (columns[:affiliation_index + 1] +
                  ['activity_type', 'group_name'] +
                  columns[affiliation_index + 1:])

    # データフレームを再構成
    df = df.reindex(columns=new_columns)
    print(f"✅ activity_type列を追加（{affiliation_index + 2}番目・F列）")
    print(f"✅ group_name列を追加（{affiliation_index + 3}番目・G列）")

    # グループメンバーマッピングを作成
    known_groups = create_group_member_mapping()
    print(f"✅ 既知グループメンバー: {len(known_groups)}件")

    # 判定ロジックを適用
    group_member_count = 0
    individual_count = 0

    for idx, row in df.iterrows():
        activity_type, group_name = determine_activity_type_and_group(row, known_groups)
        df.at[idx, 'activity_type'] = activity_type
        df.at[idx, 'group_name'] = group_name

        if activity_type == 'group_member':
            group_member_count += 1
        else:
            individual_count += 1

    print(f"\n📊 判定結果:")
    print(f"  - グループメンバー: {group_member_count:,}件")
    print(f"  - 個人: {individual_count:,}件")

    # グループ別の統計
    group_stats = df[df['activity_type'] == 'group_member']['group_name'].value_counts().head(20)
    print(f"\n📊 主要グループ（上位20）:")
    for group, count in group_stats.items():
        print(f"  - {group}: {count}件")

    # 新しいファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_with_groups_{timestamp}.csv'

    # UTF-8 BOM付きで保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - カラム数: {len(df.columns)}")
    print(f"  - activity_typeカラム位置: {new_columns.index('activity_type') + 1}番目（F列）")
    print(f"  - group_nameカラム位置: {new_columns.index('group_name') + 1}番目（G列）")

    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n完了！出力ファイル: {output_file}")