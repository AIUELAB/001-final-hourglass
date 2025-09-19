#!/usr/bin/env python3
"""
データ品質検証システム
重複括弧、person_id重複、誤ったグループ割り当てなどを検証

作成日: 2025-08-30
"""

import pandas as pd
import re
from datetime import datetime
import json
from typing import Dict, List, Tuple
from pathlib import Path

class QualityValidator:
    """データ品質検証クラス"""
    
    def __init__(self):
        self.validation_results = {
            'duplicate_parentheses': [],
            'person_id_duplicates': [],
            'incorrect_group_assignments': [],
            'empty_fields': [],
            'data_inconsistencies': []
        }
        
        # 既知の正しいグループ割り当て
        self.correct_assignments = {
            'John Frusciante': 'Red Hot Chili Peppers',
            'Joe Perry': 'Aerosmith',
            'Chad Smith': 'Red Hot Chili Peppers',
            'Anthony Kiedis': 'Red Hot Chili Peppers',
            'Flea': 'Red Hot Chili Peppers'
        }
    
    def check_duplicate_parentheses(self, df: pd.DataFrame) -> List[Dict]:
        """重複括弧パターンを検出"""
        issues = []
        pattern = re.compile(r'^([^(]+)\s*\(\1\)$')
        
        for idx, row in df.iterrows():
            display_name = str(row.get('person_name_display', ''))
            if pd.notna(display_name) and display_name:
                match = pattern.match(display_name.strip())
                if match:
                    issues.append({
                        'type': 'duplicate_parentheses',
                        'person_id': row.get('person_id', ''),
                        'display_name': display_name,
                        'suggested_fix': match.group(1).strip()
                    })
        
        self.validation_results['duplicate_parentheses'] = issues
        return issues
    
    def check_person_id_duplicates(self, df: pd.DataFrame) -> List[Dict]:
        """person_id重複を検出"""
        duplicates = []
        
        # person_idでグループ化
        id_counts = df['person_id'].value_counts()
        duplicate_ids = id_counts[id_counts > 1].index.tolist()
        
        for person_id in duplicate_ids:
            duplicate_rows = df[df['person_id'] == person_id]
            duplicates.append({
                'type': 'person_id_duplicate',
                'person_id': person_id,
                'count': len(duplicate_rows),
                'rows': duplicate_rows.index.tolist(),
                'person_names': duplicate_rows['person_name'].tolist()
            })
        
        self.validation_results['person_id_duplicates'] = duplicates
        return duplicates
    
    def check_incorrect_group_assignments(self, df: pd.DataFrame) -> List[Dict]:
        """誤ったグループ割り当てを検出"""
        incorrect = []
        
        for idx, row in df.iterrows():
            person_name = row.get('person_name', '')
            display_name = str(row.get('person_name_display', ''))
            
            # 既知の誤りをチェック
            if person_name in self.correct_assignments:
                correct_group = self.correct_assignments[person_name]
                if correct_group not in display_name and '(' in display_name:
                    # 間違ったグループが括弧内にある
                    match = re.search(r'\(([^)]+)\)', display_name)
                    if match:
                        wrong_group = match.group(1)
                        incorrect.append({
                            'type': 'incorrect_group',
                            'person_id': row.get('person_id', ''),
                            'person_name': person_name,
                            'current_group': wrong_group,
                            'correct_group': correct_group,
                            'current_display': display_name,
                            'suggested_display': f"{person_name} ({correct_group})"
                        })
        
        self.validation_results['incorrect_group_assignments'] = incorrect
        return incorrect
    
    def check_empty_fields(self, df: pd.DataFrame) -> List[Dict]:
        """空フィールドを検出"""
        empty = []
        important_fields = ['person_name', 'person_name_display', 'person_id']
        
        for field in important_fields:
            empty_count = df[field].isna().sum() + (df[field] == '').sum()
            if empty_count > 0:
                empty_rows = df[df[field].isna() | (df[field] == '')].index.tolist()
                empty.append({
                    'type': 'empty_field',
                    'field': field,
                    'count': empty_count,
                    'rows': empty_rows[:10]  # 最初の10件のみ
                })
        
        self.validation_results['empty_fields'] = empty
        return empty
    
    def check_data_inconsistencies(self, df: pd.DataFrame) -> List[Dict]:
        """データの不整合を検出"""
        inconsistencies = []
        
        # 二重括弧
        double_paren = df[df['person_name_display'].str.contains(r'\(\(|\)\)', na=False, regex=True)]
        if not double_paren.empty:
            inconsistencies.append({
                'type': 'double_parentheses',
                'count': len(double_paren),
                'examples': double_paren[['person_id', 'person_name_display']].head(5).to_dict('records')
            })
        
        # 空括弧
        empty_paren = df[df['person_name_display'].str.contains(r'\(\s*\)', na=False, regex=True)]
        if not empty_paren.empty:
            inconsistencies.append({
                'type': 'empty_parentheses',
                'count': len(empty_paren),
                'examples': empty_paren[['person_id', 'person_name_display']].head(5).to_dict('records')
            })
        
        # 複数括弧
        multi_paren = df[df['person_name_display'].str.count(r'\(') > 1]
        if not multi_paren.empty:
            inconsistencies.append({
                'type': 'multiple_parentheses',
                'count': len(multi_paren),
                'examples': multi_paren[['person_id', 'person_name_display']].head(5).to_dict('records')
            })
        
        self.validation_results['data_inconsistencies'] = inconsistencies
        return inconsistencies
    
    def generate_report(self) -> str:
        """検証レポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("📊 データ品質検証レポート")
        report.append("=" * 60)
        report.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 重複括弧
        dup_paren = self.validation_results['duplicate_parentheses']
        report.append(f"## 🔍 重複括弧: {len(dup_paren)}件")
        if dup_paren:
            for item in dup_paren[:5]:
                report.append(f"  - {item['person_id']}: '{item['display_name']}' → '{item['suggested_fix']}'")
        report.append("")
        
        # person_id重複
        id_dups = self.validation_results['person_id_duplicates']
        report.append(f"## 🆔 person_id重複: {len(id_dups)}件")
        if id_dups:
            total_duplicate_rows = sum(d['count'] for d in id_dups)
            report.append(f"  合計 {total_duplicate_rows} 行の重複レコード")
            for item in id_dups[:5]:
                report.append(f"  - {item['person_id']}: {item['count']}件の重複")
        report.append("")
        
        # 誤ったグループ割り当て
        incorrect = self.validation_results['incorrect_group_assignments']
        report.append(f"## 🎯 誤ったグループ割り当て: {len(incorrect)}件")
        if incorrect:
            for item in incorrect[:5]:
                report.append(f"  - {item['person_name']}: '{item['current_group']}' → '{item['correct_group']}'")
        report.append("")
        
        # 空フィールド
        empty = self.validation_results['empty_fields']
        if empty:
            report.append(f"## ⚠️  空フィールド:")
            for item in empty:
                report.append(f"  - {item['field']}: {item['count']}件")
        report.append("")
        
        # データ不整合
        inconsist = self.validation_results['data_inconsistencies']
        if inconsist:
            report.append(f"## 🔧 データ不整合:")
            for item in inconsist:
                report.append(f"  - {item['type']}: {item['count']}件")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None):
        """検証結果を保存"""
        if filename is None:
            filename = f"quality_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'validation_results': self.validation_results,
                'summary': {
                    'duplicate_parentheses': len(self.validation_results['duplicate_parentheses']),
                    'person_id_duplicates': len(self.validation_results['person_id_duplicates']),
                    'incorrect_groups': len(self.validation_results['incorrect_group_assignments']),
                    'empty_fields': sum(e['count'] for e in self.validation_results['empty_fields']),
                    'data_inconsistencies': sum(i['count'] for i in self.validation_results['data_inconsistencies'])
                }
            }, f, ensure_ascii=False, indent=2)
        
        return filename

def main():
    """メイン処理"""
    print("🔍 データ品質検証開始...")
    
    # 最新の修正済みファイルを読み込み
    csv_file = 'ultra_think_DUPLICATE_FIXED_20250831_040037.csv'
    if not Path(csv_file).exists():
        csv_file = 'ultra_think_FINAL_CLEAN_20250829_220113.csv'
    
    print(f"📂 ファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # バリデーター初期化
    validator = QualityValidator()
    
    # 各種検証を実行
    print("✅ 重複括弧チェック...")
    validator.check_duplicate_parentheses(df)
    
    print("✅ person_id重複チェック...")
    validator.check_person_id_duplicates(df)
    
    print("✅ グループ割り当てチェック...")
    validator.check_incorrect_group_assignments(df)
    
    print("✅ 空フィールドチェック...")
    validator.check_empty_fields(df)
    
    print("✅ データ不整合チェック...")
    validator.check_data_inconsistencies(df)
    
    # レポート生成
    report = validator.generate_report()
    print("\n" + report)
    
    # 結果保存
    result_file = validator.save_results()
    print(f"\n💾 検証結果保存: {result_file}")
    
    # 問題がある場合は警告
    total_issues = sum([
        len(validator.validation_results['duplicate_parentheses']),
        len(validator.validation_results['person_id_duplicates']),
        len(validator.validation_results['incorrect_group_assignments']),
        sum(e['count'] for e in validator.validation_results['empty_fields']),
        sum(i['count'] for i in validator.validation_results['data_inconsistencies'])
    ])
    
    if total_issues > 0:
        print(f"\n⚠️  {total_issues}件の問題が検出されました。修正が必要です。")
    else:
        print("\n✅ データ品質検証完了。問題は検出されませんでした。")

if __name__ == "__main__":
    main()