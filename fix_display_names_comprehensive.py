#!/usr/bin/env python3
"""
person_name_display包括的修正スクリプト
グループメンバーへの括弧追加、韓国アーティストの日本語表記化など
"""

import pandas as pd
import json
from datetime import datetime
import shutil
import re

# グループメンバー情報（拡張版）
GROUP_MEMBERS = {
    # バンド
    'King Gnu': ['常田大希', '井口理', '新井和輝', '勢喜遊'],
    'Official髭男dism': ['藤原聡', '小笹大輔', '楢崎誠', '松浦匡希'],
    'Mrs. GREEN APPLE': ['大森元貴', '若井滉斗', '藤澤涼架'],
    'back number': ['清水依与吏', '小島和也', '栗原寿'],
    
    # お笑いコンビ・トリオ
    '千原兄弟': ['千原ジュニア', '千原せいじ'],
    'ダウンタウン': ['松本人志', '浜田雅功'],
    'ウッチャンナンチャン': ['内村光良', '南原清隆'],
    'ナインティナイン': ['岡村隆史', '矢部浩之'],
    'オードリー': ['若林正恭', '春日俊彰'],
    'サンドウィッチマン': ['伊達みきお', '富澤たけし'],
    'バナナマン': ['設楽統', '日村勇紀'],
    '東京03': ['飯塚悟志', '豊本明長', '角田晃広'],
    
    # K-POPグループ
    'TXT': ['ヨンジュン', 'スビン', 'ボムギュ', 'テヒョン', 'ヒュニンカイ'],
    'NCT': ['ヘチャン', 'マーク', 'テヨン', 'ジェヒョン', 'ドヨン', 'ジョンウ', 
            'ユウタ', 'ジェミン', 'チョンロ', 'チソン', 'ジェノ'],
    'SEVENTEEN': ['スングァン', 'エスクプス', 'ジョンハン', 'ジョシュア', 'ジュン',
                   'ホシ', 'ウォヌ', 'ウジ', 'ドギョム', 'ミンギュ', 'バーノン', 'ディノ'],
    'BTS': ['RM', 'ジン', 'シュガ', 'J-HOPE', 'ジミン', 'V', 'ジョングク'],
    'Stray Kids': ['バンチャン', 'リノ', 'チャンビン', 'ヒョンジン', 'ハン', 
                   'フィリックス', 'スンミン', 'アイエン'],
    'ENHYPEN': ['ヒスン', 'ジェイ', 'ジェイク', 'ソンフン', 'ソヌ', 'ジョンウォン', 'ニキ'],
    
    # ジャニーズ/SMILE-UP
    '嵐': ['大野智', '櫻井翔', '相葉雅紀', '二宮和也', '松本潤'],
    'SMAP': ['中居正広', '木村拓哉', '稲垣吾郎', '草彅剛', '香取慎吾'],
    'TOKIO': ['城島茂', '山口達也', '国分太一', '松岡昌宏', '長瀬智也'],
    'V6': ['坂本昌行', '長野博', '井ノ原快彦', '森田剛', '三宅健', '岡田准一'],
    'KinKi Kids': ['堂本光一', '堂本剛'],
    'King & Prince': ['平野紫耀', '永瀬廉', '髙橋海人', '岸優太', '神宮寺勇太'],
    'SixTONES': ['ジェシー', '京本大我', '松村北斗', '髙地優吾', '森本慎太郎', '田中樹'],
    'Snow Man': ['岩本照', '深澤辰哉', '渡辺翔太', '向井康二', '阿部亮平', 
                 '目黒蓮', '宮舘涼太', '佐久間大介', 'ラウール'],
}

# 韓国名の日本語変換辞書
KOREAN_TO_JAPANESE = {
    'Yeonjun': 'ヨンジュン',
    'Haechan': 'ヘチャン',
    'Seungkwan': 'スングァン',
    'Soobin': 'スビン',
    'Beomgyu': 'ボムギュ',
    'Taehyun': 'テヒョン',
    'Hueningkai': 'ヒュニンカイ',
    'Mark': 'マーク',
    'Taeyong': 'テヨン',
    'Jaehyun': 'ジェヒョン',
    'Doyoung': 'ドヨン',
    'Johnny': 'ジョニー',
    'Yuta': 'ユウタ',
    'Jungwoo': 'ジョンウ',
    'S.Coups': 'エスクプス',
    'Jeonghan': 'ジョンハン',
    'Joshua': 'ジョシュア',
    'Jun': 'ジュン',
    'Hoshi': 'ホシ',
    'Wonwoo': 'ウォヌ',
    'Woozi': 'ウジ',
    'DK': 'ドギョム',
    'Mingyu': 'ミンギュ',
    'The8': 'ディエイト',
    'Vernon': 'バーノン',
    'Dino': 'ディノ',
}

def get_group_for_member(person_name):
    """メンバーが所属するグループを取得"""
    for group, members in GROUP_MEMBERS.items():
        if person_name in members:
            return group
    return None

