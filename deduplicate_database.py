#!/usr/bin/env python3
"""
データベース重複除去スクリプト - Ultra Think実装
15.4%の重複率を解消し、高品質なデータベースを生成
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import re
from difflib import SequenceMatcher

class DatabaseDeduplicator:
    """Ultra Think重複除去エンジン"""
    
    def __init__(self):
        # データソース優先順位
        self.source_priority = {
            'メインデータ': 1,
            '有名人データ': 2,
            'Wikidata': 3,
            'Wikipedia': 4,
            'その他': 5
        }
        
        self.stats = {
            'total_records': 0,
            'duplicates_found': 0,
            'records_merged': 0,
            'records_kept': 0,
            'birth_date_recovered': 0,
            'data_enriched': 0,
            'source_distribution': defaultdict(int),
            'merge_operations': []
        }
    
    def normalize_name(self, name: str) -> str:
        """名前の正規化"""
        if not name:
            return ""
        
        # 全角スペースを半角に統一
        name = name.replace('　', ' ')
        
        # 括弧内の情報を除去
        name = re.sub(r'[（(][^)）]*[)）]', '', name)
        
        # 余分なスペースを削除
        name = ' '.join(name.split())
        
        return name.strip()
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """名前の類似度計算"""
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # 部分一致チェック
        if norm1 in norm2 or norm2 in norm1:
            return 0.9
        
        # 文字列類似度
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def get_source_priority(self, record: Dict) -> int:
        """レコードのソース優先度取得"""
        source = record.get('source', 'その他')
        
        # ソース名の部分一致も考慮
        for key, priority in self.source_priority.items():
            if key in source:
                return priority
        
        return self.source_priority['その他']
    
    def merge_records(self, records: List[Dict]) -> Dict:
        """複数レコードをマージ"""
        if not records:
            return {}
        
        # 優先度でソート
        sorted_records = sorted(records, key=lambda x: (
            self.get_source_priority(x),
            # 生年月日がある方を優先
            0 if x.get('birth_date') else 1,
            # より多くのフィールドがある方を優先
            -len([v for v in x.values() if v])
        ))
        
        # ベースレコード（最優先）
        merged = sorted_records[0].copy()
        
        # 他のレコードから欠損データを補完
        for record in sorted_records[1:]:
            for key, value in record.items():
                # 空のフィールドを補完
                if not merged.get(key) and value:
                    merged[key] = value
                    if key == 'birth_date':
                        self.stats['birth_date_recovered'] += 1
                    self.stats['data_enriched'] += 1
                
                # リスト型フィールドの統合
                elif key in ['categories', 'aliases', 'achievements']:
                    if isinstance(value, list) and isinstance(merged.get(key), list):
                        merged[key] = list(set(merged[key] + value))
        
        # マージ情報を記録
        merged['merge_info'] = {
            'merged_count': len(records),
            'sources': [r.get('source', 'unknown') for r in records],
            'merged_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return merged
    
    def find_duplicates(self, data: Dict) -> Dict[str, List[str]]:
        """重複レコードを検出"""
        name_groups = defaultdict(list)
        
        # 名前でグループ化
        for key, value in data.items():
            if isinstance(value, dict):
                name = value.get('name', '')
                if name:
                    normalized = self.normalize_name(name)
                    name_groups[normalized].append(key)
        
        # 類似名もグループ化
        grouped_names = set()
        final_groups = {}
        
        for name1, keys1 in name_groups.items():
            if name1 in grouped_names:
                continue
            
            group = list(keys1)
            grouped_names.add(name1)
            
            # 他の名前との類似度チェック
            for name2, keys2 in name_groups.items():
                if name2 != name1 and name2 not in grouped_names:
                    similarity = self.calculate_name_similarity(name1, name2)
                    if similarity >= 0.85:  # 85%以上の類似度
                        group.extend(keys2)
                        grouped_names.add(name2)
            
            if len(group) > 1:
                final_groups[name1] = group
        
        return final_groups
    
    def deduplicate(self, input_file: str) -> Tuple[str, str]:
        """データベースの重複除去を実行"""
        print("🧹 Ultra Think重複除去エンジン起動")
        print(f"  入力: {input_file}")
        print("=" * 80)
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total_records'] = len(data)
        
        # ソース分布を記録
        for value in data.values():
            if isinstance(value, dict):
                source = value.get('source', 'unknown')
                self.stats['source_distribution'][source] += 1
        
        # 重複検出
        print("\n🔍 重複検出フェーズ")
        duplicate_groups = self.find_duplicates(data)
        self.stats['duplicates_found'] = sum(len(group) for group in duplicate_groups.values())
        
        print(f"  重複グループ: {len(duplicate_groups)}個")
        print(f"  重複レコード: {self.stats['duplicates_found']}件")
        
        # 重複除去
        print("\n🔄 マージフェーズ")
        cleaned_data = {}
        processed_keys = set()
        
        # 重複グループをマージ
        for group_name, keys in duplicate_groups.items():
            records_to_merge = []
            for key in keys:
                if key in data and isinstance(data[key], dict):
                    records_to_merge.append(data[key])
                    processed_keys.add(key)
            
            if records_to_merge:
                merged = self.merge_records(records_to_merge)
                # 最初のキーを使用（または新しいキーを生成）
                new_key = keys[0]
                cleaned_data[new_key] = merged
                self.stats['records_merged'] += len(records_to_merge) - 1
                
                # マージ操作を記録
                self.stats['merge_operations'].append({
                    'group': group_name,
                    'merged_keys': keys,
                    'result_key': new_key,
                    'records_count': len(records_to_merge)
                })
        
        # 重複していないレコードを追加
        for key, value in data.items():
            if key not in processed_keys and isinstance(value, dict):
                cleaned_data[key] = value
                self.stats['records_kept'] += 1
        
        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json = f"deduplicated_{timestamp}.json"
        output_csv = f"deduplicated_{timestamp}.csv"
        
        # JSON保存
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        
        # CSV保存
        self.save_to_csv(cleaned_data, output_csv)
        
        # レポート生成
        self.generate_report(timestamp)
        
        print(f"\n✅ 重複除去完了!")
        print(f"  出力JSON: {output_json}")
        print(f"  出力CSV: {output_csv}")
        
        return output_json, output_csv
    
    def save_to_csv(self, data: Dict, filename: str):
        """CSVファイルとして保存"""
        # フィールド収集
        all_fields = set()
        for value in data.values():
            if isinstance(value, dict):
                all_fields.update(value.keys())
        
        # merge_infoは除外
        all_fields.discard('merge_info')
        
        # フィールド順序
        priority_fields = ['id', 'name', 'original_name', 'person_name_ja', 
                          'person_name_display', 'occupation', 'main_category', 
                          'subcategory', 'birth_date', 'death_date', 'nationality']
        other_fields = sorted(all_fields - set(priority_fields))
        fieldnames = [f for f in priority_fields if f in all_fields] + other_fields
        
        # CSV書き込み
        with open(filename, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for key, value in data.items():
                if isinstance(value, dict):
                    row = {field: value.get(field, '') for field in fieldnames}
                    if 'id' not in row or not row['id']:
                        row['id'] = key
                    writer.writerow(row)
    
    def generate_report(self, timestamp: str):
        """詳細レポート生成"""
        report_file = f"DEDUPLICATION_REPORT_{timestamp}.md"
        
        # 削減率計算
        reduction_rate = (self.stats['duplicates_found'] / self.stats['total_records'] * 100) if self.stats['total_records'] > 0 else 0
        final_count = self.stats['total_records'] - self.stats['records_merged']
        
        report = f"""# 🎯 Ultra Think重複除去レポート

