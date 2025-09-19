#!/usr/bin/env python3
"""
Ultra Think 最終データベース出力
17,374人の統合データベースを生成
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any


def merge_all_databases():
    """すべての最新データベースを統合"""
    
    print("🔄 最終データベース統合中...")
    
    # 読み込むファイル（優先順位順）
    database_files = [
        'ultra_think_FINAL_MERGED_20250827_080142.csv',  # 12,374人
        'continuous_expansion_20250827_080654.csv',       # +5,000人
    ]
    
    all_persons = []
    seen_person_ids = set()
    
    for filename in database_files:
        if os.path.exists(filename):
            print(f"\n📂 読み込み中: {filename}")
            
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                # BOMを除去
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                # CSV読み込み
                import io
                csv_file = io.StringIO(content)
                reader = csv.DictReader(csv_file)
                
                count = 0
                for row in reader:
                    person_id = row.get('person_id', '')
                    
                    # 重複チェック
                    if person_id and person_id not in seen_person_ids:
                        seen_person_ids.add(person_id)
                        all_persons.append(dict(row))
                        count += 1
                    elif not person_id:
                        # IDがない場合も追加（ただし後で生成）
                        all_persons.append(dict(row))
                        count += 1
                
                print(f"  ✅ {count}人追加")
    
    print(f"\n📊 統合結果: {len(all_persons)}人")
    
    # person_idがない人物にIDを付与
    max_id = 0
    for person in all_persons:
        if person.get('person_id'):
            try:
                id_num = int(person['person_id'].replace('P', ''))
                max_id = max(max_id, id_num)
            except:
                pass
    
    for person in all_persons:
        if not person.get('person_id'):
            max_id += 1
            person['person_id'] = f"P{str(max_id).zfill(6)}"
    
    return all_persons


def save_final_database(persons: List[Dict[str, Any]]):
    """最終データベースを保存"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # CSV保存（完全版）
    csv_filename = f"ULTRA_THINK_COMPLETE_{len(persons)}_{timestamp}.csv"
    
    if persons:
        # すべてのフィールドを収集
        all_fields = set()
        for person in persons:
            all_fields.update(person.keys())
        
        # フィールドを並べ替え（重要なものを先に）
        priority_fields = [
            'episode_id', 'person_id', 'person_name', 'person_name_ja',
            'person_name_display', 'category', 'nationality', 'occupation',
            'name_recognition', 'birth_year'
        ]
        
        other_fields = sorted([f for f in all_fields if f not in priority_fields])
        headers = priority_fields + other_fields
        
        with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(persons)
        
        print(f"\n✅ CSV保存: {csv_filename}")
        print(f"  サイズ: {os.path.getsize(csv_filename) / (1024*1024):.1f} MB")
    
    # JSON保存（メタデータ付き）
    json_filename = f"ULTRA_THINK_COMPLETE_{len(persons)}_{timestamp}.json"
    
    # カテゴリ統計
    category_stats = {}
    nationality_stats = {}
    recognition_stats = {'0-29': 0, '30-49': 0, '50-69': 0, '70-89': 0, '90-100': 0}
    
    for person in persons:
        # カテゴリ
        cat = person.get('category', 'その他')
        category_stats[cat] = category_stats.get(cat, 0) + 1
        
        # 国籍
        nat = person.get('nationality', '不明')
        nationality_stats[nat] = nationality_stats.get(nat, 0) + 1
        
        # 知名度
        try:
            rec = int(person.get('name_recognition', 50))
            if rec < 30:
                recognition_stats['0-29'] += 1
            elif rec < 50:
                recognition_stats['30-49'] += 1
            elif rec < 70:
                recognition_stats['50-69'] += 1
            elif rec < 90:
                recognition_stats['70-89'] += 1
            else:
                recognition_stats['90-100'] += 1
        except:
            pass
    
    output_data = {
        'metadata': {
            'total_persons': len(persons),
            'timestamp': timestamp,
            'version': '4.0',
            'description': 'Ultra Think Complete Database - 12,410人最低ライン達成版',
            'statistics': {
                'categories': category_stats,
                'top_nationalities': dict(sorted(nationality_stats.items(), 
                                               key=lambda x: x[1], reverse=True)[:20]),
                'recognition_distribution': recognition_stats
            }
        },
        'persons': persons
    }
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON保存: {json_filename}")
    print(f"  サイズ: {os.path.getsize(json_filename) / (1024*1024):.1f} MB")
    
    # 軽量版CSV（主要フィールドのみ）
    lite_filename = f"ULTRA_THINK_LITE_{len(persons)}_{timestamp}.csv"
    
    lite_fields = [
        'person_id', 'person_name', 'person_name_ja', 'category',
        'nationality', 'occupation', 'name_recognition'
    ]
    
    with open(lite_filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=lite_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(persons)
    
    print(f"✅ 軽量版CSV保存: {lite_filename}")
    print(f"  サイズ: {os.path.getsize(lite_filename) / (1024*1024):.1f} MB")
    
    return csv_filename, json_filename, lite_filename


def generate_summary_report(persons: List[Dict[str, Any]]):
    """サマリーレポート生成"""
    
    print("\n" + "="*60)
    print("📊 最終データベースサマリー")
    print("="*60)
    
    print(f"\n総人数: {len(persons)}人")
    
    # カテゴリトップ5
    categories = {}
    for p in persons:
        cat = p.get('category', 'その他')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📂 カテゴリTOP5:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {cat}: {count}人 ({count/len(persons)*100:.1f}%)")
    
    # 国籍トップ5
    nationalities = {}
    for p in persons:
        nat = p.get('nationality', '不明')
        if nat:
            nationalities[nat] = nationalities.get(nat, 0) + 1
    
    print("\n🌍 国籍TOP5:")
    for nat, count in sorted(nationalities.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {nat}: {count}人")
    
    # 知名度分布
    recognition_ranges = {'0-29': 0, '30-49': 0, '50-69': 0, '70-89': 0, '90-100': 0}
    for p in persons:
        try:
            rec = int(p.get('name_recognition', 50))
            if rec < 30:
                recognition_ranges['0-29'] += 1
            elif rec < 50:
                recognition_ranges['30-49'] += 1
            elif rec < 70:
                recognition_ranges['50-69'] += 1
            elif rec < 90:
                recognition_ranges['70-89'] += 1
            else:
                recognition_ranges['90-100'] += 1
        except:
            pass
    
    print("\n⭐ 知名度分布:")
    for range_name, count in recognition_ranges.items():
        bar = '█' * int(count / max(recognition_ranges.values()) * 30)
        print(f"  {range_name}: {bar} {count}人")


def main():
    """メイン処理"""
    
    print("="*60)
    print("🚀 Ultra Think 最終データベース出力")
    print("="*60)
    
    # データベース統合
    all_persons = merge_all_databases()
    
    if not all_persons:
        print("❌ データベースが見つかりません")
        return
    
    # データベース保存
    print("\n💾 データベース保存中...")
    csv_file, json_file, lite_file = save_final_database(all_persons)
    
    # サマリー表示
    generate_summary_report(all_persons)
    
    print("\n" + "="*60)
    print("✨ 出力完了！")
    print(f"  最終人数: {len(all_persons)}人")
    print(f"  12,410人最低ライン達成: {'✅' if len(all_persons) >= 12410 else '❌'}")
    print("\n📁 出力ファイル:")
    print(f"  完全版CSV: {csv_file}")
    print(f"  JSON版: {json_file}")
    print(f"  軽量版CSV: {lite_file}")
    print("="*60)


if __name__ == "__main__":
    main()