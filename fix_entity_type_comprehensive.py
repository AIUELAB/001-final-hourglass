#!/usr/bin/env python3
"""
entity_type包括的修復スクリプト
全4,706件のentity_typeを適切に設定
"""

import pandas as pd
import json
from datetime import datetime
import shutil
from pathlib import Path

# 既知のグループリスト（大幅拡張）
KNOWN_GROUPS = {
    # ジャニーズ/SMILE-UP
    '嵐', 'SMAP', 'TOKIO', '関ジャニ∞', 'King & Prince', 'SixTONES', 'Snow Man',
    'NEWS', 'KAT-TUN', 'Hey! Say! JUMP', 'Kis-My-Ft2', 'A.B.C-Z', 'ジャニーズWEST',
    'なにわ男子', 'V6', 'KinKi Kids', '少年隊', 'タッキー&翼',
    
    # 女性アイドルグループ
    'AKB48', '乃木坂46', '櫻坂46', '日向坂46', 'NMB48', 'SKE48', 'HKT48', 'NGT48',
    'STU48', 'モーニング娘。', 'ももいろクローバーZ', 'Perfume', 'BABYMETAL',
    '私立恵比寿中学', 'でんぱ組.inc', 'BiSH', 'PASSPO☆',
    
    # K-POPグループ
    'BTS', 'BLACKPINK', 'TWICE', 'Stray Kids', 'SEVENTEEN', 'ENHYPEN', 'NCT',
    'TXT', 'ATEEZ', 'TREASURE', 'IZ*ONE', 'LE SSERAFIM', 'NewJeans', 'ニュージーンズ',
    'BIGBANG', 'ビッグバン', 'EXO', 'SHINee', 'SUPER JUNIOR', '2PM', 'GOT7',
    'MONSTA X', 'ITZY', 'aespa', 'NMIXX', '(G)I-DLE', 'KARA', '少女時代',
    
    # バンド・音楽グループ
    'Mr.Children', 'サザンオールスターズ', 'B\'z', 'GLAY', 'L\'Arc~en~Ciel',
    'BUMP OF CHICKEN', 'RADWIMPS', 'ONE OK ROCK', 'back number', 'Official髭男dism',
    'King Gnu', 'Mrs. GREEN APPLE', 'SEKAI NO OWARI', 'ゲスの極み乙女。',
    'サカナクション', 'ASIAN KUNG-FU GENERATION', '[Alexandros]', 'UVERworld',
    'MAN WITH A MISSION', 'DREAMS COME TRUE', 'EXILE', '三代目 J SOUL BROTHERS',
    'GENERATIONS', 'THE RAMPAGE', 'FANTASTICS', 'BALLISTIK BOYZ',
    
    # お笑いコンビ・トリオ
    '千原兄弟', 'ダウンタウン', 'ウッチャンナンチャン', 'とんねるず', 'ナインティナイン',
    'さまぁ～ず', 'くりぃむしちゅー', '爆笑問題', 'オードリー', 'サンドウィッチマン',
    'バナナマン', '東京03', 'ロバート', 'TKO', 'ノンスタイル', 'ブラックマヨネーズ',
    'チュートリアル', 'フットボールアワー', '笑い飯', 'ハライチ', 'かまいたち',
    'ミルクボーイ', '霜降り明星', 'ぺこぱ', '見取り図', 'EXIT', 'ミキ',
    'アインシュタイン', 'ジャルジャル', '和牛', 'メイプル超合金', '南海キャンディーズ',
    
    # その他のグループ
    'ハロー！プロジェクト', 'E-girls', 'AAA', 'Da-iCE', 'w-inds.', 'CHEMISTRY',
    'ゆず', 'コブクロ', 'スキマスイッチ', 'いきものがかり', 'フジファブリック',
    'アジカン', 'マキシマム ザ ホルモン', 'ケツメイシ', 'FUNKY MONKEY BABYS',
}

# 組織・団体を示すパターン
ORGANIZATION_PATTERNS = [
    '機関', '組織', '財団', '協会', '連盟', '委員会', '省', '庁',
    'プログラム', 'Programme', 'Organization', 'Foundation',
    'Association', 'Committee', 'Agency', 'Ministry'
]

