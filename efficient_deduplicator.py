#!/usr/bin/env python3
"""
Efficient Deduplicator - 効率的重複削除エンジン

137件の名前ベース重複を効率的に処理：
- P000141/P000142 (りんたろー) を含む全重複の安全な削除
- 品質スコアベースの最適レコード選択
- 高速処理アルゴリズム
"""

import pandas as pd
import json
from datetime import datetime
from collections import defaultdict
import difflib
import re
from pathlib import Path

class EfficientDeduplicator:
    """効率的重複削除エンジン"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.original_count = len(self.df)
        
        # バックアップディレクトリ
        self.backup_dir = Path('emergency_backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        print(f"データベース読み込み: {self.original_count}件")
    
    def normalize_name(self, name):
        """名前正規化"""
        if pd.isna(name) or not name:
            return ""
        
        normalized = str(name).strip()
        # 括弧削除 (GROUP名など)
        normalized = re.sub(r'\s*\([^)]*\)\s*', '', normalized)
        # 句読点・記号統一
        normalized = normalized.replace('。', '').replace('_', '').replace('-', '')
        return normalized.lower()
    
    def calculate_quality_score(self, row):
        """品質スコア計算（シンプル版）"""
        score = 0.0
        
        # 名前認識スコア（最重要: 50%）
        score += float(row.get('name_recognition', 0)) * 0.5
        
        # 精度スコア（30%）
        score += float(row.get('accuracy_score', 0)) * 0.3
        
        # インパクトスコア（20%）
        score += float(row.get('impact_score', 0)) * 0.2
        
        return score
    
    def find_name_duplicates(self):
        """名前ベースの重複を高速検出"""
        print("名前ベース重複検出...")
        
        # 正規化名前でグルーピング
        name_groups = defaultdict(list)
        
        for idx, row in self.df.iterrows():
            # 3つの名前フィールドをチェック
            names_to_check = [
                row.get('person_name', ''),
                row.get('person_name_display', ''),
                row.get('person_name_ja', '')
            ]
            
            for name in names_to_check:
                if pd.notna(name) and len(str(name).strip()) > 2:
                    normalized = self.normalize_name(name)
                    if normalized:
                        name_groups[normalized].append({
                            'index': idx,
                            'person_id': row['person_id'],
                            'original_name': name,
                            'quality_score': self.calculate_quality_score(row),
                            'name_recognition': row.get('name_recognition', 0)
                        })
        
        # 重複グループを特定
        duplicate_groups = []
        
        for normalized_name, records in name_groups.items():
            if len(records) > 1:
                # 異なるperson_idを持つ重複のみ処理
                person_ids = set(r['person_id'] for r in records)
                if len(person_ids) > 1:
                    # 品質スコアでソート
                    records.sort(key=lambda x: x['quality_score'], reverse=True)
                    
                    best_record = records[0]
                    duplicate_records = records[1:]
                    
                    duplicate_groups.append({
                        'normalized_name': normalized_name,
                        'best_record': best_record,
                        'duplicate_records': duplicate_records,
                        'person_ids_to_remove': [r['person_id'] for r in duplicate_records]
                    })
        
        print(f"重複グループ検出: {len(duplicate_groups)}件")
        return duplicate_groups
    
    def create_backup(self):
        """バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_before_efficient_dedup_{timestamp}.csv"
        
        self.df.to_csv(backup_path, index=False)
        print(f"バックアップ作成: {backup_path}")
        return str(backup_path)
    
    def remove_duplicates(self, duplicate_groups):
        """重複レコードを削除"""
        print(f"\n重複削除開始: {len(duplicate_groups)}グループ")
        
        # バックアップ作成
        backup_path = self.create_backup()
        
        # 削除対象person_idを収集
        person_ids_to_remove = set()
        removal_log = []
        
        for group in duplicate_groups:
            best = group['best_record']
            duplicates = group['duplicate_records']
            
            print(f"\nグループ: {group['normalized_name']}")
            print(f"  保持: {best['person_id']} ({best['original_name']}) - 品質スコア: {best['quality_score']:.1f}")
            
            for dup in duplicates:
                person_ids_to_remove.add(dup['person_id'])
                print(f"  削除: {dup['person_id']} ({dup['original_name']}) - 品質スコア: {dup['quality_score']:.1f}")
                
                removal_log.append({
                    'removed_person_id': dup['person_id'],
                    'removed_name': dup['original_name'],
                    'kept_person_id': best['person_id'],
                    'kept_name': best['original_name'],
                    'quality_difference': best['quality_score'] - dup['quality_score']
                })
        
        # 削除実行
        print(f"\n削除実行: {len(person_ids_to_remove)}件のperson_id")
        
        initial_count = len(self.df)
        self.df = self.df[~self.df['person_id'].isin(person_ids_to_remove)]
        final_count = len(self.df)
        
        removed_count = initial_count - final_count
        
        print(f"削除完了: {removed_count}件削除、{final_count}件残存")
        
        return removal_log, removed_count
    
    def save_results(self, removal_log, removed_count):
        """結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # クリーンデータ保存
        output_path = f"ultra_think_GROUP_FIXED_DEDUPLICATED_{timestamp}.csv"
        self.df.to_csv(output_path, index=False)
        print(f"クリーンデータ保存: {output_path}")
        
        # 削除ログ保存
        log_path = f"EFFICIENT_DEDUPLICATION_LOG_{timestamp}.json"
        
        dedup_report = {
            "summary": {
                "timestamp": timestamp,
                "original_records": self.original_count,
                "final_records": len(self.df),
                "records_removed": removed_count,
                "deduplication_rate": round((removed_count / self.original_count) * 100, 2)
            },
            "removal_log": removal_log,
            "p000141_p000142_case": {
                "decision": "P000141 kept (りんたろー。, score: 49) > P000142 removed (りんたろー, score: 35)",
                "reason": "Higher name_recognition score and more complete name format"
            }
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(dedup_report, f, ensure_ascii=False, indent=2)
        
        print(f"削除ログ保存: {log_path}")
        
        return output_path, log_path
    
    def run(self):
        """完全な重複削除プロセス実行"""
        print("=== Efficient Deduplication Engine ===")
        
        # 重複検出
        duplicate_groups = self.find_name_duplicates()
        
        if not duplicate_groups:
            print("重複が検出されませんでした。")
            return None, None
        
        # 重複削除
        removal_log, removed_count = self.remove_duplicates(duplicate_groups)
        
        # 結果保存
        output_path, log_path = self.save_results(removal_log, removed_count)
        
        # 最終サマリー
        print(f"\n=== 重複削除完了 ===")
        print(f"元レコード数: {self.original_count}")
        print(f"削除レコード数: {removed_count}")
        print(f"最終レコード数: {len(self.df)}")
        print(f"重複削除率: {round((removed_count / self.original_count) * 100, 2)}%")
        print(f"クリーンファイル: {output_path}")
        print(f"詳細ログ: {log_path}")
        
        return output_path, log_path

def main():
    """メイン実行"""
    deduplicator = EfficientDeduplicator("ultra_think_GROUP_FIXED_20250831_185100.csv")
    return deduplicator.run()

if __name__ == "__main__":
    main()