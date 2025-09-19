#!/usr/bin/env python3
"""
全データの包括的修正
- アニメ監督の誤分類を修正
- 未翻訳の英語名を日本語に変換
- カテゴリーを適切に設定
"""

import csv
import json
import shutil
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# 包括的な修正辞書
COMPREHENSIVE_FIXES = {
    # ボクサー・格闘家
    'Q745408': ('ガッツ石松', 'プロボクサー、タレント', 'スポーツ', 'ボクシング'),
    
    # ミュージシャン
    'Q1197175': ('桑田佳祐', 'ミュージシャン', 'エンターテインメント', '音楽'),
    
    # 映画監督（誤ってアニメ監督とされた人物）
    'Q210204': ('松林宗恵', '映画監督', '文化・芸術', '映画監督'),
    'Q55403': ('大島渚', '映画監督', '文化・芸術', '映画監督'),
    'Q470779': ('深作欣二', '映画監督', '文化・芸術', '映画監督'),
    'Q380846': ('新藤兼人', '映画監督、脚本家', '文化・芸術', '映画監督'),
    'Q529371': ('川島雄三', '映画監督', '文化・芸術', '映画監督'),
    'Q45253': ('相米慎二', '映画監督', '文化・芸術', '映画監督'),
    'Q333054': ('犬童一心', '映画監督', '文化・芸術', '映画監督'),
    
    # ゲームクリエイター
    'Q282263': ('鈴木裕', 'ゲームクリエイター', 'エンターテインメント', 'ゲーム'),
    'Q312525': ('坂口博信', 'ゲームクリエイター', 'エンターテインメント', 'ゲーム'),
    
    # 現代美術家
    'Q352437': ('村上隆', '現代美術家', '文化・芸術', '美術'),
    
    # 日本人ノーベル賞受賞者
    'Q1673706': ('赤崎勇', '物理学者', '学術・科学', '物理学'),
    'Q184563': ('朝永振一郎', '物理学者', '学術・科学', '物理学'),
    'Q202168': ('益川敏英', '物理学者', '学術・科学', '物理学'),
    'Q179871': ('佐藤栄作', '政治家', '政治・社会', '政治家'),
    'Q43736': ('川端康成', '作家', '文化・芸術', '作家'),
    'Q155777': ('湯川秀樹', '物理学者', '学術・科学', '物理学'),
    'Q155773': ('小柴昌俊', '物理学者', '学術・科学', '物理学'),
    'Q235453': ('下村脩', '化学者', '学術・科学', '化学'),
    'Q193033': ('福井謙一', '化学者', '学術・科学', '化学'),
    'Q268097': ('小林誠', '物理学者', '学術・科学', '物理学'),
    'Q313623': ('南部陽一郎', '物理学者', '学術・科学', '物理学'),
    'Q210760': ('梶田隆章', '物理学者', '学術・科学', '物理学'),
    'Q745837': ('大隅良典', '生物学者', '学術・科学', '生物学'),
    'Q359492': ('本庶佑', '医学者', '学術・科学', '医学'),
    'Q470916': ('吉野彰', '化学者', '学術・科学', '化学'),
    'Q1065154': ('真鍋淑郎', '気象学者', '学術・科学', '地球科学'),
}

