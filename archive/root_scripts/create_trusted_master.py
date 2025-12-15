#!/usr/bin/env python3
"""
final_fact_checked_episodes.csvに載っているエピソードのみを信頼できるものとして
新しいマスターファイルを作成する
"""

import pandas as pd
from datetime import datetime
import shutil
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def create_trusted_master():
    """信頼できるエピソードのみでマスターファイルを作成"""

    logger.info("=" * 60)
    logger.info("信頼できるエピソードマスターファイルの作成")
    logger.info("=" * 60)

    # 1. final_fact_checked_episodes.csvを読み込み
    trusted_file = 'final_fact_checked_episodes.csv'
    logger.info(f"\n📂 信頼できるエピソードファイルを読み込み: {trusted_file}")

    df_trusted = pd.read_csv(trusted_file, encoding='utf-8-sig')
    logger.info(f"✅ {len(df_trusted)}件の検証済みエピソードを読み込み")

    # 2. エピソード内容の確認
    logger.info("\n📋 エピソード内容:")
    for idx, row in df_trusted.iterrows():
        logger.info(f"  {idx+1}. {row['person_name']}（{row['episode_age']}歳）- {row['fact_check_status']}")

    # 3. 既存ファイルのアーカイブ
    logger.info("\n📦 既存ファイルのアーカイブ:")
    archive_dir = 'archive/obsolete_episodes'
    os.makedirs(archive_dir, exist_ok=True)

    # アーカイブ対象のファイルパターン
    archive_patterns = [
        'ultra_think_*.csv',
        'direct_103_episodes_*.csv',
        '*_episodes_*.csv'
    ]

    import glob
    archived_count = 0
    for pattern in archive_patterns:
        for file in glob.glob(pattern):
            if file != trusted_file:  # 信頼できるファイル以外をアーカイブ
                dest = os.path.join(archive_dir, file)
                shutil.move(file, dest)
                logger.info(f"  📁 {file} → {archive_dir}/")
                archived_count += 1

    logger.info(f"  ✅ {archived_count}個のファイルをアーカイブ")

    # 4. 新しいマスターファイルの作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    master_file = f'trusted_episodes_master_{timestamp}.csv'

    # 必要なカラムを整理
    df_master = df_trusted.copy()

    # カラム名の統一（必要に応じて）
    df_master['person_name'] = df_trusted['person_name']
    df_master['episode_age'] = df_trusted['episode_age']
    df_master['user_age'] = df_trusted['user_age']
    df_master['episode_text'] = df_trusted['episode_text']
    df_master['character_count'] = df_trusted['character_count']
    df_master['category'] = df_trusted['category']
    df_master['weighted_score'] = df_trusted['weighted_score']
    df_master['fact_check_status'] = df_trusted['fact_check_status']
    df_master['is_valid'] = df_trusted['is_valid']
    df_master['created_date'] = timestamp

    # 保存
    df_master.to_csv(master_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 新しいマスターファイル作成: {master_file}")

    # 5. サマリー統計
    logger.info("\n📊 統計サマリー:")
    logger.info(f"  総エピソード数: {len(df_master)}")
    logger.info(f"  カテゴリ分布:")
    for category, count in df_master['category'].value_counts().items():
        logger.info(f"    - {category}: {count}件")

    logger.info(f"  平均スコア: {df_master['weighted_score'].mean():.2f}")
    logger.info(f"  文字数範囲: {df_master['character_count'].min()}〜{df_master['character_count'].max()}")

    # 6. 品質チェック
    logger.info("\n✅ 品質確認:")
    all_verified = df_master['fact_check_status'].str.contains('verified').all()
    logger.info(f"  全エピソード検証済み: {all_verified}")

    all_valid = df_master['is_valid'].all()
    logger.info(f"  全エピソード有効: {all_valid}")

    # 7. シンボリックリンク作成（最新版への参照）
    latest_link = 'trusted_episodes_latest.csv'
    if os.path.exists(latest_link):
        os.remove(latest_link)
    os.symlink(master_file, latest_link)
    logger.info(f"\n🔗 最新版へのリンク作成: {latest_link} → {master_file}")

    return master_file, len(df_master)

def main():
    logger.info("🚀 信頼できるエピソードのみを使用したマスターファイル作成を開始")

    master_file, episode_count = create_trusted_master()

    logger.info("\n" + "=" * 60)
    logger.info("✨ 完了！")
    logger.info("=" * 60)
    logger.info(f"📌 重要な変更:")
    logger.info(f"  - {episode_count}件の検証済みエピソードのみを保持")
    logger.info(f"  - その他のエピソードは全て破棄（アーカイブ）")
    logger.info(f"  - 新マスターファイル: {master_file}")
    logger.info(f"  - 最新版リンク: trusted_episodes_latest.csv")
    logger.info("\n⚠️ 今後はこのファイルのみを使用してください")

if __name__ == "__main__":
    main()