def convert_korean_to_japanese(name):
    """韓国アーティスト名を日本語に変換"""
    # 完全一致
    if name in KOREAN_TO_JAPANESE:
        return KOREAN_TO_JAPANESE[name]
    
    # 部分一致（名前の一部が辞書にある場合）
    for eng, jpn in KOREAN_TO_JAPANESE.items():
        if eng.lower() in name.lower():
            return jpn
    
    return None

def fix_display_name(row):
    """person_name_displayを修正"""
    person_name_ja = str(row.get('person_name_ja', ''))
    person_name = str(row.get('person_name', ''))
    current_display = str(row.get('person_name_display', ''))
    nationality = str(row.get('nationality', ''))
    entity_type = str(row.get('entity_type', ''))
    
    # グループ自体はそのまま
    if entity_type == 'group':
        return person_name_ja
    
    # 組織もそのまま
    if entity_type == 'organization':
        return person_name_ja
    
    # 個人の場合
    new_display = person_name_ja
    
    # 1. グループメンバーチェック
    group = get_group_for_member(person_name_ja)
    if group:
        # 既に括弧がある場合は置換
        if '(' in new_display and ')' in new_display:
            new_display = re.sub(r'\([^)]*\)', f'({group})', new_display)
        else:
            new_display = f"{person_name_ja} ({group})"
    
    # 2. 韓国アーティストの日本語化
    if nationality == '韓国' and current_display and not re.match(r'^[ぁ-んァ-ヶー一-龯]+$', current_display):
        # 英語表記の場合、日本語に変換
        japanese_name = convert_korean_to_japanese(current_display)
        if japanese_name:
            if group:
                new_display = f"{japanese_name} ({group})"
            else:
                new_display = japanese_name
        elif person_name:
            # person_nameからも試す
            japanese_name = convert_korean_to_japanese(person_name)
            if japanese_name:
                if group:
                    new_display = f"{japanese_name} ({group})"
                else:
                    new_display = japanese_name
    
    # 3. 異常な短縮名の修正（例：テスラ→ニコラ・テスラ）
    if len(current_display) <= 4 and len(person_name_ja) > 6:
        # 明らかに短すぎる場合は完全名を使用
        if current_display in person_name_ja:
            new_display = person_name_ja
    
    return new_display

def fix_display_names():
    """person_name_display修正のメイン処理"""
    print("="*60)
    print("🔧 person_name_display包括的修正")
    print("="*60)
    
    # バックアップ作成
    csv_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(csv_file, backup_file)
    print(f"📦 バックアップ作成: {backup_file}")
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📂 データ読み込み: {len(df)}件")
    
    # 修正対象の分析
    print("\n🔍 修正対象の分析:")
    
    # グループメンバー候補
    member_candidates = []
    for idx, row in df.iterrows():
        if row.get('entity_type') == 'person':
            group = get_group_for_member(str(row.get('person_name_ja', '')))
            if group:
                member_candidates.append({
                    'id': row['person_id'],
                    'name': row['person_name_ja'],
                    'group': group,
                    'current_display': row.get('person_name_display', '')
                })
    
    print(f"  グループメンバー候補: {len(member_candidates)}件")
    
    # 韓国アーティスト
    korean_artists = df[(df['nationality'] == '韓国') & (df['entity_type'] == 'person')]
    english_display = korean_artists[korean_artists['person_name_display'].str.match('^[A-Za-z]+$', na=False)]
    print(f"  韓国アーティスト（英語表記）: {len(english_display)}件")
    
    # person_name_display修正
    print("\n🔄 person_name_display修正中...")
    fixed_count = 0
    fixed_examples = []
    
    for idx, row in df.iterrows():
        old_display = row.get('person_name_display', '')
        new_display = fix_display_name(row)
        
        if old_display != new_display:
            df.at[idx, 'person_name_display'] = new_display
            fixed_count += 1
            
            if len(fixed_examples) < 10:
                fixed_examples.append({
                    'id': row['person_id'],
                    'name': row['person_name_ja'],
                    'old': old_display,
                    'new': new_display
                })
        
        if idx % 500 == 0:
            print(f"  処理中: {idx}/{len(df)}")
    
    print(f"\n✅ 修正件数: {fixed_count}件")
    
    # 修正例の表示
    if fixed_examples:
        print("\n📝 修正例:")
        for ex in fixed_examples:
            print(f"  {ex['id']}: {ex['name']}")
            print(f"    変更前: {ex['old']}")
            print(f"    変更後: {ex['new']}")
    
    # 特定の問題の確認
    print("\n🔍 個別問題の確認:")
    check_ids = ['P003266', 'P002276', 'P001381', 'P001159', 'P000783']
    for check_id in check_ids:
        record = df[df['person_id'] == check_id]
        if not record.empty:
            row = record.iloc[0]
            print(f"  {check_id}: {row['person_name_ja']} → {row['person_name_display']}")
    
    # 保存
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 修正データ保存: {csv_file}")
    
    return df

if __name__ == "__main__":
    df = fix_display_names()
    print("\n✅ person_name_display修正完了")