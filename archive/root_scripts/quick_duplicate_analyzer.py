#!/usr/bin/env python3
"""
Quick Duplicate Analyzer - 高速重複分析

P000141/P000142のりんたろー重複を含む147件の重複を効率的に分析
"""

import pandas as pd
import json
from datetime import datetime
from collections import defaultdict
import difflib
import re

def normalize_name(name):
    """名前正規化"""
    if pd.isna(name) or not name:
        return ""

    normalized = str(name).strip()
    # 括弧削除
    normalized = re.sub(r'\s*\([^)]*\)\s*', '', normalized)
    # 句読点統一
    normalized = normalized.replace('。', '').replace('_', '')
    return normalized.lower()

def quick_duplicate_detection():
    """高速重複検出"""
    print("=== Quick Duplicate Detection ===")

    # データ読み込み
    df = pd.read_csv("ultra_think_GROUP_FIXED_20250831_185100.csv")
    print(f"総レコード数: {len(df)}")

    # 1. Person ID重複チェック
    person_id_dups = df['person_id'].value_counts()
    person_id_dups = person_id_dups[person_id_dups > 1]
    print(f"\nPerson ID重複: {len(person_id_dups)}件")

    # 2. 名前フィールドでの重複チェック
    name_fields = ['person_name', 'person_name_display', 'person_name_ja']
    duplicate_analysis = {
        'person_id_duplicates': [],
        'name_duplicates': [],
        'high_similarity_pairs': []
    }

    # Person ID重複の詳細
    for person_id, count in person_id_dups.items():
        dup_records = df[df['person_id'] == person_id]
        duplicate_analysis['person_id_duplicates'].append({
            'person_id': person_id,
            'count': count,
            'names': dup_records['person_name'].tolist(),
            'recognition_scores': dup_records['name_recognition'].tolist(),
            'indices': dup_records.index.tolist()
        })

    # 名前ベースの重複検出（効率化版）
    print("\n名前ベースの重複検出...")

    # 正規化名前でグルーピング
    name_groups = defaultdict(list)

    for idx, row in df.iterrows():
        for field in name_fields:
            if pd.notna(row[field]):
                normalized = normalize_name(row[field])
                if len(normalized) > 2:  # 短すぎる名前は除外
                    name_groups[normalized].append({
                        'index': idx,
                        'person_id': row['person_id'],
                        'original_name': row[field],
                        'field': field,
                        'name_recognition': row.get('name_recognition', 0)
                    })

    # 重複グループを特定
    name_duplicates_found = 0
    for normalized_name, records in name_groups.items():
        if len(records) > 1:
            # 異なるperson_idを持つ重複のみカウント
            person_ids = set(r['person_id'] for r in records)
            if len(person_ids) > 1:
                name_duplicates_found += 1

                # 品質分析
                quality_scores = []
                for record in records:
                    idx = record['index']
                    row = df.loc[idx]
                    quality = float(row.get('name_recognition', 0)) + float(row.get('accuracy_score', 0))
                    quality_scores.append((quality, record))

                quality_scores.sort(key=lambda x: x[0], reverse=True)

                duplicate_analysis['name_duplicates'].append({
                    'normalized_name': normalized_name,
                    'person_ids': list(person_ids),
                    'records': records,
                    'best_record': quality_scores[0][1],
                    'quality_scores': [(q, r['person_id']) for q, r in quality_scores]
                })

    print(f"名前ベースの重複: {name_duplicates_found}件")

    # 特別ケース: P000141とP000142の詳細分析
    print("\n=== P000141/P000142詳細分析 ===")
    p141_data = df[df['person_id'] == 'P000141']
    p142_data = df[df['person_id'] == 'P000142']

    if not p141_data.empty and not p142_data.empty:
        p141 = p141_data.iloc[0]
        p142 = p142_data.iloc[0]

        print(f"P000141: {p141['person_name']} | 認識スコア: {p141['name_recognition']}")
        print(f"P000142: {p142['person_name']} | 認識スコア: {p142['name_recognition']}")

        # 類似度計算
        similarity = difflib.SequenceMatcher(None,
                                           normalize_name(p141['person_name']),
                                           normalize_name(p142['person_name'])).ratio()
        print(f"名前類似度: {similarity:.3f}")

        # 推奨アクション
        if p141['name_recognition'] > p142['name_recognition']:
            print(f"推奨: P000141を保持、P000142を削除")
        else:
            print(f"推奨: P000142を保持、P000141を削除")

    # 統計サマリー
    total_duplicates = len(person_id_dups) + name_duplicates_found
    print(f"\n=== 重複統計 ===")
    print(f"Person ID重複: {len(person_id_dups)}件")
    print(f"名前ベース重複: {name_duplicates_found}件")
    print(f"推定総重複: {total_duplicates}件")

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"QUICK_DUPLICATE_ANALYSIS_{timestamp}.json"

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(duplicate_analysis, f, ensure_ascii=False, indent=2)

    print(f"分析レポート保存: {report_path}")

    return duplicate_analysis, report_path

if __name__ == "__main__":
    quick_duplicate_detection()