def get_wikidata_labels_batch(wikidata_ids: List[str], batch_num: int) -> Dict[str, Dict]:
    """WikidataのSPARQLで日本語ラベルを一括取得"""
    if not wikidata_ids:
        return {}
    
    valid_ids = [id for id in wikidata_ids if id and id.startswith('Q')]
    if not valid_ids:
        return {}
    
    values_str = ' '.join([f'wd:{id}' for id in valid_ids[:50]])  # 50件ずつ
    
    query = f"""
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?item ?itemLabel_ja ?itemLabel_en ?occupation ?occupationLabel
    WHERE {{
      VALUES ?item {{ {values_str} }}
      OPTIONAL {{ ?item wdt:P106 ?occupation }}
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "ja,en" .
      }}
    }}
    """
    
    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers={'User-Agent': 'WikidataFix/1.0'},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"    ⚠️ バッチ {batch_num}: HTTPエラー {response.status_code}")
            return {}
        
        data = response.json()
        result = {}
        
        for binding in data.get('results', {}).get('bindings', []):
            item_id = binding['item']['value'].split('/')[-1]
            
            if item_id not in result:
                result[item_id] = {
                    'label_ja': None,
                    'label_en': None,
                    'occupations': []
                }
            
            # 日本語ラベルの処理
            item_label = binding.get('itemLabel_ja', {}).get('value', '')
            if item_label and not item_label.startswith('Q'):
                result[item_id]['label_ja'] = item_label
            
            # 英語ラベル
            item_label_en = binding.get('itemLabel_en', {}).get('value', '')
            if item_label_en and not item_label_en.startswith('Q'):
                result[item_id]['label_en'] = item_label_en
            
            # 職業
            if 'occupationLabel' in binding:
                occ_label = binding['occupationLabel']['value']
                if not occ_label.startswith('Q') and occ_label not in result[item_id]['occupations']:
                    result[item_id]['occupations'].append(occ_label)
        
        return result
        
    except Exception as e:
        print(f"    ⚠️ バッチ {batch_num}: エラー {str(e)[:50]}")
        return {}

def determine_category(occupations: List[str], current_cat: str, current_subcat: str) -> Tuple[str, str]:
    """職業リストからカテゴリーを決定"""
    
    # 職業文字列の判定
    occupation_str = ' '.join(occupations).lower()
    
    # 真のアニメ監督の判定
    if ('アニメ' in occupation_str or 'animation' in occupation_str) and \
       ('監督' in occupation_str or 'director' in occupation_str):
        return ('文化・芸術', 'アニメ監督')
    
    # その他の判定
    if '映画監督' in occupation_str or 'film director' in occupation_str:
        return ('文化・芸術', '映画監督')
    elif 'ミュージシャン' in occupation_str or 'musician' in occupation_str:
        return ('エンターテインメント', '音楽')
    elif '歌手' in occupation_str or 'singer' in occupation_str:
        return ('エンターテインメント', '音楽')
    elif 'ボクサー' in occupation_str or 'boxer' in occupation_str:
        return ('スポーツ', 'ボクシング')
    elif '物理学者' in occupation_str or 'physicist' in occupation_str:
        return ('学術・科学', '物理学')
    elif '化学者' in occupation_str or 'chemist' in occupation_str:
        return ('学術・科学', '化学')
    elif '作家' in occupation_str or 'writer' in occupation_str:
        return ('文化・芸術', '作家')
    elif '政治家' in occupation_str or 'politician' in occupation_str:
        return ('政治・社会', '政治家')
    elif '俳優' in occupation_str or 'actor' in occupation_str:
        return ('エンターテインメント', '俳優')
    elif 'ゲーム' in occupation_str or 'game' in occupation_str:
        return ('エンターテインメント', 'ゲーム')
    
    # 現在のカテゴリーがアニメ監督の場合は変更
    if current_subcat == 'アニメ監督':
        return ('その他', '')
    
    return (current_cat, current_subcat)

