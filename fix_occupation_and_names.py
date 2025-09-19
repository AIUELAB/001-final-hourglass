#!/usr/bin/env python3
"""
職業カテゴリーの誤分類と日本語名の未翻訳を修正
Wikidata APIを使用して正確な情報を取得
"""

import csv
import json
import shutil
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests

# Wikidata エンドポイント
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# 職業カテゴリーマッピング（Wikidata ID → カテゴリー）
OCCUPATION_MAPPING = {
    # スポーツ
    'Q10871364': ('スポーツ', 'ボクシング', 'プロボクサー'),  # プロボクサー
    'Q937857': ('スポーツ', 'サッカー', 'サッカー選手'),
    'Q10871364': ('スポーツ', 'ボクシング', 'ボクサー'),
    'Q11513337': ('スポーツ', '陸上競技', '陸上選手'),
    'Q13141064': ('スポーツ', '水泳', '水泳選手'),
    'Q10873124': ('スポーツ', 'テニス', 'テニス選手'),
    
    # エンターテインメント
    'Q639669': ('エンターテインメント', '音楽', 'ミュージシャン'),
    'Q177220': ('エンターテインメント', '音楽', '歌手'),
    'Q245068': ('エンターテインメント', 'お笑い', 'お笑い芸人'),
    'Q33999': ('エンターテインメント', '俳優', '俳優'),
    'Q10800557': ('エンターテインメント', '俳優', '映画俳優'),
    
    # 文化・芸術
    'Q2526255': ('文化・芸術', '映画監督', '映画監督'),  # 映画監督
    'Q3665646': ('文化・芸術', 'アニメ監督', 'アニメ監督'),  # アニメ監督
    'Q3658341': ('文化・芸術', '漫画家', '漫画家'),
    'Q36180': ('文化・芸術', '作家', '作家'),
    'Q482980': ('文化・芸術', '作家', '小説家'),
    
    # 学術・科学
    'Q901': ('学術・科学', '科学者', '科学者'),
    'Q169470': ('学術・科学', '物理学者', '物理学者'),
    'Q593644': ('学術・科学', '化学者', '化学者'),
    'Q864503': ('学術・科学', '生物学者', '生物学者'),
    
    # 政治・社会
    'Q82955': ('政治・社会', '政治家', '政治家'),
    'Q193391': ('政治・社会', '外交官', '外交官'),
    'Q131524': ('ビジネス', '起業家', '起業家'),
}

# 日本人ノーベル賞受賞者等の翻訳辞書
NAME_TRANSLATIONS = {
    'Isamu Akasaki': '赤崎勇',
    'Shin\'ichirō Tomonaga': '朝永振一郎',
    'Shinichiro Tomonaga': '朝永振一郎',
    'Toshihide Maskawa': '益川敏英',
    'Eisaku Satō': '佐藤栄作',
    'Yasunari Kawabata': '川端康成',
    'Hideki Yukawa': '湯川秀樹',
    'Masatoshi Koshiba': '小柴昌俊',
    'Osamu Shimomura': '下村脩',
    'Kenichi Fukui': '福井謙一',
    'Makoto Kobayashi': '小林誠',
    'Yoichiro Nambu': '南部陽一郎',
    'Takaaki Kajita': '梶田隆章',
    'Yoshinori Ohsumi': '大隅良典',
    'Tasuku Honjo': '本庶佑',
    'Akira Yoshino': '吉野彰',
    'Syukuro Manabe': '真鍋淑郎',
}

def get_wikidata_info(wikidata_id: str) -> Optional[Dict]:
    """Wikidata APIから情報を取得"""
    if not wikidata_id or wikidata_id == '':
        return None
    
    # QIDの形式チェック
    if not wikidata_id.startswith('Q'):
        return None
    
    try:
        # Entity APIを使用
        params = {
            'action': 'wbgetentities',
            'ids': wikidata_id,
            'props': 'labels|claims',
            'languages': 'ja|en',
            'format': 'json'
        }
        
        response = requests.get(WIKIDATA_API, params=params, timeout=10)
        data = response.json()
        
        if 'entities' not in data or wikidata_id not in data['entities']:
            return None
        
        entity = data['entities'][wikidata_id]
        
        result = {
            'label_ja': None,
            'label_en': None,
            'occupations': []
        }
        
        # ラベル取得
        if 'labels' in entity:
            if 'ja' in entity['labels']:
                result['label_ja'] = entity['labels']['ja']['value']
            if 'en' in entity['labels']:
                result['label_en'] = entity['labels']['en']['value']
        
        # 職業（P106）取得
        if 'claims' in entity and 'P106' in entity['claims']:
            for claim in entity['claims']['P106']:
                if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                    occupation_id = claim['mainsnak']['datavalue']['value']['id']
                    result['occupations'].append(occupation_id)
        
        return result
    
    except Exception as e:
        print(f"  ⚠️ Wikidata API エラー ({wikidata_id}): {str(e)}")
        return None

def determine_category(occupations: list) -> Tuple[str, str, str]:
    """職業IDリストからカテゴリーを決定"""
    for occupation_id in occupations:
        if occupation_id in OCCUPATION_MAPPING:
            return OCCUPATION_MAPPING[occupation_id]
    
    # マッピングにない場合のフォールバック
    return ('その他', '', '')

