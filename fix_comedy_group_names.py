#!/usr/bin/env python3
"""
お笑い芸人グループ名修正スクリプト
誤ったグループ名を正しいグループ名に修正
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComedyGroupNameFixer:
    """お笑い芸人グループ名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fixed_records = []
        self.backup_created = []
        
        # 修正対象の芸人とその正しいグループ名
        self.corrections = {
            'P000432': {
                'name': 'ガク',
                'wrong_group': 'GAG少年楽団',
                'correct_group': '真空ジェシカ',
                'wrong_display': 'ガク (GAG少年楽団)',
                'correct_display': 'ガク（真空ジェシカ）'
            },
            'P002167': {
                'name': '加納',
                'wrong_group': '４ガロン',
                'correct_group': 'Aマッソ',
                'wrong_display': '加納（４ガロン）',
                'correct_display': '加納（Aマッソ）'
            },
            'P002520': {
                'name': '堂前透',
                'wrong_group': 'ビスケッティ',
                'correct_group': 'ロングコートダディ',
                'wrong_display': '堂前透（ビスケッティ）',
                'correct_display': '堂前透（ロングコートダディ）'
            },
            'P003225': {
                'name': '川北茂澄',
                'wrong_group': 'ビスケッティ',
                'correct_group': '真空ジェシカ',
                'wrong_display': '川北茂澄（ビスケッティ）',
                'correct_display': '川北茂澄（真空ジェシカ）'
            }
            # P004112 河井ゆずる（アインシュタイン）は正しいので修正不要
        }
        
        # 正しいコンビメンバー辞書（参考用）
        self.correct_groups = {
            '真空ジェシカ': ['ガク', '川北茂澄'],
            'Aマッソ': ['加納', '村上'],
            'ロングコートダディ': ['堂前透', '兎'],
            'アインシュタイン': ['河井ゆずる', '稲田直樹'],
            'ぺこぱ': ['松陰寺太勇', 'シュウペイ'],
            'ビスケッティ': ['きん', 'やす'],  # 実際のメンバー
            '４ガロン': ['志田', '下町ミルク']  # 実際のメンバー
        }
    
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
    
    def fix_group_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        グループ名を修正
        """
        df_fixed = df.copy()
        fixed_count = 0
        
        for person_id, correction in self.corrections.items():
            # 該当するレコードを検索
            mask = df_fixed['person_id'] == person_id
            
            if mask.any():
                # 現在の表示名を確認
                current_display = df_fixed.loc[mask, 'person_name_display'].iloc[0]
                
                # 修正が必要かチェック
                if correction['wrong_group'] in current_display or \
                   current_display == correction['wrong_display']:
                    
                    # 表示名を修正
                    df_fixed.loc[mask, 'person_name_display'] = correction['correct_display']
                    
                    self.fixed_records.append({
                        'person_id': person_id,
                        'person_name': correction['name'],
                        'before': current_display,
                        'after': correction['correct_display'],
                        'wrong_group': correction['wrong_group'],
                        'correct_group': correction['correct_group'],
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    fixed_count += 1
                    logger.info(f"  🔧 修正: {person_id} {correction['name']}")
                    logger.info(f"     前: {current_display}")
                    logger.info(f"     後: {correction['correct_display']}")
        
        logger.info(f"  ✅ {fixed_count}件の修正を適用")
        return df_fixed
    
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
            
            # グループ名修正
            df_fixed = self.fix_group_names(df)
            
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
                '真空ジェシカ': 0,
                'Aマッソ': 0,
                'ロングコートダディ': 0,
                'アインシュタイン': 0
            }
        }
        
        # 修正内容を集計
        for record in self.fixed_records:
            correct_group = record['correct_group']
            if correct_group in report['summary']:
                report['summary'][correct_group] += 1
        
        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🎯 お笑い芸人グループ名修正システム起動")
    logger.info("=" * 60)
    
    fixer = ComedyGroupNameFixer()
    
    # 修正対象の詳細表示
    logger.info("📋 修正対象:")
    for person_id, correction in fixer.corrections.items():
        logger.info(f"  {person_id}: {correction['name']}")
        logger.info(f"    誤: {correction['wrong_group']}")
        logger.info(f"    正: {correction['correct_group']}")
    
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
    
    logger.info(f"\n処理対象: {len(existing_files)}ファイル")
    
    # 各ファイルを処理
    success_count = 0
    for file_path in existing_files:
        if fixer.process_csv_file(file_path):
            success_count += 1
    
    # レポート生成
    report = fixer.generate_report()
    
    # レポート保存
    report_path = f"comedy_group_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🔧 修正件数: {report['total_fixed']}件")
    for group, count in report['summary'].items():
        if count > 0:
            logger.info(f"  - {group}: {count}件")
    logger.info(f"📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()