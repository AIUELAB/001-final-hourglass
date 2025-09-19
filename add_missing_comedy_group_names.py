#!/usr/bin/env python3
"""
お笑い芸人グループ名補足追加スクリプト
グループ名が欠落している芸人の表示名を修正
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


class MissingGroupNameFixer:
    """グループ名欠落修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fixed_records = []
        self.backup_created = []
        
        # 修正対象の芸人とその所属グループ
        self.missing_group_annotations = {
            'P000608': {
                'name': 'シュウペイ',
                'group': 'ぺこぱ',
                'correct_display': 'シュウペイ（ぺこぱ）'
            },
            'P003297': {
                'name': '庄司智春',
                'group': '品川庄司',
                'correct_display': '庄司智春（品川庄司）'
            },
            'P003323': {
                'name': '徳井義実',
                'group': 'チュートリアル',
                'correct_display': '徳井義実（チュートリアル）'
            },
            # P003625 村上は複数の可能性があるためスキップ
            'P003756': {
                'name': '松陰寺太勇',
                'group': 'ぺこぱ',
                'correct_display': '松陰寺太勇（ぺこぱ）'
            },
            'P003812': {
                'name': '柴田英嗣',
                'group': 'アンタッチャブル',
                'correct_display': '柴田英嗣（アンタッチャブル）'
            },
            'P004123': {
                'name': '津田篤宏',
                'group': 'ダイアン',
                'correct_display': '津田篤宏（ダイアン）'
            },
            'P004295': {
                'name': '渡部建',
                'group': 'アンジャッシュ',
                'correct_display': '渡部建（アンジャッシュ）'
            },
            'P004323': {
                'name': '瀬下豊',
                'group': '天竺鼠',
                'correct_display': '瀬下豊（天竺鼠）'
            },
            'P004450': {
                'name': '田渕章裕',
                'group': 'ALL OUT',  # 調査が必要
                'correct_display': '田渕章裕（ALL OUT）',
                'note': '要確認: ALL OUTまたは他のグループの可能性'
            },
            'P005271': {
                'name': '長谷川雅紀',
                'group': '錦鯉',
                'correct_display': '長谷川雅紀（錦鯉）'
            }
        }
        
        # 正しいコンビ/グループメンバー辞書（参考用）
        self.correct_groups = {
            'ぺこぱ': ['シュウペイ', '松陰寺太勇'],
            '品川庄司': ['品川祐', '庄司智春'],
            'チュートリアル': ['徳井義実', '福田充徳'],
            'アンタッチャブル': ['柴田英嗣', '山崎弘也'],
            'ダイアン': ['津田篤宏', 'ユースケ（西澤裕介）'],
            'アンジャッシュ': ['渡部建', '児嶋一哉'],
            '天竺鼠': ['瀬下豊', '川原克己'],
            '錦鯉': ['長谷川雅紀', '渡辺隆'],
            'ALL OUT': ['田渕章裕', '角田晃弘', 'コウテイ']  # トリオ
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
    
    def add_missing_group_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        グループ名を追加
        """
        df_fixed = df.copy()
        fixed_count = 0
        
        for person_id, annotation in self.missing_group_annotations.items():
            # 該当するレコードを検索
            mask = df_fixed['person_id'] == person_id
            
            if mask.any():
                # 現在の表示名を確認
                current_display = df_fixed.loc[mask, 'person_name_display'].iloc[0]
                
                # グループ名が含まれていない場合のみ修正
                if '（' not in str(current_display) or current_display == annotation['name']:
                    # 表示名を修正
                    df_fixed.loc[mask, 'person_name_display'] = annotation['correct_display']
                    
                    self.fixed_records.append({
                        'person_id': person_id,
                        'person_name': annotation['name'],
                        'before': current_display,
                        'after': annotation['correct_display'],
                        'group': annotation['group'],
                        'timestamp': datetime.now().isoformat(),
                        'note': annotation.get('note', '')
                    })
                    
                    fixed_count += 1
                    logger.info(f"  🔧 修正: {person_id} {annotation['name']}")
                    logger.info(f"     前: {current_display}")
                    logger.info(f"     後: {annotation['correct_display']}")
                    if 'note' in annotation:
                        logger.info(f"     注: {annotation['note']}")
                else:
                    logger.info(f"  ✓ {person_id} {annotation['name']} は既に正しい: {current_display}")
        
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
            
            # グループ名追加
            df_fixed = self.add_missing_group_names(df)
            
            # ファイル保存（UTF-8 BOM付き）
            df_fixed.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 修正済みファイル保存完了")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ エラー発生: {e}")
            return False
    
    def analyze_missing_reasons(self) -> Dict:
        """
        グループ名が欠落していた理由を分析
        """
        analysis = {
            'total_missing': len(self.missing_group_annotations),
            'reasons': {
                'not_in_dictionary': [],
                'solo_misclassified': [],
                'ambiguous_name': [],
                'processing_error': []
            },
            'affected_groups': {}
        }
        
        # グループ別に集計
        for person_id, annotation in self.missing_group_annotations.items():
            group = annotation['group']
            if group not in analysis['affected_groups']:
                analysis['affected_groups'][group] = []
            analysis['affected_groups'][group].append(annotation['name'])
        
        # 理由を推定
        for person_id, annotation in self.missing_group_annotations.items():
            if annotation['name'] == '村上':
                analysis['reasons']['ambiguous_name'].append(annotation['name'])
            elif annotation.get('note'):
                analysis['reasons']['processing_error'].append(annotation['name'])
            else:
                analysis['reasons']['not_in_dictionary'].append(annotation['name'])
        
        return analysis
    
    def generate_report(self) -> Dict:
        """
        修正レポートを生成
        """
        analysis = self.analyze_missing_reasons()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_fixed': len(self.fixed_records),
            'fixed_records': self.fixed_records,
            'backups_created': self.backup_created,
            'analysis': analysis,
            'summary_by_group': {}
        }
        
        # グループ別に修正件数を集計
        for record in self.fixed_records:
            group = record['group']
            if group not in report['summary_by_group']:
                report['summary_by_group'][group] = 0
            report['summary_by_group'][group] += 1
        
        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🎯 お笑い芸人グループ名補足追加システム起動")
    logger.info("=" * 60)
    
    fixer = MissingGroupNameFixer()
    
    # 修正対象の詳細表示
    logger.info("📋 修正対象（グループ名が欠落している芸人）:")
    for person_id, annotation in fixer.missing_group_annotations.items():
        logger.info(f"  {person_id}: {annotation['name']} → {annotation['group']}")
    
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
    report_path = f"missing_group_names_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🔧 修正件数: {report['total_fixed']}件")
    
    logger.info("\n📊 グループ別修正件数:")
    for group, count in report['summary_by_group'].items():
        logger.info(f"  - {group}: {count}件")
    
    # 原因分析表示
    logger.info("\n🔍 欠落原因分析:")
    analysis = report['analysis']
    logger.info(f"  総欠落数: {analysis['total_missing']}件")
    logger.info(f"  辞書未登録: {len(analysis['reasons']['not_in_dictionary'])}件")
    logger.info(f"  曖昧な名前: {len(analysis['reasons']['ambiguous_name'])}件")
    
    logger.info(f"\n📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()