def fix_person_data(person_data: Dict, wikidata_info: Optional[Dict]) -> Dict:
    """人物データを修正"""
    updated = False
    
    # Wikidata情報がある場合
    if wikidata_info:
        # 日本語名の修正
        if wikidata_info['label_ja']:
            # 現在の日本語名が英語のままの場合のみ更新
            current_ja = person_data.get('person_name_ja', '')
            if current_ja and current_ja == person_data.get('person_name', '') and \
               current_ja.replace(' ', '').isascii():
                person_data['person_name_ja'] = wikidata_info['label_ja']
                person_data['person_name_display'] = wikidata_info['label_ja']
                updated = True
        
        # 職業カテゴリーの修正
        if wikidata_info['occupations']:
            main_cat, sub_cat, occupation = determine_category(wikidata_info['occupations'])
            
            # アニメ監督として誤分類されている場合は必ず修正
            if person_data.get('subcategory') == 'アニメ監督':
                # 本当にアニメ監督でない限り修正
                if 'Q3665646' not in wikidata_info['occupations']:
                    person_data['main_category'] = main_cat
                    person_data['subcategory'] = sub_cat
                    person_data['occupation'] = occupation
                    updated = True
    
    # 翻訳辞書による修正
    person_name = person_data.get('person_name', '')
    if person_name in NAME_TRANSLATIONS:
        person_data['person_name_ja'] = NAME_TRANSLATIONS[person_name]
        person_data['person_name_display'] = NAME_TRANSLATIONS[person_name]
        updated = True
    
    # 特定の修正
    if person_data.get('person_name_ja') == 'ガッツ石松':
        person_data['main_category'] = 'スポーツ'
        person_data['subcategory'] = 'ボクシング'
        person_data['occupation'] = 'プロボクサー、タレント'
        updated = True
    elif person_data.get('person_name_ja') == '桑田佳祐':
        person_data['main_category'] = 'エンターテインメント'
        person_data['subcategory'] = '音楽'
        person_data['occupation'] = 'ミュージシャン'
        updated = True
    
    return person_data, updated

def main():
    """メイン処理"""
    print("=" * 60)
    print("職業カテゴリーと日本語名の修正")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_fix_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n📊 初期データ数: {len(data)}件")
    
    # 修正対象の特定
    anime_director_count = sum(1 for p in data.values() if p.get('subcategory') == 'アニメ監督')
    untranslated_count = sum(1 for p in data.values() 
                           if p.get('person_name') == p.get('person_name_ja') 
                           and p.get('person_name', '').replace(' ', '').isascii())
    
    print("\n🎯 修正対象:")
    print(f"  アニメ監督誤分類: {anime_director_count}件")
    print(f"  未翻訳の英語名: {untranslated_count}件")
    
    # 修正処理
    fix_count = 0
    fix_log = []
    api_call_count = 0
    
    for key, person in data.items():
        wikidata_id = person.get('wikidata_id', '')
        needs_fix = False
        
        # 修正が必要か判定
        if person.get('subcategory') == 'アニメ監督':
            needs_fix = True
        elif person.get('person_name') == person.get('person_name_ja') and \
             person.get('person_name', '').replace(' ', '').isascii():
            needs_fix = True
        
        if needs_fix and wikidata_id:
            # API呼び出し制限（1秒に1回）
            if api_call_count > 0 and api_call_count % 10 == 0:
                print(f"  処理中... {api_call_count}件完了")
                time.sleep(1)
            
            wikidata_info = get_wikidata_info(wikidata_id)
            api_call_count += 1
            
            old_data = {
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', '')
            }
            
            person, updated = fix_person_data(person, wikidata_info)
            
            if updated:
                fix_log.append({
                    'id': key,
                    'person_name': person.get('person_name', ''),
                    'old': old_data,
                    'new': {
                        'occupation': person.get('occupation', ''),
                        'main_category': person.get('main_category', ''),
                        'subcategory': person.get('subcategory', ''),
                        'person_name_ja': person.get('person_name_ja', ''),
                        'person_name_display': person.get('person_name_display', '')
                    }
                })
                fix_count += 1
                
                # 重要な修正を表示
                if person.get('person_name_ja') in ['ガッツ石松', '桑田佳祐', '赤崎勇']:
                    print(f"  ✏️ {person.get('person_name_ja')}: {old_data['subcategory']} → {person.get('subcategory', '')}")
        
        # API制限対策（最初の100件で一旦停止）
        if api_call_count >= 100:
            print("\n⚠️ API制限のため100件で処理を一時停止")
            break
    
    # 結果を保存
    output_file = f'occupation_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ログ保存
    log_file = f'occupation_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fix_count': fix_count,
            'timestamp': timestamp,
            'api_calls': api_call_count,
            'samples': fix_log[:50]
        }, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    print("\n📊 処理結果:")
    print(f"  修正件数: {fix_count}件")
    print(f"  API呼び出し: {api_call_count}回")
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'occupation_fixed_{timestamp}.csv'
    
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
    
    return fix_count

if __name__ == "__main__":
    main()