#!/usr/bin/env python3
"""
高速プレースホルダー検出システム
パターン分析によるプレースホルダーデータの検出
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
import re

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FastPlaceholderDetector:
    """高速プレースホルダー検出クラス"""
    
    def __init__(self):
        """初期化"""
        self.suspicious_records = []
        self.deletion_candidates = []
        self.stats = defaultdict(int)
        
    def analyze_structure(self, df: pd.DataFrame) -> Dict:
        """
        1. まずコード全体の構造を理解
        データフレームの構造解析
        """
        logger.info("📊 ステップ1: データ構造分析")
        
        structure = {
            'total_records': len(df),
            'columns': list(df.columns),
            'key_fields': ['person_id', 'person_name', 'person_name_display', 'occupation', 'nationality'],
            'data_quality': {
                'null_person_name': df['person_name'].isnull().sum(),
                'null_display_name': df['person_name_display'].isnull().sum(),
                'null_occupation': df['occupation'].isnull().sum(),
                'null_nationality': df['nationality'].isnull().sum()
            }
        }
        
        # 職業分布
        occupation_counts = df['occupation'].value_counts()
        structure['top_occupations'] = occupation_counts.head(20).to_dict()
        
        # 国籍分布
        nationality_counts = df['nationality'].value_counts()
        structure['nationalities'] = nationality_counts.to_dict()
        
        logger.info(f"  総レコード数: {structure['total_records']}")
        logger.info(f"  職業カテゴリ数: {len(occupation_counts)}")
        logger.info(f"  国籍数: {len(nationality_counts)}")
        
        return structure
    
    def detect_patterns(self, df: pd.DataFrame) -> Dict:
        """
        2. 各関数の動作を検証
        プレースホルダーパターンの検出
        """
        logger.info("🔍 ステップ2: パターン検出")
        
        patterns = {
            'consecutive_ids': [],
            'same_surname_groups': {},
            'generic_names': [],
            'no_data_groups': [],
            'suspicious_combinations': []
        }
        
        # 連続ID検出
        df_sorted = df.sort_values('person_id')
        consecutive_groups = []
        current_group = []
        
        for i in range(len(df_sorted) - 1):
            curr_id = int(df_sorted.iloc[i]['person_id'][1:])
            next_id = int(df_sorted.iloc[i+1]['person_id'][1:])
            
            if next_id == curr_id + 1:
                if not current_group:
                    current_group.append(df_sorted.iloc[i])
                current_group.append(df_sorted.iloc[i+1])
            else:
                if len(current_group) >= 5:  # 5件以上連続
                    # 同じ職業かチェック
                    occupations = [r['occupation'] for r in current_group]
                    if len(set(occupations)) == 1:
                        consecutive_groups.append({
                            'ids': [r['person_id'] for r in current_group],
                            'names': [r['person_name'] for r in current_group],
                            'occupation': occupations[0],
                            'count': len(current_group)
                        })
                current_group = []
        
        patterns['consecutive_ids'] = consecutive_groups
        logger.info(f"  連続IDグループ: {len(consecutive_groups)}件")
        
        # 同姓グループ検出
        df['surname'] = df['person_name'].apply(self._extract_surname)
        surname_groups = df.groupby('surname')
        
        for surname, group in surname_groups:
            if len(group) >= 5:  # 5人以上の同姓
                # 職業の偏りチェック
                occupation_dist = group['occupation'].value_counts()
                if occupation_dist.iloc[0] >= len(group) * 0.7:  # 70%以上が同じ職業
                    patterns['same_surname_groups'][surname] = {
                        'count': len(group),
                        'main_occupation': occupation_dist.index[0],
                        'ids': group['person_id'].tolist(),
                        'names': group['person_name'].tolist()
                    }
        
        logger.info(f"  同姓グループ: {len(patterns['same_surname_groups'])}件")
        
        # 汎用的な名前パターン
        generic_patterns = ['太郎', '次郎', '三郎', '健太', '大輔', '翔太', '拓也', '和也', '優斗', '悠斗']
        for pattern in generic_patterns:
            matching = df[df['person_name'].str.contains(pattern, na=False)]
            if len(matching) >= 3:
                patterns['generic_names'].append({
                    'pattern': pattern,
                    'count': len(matching),
                    'ids': matching['person_id'].tolist()[:10],
                    'examples': matching['person_name'].tolist()[:10]
                })
        
        logger.info(f"  汎用名パターン: {len(patterns['generic_names'])}種")
        
        return patterns
    
    def identify_issues(self, df: pd.DataFrame, patterns: Dict) -> List[Dict]:
        """
        3. 潜在的なバグやエッジケースを特定
        問題のあるデータの特定
        """
        logger.info("⚠️ ステップ3: 問題データ特定")
        
        issues = []
        
        # 連続IDグループの問題
        for group in patterns['consecutive_ids']:
            if group['count'] >= 8:  # 8件以上連続は高確率でプレースホルダー
                issues.append({
                    'type': 'CONSECUTIVE_IDS',
                    'severity': 'HIGH',
                    'description': f"{group['occupation']}で{group['count']}件の連続ID",
                    'ids': group['ids'],
                    'action': 'DELETE_ALL'
                })
                self.deletion_candidates.extend(group['ids'])
        
        # 同姓グループの問題
        for surname, info in patterns['same_surname_groups'].items():
            if info['count'] >= 8:
                issues.append({
                    'type': 'SAME_SURNAME_GROUP',
                    'severity': 'HIGH',
                    'description': f"{surname}姓の{info['main_occupation']}が{info['count']}人",
                    'ids': info['ids'],
                    'action': 'VERIFY_AND_DELETE'
                })
                self.suspicious_records.extend(info['ids'])
        
        # 汎用名の問題
        for generic in patterns['generic_names']:
            if generic['count'] >= 5:
                issues.append({
                    'type': 'GENERIC_NAME_PATTERN',
                    'severity': 'MEDIUM',
                    'description': f"「{generic['pattern']}」を含む名前が{generic['count']}件",
                    'ids': generic['ids'],
                    'action': 'REVIEW'
                })
        
        logger.info(f"  検出された問題: {len(issues)}件")
        logger.info(f"  削除候補: {len(self.deletion_candidates)}件")
        logger.info(f"  要確認: {len(self.suspicious_records)}件")
        
        return issues
    
    def propose_solutions(self, issues: List[Dict]) -> List[Dict]:
        """
        4. 改善案を提示
        検出された問題への対処法
        """
        logger.info("💡 ステップ4: 改善案生成")
        
        solutions = []
        
        # 即座に削除すべきデータ
        high_severity = [i for i in issues if i['severity'] == 'HIGH']
        if high_severity:
            all_ids = []
            for issue in high_severity:
                all_ids.extend(issue['ids'])
            
            solutions.append({
                'action': 'IMMEDIATE_DELETION',
                'description': '高確率でプレースホルダーと判定されたデータの削除',
                'target_count': len(set(all_ids)),
                'ids': list(set(all_ids))[:50],  # 最初の50件
                'command': 'df = df[~df["person_id"].isin(deletion_ids)]'
            })
        
        # PDCAルール追加
        solutions.append({
            'action': 'ADD_PDCA_RULES',
            'description': 'プレースホルダー検出ルールの追加',
            'rules': [
                {
                    'id': 'RULE_093',
                    'name': '連続ID禁止ルール',
                    'condition': '同一職業で5件以上の連続IDは自動削除'
                },
                {
                    'id': 'RULE_094',
                    'name': '同姓グループ検証ルール',
                    'condition': '同姓同職業8人以上は実在性検証必須'
                },
                {
                    'id': 'RULE_095',
                    'name': '汎用名パターン検出ルール',
                    'condition': '「太郎」「健太」等の汎用名5件以上は要確認'
                }
            ]
        })
        
        # 継続的監視
        solutions.append({
            'action': 'CONTINUOUS_MONITORING',
            'description': '定期的なプレースホルダー検出の実施',
            'frequency': '週次',
            'metrics': ['連続ID数', '同姓グループ数', 'Wikipedia記載率']
        })
        
        return solutions
    
    def _extract_surname(self, name: str) -> str:
        """姓の抽出"""
        if pd.isna(name):
            return ''
        name = str(name).strip()
        if ' ' in name:
            return name.split()[0]
        elif len(name) >= 2:
            # 日本人名の場合、最初の2文字を姓とみなす
            return name[:2]
        return name
    
    def generate_deletion_script(self, df: pd.DataFrame, deletion_ids: List[str]):
        """削除スクリプト生成"""
        script = []
        script.append("#!/usr/bin/env python3")
        script.append('"""')
        script.append('プレースホルダーデータ削除スクリプト')
        script.append(f'生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        script.append(f'削除対象: {len(deletion_ids)}件')
        script.append('"""')
        script.append('')
        script.append('import pandas as pd')
        script.append('from datetime import datetime')
        script.append('')
        script.append('# 削除対象ID')
        script.append(f'deletion_ids = {deletion_ids[:20]}  # 最初の20件')
        script.append('')
        script.append('# データ読み込み')
        script.append("df = pd.read_csv('ultra_think_MASSIVE_CLEANED_20250912_035645.csv')")
        script.append('')
        script.append('# バックアップ作成')
        script.append("backup_file = f'backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.csv'")
        script.append("df.to_csv(backup_file, index=False, encoding='utf-8-sig')")
        script.append('')
        script.append('# 削除実行')
        script.append('df_cleaned = df[~df["person_id"].isin(deletion_ids)]')
        script.append('')
        script.append('# 保存')
        script.append("output_file = f'ultra_think_FINAL_CLEAN_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.csv'")
        script.append("df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')")
        script.append('')
        script.append('print(f"削除前: {len(df)}件")')
        script.append('print(f"削除後: {len(df_cleaned)}件")')
        script.append('print(f"削除数: {len(df) - len(df_cleaned)}件")')
        
        # スクリプトファイル保存
        script_file = f'delete_placeholders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(script))
        
        logger.info(f"📝 削除スクリプト生成: {script_file}")
        
        return script_file


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 高速プレースホルダー検出システム起動")
    logger.info("=" * 60)
    
    # データ読み込み
    csv_file = Path('ultra_think_MASSIVE_CLEANED_20250912_035645.csv')
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # 検出器初期化
    detector = FastPlaceholderDetector()
    
    # 1. データ構造分析
    structure = detector.analyze_structure(df)
    
    # 2. パターン検出
    patterns = detector.detect_patterns(df)
    
    # 3. 問題特定
    issues = detector.identify_issues(df, patterns)
    
    # 4. 改善案生成
    solutions = detector.propose_solutions(issues)
    
    # レポート生成
    logger.info("\n" + "=" * 60)
    logger.info("📊 検出結果サマリー")
    logger.info("=" * 60)
    
    # 問題の詳細表示
    for issue in issues[:5]:  # 最初の5件
        logger.info(f"\n❌ {issue['type']}")
        logger.info(f"  重要度: {issue['severity']}")
        logger.info(f"  説明: {issue['description']}")
        logger.info(f"  対処: {issue['action']}")
        logger.info(f"  対象ID例: {issue['ids'][:3]}")
    
    # 削除候補がある場合、削除スクリプト生成
    if detector.deletion_candidates:
        unique_ids = list(set(detector.deletion_candidates))
        logger.info(f"\n🗑️ 削除候補: {len(unique_ids)}件")
        
        # 削除対象の詳細
        delete_df = df[df['person_id'].isin(unique_ids[:20])]
        logger.info("\n削除対象例（最初の20件）:")
        for _, row in delete_df.iterrows():
            logger.info(f"  {row['person_id']}: {row['person_name']} ({row['occupation']})")
        
        # 削除スクリプト生成
        script_file = detector.generate_deletion_script(df, unique_ids)
        logger.info(f"\n✅ 削除スクリプトを生成しました: {script_file}")
    
    # PDCAルール提案
    logger.info("\n📋 PDCAガーディアンルール追加提案:")
    for solution in solutions:
        if solution['action'] == 'ADD_PDCA_RULES':
            for rule in solution['rules']:
                logger.info(f"  {rule['id']}: {rule['name']}")
                logger.info(f"    条件: {rule['condition']}")
    
    logger.info("\n✅ プレースホルダー検出完了")


if __name__ == "__main__":
    main()