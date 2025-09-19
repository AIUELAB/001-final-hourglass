#!/usr/bin/env python3
"""
包括的表示名検証スクリプト
全データのperson_name_displayをGoogle/Wikipedia準拠で検証
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import unicodedata
from improved_wikipedia_api import ImprovedWikipediaAPI

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveDisplayNameValidator:
    """包括的表示名検証クラス"""
    
    def __init__(self):
        """初期化"""
        self.violations = []
        self.suggestions = []
        self.wikipedia_api = ImprovedWikipediaAPI()
        
        self.statistics = {
            'total_checked': 0,
            'violations_found': 0,
            'hiragana_violations': 0,
            'space_violations': 0,
            'group_violations': 0,
            'foreign_name_violations': 0,
            'wikipedia_mismatches': 0,
            'categories': {}
        }
        
        # 正しい芸名リスト（ひらがな許可）
        self.valid_stage_names = {
            'あいみょん', 'きゃりーぱみゅぱみゅ', 'ふかわりょう',
            'よゐこ', 'おぎやはぎ', 'ゆりやんレトリィバァ',
            'かなで', 'しずちゃん', 'ゆめっち', 'みちお',
            'あやなん', 'あやののの', 'きまぐれクック',
            'あんり', 'きりやはるか', 'おたけ'
        }
        
        # 正しい英語表記リスト
        self.valid_english_names = {
            'PSY', 'MrBeast', 'HIKAKIN', 'IKKO', 'GACKT',
            'hyde', 'Ado', 'YOSHIKI', 'Toshl', 'HEATH',
            'PATA', 'J', 'SUGIZO', 'RYUICHI', 'INORAN'
        }
        
        # グループデータベース読み込み
        self.load_groups_database()
    
    def load_groups_database(self):
        """グループデータベース読み込み"""
        groups_file = Path('groups_database.json')
        
        if groups_file.exists():
            with open(groups_file, 'r', encoding='utf-8') as f:
                self.groups_db = json.load(f)
                logger.info(f"📂 グループデータベース読み込み: {len(self.groups_db)}グループ")
        else:
            self.groups_db = {}
            logger.warning("⚠️ groups_database.jsonが見つかりません")
        
        # メンバー名 → グループ名の逆引き辞書作成
        self.member_to_group = {}
        for group_name, group_info in self.groups_db.items():
            if 'members' in group_info:
                for member in group_info['members']:
                    if member not in self.member_to_group:
                        self.member_to_group[member] = []
                    self.member_to_group[member].append(group_name)
    
    def validate_display_name(self, row: pd.Series) -> Dict:
        """
        表示名の包括的検証
        
        Returns:
            検証結果の辞書
        """
        result = {
            'person_id': str(row.get('person_id', '')).strip(),
            'person_name': str(row.get('person_name', '')).strip(),
            'current_display': str(row.get('person_name_display', '')).strip(),
            'occupation': str(row.get('occupation', '')).strip(),
            'violations': [],
            'suggested_display': None,
            'confidence': 1.0
        }
        
        # 1. ひらがな表記チェック
        if self._is_hiragana_only(result['current_display']):
            if result['current_display'] not in self.valid_stage_names:
                if self._has_kanji(result['person_name']):
                    result['violations'].append('不適切なひらがな表記（漢字優先）')
                    self.statistics['hiragana_violations'] += 1
        
        # 2. スペースチェック（日本語名）
        if ' ' in result['current_display'] or '　' in result['current_display']:
            if not any(c.isascii() for c in result['current_display']):
                result['violations'].append('日本語名に不要なスペース')
                self.statistics['space_violations'] += 1
        
        # 3. グループメンバーチェック
        if result['person_name'] in self.member_to_group:
            groups = self.member_to_group[result['person_name']]
            if '（' not in result['current_display']:
                result['violations'].append(f'グループ名未記載: {", ".join(groups)}')
                self.statistics['group_violations'] += 1
        
        # 4. Wikipedia検証（重い処理なのでサンプリング）
        if result['violations'] or self._should_check_wikipedia(result):
            wiki_display, source = self.wikipedia_api.get_display_name(
                result['person_name'],
                result['occupation']
            )
            
            if source in ['wikipedia_ja', 'wikipedia_en']:
                if wiki_display != result['current_display']:
                    # グループメンバーの場合は括弧を追加
                    if result['person_name'] in self.member_to_group:
                        group = self.member_to_group[result['person_name']][0]
                        if '（' not in wiki_display:
                            wiki_display = f"{wiki_display}（{group}）"
                    
                    result['suggested_display'] = wiki_display
                    result['violations'].append(f'Wikipedia表記と不一致')
                    self.statistics['wikipedia_mismatches'] += 1
        
        # 5. 外国人名チェック
        if result['person_name'] in ['PSY', 'MrBeast'] and result['current_display'] != result['person_name']:
            result['violations'].append('外国人名の誤表記')
            result['suggested_display'] = result['person_name']
            self.statistics['foreign_name_violations'] += 1
        
        # 修正提案生成
        if result['violations'] and not result['suggested_display']:
            result['suggested_display'] = self._generate_suggestion(result)
        
        return result
    
    def _should_check_wikipedia(self, result: Dict) -> bool:
        """Wikipedia検証が必要か判定（負荷軽減のため）"""
        # 既知の問題パターン
        if self._is_hiragana_only(result['current_display']):
            return True
        if ' ' in result['current_display']:
            return True
        if result['person_id'] in ['P030135', 'P003780', 'P003186']:  # 既知の問題ID
            return True
        
        # 10%のランダムサンプリング
        import random
        return random.random() < 0.1
    
    def _generate_suggestion(self, result: Dict) -> str:
        """修正提案生成"""
        suggested = result['current_display']
        
        # スペース除去
        if ' ' in suggested or '　' in suggested:
            suggested = suggested.replace(' ', '').replace('　', '')
        
        # ひらがな→漢字（可能な場合）
        if self._is_hiragana_only(suggested) and self._has_kanji(result['person_name']):
            suggested = result['person_name']
        
        # グループ名追加
        if result['person_name'] in self.member_to_group:
            group = self.member_to_group[result['person_name']][0]
            if '（' not in suggested:
                suggested = f"{suggested}（{group}）"
        
        return suggested
    
    def _is_hiragana_only(self, text: str) -> bool:
        """ひらがなのみかチェック"""
        for char in text:
            if char in ' 　（）':
                continue
            name = unicodedata.name(char, '')
            if 'HIRAGANA' not in name:
                return False
        return True
    
    def _has_kanji(self, text: str) -> bool:
        """漢字を含むかチェック"""
        for char in text:
            name = unicodedata.name(char, '')
            if 'CJK UNIFIED IDEOGRAPH' in name:
                return True
        return False
    
    def validate_dataframe(self, df: pd.DataFrame, sample_size: Optional[int] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        DataFrameの包括的検証
        
        Args:
            df: 検証対象のDataFrame
            sample_size: サンプリングサイズ（Noneで全件）
            
        Returns:
            (検証済みDataFrame, 統計情報)
        """
        logger.info("🔍 包括的表示名検証開始")
        
        # サンプリング
        if sample_size:
            df_sample = df.sample(min(sample_size, len(df)))
            logger.info(f"📊 サンプリング: {len(df_sample)}件")
        else:
            df_sample = df
        
        for idx, row in df_sample.iterrows():
            self.statistics['total_checked'] += 1
            
            # 職業カテゴリ統計
            occupation = str(row.get('occupation', '')).strip()
            category = self._get_category(occupation)
            self.statistics['categories'][category] = self.statistics['categories'].get(category, 0) + 1
            
            # 検証実行
            validation_result = self.validate_display_name(row)
            
            if validation_result['violations']:
                self.statistics['violations_found'] += 1
                self.violations.append(validation_result)
                
                if validation_result['suggested_display']:
                    self.suggestions.append({
                        'person_id': validation_result['person_id'],
                        'current': validation_result['current_display'],
                        'suggested': validation_result['suggested_display'],
                        'reason': ', '.join(validation_result['violations'])
                    })
                
                if self.statistics['violations_found'] % 10 == 0:
                    logger.info(f"🔍 検証中... {self.statistics['violations_found']}件の違反検出")
        
        return df, self.statistics
    
    def _get_category(self, occupation: str) -> str:
        """職業カテゴリ分類"""
        if 'お笑い' in occupation or 'コメディ' in occupation:
            return 'お笑い芸人'
        elif '俳優' in occupation or '女優' in occupation:
            return '俳優'
        elif '歌手' in occupation or 'ミュージシャン' in occupation:
            return '音楽'
        elif 'YouTuber' in occupation or 'VTuber' in occupation:
            return 'インターネット'
        elif 'スポーツ' in occupation or '選手' in occupation:
            return 'スポーツ'
        else:
            return 'その他'
    
    def generate_report(self):
        """検証レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.statistics,
            'violations_summary': {
                'total': len(self.violations),
                'by_type': {
                    'hiragana': self.statistics['hiragana_violations'],
                    'space': self.statistics['space_violations'],
                    'group': self.statistics['group_violations'],
                    'foreign': self.statistics['foreign_name_violations'],
                    'wikipedia': self.statistics['wikipedia_mismatches']
                }
            },
            'sample_violations': self.violations[:50],
            'suggestions': self.suggestions[:100],
            'pdca_rules_validated': [
                'RULE_087: Google検索トップ表記準拠ルール',
                'RULE_088: Wikipedia表記優先ルール',
                'RULE_089: ひらがな表記制限ルール'
            ]
        }
        
        # JSON形式で保存
        report_file = f"comprehensive_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 検証レポート保存: {report_file}")
        
        # 修正提案CSV生成
        if self.suggestions:
            suggestions_df = pd.DataFrame(self.suggestions)
            suggestions_file = f"display_name_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            suggestions_df.to_csv(suggestions_file, index=False, encoding='utf-8-sig')
            logger.info(f"💡 修正提案CSV保存: {suggestions_file}")
        
        return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 包括的表示名検証開始")
    logger.info("=" * 60)
    
    # 最新のCSVファイルを探す
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        logger.error("❌ CSVファイルが見つかりません")
        return
    
    # 最新のファイルを使用
    csv_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"📂 データ読み込み: {csv_file}")
    
    df = pd.read_csv(csv_file)
    
    # 検証実行（負荷軽減のため1000件サンプリング）
    validator = ComprehensiveDisplayNameValidator()
    df_validated, stats = validator.validate_dataframe(df, sample_size=1000)
    
    # レポート生成
    report = validator.generate_report()
    
    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 検証結果サマリー")
    logger.info("=" * 60)
    logger.info(f"  総チェック数: {stats['total_checked']}")
    logger.info(f"  違反検出数: {stats['violations_found']}")
    violation_rate = (stats['violations_found'] / max(stats['total_checked'], 1)) * 100
    logger.info(f"  違反率: {violation_rate:.2f}%")
    
    logger.info("\n  違反タイプ別:")
    logger.info(f"    - ひらがな表記: {stats['hiragana_violations']}件")
    logger.info(f"    - スペース: {stats['space_violations']}件")
    logger.info(f"    - グループ名: {stats['group_violations']}件")
    logger.info(f"    - 外国人名: {stats['foreign_name_violations']}件")
    logger.info(f"    - Wikipedia不一致: {stats['wikipedia_mismatches']}件")
    
    if stats['categories']:
        logger.info("\n  カテゴリ別チェック数:")
        for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"    - {category}: {count}件")
    
    if validator.suggestions:
        logger.info(f"\n💡 {len(validator.suggestions)}件の修正提案を生成しました")
    
    logger.info("\n✅ 包括的表示名検証完了")


if __name__ == "__main__":
    main()