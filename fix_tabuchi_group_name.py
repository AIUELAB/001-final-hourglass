#!/usr/bin/env python3
"""
田渕章裕のグループ名修正スクリプト
誤った「ALL OUT」から正しい「ちょんまげラーメン」へ修正
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TabuchiGroupNameFixer:
    """田渕章裕のグループ名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fixed_records = []
        self.backup_created = []
        
        # 修正対象
        self.correction = {
            'person_id': 'P004450',
            'name': '田渕章裕',
            'wrong_group': 'ALL OUT',
            'correct_group': 'ちょんまげラーメン',
            'wrong_display': '田渕章裕（ALL OUT）',
            'correct_display': '田渕章裕（ちょんまげラーメン）',
            'note': '旧名：インディアンス（2025年6月改名）'
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
    
    def fix_group_name(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        グループ名を修正
        """
        df_fixed = df.copy()
        fixed_count = 0
        
        # 該当するレコードを検索
        mask = df_fixed['person_id'] == self.correction['person_id']
        
        if mask.any():
            # 現在の表示名を確認
            current_display = df_fixed.loc[mask, 'person_name_display'].iloc[0]
            
            # 修正が必要かチェック（ALL OUTが含まれている場合）
            if 'ALL OUT' in str(current_display):
                # 表示名を修正
                df_fixed.loc[mask, 'person_name_display'] = self.correction['correct_display']
                
                self.fixed_records.append({
                    'person_id': self.correction['person_id'],
                    'person_name': self.correction['name'],
                    'before': current_display,
                    'after': self.correction['correct_display'],
                    'wrong_group': self.correction['wrong_group'],
                    'correct_group': self.correction['correct_group'],
                    'note': self.correction['note'],
                    'timestamp': datetime.now().isoformat()
                })
                
                fixed_count += 1
                logger.info(f"  🔧 修正: {self.correction['person_id']} {self.correction['name']}")
                logger.info(f"     前: {current_display}")
                logger.info(f"     後: {self.correction['correct_display']}")
                logger.info(f"     注: {self.correction['note']}")
            else:
                logger.info(f"  ✓ {self.correction['person_id']} {self.correction['name']} は既に正しいか、異なる表示: {current_display}")
        else:
            logger.info(f"  ⚠️ {self.correction['person_id']} が見つかりません")
        
        if fixed_count > 0:
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
            df_fixed = self.fix_group_name(df)
            
            # ファイル保存（UTF-8 BOM付き）
            df_fixed.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 修正済みファイル保存完了")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ エラー発生: {e}")
            return False
    
    def generate_report(self) -> dict:
        """
        修正レポートを生成
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'correction_target': self.correction,
            'total_fixed': len(self.fixed_records),
            'fixed_records': self.fixed_records,
            'backups_created': self.backup_created,
            'summary': {
                'wrong_info': f"{self.correction['name']}（{self.correction['wrong_group']}）",
                'correct_info': f"{self.correction['name']}（{self.correction['correct_group']}）",
                'additional_info': self.correction['note']
            }
        }
        
        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🎯 田渕章裕グループ名修正システム起動")
    logger.info("=" * 60)
    
    fixer = TabuchiGroupNameFixer()
    
    # 修正内容の詳細表示
    logger.info("📋 修正対象:")
    logger.info(f"  人物ID: {fixer.correction['person_id']}")
    logger.info(f"  名前: {fixer.correction['name']}")
    logger.info(f"  誤ったグループ名: {fixer.correction['wrong_group']}")
    logger.info(f"  正しいグループ名: {fixer.correction['correct_group']}")
    logger.info(f"  備考: {fixer.correction['note']}")
    
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
    report_path = f"tabuchi_group_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🔧 修正件数: {report['total_fixed']}件")
    
    if report['total_fixed'] > 0:
        logger.info(f"\n修正内容:")
        logger.info(f"  誤: {report['summary']['wrong_info']}")
        logger.info(f"  正: {report['summary']['correct_info']}")
        logger.info(f"  備考: {report['summary']['additional_info']}")
    
    logger.info(f"\n📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()