def main():
    print("=" * 60)
    print("全データの包括的修正")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_comprehensive_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ: {backup_file}")
    
    # データ読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 データ総数: {len(data)}件")
    
    # 修正統計
    stats = {
        'anime_fixed': 0,
        'name_translated': 0,
        'category_fixed': 0,
        'total_fixed': 0
    }
    
    # 修正対象の収集
    need_fix = {}
    for key, person in data.items():
        wikidata_id = person.get('wikidata_id', '')
        
        # 包括的修正辞書にある場合
        if wikidata_id in COMPREHENSIVE_FIXES:
            need_fix[key] = wikidata_id
        # アニメ監督の誤分類
        elif person.get('subcategory') == 'アニメ監督':
            need_fix[key] = wikidata_id
        # 英語名のまま
        elif person.get('person_name') == person.get('person_name_ja') and \
             person.get('person_name', '').replace(' ', '').isascii():
            need_fix[key] = wikidata_id
    
    print(f"\n🎯 修正対象: {len(need_fix)}件")
    
    # バッチ処理
    batch_size = 50
    processed = 0
    
    wikidata_ids = list(set([v for v in need_fix.values() if v]))
    
    for i in range(0, len(wikidata_ids), batch_size):
        batch_num = i // batch_size + 1
        batch = wikidata_ids[i:i+batch_size]
        
        print(f"\n📝 バッチ {batch_num}: {len(batch)}件処理中...")
        
        # SPARQL取得
        batch_info = get_wikidata_labels_batch(batch, batch_num)
        
        # 修正適用
        batch_fixed = 0
        for key, wikidata_id in need_fix.items():
            if wikidata_id not in batch:
                continue
            
            person = data[key]
            fixed = False
            
            # 包括的修正辞書から
            if wikidata_id in COMPREHENSIVE_FIXES:
                ja_name, occupation, main_cat, sub_cat = COMPREHENSIVE_FIXES[wikidata_id]
                person['person_name_ja'] = ja_name
                person['person_name_display'] = ja_name
                person['occupation'] = occupation
                person['main_category'] = main_cat
                person['subcategory'] = sub_cat
                fixed = True
                
                if person.get('subcategory') == 'アニメ監督' and sub_cat != 'アニメ監督':
                    stats['anime_fixed'] += 1
                stats['name_translated'] += 1
                stats['category_fixed'] += 1
            
            # SPARQLから
            elif wikidata_id in batch_info:
                info = batch_info[wikidata_id]
                
                # 日本語名
                if info.get('label_ja'):
                    current_ja = person.get('person_name_ja', '')
                    if current_ja and current_ja == person.get('person_name', '') and \
                       current_ja.replace(' ', '').isascii():
                        person['person_name_ja'] = info['label_ja']
                        person['person_name_display'] = info['label_ja']
                        stats['name_translated'] += 1
                        fixed = True
                
                # カテゴリー修正
                if info.get('occupations'):
                    old_subcat = person.get('subcategory', '')
                    main_cat, sub_cat = determine_category(
                        info['occupations'],
                        person.get('main_category', ''),
                        old_subcat
                    )
                    
                    if old_subcat == 'アニメ監督' and sub_cat != 'アニメ監督':
                        person['main_category'] = main_cat
                        person['subcategory'] = sub_cat
                        if info['occupations']:
                            person['occupation'] = '、'.join(info['occupations'][:2])
                        stats['anime_fixed'] += 1
                        stats['category_fixed'] += 1
                        fixed = True
            
            if fixed:
                batch_fixed += 1
                stats['total_fixed'] += 1
        
        print(f"    → {batch_fixed}件修正")
        processed += len(batch)
        
        # 処理制限（2000件まで）
        if processed >= 2000:
            print("\n⚠️ 処理制限に達しました（2000件）")
            break
        
        # API制限対策
        if i + batch_size < len(wikidata_ids):
            time.sleep(1)
    
    # 保存
    output_file = f'comprehensive_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    shutil.copy2(output_file, input_file)
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_file = f'comprehensive_fixed_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
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
    
    print(f"✅ CSV出力完了: {csv_file}")
    
    # 統計表示
    print("\n" + "=" * 60)
    print("📊 修正統計:")
    print(f"  アニメ監督誤分類修正: {stats['anime_fixed']}件")
    print(f"  英語名→日本語名変換: {stats['name_translated']}件")
    print(f"  カテゴリー修正: {stats['category_fixed']}件")
    print(f"  総修正件数: {stats['total_fixed']}件")
    
    # 確認
    print("\n📝 修正確認（主要人物）:")
    check_names = ['ガッツ石松', '桑田佳祐', '赤崎勇', '川端康成', '大島渚']
    for key, person in data.items():
        if person.get('person_name_ja') in check_names:
            print(f"  {person['person_name_ja']}: {person.get('subcategory')} / {person.get('occupation')}")

if __name__ == "__main__":
    main()