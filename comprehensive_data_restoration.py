#!/usr/bin/env python3
"""
包括的データ復元スクリプト
連続IDパターンによる誤削除を完全に修正
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


def analyze_and_restore_batch_data(df_original, df_deleted):
    """バッチ追加データの誤削除を分析・復元"""
    logger.info("=" * 60)
    logger.info("🔍 バッチ追加データの分析・復元")
    logger.info("=" * 60)

    # スコア0のデータを抽出
    score_zero = df_deleted[df_deleted['name_recognition'] == 0].copy()
    score_zero['id_num'] = score_zero['person_id'].str.extract(r'P(\d+)')[0].astype(int)

    # 復元対象のリスト
    restoration_targets = []

    # 1. 連続ID + 同一職業パターン（バッチ追加の明確な証拠）
    logger.info("\n📊 連続ID + 同一職業パターンの検出")
    score_zero_sorted = score_zero.sort_values('id_num')

    consecutive_groups = []
    current_group = []
    prev_id = -1

    for _, row in score_zero_sorted.iterrows():
        id_num = row['id_num']
        if prev_id == -1 or id_num == prev_id + 1:
            current_group.append(row)
        else:
            if len(current_group) >= 3:  # 3件以上連続を対象に変更（5件は厳しすぎる）
                consecutive_groups.append(current_group)
            current_group = [row]
        prev_id = id_num

    if len(current_group) >= 3:
        consecutive_groups.append(current_group)

    # 同一職業の連続グループを復元対象に
    for group in consecutive_groups:
        occupations = set([row['occupation'] for row in group])

        # 同一職業または関連職業のグループ
        if len(occupations) <= 2:  # 1-2種類の職業なら同一バッチの可能性大
            person_ids = [row['person_id'] for row in group]
            restoration_targets.extend(person_ids)

            logger.info(f"  バッチ検出: {person_ids[0]} - {person_ids[-1]} ({len(person_ids)}件)")
            logger.info(f"    職業: {list(occupations)}")

    # 2. 特定の職業カテゴリ（スポーツ選手など明らかに実在する可能性が高い）
    logger.info("\n📊 職業別の復元候補")

    # スポーツ選手は基本的に実在する可能性が高い
    sports_occupations = [
        '女子プロレスラー', 'サッカー選手', '野球選手', 'バスケットボール選手',
        'テニス選手', '水泳選手', '陸上選手', 'バレーボール選手', '体操選手',
        'フィギュアスケート選手', '卓球選手', 'バドミントン選手', 'レスリング選手',
        'ラグビー選手', '柔道選手', 'ボクシング選手', 'ゴルフ選手', '女子格闘家'
    ]

    for occupation in sports_occupations:
        occ_records = score_zero[score_zero['occupation'].str.contains(occupation, na=False)]
        if len(occ_records) > 0:
            # 連続IDチェック（3件以上連続なら確実にバッチ追加）
            occ_records_sorted = occ_records.sort_values('id_num')
            id_nums = occ_records_sorted['id_num'].values

            # 連続性チェック
            consecutive_count = 1
            for i in range(1, len(id_nums)):
                if id_nums[i] == id_nums[i-1] + 1:
                    consecutive_count += 1
                else:
                    if consecutive_count >= 3:
                        # 連続部分を復元対象に
                        start_idx = i - consecutive_count
                        end_idx = i
                        targets = occ_records_sorted.iloc[start_idx:end_idx]['person_id'].tolist()
                        restoration_targets.extend(targets)
                    consecutive_count = 1

            # 最後のグループもチェック
            if consecutive_count >= 3:
                start_idx = len(id_nums) - consecutive_count
                targets = occ_records_sorted.iloc[start_idx:]['person_id'].tolist()
                restoration_targets.extend(targets)

            logger.info(f"  {occupation}: {len(occ_records)}件検出")

    # 3. 明らかにプレースホルダーではないパターンを除外
    logger.info("\n📊 プレースホルダーパターンの再評価")

    # 真のプレースホルダーパターン（非常に限定的）
    true_placeholders = []

    # パターン1: 明らかなテストデータ（リーチ + ラグビー + マイケル以外）
    reach_pattern = score_zero[
        (score_zero['person_name'].str.contains('リーチ', na=False)) &
        (score_zero['occupation'] == 'ラグビー選手') &
        (~score_zero['person_name'].str.contains('マイケル', na=False))
    ]
    true_placeholders.extend(reach_pattern['person_id'].tolist())

    # パターン2: 定型的な名前の組み合わせ（太郎、次郎、三郎が連続）
    generic_names = ['太郎', '次郎', '三郎', '四郎', '五郎']
    for name in generic_names:
        name_pattern = score_zero[score_zero['person_name'].str.contains(name, na=False)]
        if len(name_pattern) >= 3:
            # 連続IDチェック
            name_sorted = name_pattern.sort_values('id_num')
            id_nums = name_sorted['id_num'].values
            if all(id_nums[i] == id_nums[i-1] + 1 for i in range(1, min(3, len(id_nums)))):
                true_placeholders.extend(name_pattern['person_id'].tolist())

    logger.info(f"  真のプレースホルダー: {len(true_placeholders)}件")

    # 復元対象から真のプレースホルダーを除外
    restoration_targets = list(set(restoration_targets) - set(true_placeholders))

    # 重複を除去
    restoration_targets = list(set(restoration_targets))

    logger.info(f"\n✅ 復元対象: {len(restoration_targets)}件")

    return restoration_targets, true_placeholders


def restore_scores(df, person_ids_to_restore, original_df):
    """スコアを元の値に復元"""
    logger.info("=" * 60)
    logger.info("♻️ スコア復元")
    logger.info("=" * 60)

    restored_count = 0
    restoration_log = []

    for person_id in person_ids_to_restore:
        mask = df['person_id'] == person_id

        if mask.any():
            # 元のデータから元のスコアを取得
            original_mask = original_df['person_id'] == person_id
            if original_mask.any():
                original_score = original_df.loc[original_mask, 'name_recognition'].values[0]
                df.loc[mask, 'name_recognition'] = original_score
                restored_count += 1

                # ログ記録
                person_name = df.loc[mask, 'person_name'].values[0]
                occupation = df.loc[mask, 'occupation'].values[0] if 'occupation' in df.columns else 'N/A'
                restoration_log.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'occupation': occupation,
                    'restored_score': float(original_score)
                })

                if restored_count <= 10:  # 最初の10件を表示
                    logger.info(f"  復元: {person_id} - {person_name} ({occupation}) - スコア: {original_score}")

    if restored_count > 10:
        logger.info(f"  ... 他 {restored_count - 10}件")

    logger.info(f"\n✅ {restored_count}件を復元")

    return df, restoration_log


def validate_restoration(df):
    """復元後の妥当性検証"""
    logger.info("=" * 60)
    logger.info("✅ 復元後の検証")
    logger.info("=" * 60)

    # スコア分布
    score_dist = {
        'score_0': int((df['name_recognition'] == 0).sum()),
        'score_0_10': int(((df['name_recognition'] > 0) & (df['name_recognition'] <= 10)).sum()),
        'score_10_30': int(((df['name_recognition'] > 10) & (df['name_recognition'] <= 30)).sum()),
        'score_30_50': int(((df['name_recognition'] > 30) & (df['name_recognition'] <= 50)).sum()),
        'score_50_70': int(((df['name_recognition'] > 50) & (df['name_recognition'] <= 70)).sum()),
        'score_70_100': int((df['name_recognition'] > 70).sum())
    }

    logger.info("スコア分布:")
    for range_name, count in score_dist.items():
        percentage = count / len(df) * 100
        logger.info(f"  {range_name}: {count}件 ({percentage:.1f}%)")

    # 職業別統計
    if 'occupation' in df.columns:
        logger.info("\n職業別復元状況:")
        sports_occupations = ['女子プロレスラー', 'サッカー選手', '野球選手', 'バスケットボール選手']
        for occ in sports_occupations:
            occ_records = df[df['occupation'].str.contains(occ, na=False)]
            if len(occ_records) > 0:
                occ_with_score = occ_records[occ_records['name_recognition'] > 0]
                logger.info(f"  {occ}: 総数{len(occ_records)}件, スコア>0: {len(occ_with_score)}件")

    return score_dist


def generate_comprehensive_report(restoration_log, true_placeholders, final_stats):
    """包括的な復元レポート生成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "restoration_summary": {
            "total_score_zero_before": 644,
            "restored_count": len(restoration_log),
            "true_placeholders_count": len(true_placeholders),
            "final_score_zero": final_stats['score_0']
        },
        "restoration_by_occupation": {},
        "validation_results": {
            "score_distribution": final_stats,
            "deletion_rate_before": 13.88,
            "deletion_rate_after": float(final_stats['score_0'] / 4639 * 100) if final_stats['score_0'] > 0 else 0
        },
        "restoration_log": restoration_log[:100]  # 最初の100件のみ
    }

    # 職業別の復元統計
    from collections import Counter
    occupation_counter = Counter([item['occupation'] for item in restoration_log])
    report['restoration_by_occupation'] = dict(occupation_counter.most_common(20))

    report_file = f"comprehensive_restoration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n📝 包括レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 包括的データ復元開始")
    logger.info("=" * 60)

    # 元のデータ（CLEANEDファイル）を読み込み
    original_file = "ultra_think_CLEANED_20250911_192323.csv"
    logger.info(f"📂 元データ読み込み: {original_file}")
    df_original = pd.read_csv(original_file)

    # プレースホルダー処理後のデータを読み込み
    deleted_file = "ultra_think_PLACEHOLDER_REMOVED_20250911_194305.csv"
    logger.info(f"📂 処理後データ読み込み: {deleted_file}")
    df_deleted = pd.read_csv(deleted_file)

    # バックアップ作成
    import shutil
    backup_file = f"backup_{deleted_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(deleted_file, backup_file)
    logger.info(f"💾 バックアップ作成: {backup_file}")

    # スコア0のレコード数
    score_zero_count = (df_deleted['name_recognition'] == 0).sum()
    logger.info(f"📊 スコア0レコード（修正前）: {score_zero_count}件")

    # バッチデータの分析と復元対象の特定
    restoration_targets, true_placeholders = analyze_and_restore_batch_data(df_original, df_deleted)

    # スコアの復元
    df_restored, restoration_log = restore_scores(df_deleted.copy(), restoration_targets, df_original)

    # 復元後の検証
    final_stats = validate_restoration(df_restored)

    # 復元後のデータ保存
    output_file = f"ultra_think_COMPREHENSIVE_RESTORED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_restored.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 復元データ保存: {output_file}")

    # 包括レポート生成
    report = generate_comprehensive_report(restoration_log, true_placeholders, final_stats)

    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 包括的復元完了")
    logger.info("=" * 60)
    logger.info(f"  元のスコア0: {score_zero_count}件")
    logger.info(f"  復元数: {len(restoration_log)}件")
    logger.info(f"  真のプレースホルダー: {len(true_placeholders)}件")
    logger.info(f"  最終スコア0: {final_stats['score_0']}件")
    logger.info(f"  削減率: {score_zero_count - final_stats['score_0']}件削減")

    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 包括的復元完了")
    print(f"📁 復元データ: {output_file}")
    print(f"📊 復元レコード: {report['restoration_summary']['restored_count']}件")
    print(f"📊 最終スコア0: {report['restoration_summary']['final_score_zero']}件")
