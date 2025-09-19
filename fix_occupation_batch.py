#!/usr/bin/env python3
"""
職業カテゴリーの誤分類と日本語名の未翻訳を修正（バッチ処理版）
SPARQLクエリで複数のエンティティを一括取得
"""

import csv
import json
import shutil
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

# SPARQL エンドポイント
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# 既知の誤分類修正
KNOWN_FIXES = {
    'Q745408': {  # ガッツ石松
        'person_name_ja': 'ガッツ石松',
        'person_name_display': 'ガッツ石松',
        'occupation': 'プロボクサー、タレント',
        'main_category': 'スポーツ',
        'subcategory': 'ボクシング'
    },
    'Q1197175': {  # 桑田佳祐
        'person_name_ja': '桑田佳祐',
        'person_name_display': '桑田佳祐',
        'occupation': 'ミュージシャン',
        'main_category': 'エンターテインメント',
        'subcategory': '音楽'
    },
    'Q210204': {  # 松林宗恵
        'person_name_ja': '松林宗恵',
        'person_name_display': '松林宗恵',
        'occupation': '映画監督',
        'main_category': '文化・芸術',
        'subcategory': '映画監督'
    },
    'Q55403': {  # 大島渚
        'person_name_ja': '大島渚',
        'person_name_display': '大島渚',
        'occupation': '映画監督',
        'main_category': '文化・芸術',
        'subcategory': '映画監督'
    },
    'Q470779': {  # 深作欣二
        'person_name_ja': '深作欣二',
        'person_name_display': '深作欣二',
        'occupation': '映画監督',
        'main_category': '文化・芸術',
        'subcategory': '映画監督'
    },
    'Q380846': {  # 新藤兼人
        'person_name_ja': '新藤兼人',
        'person_name_display': '新藤兼人',
        'occupation': '映画監督、脚本家',
        'main_category': '文化・芸術',
        'subcategory': '映画監督'
    },
    'Q282263': {  # 鈴木裕
        'person_name_ja': '鈴木裕',
        'person_name_display': '鈴木裕',
        'occupation': 'ゲームクリエイター',
        'main_category': 'エンターテインメント',
        'subcategory': 'ゲーム'
    },
    'Q352437': {  # 村上隆
        'person_name_ja': '村上隆',
        'person_name_display': '村上隆',
        'occupation': '現代美術家',
        'main_category': '文化・芸術',
        'subcategory': '美術'
    },
}

# 日本人ノーベル賞受賞者等の翻訳
NOBEL_LAUREATES = {
    'Q1673706': {  # 赤崎勇
        'person_name_ja': '赤崎勇',
        'person_name_display': '赤崎勇',
        'occupation': '物理学者',
        'main_category': '学術・科学',
        'subcategory': '物理学'
    },
    'Q184563': {  # 朝永振一郎
        'person_name_ja': '朝永振一郎',
        'person_name_display': '朝永振一郎',
        'occupation': '物理学者',
        'main_category': '学術・科学',
        'subcategory': '物理学'
    },
    'Q202168': {  # 益川敏英
        'person_name_ja': '益川敏英',
        'person_name_display': '益川敏英',
        'occupation': '物理学者',
        'main_category': '学術・科学',
        'subcategory': '物理学'
    },
    'Q179871': {  # 佐藤栄作
        'person_name_ja': '佐藤栄作',
        'person_name_display': '佐藤栄作',
        'occupation': '政治家',
        'main_category': '政治・社会',
        'subcategory': '政治家'
    },
    'Q43736': {  # 川端康成
        'person_name_ja': '川端康成',
        'person_name_display': '川端康成',
        'occupation': '作家',
        'main_category': '文化・芸術',
        'subcategory': '作家'
    },
    'Q155777': {  # 湯川秀樹
        'person_name_ja': '湯川秀樹',
        'person_name_display': '湯川秀樹',
        'occupation': '物理学者',
        'main_category': '学術・科学',
        'subcategory': '物理学'
    },
    'Q155773': {  # 小柴昌俊
        'person_name_ja': '小柴昌俊',
        'person_name_display': '小柴昌俊',
        'occupation': '物理学者',
        'main_category': '学術・科学',
        'subcategory': '物理学'
    },
}