# グループメンバー情報（主要なもの）
GROUP_MEMBERS = {
    'King Gnu': ['常田大希', '井口理', '新井和輝', '勢喜遊'],
    '千原兄弟': ['千原ジュニア', '千原せいじ'],
    'TXT': ['ヨンジュン', 'スビン', 'ボムギュ', 'テヒョン', 'ヒュニンカイ'],
    'NCT': ['ヘチャン', 'マーク', 'テヨン', 'ジェヒョン', 'ドヨン', 'ジョンウ'],
    'SEVENTEEN': ['スングァン', 'エスクプス', 'ジョンハン', 'ジョシュア', 'ジュン',
                   'ホシ', 'ウォヌ', 'ウジ', 'ドギョム', 'ミンギュ', 'バーノン', 'ディノ'],
}

def detect_entity_type(row):
    """entity_typeを判定"""
    person_name = str(row.get('person_name_ja', ''))
    person_name_en = str(row.get('person_name', ''))
    nationality = str(row.get('nationality', ''))
    occupation = str(row.get('occupation', ''))
    
    # 1. 組織チェック
    if nationality == '国際組織':
        return 'organization'
    
    for pattern in ORGANIZATION_PATTERNS:
        if pattern in person_name or pattern in occupation:
            return 'organization'
    
    # 2. グループチェック
    if person_name in KNOWN_GROUPS or person_name_en in KNOWN_GROUPS:
        return 'group'
    
    # 3. 架空キャラクターチェック（extended_dataから）
    try:
        if pd.notna(row.get('extended_data')):
            ext_data = json.loads(row['extended_data'])
            if ext_data.get('is_fictional') == 'TRUE':
                return 'fictional_character'
    except:
        pass
    
    # 4. デフォルトは個人
    return 'person'

def get_group_for_member(person_name):
    """メンバーが所属するグループを取得"""
    for group, members in GROUP_MEMBERS.items():
        if person_name in members:
            return group
    return None

def fix_entity_types():
    """entity_type修復のメイン処理"""
    print("="*60)
    print("🔧 entity_type包括的修復")
    print("="*60)
    
    # バックアップ作成
    csv_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(csv_file, backup_file)
    print(f"📦 バックアップ作成: {backup_file}")
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📂 データ読み込み: {len(df)}件")
    
    # 現状分析
    print("\n📊 現在のentity_type分布:")
    if 'entity_type' in df.columns:
        current_dist = df['entity_type'].value_counts(dropna=False)
        print(current_dist)
    else:
        df['entity_type'] = None
        print("  entity_typeフィールドなし（新規作成）")
    
    # entity_type判定と設定
    print("\n🔄 entity_type判定中...")
    entity_types = []
    groups_found = []
    orgs_found = []
    
    for idx, row in df.iterrows():
        entity_type = detect_entity_type(row)
        entity_types.append(entity_type)
        
        if entity_type == 'group':
            groups_found.append(f"{row['person_id']}: {row['person_name_ja']}")
        elif entity_type == 'organization':
            orgs_found.append(f"{row['person_id']}: {row['person_name_ja']}")
        
        if idx % 500 == 0:
            print(f"  処理中: {idx}/{len(df)}")
    
    df['entity_type'] = entity_types
    
    # 結果集計
    print("\n📊 修正後のentity_type分布:")
    new_dist = df['entity_type'].value_counts()
    print(new_dist)
    
    # 発見されたグループと組織
    print(f"\n🎵 グループとして分類: {len(groups_found)}件")
    for group in groups_found[:10]:
        print(f"  - {group}")
    if len(groups_found) > 10:
        print(f"  ... 他 {len(groups_found)-10}件")
    
    print(f"\n🏢 組織として分類: {len(orgs_found)}件")
    for org in orgs_found[:5]:
        print(f"  - {org}")
    
    # 特定の問題修正
    print("\n🔧 個別問題の修正:")
    
    # P015953 マルクス・アウレリウスのdisplay名修正
    df.loc[df['person_id'] == 'P015953', 'person_name_display'] = 'マルクス・アウレリウス'
    print("  ✅ P015953: display名を'マルクス・アウレリウス'に修正")
    
    # ニュージーンズとビッグバンをグループに
    df.loc[df['person_id'] == 'P015898', 'entity_type'] = 'group'
    df.loc[df['person_id'] == 'P015901', 'entity_type'] = 'group'
    print("  ✅ P015898, P015901: グループに変更")
    
    # 保存
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 修正データ保存: {csv_file}")
    print(f"📊 総レコード数: {len(df)}件")
    
    # 品質検証
    print("\n✅ 品質検証:")
    null_count = df['entity_type'].isna().sum()
    print(f"  entity_type NULL: {null_count}件 ({null_count/len(df)*100:.1f}%)")
    print(f"  entity_type 充填率: {(len(df)-null_count)/len(df)*100:.1f}%")
    
    return df

if __name__ == "__main__":
    df = fix_entity_types()
    print("\n✅ entity_type修復完了")