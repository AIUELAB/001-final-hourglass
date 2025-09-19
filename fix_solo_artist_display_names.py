#!/usr/bin/env python3
"""
ソロアーティスト表示名修正スクリプト
「名前（同じ名前）」という冗長な括弧表記を修正
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import shutil
import re

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SoloArtistDisplayFixer:
    """ソロアーティスト表示名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fixed_records = []
        self.backup_created = []
        
    def detect_redundant_brackets(self, df: pd.DataFrame) -> List[Dict]:
        """
        冗長な括弧表記を検出
        「名前（同じ名前）」パターンを探す
        """
        violations = []
        
        for idx, row in df.iterrows():
            person_id = row.get('person_id', '')
            person_name = row.get('person_name', '')
            display_name = row.get('person_name_display', '')
            
            # 「名前（同じ名前）」パターンの検出
            redundant_pattern = f"{person_name}（{person_name}）"
            
            if display_name == redundant_pattern:
                violations.append({
                    'index': idx,
                    'person_id': person_id,
                    'person_name': person_name,
                    'current_display': display_name,
                    'correct_display': person_name  # 括弧を除去
                })
                logger.info(f"  🔍 冗長括弧検出: {person_id} - {display_name}")
        
        return violations
    
    def fix_display_names(self, df: pd.DataFrame, violations: List[Dict]) -> pd.DataFrame:
        """
        表示名を修正
        """
        df_fixed = df.copy()
        
        for violation in violations:
            idx = violation['index']
            correct_display = violation['correct_display']
            
            # 表示名を修正
            df_fixed.at[idx, 'person_name_display'] = correct_display
            
            self.fixed_records.append({
                'person_id': violation['person_id'],
                'before': violation['current_display'],
                'after': correct_display,
                'timestamp': datetime.now().isoformat()
            })
            
        return df_fixed
    
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
            
            # 冗長括弧検出
            violations = self.detect_redundant_brackets(df)
            
            if not violations:
                logger.info(f"  ✅ 冗長括弧なし")
                return True
            
            logger.info(f"  ⚠️ 冗長括弧検出: {len(violations)}件")
            
            # 修正適用
            df_fixed = self.fix_display_names(df, violations)
            
            # ファイル保存（UTF-8 BOM付き）
            df_fixed.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 修正済みファイル保存完了")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ エラー発生: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """
        修正レポートを生成
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_fixed': len(self.fixed_records),
            'fixed_records': self.fixed_records,
            'backups_created': self.backup_created,
            'summary': {
                'Ado': 0,
                '優里': 0,
                'others': 0
            }
        }
        
        # 修正内容を集計
        for record in self.fixed_records:
            if 'Ado' in record['before']:
                report['summary']['Ado'] += 1
            elif '優里' in record['before']:
                report['summary']['優里'] += 1
            else:
                report['summary']['others'] += 1
        
        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🎯 ソロアーティスト表示名修正システム起動")
    logger.info("=" * 60)
    
    fixer = SoloArtistDisplayFixer()
    
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
    
    # 各ファイルを処理
    success_count = 0
    for file_path in existing_files:
        if fixer.process_csv_file(file_path):
            success_count += 1
    
    # レポート生成
    report = fixer.generate_report()
    
    # レポート保存
    report_path = f"solo_artist_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🔧 修正件数: {report['total_fixed']}件")
    logger.info(f"  - Ado: {report['summary']['Ado']}件")
    logger.info(f"  - 優里: {report['summary']['優里']}件")
    logger.info(f"  - その他: {report['summary']['others']}件")
    logger.info(f"📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()