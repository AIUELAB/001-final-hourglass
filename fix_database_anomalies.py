#!/usr/bin/env python3
"""
データベース異常値修正スクリプト
- Wikipedia有りで低スコアの人物を修正
- スコア3.0の不明人物を処理
- PDCAガーディアンルールに基づく自動修正
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import sys
import time

# システムパスに追加
sys.path.append(str(Path(__file__).parent))
from multi_api_recognition_system import MultiAPIRecognitionSystem
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseAnomalyFixer:
    """データベース異常値修正クラス"""
    
    def __init__(self, database_file: str):
        """初期化"""
        self.database_file = database_file
        self.df = pd.read_csv(database_file, encoding='utf-8-sig')
        self.multi_api = MultiAPIRecognitionSystem()
        self.wiki_system = WikipediaRecognitionSystemV2()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.fixes_made = []
        self.deletions = []
        
        logger.info("="*60)
        logger.info("🔧 データベース異常値修正処理開始")
        logger.info("="*60)
        logger.info(f"データベース: {database_file}")
        logger.info(f"総レコード数: {len(self.df)}")
    
    def fix_wikipedia_low_scores(self):
        """Wikipedia有りで低スコアの人物を修正"""
        logger.info("\n📚 Wikipedia有りで低スコアの人物を修正")
        
        if 'wikipedia_found' not in self.df.columns:
            logger.warning("wikipedia_foundカラムが存在しません")
            return
        
        # Wikipedia有りで5.0未満の人物を抽出
        wiki_low = self.df[(self.df['wikipedia_found'] == True) & 
                           (self.df['recognition_score'] < 5.0)]
        
        if wiki_low.empty:
            logger.info("  修正対象なし")
            return
        
        logger.info(f"  修正対象: {len(wiki_low)}名")
        
        for idx, row in wiki_low.iterrows():
            person_id = row['person_id']
            name = row['name']
            old_score = row['recognition_score']
            
            logger.info(f"\n  処理中: {person_id} - {name} (現スコア: {old_score})")
            
            try:
                # WikipediaAPIで再検証
                wiki_score, wiki_details = self.wiki_system.calculate_wikipedia_score(name)
                
                if wiki_score and wiki_score > old_score:
                    # PDCAルール: Wikipedia有り最低5.0保証
                    new_score = max(5.0, wiki_score)
                    
                    # データフレーム更新
                    self.df.at[idx, 'recognition_score'] = new_score
                    
                    # 評価理由更新
                    if 'evaluation_reason' in self.df.columns:
                        self.df.at[idx, 'evaluation_reason'] = f"Wikipedia再検証でスコア修正: {old_score} → {new_score}"
                    
                    self.fixes_made.append({
                        'person_id': person_id,
                        'name': name,
                        'old_score': old_score,
                        'new_score': new_score,
                        'reason': 'Wikipedia有りで低スコア'
                    })
                    
                    logger.info(f"    ✅ 修正: {old_score} → {new_score}")
                else:
                    logger.info(f"    ⏩ スキップ: Wikipedia検証失敗")
                    
            except Exception as e:
                logger.error(f"    ❌ エラー: {e}")
            
            # レート制限対策
            time.sleep(0.5)
    
    def process_score_3_persons(self):
        """スコア3.0の人物を処理"""
        logger.info("\n🔍 スコア3.0の人物を処理")
        
        score_3 = self.df[self.df['recognition_score'] == 3.0]
        
        if score_3.empty:
            logger.info("  対象なし")
            return
        
        logger.info(f"  対象: {len(score_3)}名")
        
        # occupation が空の人物を抽出
        no_occupation = score_3[score_3['occupation'].isna() | (score_3['occupation'] == '')]
        
        if not no_occupation.empty:
            logger.info(f"  職業情報なし: {len(no_occupation)}名")
            
            # 一般的な名前パターン
            common_names = ['田中', '山田', '佐藤', '山口', '山本', '伊藤', '加藤', '高橋', '鈴木', '渡辺']
            
            for idx, row in no_occupation.iterrows():
                person_id = row['person_id']
                name = row['name']
                
                # 一般的な名前かチェック
                is_common = any(cn in name for cn in common_names)
                
                if is_common and len(name) <= 5:  # 短い一般的な名前
                    logger.info(f"  🗑️ 削除候補: {person_id} - {name} (一般的な名前、情報不足)")
                    
                    self.deletions.append({
                        'person_id': person_id,
                        'name': name,
                        'reason': '一般的な名前で情報不足'
                    })
                    
                    # データフレームから削除マーク
                    self.df.at[idx, 'to_delete'] = True
                else:
                    # マルチAPIで再評価
                    try:
                        score, details = self.multi_api.calculate_comprehensive_score(
                            name=name,
                            occupation='',
                            description='',
                            min_score=3.0
                        )
                        
                        if score > 3.0:
                            self.df.at[idx, 'recognition_score'] = score
                            
                            self.fixes_made.append({
                                'person_id': person_id,
                                'name': name,
                                'old_score': 3.0,
                                'new_score': score,
                                'reason': 'マルチAPI再評価'
                            })
                            
                            logger.info(f"    ✅ 修正: 3.0 → {score:.1f}")
                        else:
                            logger.info(f"    ⚠️ 低スコア維持: {name}")
                            
                    except Exception as e:
                        logger.error(f"    ❌ エラー: {e}")
                    
                    time.sleep(0.5)
    
    def apply_pdca_rules(self):
        """PDCAガーディアンルールを適用"""
        logger.info("\n🛡️ PDCAガーディアンルール適用")
        
        rules_applied = 0
        
        # ルール1: Wikipedia有り最低5.0
        wiki_found = self.df[(self.df.get('wikipedia_found', False) == True) & 
                             (self.df['recognition_score'] < 5.0)]
        
        for idx in wiki_found.index:
            old_score = self.df.at[idx, 'recognition_score']
            self.df.at[idx, 'recognition_score'] = 5.0
            rules_applied += 1
            
            logger.info(f"  ルール適用: Wikipedia有り最低5.0 → {self.df.at[idx, 'name']}")
        
        # ルール2: アスリート最低スコア
        if 'occupation' in self.df.columns:
            athletes = self.df[self.df['occupation'].str.contains('選手|チャンピオン|メダリスト', na=False)]
            low_athletes = athletes[athletes['recognition_score'] < 6.0]
            
            for idx in low_athletes.index:
                self.df.at[idx, 'recognition_score'] = 6.0
                rules_applied += 1
                
                logger.info(f"  ルール適用: アスリート最低6.0 → {self.df.at[idx, 'name']}")
        
        logger.info(f"  合計 {rules_applied} 件のルールを適用")
    
    def save_results(self):
        """修正結果を保存"""
        
        # 削除対象を除外
        if 'to_delete' in self.df.columns:
            df_clean = self.df[self.df.get('to_delete', False) != True]
            deleted_count = len(self.df) - len(df_clean)
        else:
            df_clean = self.df
            deleted_count = 0
        
        # to_deleteカラムを削除
        if 'to_delete' in df_clean.columns:
            df_clean = df_clean.drop('to_delete', axis=1)
        
        # バックアップ作成
        backup_file = f"backup_{Path(self.database_file).name}_{self.timestamp}"
        self.df.to_csv(backup_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n💾 バックアップ: {backup_file}")
        
        # 修正済みファイル保存
        fixed_file = f"database_fixed_{self.timestamp}.csv"
        df_clean.to_csv(fixed_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 修正済みデータベース: {fixed_file}")
        
        # 元のファイルも更新
        df_clean.to_csv(self.database_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 元のファイル更新: {self.database_file}")
        
        # レポート出力
        report_file = f"anomaly_fix_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# データベース異常値修正レポート\n\n")
            f.write(f"実行日時: {datetime.now()}\n\n")
            
            f.write("## 📊 統計\n\n")
            f.write(f"- 修正件数: {len(self.fixes_made)}件\n")
            f.write(f"- 削除件数: {deleted_count}件\n")
            f.write(f"- 最終レコード数: {len(df_clean)}件\n\n")
            
            if self.fixes_made:
                f.write("## ✅ 修正内容\n\n")
                f.write("| Person ID | 名前 | 変更前 | 変更後 | 理由 |\n")
                f.write("|-----------|------|--------|--------|------|\n")
                
                for fix in self.fixes_made[:20]:  # 最初の20件
                    f.write(f"| {fix['person_id']} | {fix['name']} | "
                           f"{fix['old_score']:.1f} | {fix['new_score']:.1f} | "
                           f"{fix['reason']} |\n")
                
                if len(self.fixes_made) > 20:
                    f.write(f"\n... 他 {len(self.fixes_made) - 20}件\n")
            
            if self.deletions:
                f.write("\n## 🗑️ 削除内容\n\n")
                f.write("| Person ID | 名前 | 理由 |\n")
                f.write("|-----------|------|------|\n")
                
                for deletion in self.deletions[:20]:
                    f.write(f"| {deletion['person_id']} | {deletion['name']} | "
                           f"{deletion['reason']} |\n")
                
                if len(self.deletions) > 20:
                    f.write(f"\n... 他 {len(self.deletions) - 20}件\n")
            
            f.write("\n## 🛡️ 適用したPDCAルール\n\n")
            f.write("1. Wikipedia有り → 最低スコア5.0\n")
            f.write("2. アスリート → 最低スコア6.0\n")
            f.write("3. 一般的な名前で情報不足 → 削除\n")
        
        logger.info(f"📄 レポート: {report_file}")
        
        return fixed_file

def main():
    """メイン処理"""
    import glob
    
    # 最新のデータベースファイルを取得
    db_files = glob.glob("database_extended_wave3_*.csv")
    if not db_files:
        db_files = glob.glob("database_*.csv")
    
    if not db_files:
        logger.error("データベースファイルが見つかりません")
        return
    
    latest_db = sorted(db_files)[-1]
    logger.info(f"対象ファイル: {latest_db}")
    
    # 修正処理実行
    fixer = DatabaseAnomalyFixer(latest_db)
    
    # 各修正処理を実行
    fixer.fix_wikipedia_low_scores()
    fixer.process_score_3_persons()
    fixer.apply_pdca_rules()
    
    # 結果保存
    fixed_file = fixer.save_results()
    
    logger.info("\n" + "="*60)
    logger.info("✅ 修正処理完了")
    logger.info("="*60)
    logger.info(f"修正件数: {len(fixer.fixes_made)}")
    logger.info(f"削除件数: {len(fixer.deletions)}")
    logger.info(f"出力ファイル: {fixed_file}")

if __name__ == "__main__":
    main()