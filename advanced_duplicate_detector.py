#!/usr/bin/env python3
"""
Advanced Duplicate Detector for Ultra Think Database
高度な重複検出システム
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import re
import unicodedata
from datetime import datetime
import json
from typing import Dict, List, Tuple, Set
import shutil

class AdvancedDuplicateDetector:
    """高度な重複検出エンジン"""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self.duplicates = []
        self.statistics = {
            'total_records': 0,
            'duplicates_found': 0,
            'duplicate_patterns': {},
            'high_confidence_duplicates': 0
        }
        
    def load_data(self):
        """データベースを読み込み"""
        print(f"📂 Loading database from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file, encoding='utf-8')
        self.statistics['total_records'] = len(self.df)
        print(f"✅ Loaded {len(self.df)} records")
        
    def normalize_text(self, text: str) -> str:
        """テキストを正規化"""
        if pd.isna(text):
            return ""
        
        text = str(text)
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[。、！？!?,\.\s]+$', '', text)
        text = text.replace('　', ' ')
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = text.lower()
        text = re.sub(r'\s*[（\(][^）\)]+[）\)]', '', text)
        
        return text
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """文字列の類似度を計算"""
        norm1 = self.normalize_text(str(text1))
        norm2 = self.normalize_text(str(text2))
        
        if norm1 == norm2:
            return 1.0
        
        if norm1 in norm2 or norm2 in norm1:
            return 0.95
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def detect_duplicates(self):
        """重複を検出"""
        print("\n🔍 Detecting duplicates with advanced patterns...")
        
        # 名前ベースの重複検出
        self.detect_name_duplicates()
        
        # 連番IDの重複検出
        self.detect_sequential_id_duplicates()
        
    def detect_name_duplicates(self):
        """名前ベースの重複検出"""
        print("   Checking name-based duplicates...")
        
        name_groups = {}
        
        for idx, row in self.df.iterrows():
            person_name = str(row['person_name'])
            normalized = self.normalize_text(person_name)
            
            if normalized not in name_groups:
                name_groups[normalized] = []
            name_groups[normalized].append({
                'index': idx,
                'person_id': row['person_id'],
                'person_name': person_name,
                'person_name_display': row['person_name_display'],
                'recognition': row.get('name_recognition', 0)
            })
        
        # 重複グループを検出
        for normalized_name, records in name_groups.items():
            if len(records) > 1:
                self.duplicates.append({
                    'type': 'name_duplicate',
                    'normalized_name': normalized_name,
                    'records': records,
                    'confidence': 0.95
                })
                
                # りんたろーのケースをログ
                if any('りんたろー' in r['person_name'] for r in records):
                    print(f"   ⚠️ Found りんたろー duplicates: {[r['person_id'] for r in records]}")
    
    def detect_sequential_id_duplicates(self):
        """連番IDで似た名前を検出"""
        print("   Checking sequential ID duplicates...")
        
        for i in range(len(self.df) - 1):
            current = self.df.iloc[i]
            next_rec = self.df.iloc[i + 1]
            
            try:
                current_num = int(current['person_id'][1:])
                next_num = int(next_rec['person_id'][1:])
                
                if next_num == current_num + 1:
                    similarity = self.calculate_similarity(
                        current['person_name'],
                        next_rec['person_name']
                    )
                    
                    if similarity > 0.85:
                        self.duplicates.append({
                            'type': 'sequential_duplicate',
                            'records': [
                                {
                                    'person_id': current['person_id'],
                                    'person_name': current['person_name'],
                                    'recognition': current.get('name_recognition', 0)
                                },
                                {
                                    'person_id': next_rec['person_id'],
                                    'person_name': next_rec['person_name'],
                                    'recognition': next_rec.get('name_recognition', 0)
                                }
                            ],
                            'similarity': similarity,
                            'confidence': similarity
                        })
            except (ValueError, KeyError):
                continue
    
    def analyze_duplicates(self):
        """重複を分析"""
        print("\n📊 Analyzing duplicates...")
        
        all_duplicates = set()
        high_confidence = 0
        
        for dup in self.duplicates:
            if dup['confidence'] >= 0.90:
                high_confidence += 1
            
            for record in dup['records']:
                all_duplicates.add(record['person_id'])
        
        self.statistics['duplicates_found'] = len(all_duplicates)
        self.statistics['high_confidence_duplicates'] = high_confidence
        
        # P000141/P000142の詳細
        rintaro_dups = [d for d in self.duplicates 
                       if any('りんたろー' in str(r.get('person_name', '')) 
                             for r in d['records'])]
        
        if rintaro_dups:
            print("\n🎯 P000141/P000142 (りんたろー) Analysis:")
            for dup in rintaro_dups:
                print(f"   Type: {dup['type']}")
                print(f"   Confidence: {dup['confidence']:.2%}")
                for record in dup['records']:
                    print(f"      {record['person_id']}: {record.get('person_name')} (Recognition: {record.get('recognition', 0)})")
        
        return all_duplicates
    
    def run(self):
        """完全な重複検出プロセスを実行"""
        print("="*60)
        print("ADVANCED DUPLICATE DETECTOR")
        print("="*60)
        
        self.load_data()
        self.detect_duplicates()
        duplicates = self.analyze_duplicates()
        
        print(f"\n✅ Detection complete!")
        print(f"   Found {self.statistics['duplicates_found']} potential duplicates")
        
        return duplicates


def main():
    csv_file = 'ultra_think_GROUP_FIXED_20250831_185100.csv'
    detector = AdvancedDuplicateDetector(csv_file)
    duplicates = detector.run()
    
    if duplicates:
        print(f"\n⚠️ {len(duplicates)} duplicates detected!")
        print("   Including P000141/P000142 (りんたろー)")
    else:
        print("\n✅ No duplicates found!")
    
    return duplicates

if __name__ == "__main__":
    main()
