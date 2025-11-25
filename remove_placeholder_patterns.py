#!/usr/bin/env python3
"""
明確なプレースホルダーパターンの削除
リーチ姓、関田姓、飯塚姓等の明らかなテストデータを削除
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_database(csv_file):
    """データベースのバックアップ"""
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(csv_file, backup_file)
    logger.info(f"💾 バックアップ作成: {backup_file}")
    return backup_file


def identify_placeholders(df):
    """プレースホルダーの特定"""
    logger.info("=" * 60)
    logger.info("🔍 プレースホルダーパターンの検出")
    logger.info("=" * 60)

    placeholders = []

    # 1. リーチ姓のラグビー選手（リーチマイケル以外）
    reach_pattern = df[
        (df['person_name'].str.contains('リーチ', na=False)) &
        (df['occupation'] == 'ラグビー選手') &
        (~df['person_name'].str.contains('マイケル', na=False))
    ]
    for _, row in reach_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  リーチパターン: {row['person_id']}: {row['person_name']}")

    # 2. 関田姓のバレーボール選手
    sekita_pattern = df[
        (df['person_name'].str.contains('関田', na=False)) &
        (df['occupation'] == 'バレーボール選手')
    ]
    for _, row in sekita_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  関田パターン: {row['person_id']}: {row['person_name']}")

    # 3. 飯塚姓の陸上選手（飯塚翔太は実在するが要確認）
    iizuka_pattern = df[
        (df['person_name'].str.contains('飯塚', na=False)) &
        (df['occupation'] == '陸上選手') &
        (df['person_name'].str.contains('三郎|健太|和也|大輔|太郎|拓也|次郎|雄大', na=False))
    ]
    for _, row in iizuka_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  飯塚パターン: {row['person_id']}: {row['person_name']}")

    # 4. 香川姓のサッカー選手（香川真司以外の定型名）
    kagawa_pattern = df[
        (df['person_name'].str.contains('香川', na=False)) &
        (df['occupation'] == 'サッカー選手') &
        (df['person_name'].str.contains('三郎|健太|和也|大輔|太郎|拓也|次郎|翔太', na=False))
    ]
    for _, row in kagawa_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  香川パターン: {row['person_id']}: {row['person_name']}")

    # 5. 馬場姓のバスケットボール選手（馬場雄大は実在するが要確認）
    baba_pattern = df[
        (df['person_name'].str.contains('馬場', na=False)) &
        (df['occupation'] == 'バスケットボール選手') &
        (df['person_name'].str.contains('三郎|大輔|太郎|拓也|次郎|翔太', na=False))
    ]
    for _, row in baba_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  馬場パターン: {row['person_id']}: {row['person_name']}")

    # 6. 高橋姓の野球選手の定型名
    takahashi_pattern = df[
        (df['person_name'].str.contains('高橋.*拓也|高橋.*次郎|高橋.*直樹|高橋.*翔太', na=False)) &
        (df['occupation'] == '野球選手') &
        (df['name_recognition'] == 50.0)  # スコア50.0も条件に追加
    ]
    for _, row in takahashi_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  高橋パターン: {row['person_id']}: {row['person_name']}")

    # 7. 高谷姓のレスリング選手
    takaya_pattern = df[
        (df['person_name'].str.contains('高谷', na=False)) &
        (df['occupation'] == 'レスリング選手')
    ]
    for _, row in takaya_pattern.iterrows():
        placeholders.append(row['person_id'])
        logger.info(f"  高谷パターン: {row['person_id']}: {row['person_name']}")

    # 8. 伊藤直樹（テニス選手）- 個別指定
    if 'P001949' in df['person_id'].values:
        placeholders.append('P001949')
        logger.info(f"  個別指定: P001949: 伊藤直樹")

    # 9. スコア50.0で連続IDのパターン
    score_50 = df[df['name_recognition'] == 50.0].copy()
    score_50['id_num'] = score_50['person_id'].str.extract(r'P(\d+)')[0].astype(int)
    score_50 = score_50.sort_values('id_num')

    # 連続するIDをグループ化
    consecutive_groups = []
    current_group = []
    prev_id = -1

    for idx, row in score_50.iterrows():
        id_num = row['id_num']
        if prev_id == -1 or id_num == prev_id + 1:
            current_group.append(row['person_id'])
        else:
            if len(current_group) >= 5:  # 5件以上連続
                consecutive_groups.append(current_group)
            current_group = [row['person_id']]
        prev_id = id_num

    if len(current_group) >= 5:
        consecutive_groups.append(current_group)

    for group in consecutive_groups:
        logger.info(f"  連続IDパターン: {group[0]} - {group[-1]} ({len(group)}件)")
        placeholders.extend(group)

    # 重複を除去
    placeholders = list(set(placeholders))
    logger.info(f"\n📊 検出されたプレースホルダー: {len(placeholders)}件")

    return placeholders


def set_score_zero(df, placeholder_ids):
    """プレースホルダーのスコアを0に設定"""
    logger.info("=" * 60)
    logger.info("🔧 スコア0設定")
    logger.info("=" * 60)

    updated_count = 0
    for person_id in placeholder_ids:
        mask = df['person_id'] == person_id
        if mask.any():
            df.loc[mask, 'name_recognition'] = 0.0
            updated_count += 1

    logger.info(f"✅ {updated_count}件のスコアを0に設定")
    return df


def generate_report(df, placeholder_ids, original_count):
    """レポート生成"""
    score_zero = df[df['name_recognition'] == 0]

    report = {
        'timestamp': datetime.now().isoformat(),
        'original_count': original_count,
        'final_count': len(df),
        'placeholder_detected': len(placeholder_ids),
        'score_zero_total': len(score_zero),
        'placeholder_ids': placeholder_ids,
        'statistics': {
            'score_distribution': {
                '0': int((df['name_recognition'] == 0).sum()),
                '0-10': int(((df['name_recognition'] > 0) & (df['name_recognition'] <= 10)).sum()),
                '10-30': int(((df['name_recognition'] > 10) & (df['name_recognition'] <= 30)).sum()),
                '30-50': int(((df['name_recognition'] > 30) & (df['name_recognition'] <= 50)).sum()),
                '50-70': int(((df['name_recognition'] > 50) & (df['name_recognition'] <= 70)).sum()),
                '70-100': int((df['name_recognition'] > 70).sum())
            }
        }
    }

    report_file = f"placeholder_removal_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"📝 レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 プレースホルダー削除処理開始")
    logger.info("=" * 60)

    # データ読み込み
    csv_file = "ultra_think_CLEANED_20250911_192323.csv"
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    original_count = len(df)
    logger.info(f"📊 元レコード数: {original_count}件")

    # バックアップ作成
    backup_file = backup_database(csv_file)

    # プレースホルダー検出
    placeholder_ids = identify_placeholders(df)

    # スコア0設定
    df = set_score_zero(df, placeholder_ids)

    # スコア0のレコードを削除するオプション（コメントアウト中）
    # df = df[df['name_recognition'] > 0].copy()
    # logger.info(f"スコア0削除後: {len(df)}件")

    # 修正後のデータ保存
    output_file = f"ultra_think_PLACEHOLDER_REMOVED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")

    # レポート生成
    report = generate_report(df, placeholder_ids, original_count)

    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 プレースホルダー削除完了")
    logger.info("=" * 60)
    logger.info(f"  元レコード数: {original_count}件")
    logger.info(f"  最終レコード数: {len(df)}件")
    logger.info(f"  プレースホルダー検出: {len(placeholder_ids)}件")
    logger.info(f"  スコア0設定: {(df['name_recognition'] == 0).sum()}件")

    # スコア分布表示
    logger.info("\n📊 スコア分布:")
    for range_label, count in report['statistics']['score_distribution'].items():
        logger.info(f"  {range_label}: {count}件")

    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 処理完了")
    print(f"📁 出力ファイル: {output_file}")
