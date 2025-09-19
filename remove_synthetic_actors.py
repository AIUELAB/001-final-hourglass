#!/usr/bin/env python3
"""
合成俳優の検出と削除
中村姓の架空俳優を含む、massive_actorsバッチから生成された合成データを除去
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Set
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def detect_synthetic_actors(df: pd.DataFrame) -> List[str]:
    """合成俳優を検出"""
    
    synthetic_ids = []
    
    # 1. 中村姓のパターン（確実に合成）
    nakamura_actors = df[
        (df['person_name_ja'].str.startswith('中村', na=False)) &
        (df['occupation'] == '俳優') &
        (df['name_recognition'] == 60.0)
    ]
    synthetic_ids.extend(nakamura_actors['person_id'].tolist())
    logger.info(f"中村パターン: {len(nakamura_actors)}件検出")
    
    # 2. massive_actorsバッチの全レコード確認
    massive_actors = df[
        (df['data_source'].str.contains('massive_actors', na=False)) |
        (df['data_source'].isna() & (df['occupation'] == '俳優'))
    ]
    
    # 共通パターンを持つ俳優を検出
    for idx, row in massive_actors.iterrows():
        if row['person_id'] not in synthetic_ids:
            # 認知度60.0で正確度85.0のパターン
            if row.get('name_recognition') == 60.0 and row.get('accuracy_score', 85.0) == 85.0:
                synthetic_ids.append(row['person_id'])
    
    # 3. 一般的な姓と名前の組み合わせパターン
    common_surnames = ['佐藤', '鈴木', '高橋', '田中', '渡辺', '伊藤', '山本', '小林', '中村']
    common_first_names = ['健太', '優斗', '大輝', '悠斗', '拓海', '涼太', '真央', '翔', '蓮', '颯太',
                          '太郎', '次郎', '三郎', '健', '勇', '誠', '浩', '隆', '和也', '直樹']
    
    for surname in common_surnames:
        surname_actors = df[
            (df['person_name_ja'].str.startswith(surname, na=False)) &
            (df['occupation'] == '俳優')
        ]
        
        # 同じ姓で5人以上の俳優がいる場合は疑わしい
        if len(surname_actors) >= 5:
            # 名前が一般的なパターンかチェック
            for idx, row in surname_actors.iterrows():
                name = str(row.get('person_name_ja', ''))
                first_name = name.replace(surname, '')
                
                if first_name in common_first_names:
                    if row['person_id'] not in synthetic_ids:
                        # 認知度が低〜中程度（60-70）で一定
                        if 55 <= row.get('name_recognition', 0) <= 70:
                            synthetic_ids.append(row['person_id'])
    
    # 4. タイムスタンプパターン（2025-08-27に大量生成）
    timestamp_pattern = df[
        (df['last_updated'].str.contains('2025-08-27T04:52', na=False)) &
        (df['occupation'] == '俳優')
    ]
    
    for idx, row in timestamp_pattern.iterrows():
        if row['person_id'] not in synthetic_ids:
            synthetic_ids.append(row['person_id'])
    
    # 重複を除去
    synthetic_ids = list(set(synthetic_ids))
    
    logger.info(f"合計 {len(synthetic_ids)}件の合成俳優を検出")
    
    return synthetic_ids

def analyze_synthetic_patterns(df: pd.DataFrame, synthetic_ids: List[str]) -> Dict:
    """合成パターンの分析"""
    
    synthetic_df = df[df['person_id'].isin(synthetic_ids)]
    
    analysis = {
        'total_count': len(synthetic_ids),
        'surname_distribution': {},
        'recognition_scores': {},
        'data_sources': {},
        'timestamps': []
    }
    
    # 姓の分布
    for idx, row in synthetic_df.iterrows():
        name = str(row.get('person_name_ja', ''))
        if len(name) > 0:
            surname = name[:2] if len(name) > 2 else name
            analysis['surname_distribution'][surname] = analysis['surname_distribution'].get(surname, 0) + 1
    
    # 認知度スコアの分布
    for score in synthetic_df['name_recognition'].value_counts().head(10).items():
        analysis['recognition_scores'][float(score[0])] = int(score[1])
    
    # データソースの分布
    for source in synthetic_df['data_source'].value_counts().items():
        analysis['data_sources'][str(source[0])] = int(source[1])
    
    # タイムスタンプのパターン
    timestamps = synthetic_df['last_updated'].dropna().unique()
    analysis['timestamps'] = sorted([str(ts) for ts in timestamps[:10]])
    
    return analysis

def remove_synthetic_actors(csv_file: str) -> str:
    """合成俳優を削除してクリーンなデータを作成"""
    
    logger.info("="*60)
    logger.info("合成俳優の削除処理開始")
    logger.info("="*60)
    
    # データ読み込み
    logger.info(f"ファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    original_count = len(df)
    
    # バックアップ作成
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    logger.info(f"バックアップ作成: {backup_file}")
    
    # 合成俳優の検出
    synthetic_ids = detect_synthetic_actors(df)
    
    # パターン分析
    analysis = analyze_synthetic_patterns(df, synthetic_ids)
    
    # 削除対象のプレビュー
    synthetic_df = df[df['person_id'].isin(synthetic_ids)]
    preview_file = f"SYNTHETIC_ACTORS_TO_REMOVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    synthetic_df.to_csv(preview_file, index=False, encoding='utf-8-sig')
    logger.info(f"削除対象プレビュー: {preview_file}")
    
    # サンプル表示
    logger.info("\n削除対象の例（最初の10件）:")
    for idx, row in synthetic_df.head(10).iterrows():
        logger.info(f"  {row['person_id']}: {row['person_name_ja']} - {row['occupation']}")
    
    # 削除実行
    clean_df = df[~df['person_id'].isin(synthetic_ids)]
    removed_count = original_count - len(clean_df)
    
    # 結果を保存
    output_file = f"ultra_think_CLEAN_NO_SYNTHETIC_ACTORS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    clean_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # レポート生成
    report = {
        'execution_time': datetime.now().isoformat(),
        'original_count': original_count,
        'removed_count': removed_count,
        'final_count': len(clean_df),
        'removal_rate': f"{removed_count/original_count*100:.2f}%",
        'analysis': analysis,
        'files': {
            'backup': backup_file,
            'preview': preview_file,
            'output': output_file
        }
    }
    
    report_file = f"SYNTHETIC_ACTORS_REMOVAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    logger.info("\n" + "="*60)
    logger.info("削除完了")
    logger.info("="*60)
    logger.info(f"元のレコード数: {original_count:,}")
    logger.info(f"削除数: {removed_count:,}")
    logger.info(f"最終レコード数: {len(clean_df):,}")
    logger.info(f"削除率: {removed_count/original_count*100:.2f}%")
    
    logger.info(f"\n姓の分布（上位5）:")
    for surname, count in sorted(analysis['surname_distribution'].items(), 
                                 key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"  {surname}: {count}件")
    
    logger.info(f"\n出力ファイル:")
    logger.info(f"  クリーンデータ: {output_file}")
    logger.info(f"  レポート: {report_file}")
    logger.info(f"  削除対象リスト: {preview_file}")
    
    return output_file

def main():
    """メイン処理"""
    # 最新のデータファイルを使用
    csv_file = "ultra_think_FINAL_VALIDATED_20250912.csv"
    
    # 合成俳優の削除実行
    clean_file = remove_synthetic_actors(csv_file)
    
    logger.info("\n✅ 処理完了")
    logger.info("合成俳優の削除が完了しました。")
    logger.info("PDCAガーディアンにルールを追加して再発を防止してください。")

if __name__ == "__main__":
    main()