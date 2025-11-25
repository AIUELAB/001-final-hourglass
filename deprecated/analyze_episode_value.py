#!/usr/bin/env python3
"""
エピソード価値分析スクリプト
Episode Value Analysis Script

このスクリプトは、エピソードとしての価値が低い真のプレースホルダーを特定します。
架空キャラクターも含めたエピソードデータベースとして分析を行います。
"""

import pandas as pd
import json
import re
from datetime import datetime
from collections import Counter

def calculate_episode_value_score(row):
    """
    エピソード価値スコアを計算
    高いスコア = 削除候補
    低いスコア = 保持すべき
    """
    score = 0.0

    # 1. 知名度スコア (50% weight)
    recognition = row.get('name_recognition', 35)
    if pd.isna(recognition) or recognition < 30:
        score += 0.5
    elif recognition < 35:
        score += 0.4
    elif recognition == 35:  # 疑わしい一律スコア
        score += 0.3
    elif recognition < 40:
        score += 0.2
    # 40以上は価値ありとして0点

    # 2. 設定充実度 (30% weight)
    person_name = str(row.get('person_name', ''))
    person_name_display = str(row.get('person_name_display', ''))
    occupation = str(row.get('occupation', ''))
    nationality = str(row.get('nationality', ''))

    # 設定が不明確な場合
    if occupation in ['不明', '', 'nan', None, 'None']:
        score += 0.3
    elif occupation == '架空キャラクター':
        # 架空キャラクターは設定ありとして減点しない
        score += 0.0

    if nationality in ['不明', '', 'nan', None, 'None']:
        score += 0.15

    # 作品名付きの架空キャラクターは価値あり
    if '（' in person_name_display and '）' in person_name_display:
        score -= 0.2  # ボーナス点

    # 3. データ完全性 (20% weight)
    missing_count = 0
    critical_fields = ['person_name', 'person_name_display', 'occupation']

    for field in critical_fields:
        if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
            missing_count += 1

    score += (missing_count / len(critical_fields)) * 0.2

    return min(1.0, max(0.0, score))  # 0-1の範囲に制限

def detect_placeholder_patterns(name):
    """
    プレースホルダーパターンを検出
    """
    if pd.isna(name):
        return True

    name = str(name)

    # 明確なプレースホルダーパターン
    placeholder_patterns = [
        r'^田中太郎',
        r'^山田花子',
        r'^テスト',
        r'^Test',
        r'^Sample',
        r'^Person\d+',
        r'^User\d+',
        r'^名前\d+',
        r'^人物\d+',
        r'^Character\d+',
        r'^\d+$',  # 数字のみ
        r'^[A-Z]{1,2}\d+$',  # A1, B2などのパターン
    ]

    for pattern in placeholder_patterns:
        if re.match(pattern, name, re.IGNORECASE):
            return True

    # 汎用的すぎる名前
    generic_names = [
        '太郎', '花子', '一郎', '次郎', '三郎',
        'たろう', 'はなこ', 'いちろう', 'じろう',
        'タロウ', 'ハナコ', 'イチロウ', 'ジロウ',
        'test', 'sample', 'example', 'dummy',
        'placeholder', 'temp', 'tmp'
    ]

    name_lower = name.lower()
    for generic in generic_names:
        if generic.lower() == name_lower:
            return True

    return False

def identify_protected_entries(row):
    """
    保護すべきエントリーを識別
    """
    # 架空キャラクター（設定あり）は保護
    if row.get('category') == '架空の存在':
        return True

    # 作品名付きキャラクターは保護
    display = str(row.get('person_name_display', ''))
    if '（' in display and '）' in display:
        return True

    # VTuber/YouTuberは保護
    occupation = str(row.get('occupation', '')).lower()
    if 'youtuber' in occupation or 'vtuber' in occupation or 'ユーチューバー' in occupation:
        return True

    # ミュージシャン/アーティストは保護
    if any(word in occupation for word in ['歌手', '音楽', 'ミュージシャン', 'アーティスト', 'バンド', 'ボーカル']):
        return True

    # 高知名度（40以上）は保護
    if row.get('name_recognition', 0) >= 40:
        return True

    return False

