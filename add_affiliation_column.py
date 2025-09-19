#!/usr/bin/env python3
"""
事務所・レーベル情報をaffiliationカラムとして追加するスクリプト
"""

import pandas as pd
from datetime import datetime
import json

def create_affiliation_mapping():
    """主要人物の事務所・レーベルマッピングを作成"""

    mapping = {
        # YouTuber/デジタルクリエイター
        'HIKAKIN': 'UUUM',
        'はじめしゃちょー': 'UUUM',
        'フィッシャーズ': 'UUUM',
        '東海オンエア': 'UUUM',
        'ヒカル': 'VAZ',
        'ラファエル': 'マネージメント契約なし',
        'きりたんぽ': 'UUUM',
        'コムドット': 'エイベックス',
        'スカイピース': 'VAZ',
        'フワちゃん': 'フワちゃんTV',

        # VTuber
        'さくらみこ': 'ホロライブプロダクション',
        '兎田ぺこら': 'ホロライブプロダクション',
        '宝鐘マリン': 'ホロライブプロダクション',
        '湊あくあ': 'ホロライブプロダクション',
        '星街すいせい': 'ホロライブプロダクション',
        '月ノ美兎': 'にじさんじ',
        '葛葉': 'にじさんじ',
        '叶': 'にじさんじ',

        # 音楽アーティスト（ソロ）
        'Ado': 'クラウドナイン',
        '米津玄師': 'reissue records',
        '藤井風': 'ユニバーサルミュージック',
        'あいみょん': 'ワーナーミュージック・ジャパン',
        'YOASOBI': 'ソニー・ミュージック',
        'Ayase（YOASOBI）': 'ソニー・ミュージック',
        'ikura（YOASOBI）': 'ソニー・ミュージック',
        '髭男dism': 'ポニーキャニオン',
        'King Gnu': 'ソニー・ミュージック',
        'Mrs. GREEN APPLE': 'ユニバーサルミュージック',
        '優里': 'ソニー・ミュージック',
        'Vaundy': 'SDR',

        # バンド・グループ
        'SEKAI NO OWARI': 'トイズファクトリー',
        'Fukase（SEKAI NO OWARI）': 'トイズファクトリー',
        'ONE OK ROCK': 'アミューズ',
        'RADWIMPS': 'ユニバーサルミュージック',
        'サカナクション': 'ビクターエンタテインメント',
        'BUMP OF CHICKEN': 'トイズファクトリー',
        'back number': 'ユニバーサルミュージック',

        # ジャニーズ系（現SMILE-UP.）
        '嵐': 'ジャニーズ事務所（当時）',
        '大野智（嵐）': 'ジャニーズ事務所（当時）',
        '櫻井翔（嵐）': 'ジャニーズ事務所（当時）',
        '相葉雅紀（嵐）': 'ジャニーズ事務所（当時）',
        '二宮和也（嵐）': 'ジャニーズ事務所（当時）',
        '松本潤（嵐）': 'ジャニーズ事務所（当時）',
        'King & Prince': 'SMILE-UP.',
        'SixTONES': 'SMILE-UP.',
        'Snow Man': 'SMILE-UP.',
        'なにわ男子': 'SMILE-UP.',

        # K-POP
        'BTS': 'BIGHIT MUSIC',
        'RM（BTS）': 'BIGHIT MUSIC',
        'Jin（BTS）': 'BIGHIT MUSIC',
        'SUGA（BTS）': 'BIGHIT MUSIC',
        'J-Hope（BTS）': 'BIGHIT MUSIC',
        'Jimin（BTS）': 'BIGHIT MUSIC',
        'V（BTS）': 'BIGHIT MUSIC',
        'Jungkook（BTS）': 'BIGHIT MUSIC',
        'BLACKPINK': 'YG Entertainment',
        'Stray Kids': 'JYP Entertainment',
        'SEVENTEEN': 'PLEDIS Entertainment',
        'TWICE': 'JYP Entertainment',
        'ENHYPEN': 'BELIFT LAB',

        # 女性アイドルグループ
        '乃木坂46': '乃木坂46合同会社',
        '櫻坂46': 'Seed & Flower合同会社',
        '日向坂46': 'Seed & Flower合同会社',
        'AKB48': 'DH',
        'NiziU': 'JYP Entertainment Japan',
        'モーニング娘。': 'アップフロント',

        # お笑い芸人
        'ダウンタウン': '吉本興業',
        '松本人志（ダウンタウン）': '吉本興業',
        '浜田雅功（ダウンタウン）': '吉本興業',
        'ナインティナイン': '吉本興業',
        '岡村隆史（ナインティナイン）': '吉本興業',
        '矢部浩之（ナインティナイン）': '吉本興業',
        '千鳥': '吉本興業',
        '大悟（千鳥）': '吉本興業',
        'ノブ（千鳥）': '吉本興業',
        'サンドウィッチマン': 'グレープカンパニー',
        '伊達みきお（サンドウィッチマン）': 'グレープカンパニー',
        '富澤たけし（サンドウィッチマン）': 'グレープカンパニー',
        '霜降り明星': '吉本興業',
        'せいや（霜降り明星）': '吉本興業',
        '粗品（霜降り明星）': '吉本興業',
        'かまいたち': '吉本興業',
        '山内健司（かまいたち）': '吉本興業',
        '濱家隆一（かまいたち）': '吉本興業',
        'オードリー': 'ケイダッシュ',
        '若林正恭（オードリー）': 'ケイダッシュ',
        '春日俊彰（オードリー）': 'ケイダッシュ',
        '有吉弘行': '太田プロダクション',
        'マツコ・デラックス': 'ナチュラルエイト',

        # 俳優・女優
        '木村拓哉': 'ジャニーズ事務所（当時）',
        '福山雅治': 'アミューズ',
        '佐藤健': 'アミューズ',
        '菅田将暉': 'トップコート',
        '山田涼介': 'SMILE-UP.',
        '横浜流星': 'スターダストプロモーション',
        '吉沢亮': 'アミューズ',
        '新垣結衣': 'レプロエンタテインメント',
        '石原さとみ': 'ホリプロ',
        '有村架純': 'フラーム',
        '広瀬すず': 'フォスタープラス',
        '橋本環奈': 'ディスカバリー・ネクスト',
        '浜辺美波': '東宝芸能',
        '今田美桜': 'コンテンツ3',

        # 声優
        '花江夏樹': 'アクロスエンタテインメント',
        '鬼頭明里': 'ラクーンドッグ',
        '梶裕貴': 'ヴィムス',
        '竹達彩奈': 'リンク・プラン',
        '悠木碧': 'プロ・フィット',
        '佐倉綾音': 'アイムエンタープライズ',
        '水瀬いのり': 'アクセルワン',

        # スポーツ選手
        '大谷翔平': 'CAA（Creative Artists Agency）',
        '羽生結弦': 'フリー',
        '井上尚弥': '大橋ボクシングジム',
        '八村塁': 'エイジェント契約',
        '久保建英': 'UDN SPORTS',
    }

    return mapping

