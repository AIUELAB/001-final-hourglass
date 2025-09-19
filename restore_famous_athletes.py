#!/usr/bin/env python3
"""
有名アスリート復元スクリプト
Wikipediaに掲載されている実在の有名人を復元
"""

import pandas as pd
import json
from datetime import datetime
import logging
from pathlib import Path
from famous_person_protection_list import FamousPersonProtectionList
from wikipedia_api_implementation import WikipediaValidator

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FamousAthleteRestorer:
    """有名アスリート復元クラス"""
    
    def __init__(self):
        """初期化"""
        self.protector = FamousPersonProtectionList()
        self.validator = WikipediaValidator()
        self.restoration_log = []
        
        # 削除されたことが確認された有名人リスト
        self.deleted_famous_people = [
            {'person_id': 'P003301', 'name': '張本勲', 'occupation': '野球選手'},
            {'person_id': 'P003306', 'name': 'Tomokazu Harimoto', 'display': '張本智和', 'occupation': '卓球選手'},
            {'person_id': 'P004337', 'name': '為末大', 'occupation': '陸上選手'},
            {'person_id': 'P004344', 'name': 'Terunofuji Haruo', 'display': '照ノ富士', 'occupation': '大相撲力士'},
            {'person_id': 'P005242', 'name': 'Nishikori Kei', 'display': '錦織圭', 'occupation': 'テニス選手'},
            {'person_id': 'P005253', 'name': 'Kamada Daichi', 'display': '鎌田大地', 'occupation': 'サッカー選手'},
            {'person_id': 'P002312', 'name': '古賀淳也', 'occupation': '水泳選手'},
            {'person_id': 'P002313', 'name': '古賀紗理那', 'occupation': 'バレーボール選手'},
        ]
    
    def verify_wikipedia_existence(self, person: dict) -> bool:
        """Wikipedia存在確認"""
        name = person.get('display', person['name'])
        occupation = person['occupation']
        
        exists, method = self.validator.check_existence(name, occupation)
        
        if exists:
            logger.info(f"✅ Wikipedia確認: {name} ({occupation}) - {method}")
        else:
            logger.warning(f"⚠️ Wikipedia未確認: {name} ({occupation})")
        
        return exists
    
    def restore_famous_people(self, csv_file: str) -> pd.DataFrame:
        """有名人データ復元"""
        logger.info("=" * 60)
        logger.info("🔄 有名アスリート復元開始")
        logger.info("=" * 60)
        
        # データ読み込み
        df = pd.read_csv(csv_file)
        initial_count = len(df)
        
        restored_count = 0
        
        for person in self.deleted_famous_people:
            person_id = person['person_id']
            display_name = person.get('display', person['name'])
            
            # Wikipedia確認
            wiki_exists = self.verify_wikipedia_existence(person)
            
            # 保護リスト確認
            is_protected, reason = self.protector.is_protected(
                display_name, person['occupation']
            )
            
            # データ内で該当レコードを探す
            mask = df['person_id'] == person_id
            
            if mask.any():
                current_score = df.loc[mask, 'name_recognition'].iloc[0]
                
                if current_score == 0 or pd.isna(current_score):
                    # スコアを復元（Wikipedia確認済みは80、保護リストは70、その他は60）
                    if wiki_exists:
                        new_score = 80
                        restoration_reason = "Wikipedia掲載確認済み"
                    elif is_protected:
                        new_score = 70
                        restoration_reason = f"保護リスト: {reason}"
                    else:
                        new_score = 60
                        restoration_reason = "有名アスリート（手動確認）"
                    
                    df.loc[mask, 'name_recognition'] = new_score
                    restored_count += 1
                    
                    self.restoration_log.append({
                        'person_id': person_id,
                        'person_name': person['name'],
                        'display_name': display_name,
                        'occupation': person['occupation'],
                        'old_score': current_score,
                        'new_score': new_score,
                        'reason': restoration_reason,
                        'wikipedia_verified': wiki_exists,
                        'protected': is_protected
                    })
                    
                    logger.info(f"✅ 復元: {display_name} ({person_id}) - スコア: {current_score} → {new_score} ({restoration_reason})")
                else:
                    logger.info(f"ℹ️ スキップ: {display_name} - 既にスコアあり ({current_score})")
            else:
                # レコードが見つからない場合は新規追加
                new_record = {
                    'person_id': person_id,
                    'person_name': person['name'],
                    'person_name_display': display_name,
                    'occupation': person['occupation'],
                    'name_recognition': 80 if wiki_exists else 70,
                    'extra': json.dumps({
                        'restored': True,
                        'restoration_date': datetime.now().isoformat(),
                        'wikipedia_verified': wiki_exists,
                        'protected': is_protected
                    })
                }
                
                df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
                restored_count += 1
                
                logger.info(f"➕ 新規追加: {display_name} ({person_id})")
                
                self.restoration_log.append({
                    'person_id': person_id,
                    'person_name': person['name'],
                    'display_name': display_name,
                    'occupation': person['occupation'],
                    'action': 'ADDED',
                    'new_score': new_record['name_recognition'],
                    'wikipedia_verified': wiki_exists,
                    'protected': is_protected
                })
        
        # 追加の有名人チェック（保護リストから）
        logger.info("\n📋 保護リスト内の人物を確認中...")
        
        for name, info in self.protector.absolute_protection.items():
            # データ内を検索（表示名または本名で）
            mask = (df['person_name_display'] == name) | (df['person_name'] == name)
            
            if mask.any():
                current_scores = df.loc[mask, 'name_recognition']
                low_score_mask = mask & ((df['name_recognition'] == 0) | pd.isna(df['name_recognition']))
                
                if low_score_mask.any():
                    df.loc[low_score_mask, 'name_recognition'] = 85
                    restored_count += len(df[low_score_mask])
                    logger.info(f"✅ 保護リストから復元: {name} - {len(df[low_score_mask])}件")
        
        # レポート生成
        self.generate_report(initial_count, restored_count)
        
        logger.info(f"\n📊 復元結果:")
        logger.info(f"  初期レコード数: {initial_count}")
        logger.info(f"  復元件数: {restored_count}")
        logger.info(f"  最終レコード数: {len(df)}")
        
        return df
    
    def generate_report(self, initial_count: int, restored_count: int):
        """復元レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'initial_records': initial_count,
                'restored_count': restored_count,
                'restoration_log': self.restoration_log
            },
            'wikipedia_stats': self.validator.get_stats(),
            'protection_list_size': len(self.protector.absolute_protection)
        }
        
        report_file = f"famous_athlete_restoration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 レポート保存: {report_file}")


def main():
    """メイン処理"""
    logger.info("🚀 有名アスリート復元システム起動")
    
    # 復元対象ファイル
    csv_file = "ultra_think_COMPREHENSIVE_RESTORED_20250911_200550.csv"
    
    if not Path(csv_file).exists():
        # 代替ファイルを探す
        logger.warning(f"⚠️ {csv_file} が見つかりません")
        # 最新のultra_thinkファイルを探す
        ultra_think_files = list(Path('.').glob('ultra_think_*.csv'))
        if ultra_think_files:
            csv_file = str(max(ultra_think_files, key=lambda x: x.stat().st_mtime))
            logger.info(f"📂 代替ファイル使用: {csv_file}")
        else:
            logger.error("❌ 処理可能なCSVファイルが見つかりません")
            return
    
    # 復元実行
    restorer = FamousAthleteRestorer()
    df_restored = restorer.restore_famous_people(csv_file)
    
    # 結果保存
    output_file = f"ultra_think_ATHLETES_RESTORED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_restored.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 復元データ保存: {output_file}")
    
    logger.info("\n✅ 有名アスリート復元完了")
    logger.info("📋 Wikipediaに掲載されている実在の人物を適切に復元しました")


if __name__ == "__main__":
    main()