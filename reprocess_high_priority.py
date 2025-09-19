#!/usr/bin/env python3
"""
高優先度データの再処理
ヒカキンなど明らかな有名人と括弧付き名前を優先的に再評価
"""

import pandas as pd
import json
import time
from datetime import datetime
import logging
from pathlib import Path
import sys

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# 改善版システムをインポート
sys.path.append(str(Path(__file__).parent))
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

def load_data_with_issues():
    """問題のあるデータを読み込み"""
    
    # 元の結果ファイル
    result_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/recognition_results_ALL_20250908_224635.csv"
    
    try:
        df = pd.read_csv(result_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み完了: {len(df)}件")
        return df
    except Exception as e:
        logger.error(f"データ読み込みエラー: {e}")
        return None

def identify_high_priority_records(df):
    """高優先度レコードを特定"""
    
    high_priority = []
    
    # 1. 明らかな有名人（スコア0で削除対象）
    famous_names = [
        "ヒカキン", "HIKAKIN", "HikakinTV",
        "はじめしゃちょー", "hajime", 
        "フィッシャーズ", "Fischer's",
        "東海オンエア", 
        "水溜りボンド",
        "吉田美和", "DREAMS COME TRUE",
        "PSY", "サイ",
        "ル・セラフィム", "LE SSERAFIM",
        "BTS", "防弾少年団",
        "TWICE", "トゥワイス",
        "NewJeans", "ニュージーンズ",
        "Stray Kids", "ストレイキッズ"
    ]
    
    for name in famous_names:
        # 名前が含まれていて、削除対象になっているレコード
        matches = df[
            (df['name'].str.contains(name, case=False, na=False)) & 
            (df['should_delete'] == True)
        ]
        if not matches.empty:
            for idx, row in matches.iterrows():
                high_priority.append({
                    'index': idx,
                    'person_id': row['person_id'],
                    'person_name': row['name'],
                    'current_score': row.get('recognition_score', 0),
                    'reason': f'有名人なのに削除対象: {name}'
                })
    
    # 2. 括弧付き名前（処理改善が必要）
    parentheses_records = df[
        df['name'].str.contains(r'[（(]', na=False) &
        (df['should_delete'] == True)
    ]
    
    for idx, row in parentheses_records.head(100).iterrows():  # 最初の100件
        high_priority.append({
            'index': idx,
            'person_id': row['person_id'],
            'person_name': row['name'],
            'current_score': row.get('recognition_score', 0),
            'reason': '括弧付き名前の処理改善'
        })
    
    logger.info(f"高優先度レコード: {len(high_priority)}件")
    return high_priority

def reprocess_priority_records(df, priority_records):
    """高優先度レコードを再処理"""
    
    wiki_system = WikipediaRecognitionSystemV2()
    results = []
    
    logger.info("="*60)
    logger.info("🔄 高優先度レコードの再処理開始")
    logger.info("="*60)
    
    total = len(priority_records)
    success = 0
    improved = 0
    
    for i, record in enumerate(priority_records):
        try:
            name = record['person_name']
            logger.info(f"\n[{i+1}/{total}] 処理中: {name}")
            logger.info(f"  理由: {record['reason']}")
            logger.info(f"  現在のスコア: {record['current_score']}")
            
            # Wikipedia検索
            result = wiki_system.search_wikipedia(name)
            
            new_score = result.get('recognition_score', 0)
            found = result.get('found', False)
            
            # 改善されたか確認
            if new_score > record['current_score']:
                improved += 1
                logger.info(f"  ✅ 改善: {record['current_score']} → {new_score}")
            else:
                logger.info(f"  ⚠️ 変化なし: {new_score}")
            
            if found:
                success += 1
                logger.info(f"  📖 Wikipedia: {result.get('page_title', 'N/A')}")
            
            results.append({
                'person_id': record['person_id'],
                'person_name': name,
                'old_score': record['current_score'],
                'new_score': new_score,
                'wikipedia_found': found,
                'wikipedia_page': result.get('page_title', ''),
                'successful_variant': result.get('successful_variant', ''),
                'should_delete': not found and new_score < 3.0,
                'improvement': new_score - record['current_score']
            })
            
            # レート制限対策
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"エラー: {record['person_name']} - {e}")
            continue
    
    logger.info("="*60)
    logger.info("📊 再処理結果")
    logger.info("="*60)
    logger.info(f"処理件数: {total}")
    logger.info(f"Wikipedia発見: {success} ({success/total*100:.1f}%)")
    logger.info(f"スコア改善: {improved} ({improved/total*100:.1f}%)")
    
    return pd.DataFrame(results)

def analyze_improvement(df_results):
    """改善効果を分析"""
    
    logger.info("="*60)
    logger.info("📈 改善効果分析")
    logger.info("="*60)
    
    # 削除対象から除外されたレコード
    saved_records = df_results[
        (df_results['old_score'] == 0) & 
        (df_results['new_score'] > 0)
    ]
    
    logger.info(f"削除対象から救済: {len(saved_records)}件")
    
    # 大幅改善（スコア5以上向上）
    major_improvements = df_results[df_results['improvement'] >= 5]
    logger.info(f"大幅改善（+5以上）: {len(major_improvements)}件")
    
    # 有名人の改善例
    if len(saved_records) > 0:
        logger.info("\n✅ 救済された有名人（上位10件）:")
        for _, row in saved_records.head(10).iterrows():
            logger.info(f"  - {row['person_name']}: {row['old_score']:.1f} → {row['new_score']:.1f}")
    
    # 統計サマリー
    avg_improvement = df_results['improvement'].mean()
    max_improvement = df_results['improvement'].max()
    
    logger.info(f"\n統計:")
    logger.info(f"  平均改善: +{avg_improvement:.2f}")
    logger.info(f"  最大改善: +{max_improvement:.1f}")
    logger.info(f"  削除率への影響: -{len(saved_records)/47.01:.1f}%")

def save_results(df_results):
    """結果を保存"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV保存
    csv_file = f"high_priority_reprocessed_{timestamp}.csv"
    df_results.to_csv(csv_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n結果CSV: {csv_file}")
    
    # 統計情報保存
    stats = {
        'timestamp': timestamp,
        'total_processed': len(df_results),
        'wikipedia_found': df_results['wikipedia_found'].sum(),
        'saved_from_deletion': len(df_results[(df_results['old_score'] == 0) & (df_results['new_score'] > 0)]),
        'average_improvement': float(df_results['improvement'].mean()),
        'max_improvement': float(df_results['improvement'].max())
    }
    
    stats_file = f"high_priority_stats_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"統計JSON: {stats_file}")
    
    return csv_file, stats_file

def main():
    """メイン処理"""
    
    logger.info("高優先度データ再処理ツール")
    logger.info("="*60)
    
    # データ読み込み
    df = load_data_with_issues()
    if df is None:
        return
    
    # 高優先度レコード特定
    priority_records = identify_high_priority_records(df)
    
    if not priority_records:
        logger.info("高優先度レコードが見つかりませんでした")
        return
    
    # 再処理実行
    df_results = reprocess_priority_records(df, priority_records)
    
    # 改善効果分析
    analyze_improvement(df_results)
    
    # 結果保存
    save_results(df_results)
    
    logger.info("\n✅ 高優先度データの再処理完了")

if __name__ == "__main__":
    main()