def apply_occupation_based_rules(df):
    """職業ベースのルールを適用"""

    rules = []

    # お笑い芸人のルール
    comedians_yoshimoto = df[(df['occupation'] == 'お笑い芸人') &
                             (df['affiliation'].isna())].index[:50]  # 上位50人を吉本と推定
    for idx in comedians_yoshimoto:
        rules.append((idx, '吉本興業（推定）'))

    # YouTuberのルール
    youtubers_uuum = df[(df['occupation'] == 'YouTuber') &
                        (df['affiliation'].isna()) &
                        (df['category'].isin(['その他', '現代のイノベーター']))].index[:20]
    for idx in youtubers_uuum:
        rules.append((idx, 'UUUM（推定）'))

    # VTuberのルール
    vtubers = df[(df['occupation'] == 'VTuber') &
                 (df['affiliation'].isna())].index
    for idx in vtubers[:10]:
        rules.append((idx, 'ホロライブ/にじさんじ（推定）'))

    return rules

def main():
    print("=" * 50)
    print("事務所・レーベル情報カラム追加処理")
    print("=" * 50)

    # CSVファイルを読み込み
    input_file = 'ultra_think_database_export_20250915_123207.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # カラム位置を確認
    columns = list(df.columns)
    occupation_index = columns.index('occupation')
    print(f"✅ occupation列の位置: {occupation_index + 1}番目（{columns[occupation_index]}）")

    # affiliationカラムを追加（occupationの直後）
    new_columns = columns[:occupation_index + 1] + ['affiliation'] + columns[occupation_index + 1:]
    df = df.reindex(columns=new_columns)
    print(f"✅ affiliationカラムを追加（{occupation_index + 2}番目）")

    # マッピングデータを作成
    affiliation_mapping = create_affiliation_mapping()
    print(f"✅ 事務所マッピングデータ: {len(affiliation_mapping)}件")

    # マッピングを適用
    mapped_count = 0
    for person_name, affiliation in affiliation_mapping.items():
        # person_name_displayで検索
        mask = df['person_name_display'] == person_name
        if mask.any():
            df.loc[mask, 'affiliation'] = affiliation
            mapped_count += mask.sum()

        # person_nameでも検索（表記ゆれ対応）
        mask2 = df['person_name'] == person_name
        if mask2.any():
            df.loc[mask2, 'affiliation'] = affiliation
            mapped_count += mask2.sum()

    print(f"✅ 手動マッピング適用: {mapped_count}件")

    # 職業ベースのルールを適用
    rules = apply_occupation_based_rules(df)
    for idx, affiliation in rules:
        if pd.isna(df.loc[idx, 'affiliation']):
            df.loc[idx, 'affiliation'] = affiliation
    print(f"✅ ルールベース推定適用: {len(rules)}件")

    # 統計情報
    filled_count = df['affiliation'].notna().sum()
    fill_rate = (filled_count / len(df)) * 100
    print(f"\n📊 統計情報:")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - affiliation入力済み: {filled_count:,}件")
    print(f"  - 入力率: {fill_rate:.1f}%")

    # 新しいファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_with_affiliation_{timestamp}.csv'

    # UTF-8 BOM付きで保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - カラム数: {len(df.columns)}")
    print(f"  - affiliationカラム位置: {new_columns.index('affiliation') + 1}番目（E列）")

    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n完了！出力ファイル: {output_file}")