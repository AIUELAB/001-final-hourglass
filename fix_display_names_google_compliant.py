#!/usr/bin/env python3
"""
表示名修正スクリプト - Google検索トップ準拠版
person_name_displayをGoogle/Wikipedia検索結果に基づいて修正
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from enhanced_wikipedia_api import EnhancedWikipediaAPI

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleCompliantDisplayNameFixer:
    """Google検索準拠表示名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fix_log = []
        self.wikipedia_api = EnhancedWikipediaAPI()
        
        # 明確な修正対象リスト（ユーザー指定）
        self.explicit_fixes = {
            # 外国人アーティスト
            'P030135': {'current': 'サイ', 'correct': 'PSY', 'reason': 'Google検索トップはPSY'},
            
            # 日本人俳優（ひらがな誤表記）
            'P003780': {'current': 'そめたに しょうた', 'correct': '染谷将太', 'reason': 'Wikipedia表記は漢字'},
            'P003186': {'current': 'おかだ まさき', 'correct': '岡田将生', 'reason': 'Wikipedia表記は漢字'},
            'P003676': {'current': 'まつざか とおり', 'correct': '松坂桃李', 'reason': 'Wikipedia表記は漢字'},
            'P004322': {'current': 'はまだ がく', 'correct': '濱田岳', 'reason': 'Wikipedia表記は漢字'},
            'P004371': {'current': 'えいた', 'correct': '瑛太', 'reason': 'Wikipedia表記は漢字'},
            
            # V6メンバー（ひらがな誤表記）
            'P001552': {'current': 'みやけ けん', 'correct': '三宅健', 'reason': 'Wikipedia表記は漢字'},
            'P001760': {'current': 'いのはら よしひこ', 'correct': '井ノ原快彦', 'reason': 'Wikipedia表記は漢字'},
            'P002496': {'current': 'さかもと まさゆき', 'correct': '坂本昌行', 'reason': 'Wikipedia表記は漢字'},
            
            # スポーツ選手
            'P001573': {'current': 'みうら かずよし', 'correct': '三浦知良', 'reason': 'Wikipedia表記は漢字'},
            
            # お笑い芸人（スペース誤用）
            'P000052': {'current': 'いかりや ちょうすけ', 'correct': 'いかりや長介', 'reason': 'スペース不要'},
            'P001887': {'current': 'なかもと こうじ', 'correct': '仲本工事', 'reason': 'Wikipedia表記は漢字'}
        }
        
        # グループメンバー表記（前回修正済みだが確認）
        self.group_members = {
            'いかりや長介': 'ザ・ドリフターズ',
            '仲本工事': 'ザ・ドリフターズ',
            '加藤茶': 'ザ・ドリフターズ',
            '高木ブー': 'ザ・ドリフターズ',
            '志村けん': 'ザ・ドリフターズ'
        }
        
        # ひらがな表記が正しい芸名リスト
        self.valid_hiragana_names = [
            'あいみょん', 'ふかわりょう', 'きゃりーぱみゅぱみゅ',
            'よゐこ', 'おぎやはぎ', 'ゆりやんレトリィバァ',
            'あやなん', 'あやののの', 'きまぐれクック',
            'かなで', 'しずちゃん', 'ゆめっち', 'みちお'
        ]
        
        # 英語表記が正しいリスト
        self.valid_english_names = [
            'PSY', 'MrBeast', 'HIKAKIN', 'IKKO', 'GACKT',
            'hyde', 'Ado', 'YOSHIKI', 'Toshl', 'J-Hope',
            'RM', 'Suga', 'Jin', 'Jimin', 'V', 'Jungkook'
        ]
    
    def fix_display_name(self, row: pd.Series) -> Optional[str]:
        """
        表示名を修正
        
        Args:
            row: DataFrameの行
            
        Returns:
            修正後の表示名（修正不要ならNone）
        """
        person_id = str(row.get('person_id', '')).strip()
        person_name = str(row.get('person_name', '')).strip()
        current_display = str(row.get('person_name_display', '')).strip()
        occupation = str(row.get('occupation', '')).strip()
        
        # 明示的な修正対象
        if person_id in self.explicit_fixes:
            fix_info = self.explicit_fixes[person_id]
            new_display = fix_info['correct']
            
            # グループメンバーチェック
            if person_name in self.group_members:
                group = self.group_members[person_name]
                if '（' not in new_display:
                    new_display = f"{new_display}（{group}）"
            
            return new_display
        
        # Wikipedia API による自動修正
        # ひらがなのみの表示名で、芸名リストにない場合
        if self._is_hiragana_only(current_display) and current_display not in self.valid_hiragana_names:
            # 元の名前が漢字を含む場合
            if self._has_kanji(person_name):
                # Wikipedia検索
                wiki_display, source = self.wikipedia_api.get_display_name(person_name, occupation)
                if source in ['wikipedia_ja', 'original_kanji'] and wiki_display != current_display:
                    # グループメンバーチェック
                    if person_name in self.group_members:
                        group = self.group_members[person_name]
                        if '（' not in wiki_display:
                            wiki_display = f"{wiki_display}（{group}）"
                    return wiki_display
        
        # スペース除去（いかりや ちょうすけ → いかりや長介）
        if ' ' in current_display and not any(c.isascii() for c in current_display):
            # 日本語名でスペースがある場合は除去
            no_space = current_display.replace(' ', '').replace('　', '')
            if no_space != current_display:
                # グループメンバーチェック
                if person_name in self.group_members:
                    group = self.group_members[person_name]
                    if '（' not in no_space:
                        no_space = f"{no_space}（{group}）"
                return no_space
        
        return None
    
    def _is_hiragana_only(self, text: str) -> bool:
        """ひらがなのみかチェック"""
        import unicodedata
        for char in text:
            if char in ' 　（）':
                continue
            category = unicodedata.category(char)
            name = unicodedata.name(char, '')
            if 'HIRAGANA' not in name:
                return False
        return True
    
    def _has_kanji(self, text: str) -> bool:
        """漢字を含むかチェック"""
        import unicodedata
        for char in text:
            name = unicodedata.name(char, '')
            if 'CJK UNIFIED IDEOGRAPH' in name:
                return True
        return False
    
    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        DataFrameを処理して表示名を修正
        
        Args:
            df: 処理対象のDataFrame
            
        Returns:
            (修正後のDataFrame, 統計情報)
        """
        stats = {
            'total_processed': 0,
            'fixed_count': 0,
            'explicit_fixes': 0,
            'wikipedia_fixes': 0,
            'space_removal_fixes': 0
        }
        
        # バックアップ作成
        df_backup = df.copy()
        
        for idx, row in df.iterrows():
            stats['total_processed'] += 1
            
            person_id = str(row.get('person_id', '')).strip()
            person_name = str(row.get('person_name', '')).strip()
            current_display = str(row.get('person_name_display', '')).strip()
            occupation = str(row.get('occupation', '')).strip()
            
            # 修正実行
            new_display = self.fix_display_name(row)
            
            if new_display and new_display != current_display:
                df.at[idx, 'person_name_display'] = new_display
                stats['fixed_count'] += 1
                
                # 修正理由分類
                if person_id in self.explicit_fixes:
                    stats['explicit_fixes'] += 1
                    reason = self.explicit_fixes[person_id]['reason']
                elif ' ' in current_display:
                    stats['space_removal_fixes'] += 1
                    reason = 'スペース除去'
                else:
                    stats['wikipedia_fixes'] += 1
                    reason = 'Wikipedia準拠'
                
                self.fix_log.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'original_display': current_display,
                    'new_display': new_display,
                    'occupation': occupation,
                    'reason': reason
                })
                
                logger.info(f"✅ 修正: {person_id} {current_display} → {new_display} ({reason})")
        
        return df, stats
    
    def generate_report(self, stats: Dict):
        """
        修正レポート生成
        
        Args:
            stats: 統計情報
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'fix_log': self.fix_log,
            'rules_applied': [
                'Google検索トップ表記準拠',
                'Wikipedia表記優先',
                'ひらがな表記は芸名のみ',
                'スペース除去（日本語名）',
                'グループメンバー括弧付与'
            ]
        }
        
        report_file = f"display_name_fix_google_compliant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 レポート保存: {report_file}")
        
        # マークダウンレポート生成
        self.generate_markdown_report(stats)
    
    def generate_markdown_report(self, stats: Dict):
        """マークダウン形式のレポート生成"""
        report = []
        report.append("# 表示名修正レポート（Google検索準拠）")
        report.append("")
        report.append(f"修正日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 📊 修正サマリー")
        report.append("")
        report.append(f"- **総処理数**: {stats['total_processed']}件")
        report.append(f"- **修正件数**: {stats['fixed_count']}件")
        report.append(f"  - 明示的修正: {stats['explicit_fixes']}件")
        report.append(f"  - Wikipedia準拠: {stats['wikipedia_fixes']}件")
        report.append(f"  - スペース除去: {stats['space_removal_fixes']}件")
        report.append("")
        
        if self.fix_log:
            report.append("## 修正詳細")
            report.append("")
            report.append("| Person ID | 元の表示名 | 修正後 | 理由 |")
            report.append("|-----------|-----------|--------|------|")
            
            for fix in self.fix_log[:20]:  # 最初の20件
                report.append(f"| {fix['person_id']} | {fix['original_display']} | {fix['new_display']} | {fix['reason']} |")
            
            if len(self.fix_log) > 20:
                report.append("")
                report.append(f"*他 {len(self.fix_log) - 20}件の修正*")
        
        report.append("")
        report.append("## ✅ 適用ルール")
        report.append("")
        report.append("1. Google検索トップの表記に準拠")
        report.append("2. Wikipedia日本語版の表記を優先")
        report.append("3. ひらがな表記は芸名のみ許可")
        report.append("4. 日本語名のスペースは除去")
        report.append("5. グループメンバーには括弧付与")
        report.append("")
        
        # レポート保存
        report_file = f"DISPLAY_NAME_FIX_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        logger.info(f"📄 マークダウンレポート生成: {report_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 表示名修正開始（Google検索準拠）")
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
    
    # 修正処理
    fixer = GoogleCompliantDisplayNameFixer()
    df_fixed, stats = fixer.process_dataframe(df)
    
    # レポート生成
    fixer.generate_report(stats)
    
    # 結果保存
    output_file = f"ultra_think_GOOGLE_COMPLIANT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_fixed.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")
    
    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"  総処理数: {stats['total_processed']}")
    logger.info(f"  修正件数: {stats['fixed_count']}")
    logger.info(f"    - 明示的修正: {stats['explicit_fixes']}")
    logger.info(f"    - Wikipedia準拠: {stats['wikipedia_fixes']}")
    logger.info(f"    - スペース除去: {stats['space_removal_fixes']}")
    
    logger.info("\n✅ 表示名修正完了（Google検索準拠）")


if __name__ == "__main__":
    main()