def main():
    print("="*60)
    print("エピソード価値分析")
    print("Episode Value Analysis")
    print("="*60)

    # データベース読み込み
    csv_file = 'ultra_think_FICTIONAL_COMPLETE_20250901_005521.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")

    # 分析結果の初期化
    analysis_results = {
        'total_records': len(df),
        'category_a': [],  # 即削除（高確信度）
        'category_b': [],  # 検証後削除（中確信度）
        'category_c': [],  # 保護対象
        'statistics': {}
    }

    # 各レコードを分析
    print("\n🔍 Analyzing episode value for each record...")

    for idx, row in df.iterrows():
        person_id = row['person_id']
        person_name = row.get('person_name', '')
        person_name_display = row.get('person_name_display', '')
        occupation = row.get('occupation', '')
        recognition = row.get('name_recognition', 35)

        # プレースホルダーパターン検出
        is_placeholder = detect_placeholder_patterns(person_name) or \
                        detect_placeholder_patterns(person_name_display)

        # 保護対象チェック
        is_protected = identify_protected_entries(row)

        # エピソード価値スコア計算
        episode_score = calculate_episode_value_score(row)

        # カテゴリ分類
        if is_protected:
            analysis_results['category_c'].append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_display': person_name_display,
                'occupation': occupation,
                'recognition': recognition,
                'reason': 'Protected entry'
            })
        elif is_placeholder or episode_score >= 0.90:
            analysis_results['category_a'].append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_display': person_name_display,
                'occupation': occupation,
                'recognition': recognition,
                'score': episode_score,
                'reason': 'Placeholder pattern' if is_placeholder else 'Very low episode value'
            })
        elif episode_score >= 0.70:
            analysis_results['category_b'].append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_display': person_name_display,
                'occupation': occupation,
                'recognition': recognition,
                'score': episode_score,
                'reason': 'Low episode value'
            })
        else:
            analysis_results['category_c'].append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_display': person_name_display,
                'occupation': occupation,
                'recognition': recognition,
                'reason': 'Acceptable episode value'
            })

    # 統計情報
    print("\n📊 Analysis Results:")
    print(f"  Category A (即削除): {len(analysis_results['category_a'])} records")
    print(f"  Category B (検証後削除): {len(analysis_results['category_b'])} records")
    print(f"  Category C (保護): {len(analysis_results['category_c'])} records")

    # カテゴリAの詳細表示
    if analysis_results['category_a']:
        print("\n🚨 Category A - Immediate deletion candidates:")
        for item in analysis_results['category_a'][:10]:  # 最初の10件
            print(f"  {item['person_id']}: {item['person_name']} - {item['reason']}")
            print(f"    Occupation: {item['occupation']}, Recognition: {item['recognition']}")
        if len(analysis_results['category_a']) > 10:
            print(f"  ... and {len(analysis_results['category_a']) - 10} more")

    # カテゴリBの詳細表示
    if analysis_results['category_b']:
        print("\n⚠️ Category B - Review required:")
        for item in analysis_results['category_b'][:10]:  # 最初の10件
            print(f"  {item['person_id']}: {item['person_name']} - {item['reason']}")
            print(f"    Occupation: {item['occupation']}, Recognition: {item['recognition']}")
        if len(analysis_results['category_b']) > 10:
            print(f"  ... and {len(analysis_results['category_b']) - 10} more")

    # 統計分析
    recognition_scores = df['name_recognition'].dropna()
    analysis_results['statistics'] = {
        'recognition_distribution': {
            '<30': len(df[df['name_recognition'] < 30]),
            '30-34': len(df[(df['name_recognition'] >= 30) & (df['name_recognition'] < 35)]),
            '35': len(df[df['name_recognition'] == 35]),
            '36-39': len(df[(df['name_recognition'] > 35) & (df['name_recognition'] < 40)]),
            '40+': len(df[df['name_recognition'] >= 40])
        },
        'occupation_missing': len(df[df['occupation'].isna() | (df['occupation'] == '不明')]),
        'fictional_characters': len(df[df['category'] == '架空の存在']),
        'vtubers_youtubers': len(df[df['occupation'].str.contains('YouTuber|VTuber|ユーチューバー', na=False, case=False)])
    }

    print("\n📈 Database Statistics:")
    print(f"  Recognition < 30: {analysis_results['statistics']['recognition_distribution']['<30']}")
    print(f"  Recognition = 35 (suspicious): {analysis_results['statistics']['recognition_distribution']['35']}")
    print(f"  Fictional characters: {analysis_results['statistics']['fictional_characters']}")
    print(f"  VTubers/YouTubers: {analysis_results['statistics']['vtubers_youtubers']}")

    # 結果を保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"episode_value_analysis_{timestamp}.json"

    # カテゴリAとBのIDリストを作成
    deletion_candidates = {
        'category_a_ids': [item['person_id'] for item in analysis_results['category_a']],
        'category_b_ids': [item['person_id'] for item in analysis_results['category_b']],
        'category_a_count': len(analysis_results['category_a']),
        'category_b_count': len(analysis_results['category_b']),
        'protected_count': len(analysis_results['category_c']),
        'timestamp': datetime.now().isoformat()
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(deletion_candidates, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Analysis report saved: {report_file}")

    # 詳細レポートも保存
    detailed_report_file = f"episode_value_detailed_{timestamp}.json"
    with open(detailed_report_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    print(f"📝 Detailed report saved: {detailed_report_file}")

    print("\n✅ Episode value analysis completed!")
    print(f"   Recommended deletions: {len(analysis_results['category_a']) + len(analysis_results['category_b'])} records")
    print(f"   ({len(analysis_results['category_a'])} immediate + {len(analysis_results['category_b'])} after review)")

    return deletion_candidates

if __name__ == "__main__":
    results = main()
