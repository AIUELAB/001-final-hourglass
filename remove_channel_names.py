#!/usr/bin/env python3
"""
チャンネル名誤登録削除スクリプト
YouTubeチャンネル名など、人物でないエンティティを削除
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChannelNameRemover:
    """チャンネル名削除クラス"""

    def __init__(self):
        """初期化"""
        self.removed_records = []
        self.backup_created = []

        # 削除対象のperson_id
        self.target_ids = {'P001061'}  # ヒカキンゲームズ

        # チャンネル名パターン（将来の検出用）
        self.channel_patterns = [
            'ゲームズ$',
            'Games$',
            'TV$',
            'チャンネル$',
            'Channel$',
            'Gaming$',
            'ゲーム実況$'
        ]

    def create_backup(self, file_path: str) -> str:
        """
        バックアップファイルを作成
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup_{timestamp}"

        shutil.copy2(file_path, backup_path)
        self.backup_created.append(backup_path)
        logger.info(f"  📦 バックアップ作成: {backup_path}")

        return backup_path

    def remove_channel_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        チャンネル名レコードを削除
        """
        initial_count = len(df)

        # 削除対象のレコードを記録
        for person_id in self.target_ids:
            if person_id in df['person_id'].values:
                record = df[df['person_id'] == person_id].iloc[0]
                self.removed_records.append({
                    'person_id': person_id,
                    'person_name': record.get('person_name', ''),
                    'person_name_display': record.get('person_name_display', ''),
                    'entity_type': record.get('entity_type', ''),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"  🗑️ 削除: {person_id} - {record.get('person_name_display', '')}")

        # 削除実行
        df_cleaned = df[~df['person_id'].isin(self.target_ids)]

        removed_count = initial_count - len(df_cleaned)
        if removed_count > 0:
            logger.info(f"  ✅ {removed_count}件のレコードを削除")

        return df_cleaned

    def process_csv_file(self, file_path: str) -> bool:
        """
        CSVファイルを処理
        """
        logger.info(f"\n🔧 処理開始: {file_path}")

        # ファイル存在確認
        if not Path(file_path).exists():
            logger.warning(f"  ⚠️ ファイルが存在しません: {file_path}")
            return False

        try:
            # バックアップ作成
            self.create_backup(file_path)

            # データ読み込み
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            logger.info(f"  📊 データ読み込み完了: {len(df)}行")

            # チャンネル名レコード削除
            df_cleaned = self.remove_channel_records(df)

            if len(df) == len(df_cleaned):
                logger.info(f"  ℹ️ 削除対象なし")
                return True

            # ファイル保存（UTF-8 BOM付き）
            df_cleaned.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 クリーンアップ済みファイル保存完了")

            return True

        except Exception as e:
            logger.error(f"  ❌ エラー発生: {e}")
            return False

    def generate_report(self) -> Dict:
        """
        削除レポートを生成
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_removed': len(self.removed_records),
            'removed_records': self.removed_records,
            'backups_created': self.backup_created,
            'target_ids': list(self.target_ids)
        }

        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🗑️ チャンネル名誤登録削除システム起動")
    logger.info("=" * 60)

    remover = ChannelNameRemover()

    # 処理対象ファイルリスト
    target_files = [
        'ultra_think_GROUP_FIXED_20250912_044856.csv',
        'ultra_think_COMPLETE_20250912_042500.csv',
        'ultra_think_FINAL_CLEAN_20250912_042742_FICTIONAL_FIXED_FICTIONAL_COMPLETE.csv',
        'ultra_think_FINAL_CLEAN_20250912_042742.csv',
        'ultra_think_COMPREHENSIVE_FIX_20250912_071739.csv'
    ]

    # 存在するファイルのみ処理
    existing_files = []
    for file_path in target_files:
        if Path(file_path).exists():
            existing_files.append(file_path)

    if not existing_files:
        logger.warning("処理対象ファイルが見つかりません")
        return

    logger.info(f"処理対象: {len(existing_files)}ファイル")
    logger.info(f"削除対象ID: P001061 (ヒカキンゲームズ)")

    # 各ファイルを処理
    success_count = 0
    for file_path in existing_files:
        if remover.process_csv_file(file_path):
            success_count += 1

    # レポート生成
    report = remover.generate_report()

    # レポート保存
    report_path = f"channel_removal_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 削除結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🗑️ 削除件数: {report['total_removed']}件")
    if report['removed_records']:
        for record in report['removed_records']:
            logger.info(f"  - {record['person_id']}: {record['person_name_display']}")
    logger.info(f"📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
