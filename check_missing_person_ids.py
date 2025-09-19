#!/usr/bin/env python3
"""
指定されたperson_idがCSVファイルに存在するかを確認
"""

import csv
import json
from datetime import datetime

# 指定されたperson_id一覧
target_ids = {
    # エンタメカテゴリ（34件）
    'エンタメ': [
        'P002839', 'P002843', 'P002845', 'P002861', 'P002863', 'P002864', 
        'P002867', 'P002871', 'P002875', 'P002876', 'P002881', 'P002887', 
        'P003047', 'P003051', 'P003055', 'P003062', 'P003071', 'P003077', 
        'P003081', 'P003083', 'P004237', 'P004239', 'P004247', 'P004251', 
        'P004252', 'P004254', 'P004257', 'P004260', 'P004266', 'P004271', 
        'P004272', 'P004275', 'P004279', 'P004282'
    ],
    # スポーツカテゴリ（4件）
    'スポーツ': [
        'P005334', 'P005338', 'P005339', 'P005340'
    ],
    # 歴史カテゴリ（7件）
    '歴史': [
        'P001562', 'P001563', 'P001565', 'P001567', 'P001568', 'P001576', 'P001577'
    ]
}

def check_csv_for_person_ids(csv_file_path: str):
    """CSVファイルから指定されたperson_idを検索"""
    
    found_records = {}
    missing_ids = []
    
    # 全ての対象IDをフラットなリストに変換
    all_target_ids = []
    for category, ids in target_ids.items():
        all_target_ids.extend(ids)
    
    print(f"検索対象: {len(all_target_ids)}件のperson_id")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                person_id = row.get('person_id')
                if person_id in all_target_ids:
                    found_records[person_id] = {
                        'person_id': person_id,
                        'person_name': row.get('person_name', ''),
                        'person_name_display': row.get('person_name_display', ''),
                        'occupation': row.get('occupation', ''),
                        'nationality': row.get('nationality', ''),
                        'category': row.get('category', ''),
                        'accuracy_score': row.get('accuracy_score', ''),
                        'name_recognition': row.get('name_recognition', ''),
                        'source': row.get('source', '')
                    }
    
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {str(e)}")
        return None
    
    # 見つからなかったIDを特定
    found_ids = set(found_records.keys())
    all_target_ids_set = set(all_target_ids)
    missing_ids = list(all_target_ids_set - found_ids)
    
    # 結果をカテゴリ別に整理
    results_by_category = {}
    for category, ids in target_ids.items():
        results_by_category[category] = {
            'requested_ids': ids,
            'found_records': {pid: found_records[pid] for pid in ids if pid in found_records},
            'missing_ids': [pid for pid in ids if pid not in found_records],
            'found_count': len([pid for pid in ids if pid in found_records]),
            'missing_count': len([pid for pid in ids if pid not in found_records]),
            'total_count': len(ids)
        }
    
    # サマリー情報
    summary = {
        'total_requested': len(all_target_ids),
        'total_found': len(found_records),
        'total_missing': len(missing_ids),
        'found_percentage': len(found_records) / len(all_target_ids) * 100,
        'missing_percentage': len(missing_ids) / len(all_target_ids) * 100,
        'analysis_date': datetime.now().isoformat(),
        'csv_file': csv_file_path
    }
    
    return {
        'summary': summary,
        'by_category': results_by_category,
        'all_found_records': found_records,
        'all_missing_ids': missing_ids
    }

def main():
    csv_file_path = 'ultra_think_NO_GROUPS_20250912_064413.csv'
    
    print("指定されたperson_idのCSV存在確認を開始...")
    print(f"対象CSVファイル: {csv_file_path}")
    
    results = check_csv_for_person_ids(csv_file_path)
    
    if not results:
        print("検索処理でエラーが発生しました")
        return
    
    # 結果を表示
    summary = results['summary']
    print("\n" + "=" * 60)
    print("person_id存在確認結果サマリー")
    print("=" * 60)
    print(f"検索対象: {summary['total_requested']}件")
    print(f"CSV内で発見: {summary['total_found']}件 ({summary['found_percentage']:.1f}%)")
    print(f"CSV内で未発見: {summary['total_missing']}件 ({summary['missing_percentage']:.1f}%)")
    
    print("\nカテゴリ別詳細:")
    for category, data in results['by_category'].items():
        print(f"{category}: {data['found_count']}/{data['total_count']} 発見 ({data['found_count']/data['total_count']*100:.1f}%)")
        if data['missing_ids']:
            print(f"  未発見ID: {', '.join(data['missing_ids'])}")
    
    # 結果をJSONファイルに保存
    output_file = f"person_id_csv_check_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n詳細結果ファイル: {output_file}")
    
    # 発見された全レコードを表示
    if results['all_found_records']:
        print("\n発見されたレコード:")
        for pid, record in results['all_found_records'].items():
            print(f"{pid}: {record['person_name']} ({record['occupation']}, {record['category']})")
    
    return results

if __name__ == "__main__":
    main()