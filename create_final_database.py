#!/usr/bin/env python3
"""
最終データベース生成スクリプト
スコア0のレコードを除外し、クリーンなデータベースを作成
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_latest_database():
    """最新のデータベースファイルを読み込み"""
    # PLACEHOLDER_REMOVEDファイルを探す
    files = list(Path('.').glob('ultra_think_PLACEHOLDER_REMOVED_*.csv'))
    
    if not files:
        # なければCLEANEDファイルを探す
        files = list(Path('.').glob('ultra_think_CLEANED_*.csv'))
    
    if not files:
        raise FileNotFoundError("処理済みデータベースファイルが見つかりません")
    
    # 最新のファイルを選択
    latest_file = sorted(files, key=lambda x: x.stat().st_mtime)[-1]
    logger.info(f"📂 データベース読み込み: {latest_file}")
    
    return pd.read_csv(latest_file), latest_file.name


def analyze_database(df):
    """データベースの分析"""
    logger.info("=" * 60)
    logger.info("📊 データベース分析")
    logger.info("=" * 60)
    
    # スコア分布
    score_distribution = {
        'score_0': (df['name_recognition'] == 0).sum(),
        'score_1_10': ((df['name_recognition'] > 0) & (df['name_recognition'] <= 10)).sum(),
        'score_10_30': ((df['name_recognition'] > 10) & (df['name_recognition'] <= 30)).sum(),
        'score_30_50': ((df['name_recognition'] > 30) & (df['name_recognition'] <= 50)).sum(),
        'score_50_70': ((df['name_recognition'] > 50) & (df['name_recognition'] <= 70)).sum(),
        'score_70_100': (df['name_recognition'] > 70).sum()
    }
    
    logger.info("スコア分布:")
    for range_name, count in score_distribution.items():
        percentage = count / len(df) * 100
        logger.info(f"  {range_name}: {count}件 ({percentage:.1f}%)")
    
    # エンティティタイプ分布
    if 'entity_type' in df.columns:
        entity_types = df['entity_type'].value_counts()
        logger.info("\nエンティティタイプ:")
        for entity_type, count in entity_types.items():
            logger.info(f"  {entity_type}: {count}件")
    
    # 職業分布（上位10）
    if 'occupation' in df.columns:
        top_occupations = df['occupation'].value_counts().head(10)
        logger.info("\n職業分布（上位10）:")
        for occupation, count in top_occupations.items():
            logger.info(f"  {occupation}: {count}件")
    
    return score_distribution


def remove_score_zero_records(df):
    """スコア0のレコードを除外"""
    logger.info("=" * 60)
    logger.info("🗑️ スコア0レコード除外")
    logger.info("=" * 60)
    
    score_zero_count = (df['name_recognition'] == 0).sum()
    logger.info(f"スコア0レコード数: {score_zero_count}件")
    
    if score_zero_count > 0:
        # スコア0のサンプル表示
        score_zero_sample = df[df['name_recognition'] == 0].head(10)
        logger.info("\nスコア0レコードのサンプル（最初の10件）:")
        for _, row in score_zero_sample.iterrows():
            logger.info(f"  {row['person_id']}: {row['person_name']} ({row.get('occupation', 'N/A')})")
        
        # 除外実行
        df_clean = df[df['name_recognition'] > 0].copy()
        logger.info(f"\n✅ {score_zero_count}件を除外")
        logger.info(f"最終レコード数: {len(df_clean)}件")
        
        return df_clean, score_zero_count
    else:
        logger.info("✅ スコア0のレコードはありません")
        return df, 0


def validate_final_database(df):
    """最終データベースの妥当性検証"""
    logger.info("=" * 60)
    logger.info("✅ 最終検証")
    logger.info("=" * 60)
    
    validations = []
    
    # 1. グループエンティティチェック
    if 'entity_type' in df.columns:
        group_count = (df['entity_type'] == 'group').sum()
        if group_count == 0:
            logger.info("✅ グループエンティティなし")
            validations.append({"check": "no_groups", "passed": True})
        else:
            logger.warning(f"⚠️ グループエンティティが{group_count}件残っています")
            validations.append({"check": "no_groups", "passed": False, "count": group_count})
    
    # 2. スコア範囲チェック
    invalid_scores = df[(df['name_recognition'] < 0) | (df['name_recognition'] > 100)]
    if len(invalid_scores) == 0:
        logger.info("✅ スコア範囲正常（0-100）")
        validations.append({"check": "score_range", "passed": True})
    else:
        logger.warning(f"⚠️ 異常スコアが{len(invalid_scores)}件あります")
        validations.append({"check": "score_range", "passed": False, "count": len(invalid_scores)})
    
    # 3. 既知有名人チェック
    known_celebrities = ['HIKAKIN', '米津玄師', '大谷翔平']
    for celebrity in known_celebrities:
        if celebrity in df['person_name'].values:
            score = df[df['person_name'] == celebrity]['name_recognition'].values[0]
            if score > 7.0:
                logger.info(f"✅ {celebrity}: スコア{score}")
                validations.append({"check": f"celebrity_{celebrity}", "passed": True, "score": float(score)})
            else:
                logger.warning(f"⚠️ {celebrity}のスコアが低すぎます: {score}")
                validations.append({"check": f"celebrity_{celebrity}", "passed": False, "score": float(score)})
    
    # 4. 重複チェック
    duplicates = df[df.duplicated(subset=['person_name', 'occupation'], keep=False)]
    if len(duplicates) == 0:
        logger.info("✅ 重複なし")
        validations.append({"check": "no_duplicates", "passed": True})
    else:
        logger.info(f"ℹ️ {len(duplicates)}件の潜在的重複（同姓同名の別人の可能性）")
        validations.append({"check": "no_duplicates", "info": True, "count": len(duplicates)})
    
    return validations


def generate_final_report(df, original_count, removed_count, validations):
    """最終レポート生成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "database_stats": {
            "original_count": int(original_count),
            "removed_count": int(removed_count),
            "final_count": int(len(df))
        },
        "score_distribution": {
            "min": float(df['name_recognition'].min()),
            "max": float(df['name_recognition'].max()),
            "mean": float(df['name_recognition'].mean()),
            "median": float(df['name_recognition'].median())
        },
        "validations": validations,
        "quality_metrics": {
            "removal_rate": float(removed_count / original_count * 100) if original_count > 0 else 0,
            "avg_score": float(df['name_recognition'].mean()),
            "high_score_count": int((df['name_recognition'] >= 7.0).sum())
        }
    }
    
    report_file = f"final_database_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📝 レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 最終データベース生成開始")
    logger.info("=" * 60)
    
    # データ読み込み
    df, source_file = load_latest_database()
    original_count = len(df)
    logger.info(f"📊 元レコード数: {original_count}件")
    
    # データベース分析
    score_dist = analyze_database(df)
    
    # スコア0レコード除外
    df_clean, removed_count = remove_score_zero_records(df)
    
    # 最終検証
    validations = validate_final_database(df_clean)
    
    # 最終データベース保存
    output_file = f"ultra_think_FINAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_clean.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 最終データベース保存: {output_file}")
    
    # レポート生成
    report = generate_final_report(df_clean, original_count, removed_count, validations)
    
    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 最終データベース生成完了")
    logger.info("=" * 60)
    logger.info(f"  元レコード数: {original_count}件")
    logger.info(f"  除外レコード数: {removed_count}件")
    logger.info(f"  最終レコード数: {len(df_clean)}件")
    logger.info(f"  削除率: {removed_count/original_count*100:.1f}%")
    logger.info(f"  平均スコア: {df_clean['name_recognition'].mean():.2f}")
    logger.info(f"  高スコア（≥7.0）: {(df_clean['name_recognition'] >= 7.0).sum()}件")
    
    # 品質判定
    if removed_count / original_count <= 0.20:  # 削除率20%以下
        logger.info("\n✅ 品質基準クリア")
    else:
        logger.warning(f"\n⚠️ 削除率が高い（{removed_count/original_count*100:.1f}%）")
    
    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 処理完了")
    print(f"📁 最終データベース: {output_file}")
    print(f"📊 最終レコード数: {report['database_stats']['final_count']}件")