#!/usr/bin/env python3
"""
誤削除データの復元スクリプト
連続IDパターンで誤ってプレースホルダーとして削除されたデータを復元
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


def analyze_wrongly_deleted_data(df_original, df_deleted):
    """誤削除されたデータの分析"""
    logger.info("=" * 60)
    logger.info("🔍 誤削除データの分析")
    logger.info("=" * 60)

    # スコア0のデータを抽出
    score_zero = df_deleted[df_deleted['name_recognition'] == 0].copy()

    # 保護すべきデータの特定
    protected_data = []

    # 1. 女子プロレスラー（Wikipedia掲載者多数）
    wrestlers = score_zero[score_zero['occupation'].str.contains('女子プロレス', na=False)]
    logger.info(f"女子プロレスラー: {len(wrestlers)}件")
    protected_data.extend(wrestlers['person_id'].tolist())

    # 2. バッチ追加データ（original_batch_id持ち）
    if 'extra' in score_zero.columns:
        batch_added = score_zero[score_zero['extra'].str.contains('original_batch_id', na=False)]
        logger.info(f"バッチ追加データ: {len(batch_added)}件")
        protected_data.extend(batch_added['person_id'].tolist())

    # 3. 有名スポーツ選手の個別確認（Wikipedia掲載確実な人物）
    famous_athletes = [
        # 女子プロレスラー
        'Bull Nakano', 'Akira Hokuto', 'Jaguar Yokota', 'Aja Kong',
        'Dump Matsumoto', 'Chigusa Nagayo', 'Lioness Asuka', 'Shinobu Kandori',
        'Manami Toyota', 'Io Shirai', 'Kairi Sane', 'Asuka',
        # その他の可能性のある有名選手を検索
        '北斗晶', 'ジャガー横田', 'アジャ・コング', 'ダンプ松本', '神取忍',
        'ブル中野', '長与千種', 'ライオネス飛鳥', '豊田真奈美',
        '紫雷イオ', 'カイリ・セイン', 'アスカ'
    ]

    for name in famous_athletes:
        matches = score_zero[
            (score_zero['person_name'].str.contains(name, na=False)) |
            (score_zero['person_name_display'].str.contains(name, na=False))
        ]
        if len(matches) > 0:
            logger.info(f"  有名人検出: {name} - {len(matches)}件")
            protected_data.extend(matches['person_id'].tolist())

    # 重複を除去
    protected_data = list(set(protected_data))

    logger.info(f"\n📊 復元対象: {len(protected_data)}件")

    return protected_data


def restore_data(df, person_ids_to_restore, original_df):
    """データの復元（元のスコアに戻す）"""
    logger.info("=" * 60)
    logger.info("♻️ データ復元")
    logger.info("=" * 60)

    restored_count = 0

    for person_id in person_ids_to_restore:
        # 削除後のデータでマスク
        mask = df['person_id'] == person_id

        if mask.any():
            # 元のデータから元のスコアを取得
            original_mask = original_df['person_id'] == person_id
            if original_mask.any():
                original_score = original_df.loc[original_mask, 'name_recognition'].values[0]
                df.loc[mask, 'name_recognition'] = original_score
                restored_count += 1

                # ログ出力
                person_name = df.loc[mask, 'person_name'].values[0]
                occupation = df.loc[mask, 'occupation'].values[0] if 'occupation' in df.columns else 'N/A'
                logger.info(f"  復元: {person_id} - {person_name} ({occupation}) - スコア: {original_score}")

    logger.info(f"\n✅ {restored_count}件を復元")

    return df


def validate_restoration(df):
    """復元後の検証"""
    logger.info("=" * 60)
    logger.info("✅ 復元後の検証")
    logger.info("=" * 60)

    # スコア分布
    score_dist = {
        'score_0': (df['name_recognition'] == 0).sum(),
        'score_0_10': ((df['name_recognition'] > 0) & (df['name_recognition'] <= 10)).sum(),
        'score_10_30': ((df['name_recognition'] > 10) & (df['name_recognition'] <= 30)).sum(),
        'score_30_50': ((df['name_recognition'] > 30) & (df['name_recognition'] <= 50)).sum(),
        'score_50_70': ((df['name_recognition'] > 50) & (df['name_recognition'] <= 70)).sum(),
        'score_70_100': (df['name_recognition'] > 70).sum()
    }

    logger.info("スコア分布:")
    for range_name, count in score_dist.items():
        percentage = count / len(df) * 100
        logger.info(f"  {range_name}: {count}件 ({percentage:.1f}%)")

    # 女子プロレスラーの確認
    if 'occupation' in df.columns:
        wrestlers = df[df['occupation'].str.contains('女子プロレス', na=False)]
        wrestlers_with_score = wrestlers[wrestlers['name_recognition'] > 0]
        logger.info(f"\n女子プロレスラー:")
        logger.info(f"  総数: {len(wrestlers)}件")
        logger.info(f"  スコア>0: {len(wrestlers_with_score)}件")

    return score_dist


def generate_restoration_report(original_count, restored_ids, final_stats):
    """復元レポート生成"""
    # Convert numpy int64 to Python int
    final_stats_converted = {k: int(v) if isinstance(v, (np.integer, np.int64)) else v for k, v in final_stats.items()}

    report = {
        "timestamp": datetime.now().isoformat(),
        "restoration_summary": {
            "original_deleted_count": int(original_count),
            "restored_count": len(restored_ids),
            "restoration_rate": float(len(restored_ids) / original_count * 100) if original_count > 0 else 0
        },
        "restored_categories": {
            "women_wrestlers": len([pid for pid in restored_ids if 'P00550' in pid or 'P00551' in pid or 'P00552' in pid]),
            "other_athletes": len(restored_ids) - len([pid for pid in restored_ids if 'P00550' in pid or 'P00551' in pid or 'P00552' in pid])
        },
        "final_statistics": final_stats_converted,
        "restored_person_ids": restored_ids
    }

    report_file = f"restoration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n📝 レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 誤削除データ復元開始")
    logger.info("=" * 60)

    # 元のデータ（CLEANEDファイル）を読み込み
    original_file = "ultra_think_CLEANED_20250911_192323.csv"
    logger.info(f"📂 元データ読み込み: {original_file}")
    df_original = pd.read_csv(original_file)

    # プレースホルダー処理後のデータを読み込み
    deleted_file = "ultra_think_PLACEHOLDER_REMOVED_20250911_194305.csv"
    logger.info(f"📂 処理後データ読み込み: {deleted_file}")
    df_deleted = pd.read_csv(deleted_file)

    # スコア0のレコード数
    score_zero_count = (df_deleted['name_recognition'] == 0).sum()
    logger.info(f"📊 スコア0レコード: {score_zero_count}件")

    # 誤削除データの分析
    protected_ids = analyze_wrongly_deleted_data(df_original, df_deleted)

    # データの復元
    df_restored = restore_data(df_deleted.copy(), protected_ids, df_original)

    # 復元後の検証
    final_stats = validate_restoration(df_restored)

    # 復元後のデータ保存
    output_file = f"ultra_think_RESTORED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_restored.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 復元データ保存: {output_file}")

    # レポート生成
    report = generate_restoration_report(score_zero_count, protected_ids, final_stats)

    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 復元完了")
    logger.info("=" * 60)
    logger.info(f"  元のスコア0: {score_zero_count}件")
    logger.info(f"  復元数: {len(protected_ids)}件")
    logger.info(f"  最終スコア0: {(df_restored['name_recognition'] == 0).sum()}件")
    logger.info(f"  削減率: {(score_zero_count - len(protected_ids))/score_zero_count*100:.1f}%")

    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 処理完了")
    print(f"📁 復元データ: {output_file}")
    print(f"📊 復元レコード: {report['restoration_summary']['restored_count']}件")
