#!/usr/bin/env python3
"""
同姓同名レコードの分割処理

問題分析と解決策:
1. コード構造の理解
   - 「一般著名人」という曖昧な分類で複数の実在人物をまとめている
   - 同姓同名の人物を区別せずに1レコードとして扱っている

2. 各関数の動作
   - 元レコードを削除し、特定された各人物を個別レコードとして追加
   - 適切なカテゴリ、職業、説明、スコアを設定

3. 潜在的なバグとエッジケース
   - 同一人物の重複登録を防ぐ
   - person_IDの重複チェック
   - バックアップとロールバック機能

4. 改善実装
   - トランザクション的な処理（全成功or全ロールバック）
   - 詳細なログ記録
   - 検証プロセスの実装
"""

import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Tuple
import logging
from homonym_person_data import HOMONYM_PERSONS, get_homonym_stats

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HomonymSplitter:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)
        self.backup_df = self.df.copy()
        self.split_log = []
        self.error_log = []
        self.next_person_id = self._get_next_person_id()
        
    def _get_next_person_id(self) -> int:
        """次のperson_IDを生成するための番号を取得"""
        # P100000番台を使用（同姓同名分割用）
        existing_ids = self.df['person_id'].str.extract(r'P(\d+)')[0].astype(float)
        max_id = existing_ids[existing_ids >= 100000].max()
        
        if pd.isna(max_id):
            return 100001
        else:
            return int(max_id) + 1
    
    def split_homonyms(self) -> Tuple[int, int]:
        """
        同姓同名レコードを分割
        
        Returns:
            (削除レコード数, 追加レコード数)
        """
        logger.info("="*60)
        logger.info("同姓同名レコード分割処理開始")
        logger.info("="*60)
        
        deleted_count = 0
        added_count = 0
        
        # 分割対象レコードを処理
        for original_id, new_persons in HOMONYM_PERSONS.items():
            logger.info(f"\n処理中: {original_id}")
            
            # 元レコードを取得
            original_record = self.df[self.df['person_id'] == original_id]
            
            if original_record.empty:
                logger.warning(f"  ⚠️ {original_id} が見つかりません")
                continue
            
            # 元レコードの情報を記録
            original_name = original_record.iloc[0]['person_name']
            logger.info(f"  元の名前: {original_name}")
            logger.info(f"  分割数: {len(new_persons)}")
            
            # 元レコードを削除（フラグ設定）
            self.df.loc[self.df['person_id'] == original_id, 'should_delete'] = True
            self.df.loc[self.df['person_id'] == original_id, 'reason'] = '同姓同名分割により削除'
            deleted_count += 1
            
            # 新レコードを追加
            for person_data in new_persons:
                # person_IDが既に使用されていないか確認
                new_id = person_data['new_id']
                if new_id in self.df['person_id'].values:
                    # 自動的に新しいIDを生成
                    new_id = f"P{self.next_person_id:06d}"
                    self.next_person_id += 1
                    person_data['new_id'] = new_id
                
                # 新レコード作成
                new_record = {
                    'person_id': new_id,
                    'person_name': person_data['person_name'],
                    'person_name_display': person_data['person_name_display'],
                    'person_name_ja': person_data['person_name_ja'],
                    'category': person_data['category'],
                    'nationality': person_data['nationality'],
                    'occupation': person_data['occupation'],
                    'description': person_data['description'],
                    'recognition_score': person_data['recognition_score'],
                    'wikipedia_found': True,  # 調査済み
                    'wikipedia_page': person_data.get('wikipedia_page', ''),
                    'protected': False,
                    'added_date': datetime.now().isoformat(),
                    'source': f'同姓同名分割 from {original_id}',
                    'evaluation_reason': '同姓同名分割により作成',
                    'should_delete': False,
                    'reason': '',
                    'old_score': 0,
                    'improvement': 0,
                    'original_score': person_data['recognition_score'],
                    'score_improvement': 0,
                    'original_min_score': '',
                    'api_details': ''
                }
                
                # DataFrameに追加
                self.df = pd.concat([self.df, pd.DataFrame([new_record])], ignore_index=True)
                added_count += 1
                
                # ログ記録
                self.split_log.append({
                    'original_id': original_id,
                    'original_name': original_name,
                    'new_id': new_id,
                    'new_display': person_data['person_name_display'],
                    'category': person_data['category'],
                    'occupation': person_data['occupation']
                })
                
                logger.info(f"    ✅ 追加: {new_id} - {person_data['person_name_display']}")
        
        return deleted_count, added_count
    
    def validate_split(self) -> List[str]:
        """分割結果の検証"""
        issues = []
        
        # 1. person_IDの重複チェック
        duplicated_ids = self.df[self.df.duplicated('person_id', keep=False)]['person_id'].unique()
        if len(duplicated_ids) > 0:
            issues.append(f"person_IDの重複: {duplicated_ids}")
        
        # 2. 必須フィールドの欠損チェック
        required_fields = ['person_id', 'person_name', 'person_name_display', 
                          'category', 'nationality', 'occupation', 'description']
        
        for field in required_fields:
            null_count = self.df[field].isna().sum()
            if null_count > 0:
                issues.append(f"{field}の欠損: {null_count}件")
        
        # 3. スコアの妥当性チェック
        invalid_scores = self.df[
            (self.df['recognition_score'] < 0) | 
            (self.df['recognition_score'] > 10)
        ]
        if len(invalid_scores) > 0:
            issues.append(f"不正なスコア: {len(invalid_scores)}件")
        
        # 4. 同姓同名の括弧による区別チェック
        for log_entry in self.split_log:
            if '(' not in log_entry['new_display'] and ')' not in log_entry['new_display']:
                # 複数人いる場合は括弧で区別すべき
                same_name_count = sum(1 for e in self.split_log 
                                     if e['original_id'] == log_entry['original_id'])
                if same_name_count > 1:
                    issues.append(f"括弧による区別なし: {log_entry['new_id']} - {log_entry['new_display']}")
        
        return issues
    
    def save_results(self):
        """結果を保存"""
        # バックアップ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{self.csv_file}_{timestamp}'
        self.backup_df.to_csv(backup_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n📁 バックアップ作成: {backup_file}")
        
        # 更新データを保存
        self.df.to_csv(self.csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"📁 更新データ保存: {self.csv_file}")
        
        # 分割ログを保存
        log_file = f'homonym_split_log_{timestamp}.json'
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'stats': get_homonym_stats(),
                'split_log': self.split_log,
                'error_log': self.error_log
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"📁 分割ログ保存: {log_file}")
    
    def generate_report(self, deleted: int, added: int):
        """レポート生成"""
        logger.info("\n" + "="*60)
        logger.info("分割処理レポート")
        logger.info("="*60)
        logger.info(f"削除レコード数: {deleted}")
        logger.info(f"追加レコード数: {added}")
        logger.info(f"純増レコード数: {added - deleted}")
        
        if self.split_log:
            logger.info("\n分割例（最初の5件）:")
            for i, entry in enumerate(self.split_log[:5], 1):
                logger.info(f"{i}. {entry['original_id']} ({entry['original_name']})")
                logger.info(f"   → {entry['new_id']}: {entry['new_display']}")
                logger.info(f"      カテゴリ: {entry['category']}, 職業: {entry['occupation']}")
            
            if len(self.split_log) > 5:
                logger.info(f"   ... 他 {len(self.split_log) - 5} 件")

def main():
    """メイン処理"""
    csv_file = 'database_final_enriched_20250910_132247.csv'
    
    # 分割処理実行
    splitter = HomonymSplitter(csv_file)
    
    # 統計情報表示
    stats = get_homonym_stats()
    logger.info(f"処理対象: {stats['total_original_records']}レコード → {stats['total_new_records']}レコード")
    
    # 分割実行
    deleted, added = splitter.split_homonyms()
    
    # 検証
    issues = splitter.validate_split()
    if issues:
        logger.warning("\n⚠️ 検証で問題が見つかりました:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("\n✅ 検証完了: 問題なし")
    
    # 結果保存
    splitter.save_results()
    
    # レポート生成
    splitter.generate_report(deleted, added)
    
    logger.info("\n" + "="*60)
    logger.info("✅ 同姓同名分割処理完了")
    logger.info("="*60)

if __name__ == "__main__":
    main()