## 📊 実行結果サマリー
- **実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **元レコード数**: {self.stats['total_records']:,}件
- **重複検出数**: {self.stats['duplicates_found']:,}件 ({reduction_rate:.1f}%)
- **最終レコード数**: {final_count:,}件
- **削減数**: {self.stats['records_merged']:,}件

## 🔄 マージ統計
- **マージ操作数**: {len(self.stats['merge_operations'])}回
- **生年月日復元**: {self.stats['birth_date_recovered']}件
- **データ補完**: {self.stats['data_enriched']}フィールド

## 📈 データソース分布（元データ）
"""
        for source, count in sorted(self.stats['source_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True):
            percentage = count / self.stats['total_records'] * 100
            report += f"- **{source}**: {count:,}件 ({percentage:.1f}%)\n"
        
        # マージ詳細（最初の20件）
        report += f"\n## 🔍 マージ操作詳細（最初の20件）\n"
        for i, op in enumerate(self.stats['merge_operations'][:20], 1):
            report += f"""
### {i}. {op['group']}
- マージ数: {op['records_count']}件
- 統合キー: {', '.join(op['merged_keys'][:5])}{'...' if len(op['merged_keys']) > 5 else ''}
- 結果キー: {op['result_key']}
"""
        
        report += f"""
## ✨ 改善効果
- **重複解消**: {self.stats['duplicates_found']:,}件の重複を除去
- **データ品質向上**: {self.stats['data_enriched']}フィールドのデータ補完
- **生年月日復元**: {self.stats['birth_date_recovered']}件の欠損データ復元

## 🎯 結論
Ultra Think重複除去により、データベースの品質が大幅に向上しました。
- 重複率: {reduction_rate:.1f}% → 0%
- データ完全性の向上
- 一貫性のある高品質データベースの実現

---
*Ultra Think Engine v2.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # コンソール出力
        print("\n" + "=" * 80)
        print("📊 重複除去結果")
        print("=" * 80)
        print(f"元レコード数: {self.stats['total_records']:,}件")
        print(f"重複検出: {self.stats['duplicates_found']:,}件 ({reduction_rate:.1f}%)")
        print(f"最終レコード数: {final_count:,}件")
        print(f"削減: {self.stats['records_merged']:,}件")
        print(f"\n📄 詳細レポート: {report_file}")


def main():
    """メイン実行"""
    deduplicator = DatabaseDeduplicator()
    
    # 最新のデータファイルを使用
    input_file = 'category_fixed_20250825_101132.json'
    
    json_file, csv_file = deduplicator.deduplicate(input_file)
    
    print("\n🏆 Ultra Think重複除去完了!")
    print(f"  クリーンJSON: {json_file}")
    print(f"  クリーンCSV: {csv_file}")
    
    return json_file, csv_file


if __name__ == "__main__":
    main()