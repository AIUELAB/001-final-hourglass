#!/usr/bin/env python3
"""
改善版Wikipedia検索システムでの再処理スクリプト
4,701件のデータを正しく評価し直す
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import time
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# 改善版のWikipedia検索システムをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2 as WikipediaRecognitionSystem

def load_latest_data():
    """最新のultra_thinkデータを読み込み"""
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_RANKED_20250907_161756.csv"
    
    if not os.path.exists(csv_file):
        logger.error(f"ファイルが見つかりません: {csv_file}")
        return None
    
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み完了: {len(df)}件")
        return df
    except Exception as e:
        logger.error(f"CSV読み込みエラー: {e}")
        return None

def analyze_current_state(df):
    """現在の削除状態を分析"""
    if 'should_delete' not in df.columns:
        logger.warning("should_delete列が存在しません")
        return
    
    total = len(df)
    delete_count = df['should_delete'].sum() if 'should_delete' in df.columns else 0
    delete_rate = (delete_count / total * 100) if total > 0 else 0
    
    logger.info("="*60)
    logger.info("📊 現在の状態分析")
    logger.info("="*60)
    logger.info(f"総レコード数: {total:,}")
    logger.info(f"削除対象数: {delete_count:,}")
    logger.info(f"削除率: {delete_rate:.1f}%")
    
    if delete_rate > 20:
        logger.warning(f"⚠️ 削除率が異常に高い！ (正常範囲: 10-20%)")
    
    return delete_count, delete_rate

def reprocess_with_improved_system(df, sample_size=None):
    """改善版システムで再処理"""
    
    # WikipediaRecognitionSystemを初期化
    wiki_system = WikipediaRecognitionSystem()
    
    # サンプルサイズの設定
    if sample_size:
        df_process = df.head(sample_size)
        logger.info(f"サンプル処理モード: {sample_size}件")
    else:
        df_process = df
        logger.info(f"全件処理モード: {len(df_process)}件")
    
    # 処理結果を格納
    results = []
    
    # プログレス表示の設定
    total = len(df_process)
    checkpoint_interval = 100
    
    logger.info("="*60)
    logger.info("🔄 改善版Wikipedia検索システムで再処理開始")
    logger.info("="*60)
    
    start_time = time.time()
    errors = 0
    success = 0
    
    for idx, row in df_process.iterrows():
        try:
            # person_name_displayを優先、なければperson_nameを使用
            name = row.get('person_name_display', row.get('person_name', ''))
            
            if not name:
                logger.warning(f"行 {idx}: 名前が空です")
                continue
            
            # Wikipedia検索を実行
            result = wiki_system.search_wikipedia(name)
            
            # 結果を記録
            results.append({
                'person_id': row.get('person_id', f'P{idx:06d}'),
                'person_name': name,
                'wikipedia_found': result['found'],
                'wikipedia_score': result.get('recognition_score', 0),
                'wikipedia_page_title': result.get('page_title', ''),
                'search_variations_tried': len(result.get('search_attempts', [])),
                'successful_variant': result.get('successful_variant', ''),
                'should_delete': not result['found'] and result.get('recognition_score', 0) < 3.0
            })
            
            success += 1
            
            # チェックポイント
            if (idx + 1) % checkpoint_interval == 0:
                current_results = pd.DataFrame(results)
                delete_count = current_results['should_delete'].sum()
                delete_rate = delete_count / len(current_results) * 100
                
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed if elapsed > 0 else 0
                eta = (total - (idx + 1)) / rate if rate > 0 else 0
                
                logger.info(f"進捗: {idx+1}/{total} ({(idx+1)/total*100:.1f}%)")
                logger.info(f"  削除率: {delete_rate:.1f}% (削除: {delete_count}/{len(current_results)})")
                logger.info(f"  処理速度: {rate:.1f}件/秒")
                logger.info(f"  推定残り時間: {eta/60:.1f}分")
                
                # 削除率が20%を超えたら警告
                if delete_rate > 20:
                    logger.warning(f"⚠️ 削除率が20%を超えています！ ({delete_rate:.1f}%)")
                    
                    # RULE_035により自動停止
                    if delete_rate > 30:
                        logger.error("🚨 削除率が30%を超えたため処理を中断します")
                        break
            
        except Exception as e:
            logger.error(f"行 {idx} 処理エラー: {e}")
            errors += 1
            continue
    
    # 処理完了
    elapsed_total = time.time() - start_time
    
    logger.info("="*60)
    logger.info("✅ 再処理完了")
    logger.info("="*60)
    logger.info(f"処理時間: {elapsed_total/60:.1f}分")
    logger.info(f"成功: {success}件")
    logger.info(f"エラー: {errors}件")
    
    return pd.DataFrame(results)

def save_results(df_results):
    """結果を保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"reprocessed_wikipedia_{timestamp}.csv"
    
    # UTF-8 BOMで保存（Excel対応）
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"結果を保存しました: {output_file}")
    
    # 統計情報も保存
    if len(df_results) > 0:
        stats = {
            'timestamp': timestamp,
            'total_records': len(df_results),
            'wikipedia_found': df_results['wikipedia_found'].sum() if 'wikipedia_found' in df_results.columns else 0,
            'should_delete': df_results['should_delete'].sum() if 'should_delete' in df_results.columns else 0,
            'deletion_rate': (df_results['should_delete'].sum() / len(df_results) * 100) if 'should_delete' in df_results.columns and len(df_results) > 0 else 0,
            'average_score': df_results['wikipedia_score'].mean() if 'wikipedia_score' in df_results.columns else 0,
            'variations_tried': df_results['search_variations_tried'].mean() if 'search_variations_tried' in df_results.columns else 0
        }
    else:
        stats = {
            'timestamp': timestamp,
            'total_records': 0,
            'wikipedia_found': 0,
            'should_delete': 0,
            'deletion_rate': 0,
            'average_score': 0,
            'variations_tried': 0
        }
    
    stats_file = f"reprocessed_wikipedia_{timestamp}_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"統計情報を保存しました: {stats_file}")
    
    return output_file, stats