def get_wikidata_batch(wikidata_ids: List[str]) -> Dict[str, Dict]:
    """複数のWikidata IDの情報を一括取得"""
    if not wikidata_ids:
        return {}
    
    # QIDのみをフィルタ
    valid_ids = [id for id in wikidata_ids if id and id.startswith('Q')]
    if not valid_ids:
        return {}
    
    # VALUES句用のID文字列作成
    values_str = ' '.join([f'wd:{id}' for id in valid_ids])
    
    query = f"""
    SELECT ?item ?itemLabel_ja ?itemLabel_en ?occupation ?occupationLabel_ja
    WHERE {{
      VALUES ?item {{ {values_str} }}
      OPTIONAL {{
        ?item wdt:P106 ?occupation .
        SERVICE wikibase:label {{ 
          bd:serviceParam wikibase:language "ja" .
          ?occupation rdfs:label ?occupationLabel_ja .
        }}
      }}
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "ja" .
        ?item rdfs:label ?itemLabel_ja .
      }}
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "en" .
        ?item rdfs:label ?itemLabel_en .
      }}
    }}
    """
    
    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  ⚠️ SPARQL エラー: {response.status_code}")
            return {}
        
        data = response.json()
        
        # 結果を辞書に整理
        result = {}
        for binding in data.get('results', {}).get('bindings', []):
            item_id = binding['item']['value'].split('/')[-1]
            
            if item_id not in result:
                result[item_id] = {
                    'label_ja': binding.get('itemLabel_ja', {}).get('value'),
                    'label_en': binding.get('itemLabel_en', {}).get('value'),
                    'occupations': []
                }
            
            if 'occupationLabel_ja' in binding:
                occupation = binding['occupationLabel_ja']['value']
                if occupation not in result[item_id]['occupations']:
                    result[item_id]['occupations'].append(occupation)
        
        return result
    
    except Exception as e:
        print(f"  ⚠️ SPARQL エラー: {str(e)}")
        return {}

def determine_category_from_occupation(occupations: List[str]) -> Tuple[str, str]:
    """職業名からカテゴリーを決定"""
    for occupation in occupations:
        # アニメ監督チェック
        if 'アニメ' in occupation and '監督' in occupation:
            return ('文化・芸術', 'アニメ監督')
        # 映画監督
        elif '映画監督' in occupation:
            return ('文化・芸術', '映画監督')
        # ミュージシャン
        elif 'ミュージシャン' in occupation or '歌手' in occupation:
            return ('エンターテインメント', '音楽')
        # ボクサー
        elif 'ボクサー' in occupation or 'ボクシング' in occupation:
            return ('スポーツ', 'ボクシング')
        # 作家
        elif '作家' in occupation or '小説家' in occupation:
            return ('文化・芸術', '作家')
        # 科学者
        elif '物理学者' in occupation or '化学者' in occupation or '生物学者' in occupation:
            return ('学術・科学', '科学')
        # 政治家
        elif '政治家' in occupation:
            return ('政治・社会', '政治家')
    
    return ('その他', '')

