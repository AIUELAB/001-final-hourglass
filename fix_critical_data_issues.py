#!/usr/bin/env python3
"""
重大なデータ品質問題の修正
1. グループ名の修正（P003218など）
2. プレースホルダーデータの削除（ダニエル名）
3. データ整合性の確認
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import shutil
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_database(csv_file):
    """データベースのバックアップを作成"""
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(csv_file, backup_file)
    logger.info(f"💾 バックアップ作成: {backup_file}")
    return backup_file


def fix_group_names(df):
    """グループのperson_name問題を修正"""
    logger.info("=" * 60)
    logger.info("🔧 グループ名の修正")
    logger.info("=" * 60)
    
    # グループレコードを特定
    groups = df[df['entity_type'] == 'group'].copy()
    logger.info(f"📊 グループ数: {len(groups)}件")
    
    fixes = []
    
    for idx, row in groups.iterrows():
        person_id = row['person_id']
        current_name = row['person_name']
        display_name = row['person_name_display']
        
        # person_nameとdisplay_nameが異なる場合は修正が必要
        if current_name != display_name:
            logger.info(f"  ❌ {person_id}: '{current_name}' → '{display_name}'")
            df.at[idx, 'person_name'] = display_name
            fixes.append({
                'person_id': person_id,
                'old_name': current_name,
                'new_name': display_name,
                'type': 'group_name_fix'
            })
        else:
            logger.info(f"  ✅ {person_id}: '{current_name}' (正常)")
    
    logger.info(f"\n✅ グループ名修正: {len(fixes)}件")
    return df, fixes


def remove_placeholders(df):
    """プレースホルダーデータを削除"""
    logger.info("=" * 60)
    logger.info("🗑️ プレースホルダーの削除")
    logger.info("=" * 60)
    
    deletions = []
    
    # 1. ダニエル名パターンの削除（P000826-P000833）
    daniel_ids = [f'P00082{i}' for i in range(6, 10)] + [f'P00083{i}' for i in range(0, 4)]
    daniel_pattern = df['person_id'].isin(daniel_ids)
    
    logger.info(f"📋 ダニエル名プレースホルダー: {daniel_pattern.sum()}件")
    for idx in df[daniel_pattern].index:
        row = df.loc[idx]
        logger.info(f"  削除: {row['person_id']}: {row['person_name']} ({row['occupation']})")
        deletions.append({
            'person_id': row['person_id'],
            'person_name': row['person_name'],
            'reason': 'daniel_placeholder',
            'occupation': row['occupation']
        })
    
    # 2. 他の疑わしいテニス選手パターンも確認
    tennis_players = df[
        (df['occupation'] == 'テニス選手') & 
        (df['name_recognition'] == 50.0) &
        (df['nationality'] == '日本')
    ]
    
    # ダニエル以外の疑わしいパターンを検出
    suspicious_patterns = []
    for idx, row in tennis_players.iterrows():
        name = row['person_name']
        # カタカナ名 + 日本人名のパターン
        if any(foreign in name for foreign in ['マイケル', 'ジョン', 'ロバート', 'デビッド']):
            if row['person_id'] not in daniel_ids:
                suspicious_patterns.append(row)
    
    if suspicious_patterns:
        logger.info(f"\n⚠️ 他の疑わしいパターン: {len(suspicious_patterns)}件")
        for row in suspicious_patterns[:5]:  # 最初の5件を表示
            logger.info(f"  要確認: {row['person_id']}: {row['person_name']}")
    
    # ダニエルパターンのみ削除（他は要手動確認）
    df_cleaned = df[~daniel_pattern].copy()
    logger.info(f"\n✅ 削除完了: {len(deletions)}件")
    logger.info(f"📊 残りレコード: {len(df_cleaned)}件")
    
    return df_cleaned, deletions


def validate_data_integrity(df):
    """データ整合性の検証"""
    logger.info("=" * 60)
    logger.info("🔍 データ整合性検証")
    logger.info("=" * 60)
    
    issues = []
    
    # 1. entity_typeのNULLチェック
    null_entity = df['entity_type'].isna().sum()
    if null_entity > 0:
        issues.append(f"entity_typeがNULL: {null_entity}件")
    
    # 2. グループのperson_name検証
    groups = df[df['entity_type'] == 'group']
    for idx, row in groups.iterrows():
        if row['person_name'] != row['person_name_display']:
            issues.append(f"グループ名不一致: {row['person_id']}")
    
    # 3. 同一スコアクラスターの検出
    score_counts = df['name_recognition'].value_counts()
    for score, count in score_counts.items():
        if count > 50:  # 50件以上の同一スコア
            logger.warning(f"  ⚠️ スコア {score}: {count}件（要確認）")
    
    # 4. 連番IDの検出
    df_sorted = df.sort_values('person_id')
    consecutive_groups = []
    current_group = []
    
    for i in range(len(df_sorted) - 1):
        curr_id = int(df_sorted.iloc[i]['person_id'][1:])
        next_id = int(df_sorted.iloc[i + 1]['person_id'][1:])
        
        if next_id == curr_id + 1:
            if not current_group:
                current_group.append(df_sorted.iloc[i])
            current_group.append(df_sorted.iloc[i + 1])
        else:
            if len(current_group) >= 10:  # 10件以上の連番
                consecutive_groups.append(current_group)
            current_group = []
    
    if consecutive_groups:
        logger.warning(f"  ⚠️ 連番IDグループ: {len(consecutive_groups)}個検出")
    
    if issues:
        logger.error(f"❌ 整合性問題: {len(issues)}件")
        for issue in issues[:10]:  # 最初の10件表示
            logger.error(f"  - {issue}")
    else:
        logger.info("✅ データ整合性: 問題なし")
    
    return issues


def generate_fix_report(fixes, deletions, issues, original_count, final_count):
    """修正レポートの生成"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'original_count': original_count,
        'final_count': final_count,
        'change_count': original_count - final_count,
        'group_fixes': len(fixes),
        'deletions': len(deletions),
        'integrity_issues': len(issues),
        'details': {
            'group_fixes': fixes,
            'deletions': deletions,
            'issues': issues
        }
    }
    
    report_file = f"data_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📝 レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 重大データ品質問題の修正開始")
    logger.info("=" * 60)
    
    # データ読み込み
    csv_file = "ultra_think_FINAL_DATABASE_20250910_202039.csv"
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    original_count = len(df)
    logger.info(f"📊 元レコード数: {original_count}件")
    
    # バックアップ作成
    backup_file = backup_database(csv_file)
    
    # 1. グループ名の修正
    df, fixes = fix_group_names(df)
    
    # 2. プレースホルダーの削除
    df, deletions = remove_placeholders(df)
    
    # 3. データ整合性の検証
    issues = validate_data_integrity(df)
    
    # 4. 修正後のデータ保存
    output_file = f"ultra_think_FIXED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")
    
    # 5. レポート生成
    final_count = len(df)
    report = generate_fix_report(fixes, deletions, issues, original_count, final_count)
    
    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 修正完了サマリー")
    logger.info("=" * 60)
    logger.info(f"  元レコード数: {original_count}件")
    logger.info(f"  最終レコード数: {final_count}件")
    logger.info(f"  削除数: {original_count - final_count}件")
    logger.info(f"  グループ名修正: {len(fixes)}件")
    logger.info(f"  プレースホルダー削除: {len(deletions)}件")
    logger.info(f"  残存問題: {len(issues)}件")
    
    if len(issues) == 0:
        logger.info("\n✅ すべての重大問題を修正しました！")
    else:
        logger.warning(f"\n⚠️ {len(issues)}件の問題が残っています（要手動確認）")
    
    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 処理完了")
    print(f"📁 出力ファイル: {output_file}")