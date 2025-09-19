#!/usr/bin/env python3
"""
削除された人物からブラックパターンを抽出
"""

import pandas as pd
import json
from collections import Counter
import re

def analyze_blacklist_patterns():
    """削除された人物からパターンを抽出"""
    
    # 削除データを読み込み
    deleted_file = "deleted_persons_20250828_075912.csv"
    print(f"📁 削除データを読み込み中: {deleted_file}")
    df = pd.read_csv(deleted_file, encoding='utf-8')
    print(f"✅ {len(df)}人の削除人物を読み込みました")
    
    # パターン分析
    patterns = {
        'occupation_patterns': [],  # 職業パターン
        'category_patterns': [],    # カテゴリパターン
        'era_patterns': [],         # 時代パターン
        'name_patterns': [],        # 名前パターン
        'rules': {}                 # 自動判定ルール
    }
    
    # 1. 職業パターンの分析
    print("\n📊 職業パターン分析:")
    occupation_counts = df['occupation'].value_counts()
    
    # 削除率が高い職業を抽出
    blacklist_occupations = []
    for occ, count in occupation_counts.items():
        if count >= 10:  # 10人以上削除された職業
            blacklist_occupations.append({
                'pattern': str(occ),
                'count': int(count),
                'confidence': 0.9  # 高確率で削除
            })
    
    patterns['occupation_patterns'] = blacklist_occupations[:50]  # 上位50職業
    
    print(f"  高削除率職業: {len(blacklist_occupations)}種類")
    for item in blacklist_occupations[:10]:
        print(f"    {item['pattern']}: {item['count']}人")
    
    # 2. 職業の一般パターン抽出
    occupation_suffixes = Counter()
    for occ in df['occupation'].dropna():
        occ_str = str(occ)
        # 「○○選手」「○○奉行」などのパターンを抽出
        if '選手' in occ_str:
            occupation_suffixes['選手'] += 1
        if '奉行' in occ_str:
            occupation_suffixes['奉行'] += 1
        if '代官' in occ_str:
            occupation_suffixes['代官'] += 1
        if '家臣' in occ_str:
            occupation_suffixes['家臣'] += 1
        if '藩主' in occ_str:
            occupation_suffixes['藩主'] += 1
        if '大名' in occ_str:
            occupation_suffixes['大名'] += 1
        if '武将' in occ_str:
            occupation_suffixes['武将'] += 1
    
    # 3. カテゴリパターンの分析
    print("\n📊 カテゴリパターン分析:")
    category_counts = df['category'].value_counts()
    
    category_deletion_rates = {}
    for cat, count in category_counts.items():
        deletion_rate = count / len(df)
        category_deletion_rates[str(cat)] = {
            'count': int(count),
            'rate': float(deletion_rate),
            'action': 'review' if deletion_rate > 0.1 else 'pass'
        }
    
    patterns['category_patterns'] = category_deletion_rates
    
    print(f"  カテゴリ別削除数:")
    for cat, info in list(category_deletion_rates.items())[:5]:
        print(f"    {cat}: {info['count']}人 ({info['rate']*100:.1f}%)")
    
    # 4. 自動判定ルールの生成
    rules = {
        'auto_delete': {
            'occupations': [
                '代官', '勘定奉行', '若年寄', '旗本', '老中',
                '町奉行', '寺社奉行', '家老', '藩士', '御家人'
            ],
            'patterns': [
                {'type': 'suffix', 'value': '奉行', 'confidence': 0.8},
                {'type': 'suffix', 'value': '代官', 'confidence': 0.8},
                {'type': 'suffix', 'value': '家臣', 'confidence': 0.7},
                {'type': 'contains', 'value': '藩主', 'confidence': 0.7}
            ]
        },
        'review_required': {
            'occupations': [
                '俳優', '歌手', '芸人', 'タレント', 'モデル',
                'アナウンサー', '声優', 'YouTuber', 'インフルエンサー'
            ],
            'categories': ['エンタメ', 'メディア', 'その他'],
            'name_recognition_threshold': 30  # 認知度30%未満は要確認
        },
        'auto_keep': {
            'categories': ['学術・科学', '政治', '文化・芸術'],
            'name_recognition_threshold': 50  # 認知度50%以上は維持
        }
    }
    
    patterns['rules'] = rules
    
    # 5. 統計サマリー
    summary = {
        'total_deleted': len(df),
        'unique_occupations': len(occupation_counts),
        'unique_categories': len(category_counts),
        'top_deleted_occupation': str(occupation_counts.index[0]) if len(occupation_counts) > 0 else '',
        'top_deleted_category': str(category_counts.index[0]) if len(category_counts) > 0 else ''
    }
    
    patterns['summary'] = summary
    
    print(f"\n📈 削除パターンサマリー:")
    print(f"  総削除数: {summary['total_deleted']}")
    print(f"  ユニーク職業数: {summary['unique_occupations']}")
    print(f"  最多削除職業: {summary['top_deleted_occupation']}")
    print(f"  最多削除カテゴリ: {summary['top_deleted_category']}")
    
    # ファイル保存
    output_file = "blacklist_patterns.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(patterns, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ブラックパターンを保存: {output_file}")
    
    return patterns


if __name__ == "__main__":
    analyze_blacklist_patterns()