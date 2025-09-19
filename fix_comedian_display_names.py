#!/usr/bin/env python3
"""
お笑い芸人の表示名修正スクリプト
グループ名を括弧付きで追加し、統一ルールに準拠させる
"""

import pandas as pd
import json
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComedianDisplayNameFixer:
    """お笑い芸人表示名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.fix_log = []
        
        # グループ・メンバー対応表（手動定義）
        self.comedian_groups = {
            # ザ・ドリフターズ
            'いかりや長介': 'ザ・ドリフターズ',
            '加藤茶': 'ザ・ドリフターズ',
            '仲本工事': 'ザ・ドリフターズ',
            '高木ブー': 'ザ・ドリフターズ',
            '志村けん': 'ザ・ドリフターズ',
            
            # FUJIWARA
            '原西孝幸': 'FUJIWARA',
            'Takayuki Haranishi': 'FUJIWARA',
            '藤本敏史': 'FUJIWARA',
            'フジモン': 'FUJIWARA',
            '原': 'FUJIWARA',
            'Hara': 'FUJIWARA',
            
            # 南海キャンディーズ
            'しずちゃん': '南海キャンディーズ',
            '山崎静代': '南海キャンディーズ',
            '山里亮太': '南海キャンディーズ',
            
            # 3時のヒロイン
            'ゆめっち': '3時のヒロイン',
            'かなで': '3時のヒロイン',
            '福田麻貴': '3時のヒロイン',
            
            # アキナ
            '秋山賢太': 'アキナ',
            '山名文和': 'アキナ',
            
            # 和牛
            '水田信二': '和牛',
            '川西賢志郎': '和牛',
            
            # 見取り図
            'リリー': '見取り図',
            '盛山晋太郎': '見取り図',
            
            # スピードワゴン
            '井戸田潤': 'スピードワゴン',
            '小沢一敬': 'スピードワゴン',
            
            # アンタッチャブル
            '山崎弘也': 'アンタッチャブル',
            '柴田英嗣': 'アンタッチャブル',
            
            # トータルテンボス
            '大村朋宏': 'トータルテンボス',
            '藤田憲右': 'トータルテンボス',
            
            # よゐこ
            '有野晋哉': 'よゐこ',
            '濱口優': 'よゐこ',
            
            # 錦鯉
            '長谷川雅紀': '錦鯉',
            '渡辺隆': '錦鯉',
            
            # おぎやはぎ
            '小木博明': 'おぎやはぎ',
            '矢作兼': 'おぎやはぎ',
            
            # その他（単語のみの芸名）
            'みちお': 'トム・ブラウン',  # トム・ブラウンのみちお
            '加納': '４ガロン',  # ４ガロンの加納
            'きりやはるか': 'きりやはるか',  # ピン芸人
            'おたけ': 'でんぱ組.inc',  # 可能性があるが要確認
            'Masayasu Otake': 'でんぱ組.inc',
        }
        
        # 問題のあるperson_idリスト
        self.target_person_ids = [
            'P000052',  # いかりや長介
            'P001887',  # 仲本工事
            'P000057',  # Masayasu Otake
            'P000058',  # かなで
            'P000063',  # きりやはるか
            'P000072',  # しずちゃん
            'P000119',  # みちお
            'P000133',  # ゆめっち
            'P001442',  # リリー
            'P002167',  # 加納
            'P002301',  # Takayuki Haranishi
            'P002304',  # Hara
        ]
    
    def fix_display_name(self, person_name: str, current_display: str, occupation: str) -> str:
        """
        表示名を修正
        
        Args:
            person_name: person_name列の値
            current_display: 現在のperson_name_display列の値
            occupation: occupation列の値
            
        Returns:
            修正後の表示名
        """
        # グループ名を取得
        group_name = self.comedian_groups.get(person_name)
        
        if not group_name:
            # 別名でも検索
            for key, group in self.comedian_groups.items():
                if key in person_name or person_name in key:
                    group_name = group
                    break
        
        if group_name:
            # ピン芸人の場合はそのまま
            if group_name == person_name:
                return person_name
            
            # 既に括弧がある場合はチェック
            if '(' in current_display and ')' in current_display:
                # 正しいグループ名か確認
                if group_name in current_display:
                    return current_display
                else:
                    # 間違ったグループ名の場合は修正
                    base_name = current_display.split('(')[0].strip()
                    return f"{base_name}（{group_name}）"
            
            # 表示名を決定
            if person_name in ['Takayuki Haranishi', 'Masayasu Otake', 'Hara']:
                # 英語名の場合は日本語名に変換
                if person_name == 'Takayuki Haranishi':
                    base_name = '原西孝幸'
                elif person_name == 'Masayasu Otake':
                    base_name = 'おたけ'
                elif person_name == 'Hara':
                    base_name = '原'
                else:
                    base_name = person_name
            else:
                base_name = person_name
            
            return f"{base_name}（{group_name}）"
        
        # グループが見つからない場合は現状維持
        return current_display if current_display else person_name
    
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
            'target_ids_found': 0,
            'groups_added': {}
        }
        
        # ターゲットIDの処理
        for person_id in self.target_person_ids:
            mask = df['person_id'] == person_id
            if mask.any():
                stats['target_ids_found'] += 1
                row = df[mask].iloc[0]
                
                person_name = str(row.get('person_name', '')).strip()
                current_display = str(row.get('person_name_display', '')).strip()
                occupation = str(row.get('occupation', '')).strip()
                
                # 修正前の値を記録
                original_display = current_display
                
                # 表示名を修正
                new_display = self.fix_display_name(person_name, current_display, occupation)
                
                # 変更があった場合
                if new_display != original_display:
                    df.loc[mask, 'person_name_display'] = new_display
                    stats['fixed_count'] += 1
                    
                    # グループ名を抽出して統計
                    if '（' in new_display and '）' in new_display:
                        group = new_display.split('（')[1].split('）')[0]
                        stats['groups_added'][group] = stats['groups_added'].get(group, 0) + 1
                    
                    self.fix_log.append({
                        'person_id': person_id,
                        'person_name': person_name,
                        'original_display': original_display,
                        'new_display': new_display,
                        'occupation': occupation
                    })
                    
                    logger.info(f"✅ 修正: {person_id} {person_name} → {new_display}")
        
        # お笑い芸人全体をチェック（追加処理）
        comedy_mask = df['occupation'].str.contains('お笑い|コメディ', na=False)
        for idx, row in df[comedy_mask].iterrows():
            person_name = str(row.get('person_name', '')).strip()
            current_display = str(row.get('person_name_display', '')).strip()
            occupation = str(row.get('occupation', '')).strip()
            
            # グループメンバーか確認
            if person_name in self.comedian_groups:
                new_display = self.fix_display_name(person_name, current_display, occupation)
                
                if new_display != current_display:
                    df.at[idx, 'person_name_display'] = new_display
                    stats['fixed_count'] += 1
                    
                    if '（' in new_display and '）' in new_display:
                        group = new_display.split('（')[1].split('）')[0]
                        stats['groups_added'][group] = stats['groups_added'].get(group, 0) + 1
        
        stats['total_processed'] = len(df)
        
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
                'グループメンバーには（グループ名）を付与',
                'ピン芸人はそのまま',
                '英語名は日本語名に変換',
                'person_name_display統一ルールに準拠'
            ]
        }
        
        report_file = f"comedian_display_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 レポート保存: {report_file}")
        
        # サマリー表示
        logger.info("\n" + "=" * 60)
        logger.info("📊 修正結果サマリー")
        logger.info("=" * 60)
        logger.info(f"  総レコード数: {stats['total_processed']}")
        logger.info(f"  修正件数: {stats['fixed_count']}")
        logger.info(f"  ターゲットID発見数: {stats['target_ids_found']}")
        
        if stats['groups_added']:
            logger.info("\n  追加されたグループ:")
            for group, count in stats['groups_added'].items():
                logger.info(f"    {group}: {count}名")


def main():
    """メイン処理"""
    logger.info("🚀 お笑い芸人表示名修正開始")
    
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
    fixer = ComedianDisplayNameFixer()
    df_fixed, stats = fixer.process_dataframe(df)
    
    # レポート生成
    fixer.generate_report(stats)
    
    # 結果保存
    output_file = f"ultra_think_COMEDIAN_FIXED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_fixed.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")
    
    logger.info("\n✅ お笑い芸人表示名修正完了")


if __name__ == "__main__":
    main()