def verify_improvements(df_results):
    """改善の検証"""
    logger.info("="*60)
    logger.info("📊 改善効果の検証")
    logger.info("="*60)
    
    # 括弧付き名前の処理確認
    parentheses_names = df_results[df_results['person_name'].str.contains(r'[（(]', na=False)]
    if len(parentheses_names) > 0:
        found_with_parentheses = parentheses_names['wikipedia_found'].sum()
        rate = found_with_parentheses / len(parentheses_names) * 100
        logger.info(f"括弧付き名前: {len(parentheses_names)}件中{found_with_parentheses}件でWikipedia発見 ({rate:.1f}%)")
    
    # 有名人の確認
    famous_people = [
        "吉田美和 (DREAMS COME TRUE)",
        "PSY (サイ)",
        "ル・セラフィム",
        "HIKAKIN",
        "大谷翔平"
    ]
    
    for name in famous_people:
        person_data = df_results[df_results['person_name'].str.contains(name.split('(')[0].strip(), na=False)]
        if not person_data.empty:
            row = person_data.iloc[0]
            status = "✅" if row['wikipedia_found'] else "❌"
            logger.info(f"{status} {name}: スコア={row['wikipedia_score']:.1f}, 削除={row['should_delete']}")

def main():
    """メイン処理"""
    logger.info("="*60)
    logger.info("🚀 Wikipedia検索システム改善版での再処理")
    logger.info("="*60)
    
    # データ読み込み
    df = load_latest_data()
    if df is None:
        return
    
    # 現在の状態を分析
    analyze_current_state(df)
    
    # ユーザーに確認
    logger.info("\n処理オプション:")
    logger.info("1. サンプル処理 (100件)")
    logger.info("2. 全件処理 (4,701件、約5-8時間)")
    
    # サンプル処理で開始
    logger.info("\nまずサンプル100件で処理を開始します...")
    
    # 再処理実行（まずはサンプル）
    df_results = reprocess_with_improved_system(df, sample_size=100)
    
    # 結果を保存
    output_file, stats = save_results(df_results)
    
    # 改善効果を検証
    verify_improvements(df_results)
    
    # 最終統計
    logger.info("="*60)
    logger.info("📈 最終統計")
    logger.info("="*60)
    logger.info(f"削除率: {stats['deletion_rate']:.1f}%")
    logger.info(f"Wikipedia発見: {stats['wikipedia_found']}/{stats['total_records']}")
    logger.info(f"平均スコア: {stats['average_score']:.2f}")
    logger.info(f"平均検索バリエーション数: {stats['variations_tried']:.1f}")
    
    if stats['deletion_rate'] <= 20:
        logger.info("✅ 削除率が正常範囲内です！")
    else:
        logger.warning("⚠️ 削除率がまだ高めです。追加の調整が必要かもしれません。")

if __name__ == "__main__":
    main()