def fix_person_batch(data: Dict, batch_info: Dict[str, Dict]) -> int:
    """バッチでデータを修正"""
    fix_count = 0
    
    for key, person in data.items():
        wikidata_id = person.get('wikidata_id', '')
        updated = False
        
        # 既知の修正を適用
        if wikidata_id in KNOWN_FIXES:
            for field, value in KNOWN_FIXES[wikidata_id].items():
                person[field] = value
            updated = True
        
        # ノーベル賞受賞者の修正
        elif wikidata_id in NOBEL_LAUREATES:
            for field, value in NOBEL_LAUREATES[wikidata_id].items():
                person[field] = value
            updated = True
        
        # SPARQLから取得した情報で修正
        elif wikidata_id in batch_info:
            info = batch_info[wikidata_id]
            
            # 日本語名の修正
            if info.get('label_ja'):
                current_ja = person.get('person_name_ja', '')
                # 英語名のままの場合のみ更新
                if current_ja and current_ja == person.get('person_name', '') and \
                   current_ja.replace(' ', '').isascii():
                    person['person_name_ja'] = info['label_ja']
                    person['person_name_display'] = info['label_ja']
                    updated = True
            
            # アニメ監督として誤分類されている場合
            if person.get('subcategory') == 'アニメ監督' and info.get('occupations'):
                # 本当にアニメ監督でない限り修正
                if not any('アニメ' in occ for occ in info['occupations']):
                    main_cat, sub_cat = determine_category_from_occupation(info['occupations'])
                    person['main_category'] = main_cat
                    person['subcategory'] = sub_cat
                    if info['occupations']:
                        person['occupation'] = '、'.join(info['occupations'][:2])  # 最初の2つ
                    updated = True
        
        if updated:
            fix_count += 1
    
    return fix_count

def main():
    """メイン処理"""
    print("=" * 60)
    print("職業カテゴリーと日本語名の修正（バッチ処理版）")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_batch_fix_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n📊 初期データ数: {len(data)}件")
    
    # 修正対象の特定
    anime_directors = []
    untranslated = []
    
    for key, person in data.items():
        wikidata_id = person.get('wikidata_id', '')
        
        # アニメ監督として誤分類
        if person.get('subcategory') == 'アニメ監督' and wikidata_id:
            anime_directors.append(wikidata_id)
        
        # 未翻訳の英語名
        if person.get('person_name') == person.get('person_name_ja') and \
           person.get('person_name', '').replace(' ', '').isascii() and wikidata_id:
            untranslated.append(wikidata_id)
    
    print("\n🎯 修正対象:")
    print(f"  アニメ監督誤分類: {len(anime_directors)}件")
    print(f"  未翻訳の英語名: {len(untranslated)}件")
    
    # バッチ処理（50件ずつ）
    all_ids = list(set(anime_directors + untranslated))
    batch_size = 50
    total_fixed = 0
    
    print(f"\n📝 バッチ処理開始（{len(all_ids)}件を{batch_size}件ずつ）")
    
    for i in range(0, min(len(all_ids), 500), batch_size):  # 最大500件まで
        batch = all_ids[i:i+batch_size]
        print(f"  バッチ {i//batch_size + 1}: {len(batch)}件処理中...")
        
        # SPARQLでバッチ取得
        batch_info = get_wikidata_batch(batch)
        
        # 修正適用
        fixed = fix_person_batch(data, batch_info)
        total_fixed += fixed
        
        print(f"    → {fixed}件修正")
        
        # API制限対策
        if i + batch_size < len(all_ids):
            time.sleep(2)  # 2秒待機
    
    # 結果を保存
    output_file = f'batch_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    print("\n📊 処理結果:")
    print(f"  修正件数: {total_fixed}件")
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'batch_fixed_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for key, person in data.items():
            row = {
                'id': person.get('id', key),
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', ''),
                'grade': person.get('grade', ''),
                'birth_date': person.get('birth_date', ''),
                'death_date': person.get('death_date', ''),
                'nationality': person.get('nationality', ''),
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'description': person.get('description', '')
            }
            writer.writerow(row)
    
    print(f"✅ CSV出力完了: {csv_filename}")
    print(f"📊 総エントリ数: {len(data)}件")
    
    # 修正確認（主要な人物）
    print("\n📝 主要な修正:")
    for key, person in data.items():
        if person.get('person_name_ja') in ['ガッツ石松', '桑田佳祐', '赤崎勇', '朝永振一郎', '川端康成']:
            print(f"  {person['person_name_ja']}: {person.get('subcategory', '')} ({person.get('occupation', '')})")
    
    return total_fixed

if __name__ == "__main__":
    main()