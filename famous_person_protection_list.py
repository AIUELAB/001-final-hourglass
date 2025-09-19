#!/usr/bin/env python3
"""
有名人保護リスト管理
Wikipedia掲載が確実な人物を無条件で保護
"""

import json
from typing import Dict, List, Set
from datetime import datetime
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FamousPersonProtectionList:
    """有名人保護リスト管理クラス"""
    
    def __init__(self):
        """初期化"""
        # 絶対保護リスト（削除不可）
        self.absolute_protection = {
            # 野球
            '張本勲': {'occupation': '野球選手', 'reason': '日本プロ野球通算3085安打、名球会'},
            '王貞治': {'occupation': '野球選手', 'reason': 'ホームラン世界記録868本'},
            'イチロー': {'occupation': '野球選手', 'reason': 'MLB通算3089安打'},
            '大谷翔平': {'occupation': '野球選手', 'reason': 'MLB二刀流、MVP'},
            
            # 卓球
            '張本智和': {'occupation': '卓球選手', 'reason': 'オリンピック代表、世界ランキング'},
            '福原愛': {'occupation': '卓球選手', 'reason': '元日本代表、オリンピック出場'},
            '水谷隼': {'occupation': '卓球選手', 'reason': 'オリンピック金メダリスト'},
            '伊藤美誠': {'occupation': '卓球選手', 'reason': 'オリンピックメダリスト'},
            
            # 陸上
            '為末大': {'occupation': '陸上選手', 'reason': '400mハードル日本記録保持者'},
            '室伏広治': {'occupation': '陸上選手', 'reason': 'ハンマー投げ金メダリスト'},
            '高橋尚子': {'occupation': '陸上選手', 'reason': 'マラソン金メダリスト'},
            
            # 大相撲
            '照ノ富士': {'occupation': '大相撲力士', 'reason': '第73代横綱'},
            '白鵬': {'occupation': '大相撲力士', 'reason': '第69代横綱、優勝45回'},
            '貴乃花': {'occupation': '大相撲力士', 'reason': '第65代横綱'},
            
            # テニス
            '錦織圭': {'occupation': 'テニス選手', 'reason': '世界ランキング最高4位'},
            '大坂なおみ': {'occupation': 'テニス選手', 'reason': 'グランドスラム優勝4回'},
            
            # サッカー
            '鎌田大地': {'occupation': 'サッカー選手', 'reason': '日本代表、ブンデスリーガ'},
            '三笘薫': {'occupation': 'サッカー選手', 'reason': '日本代表、プレミアリーグ'},
            '久保建英': {'occupation': 'サッカー選手', 'reason': '日本代表、ラ・リーガ'},
            '本田圭佑': {'occupation': 'サッカー選手', 'reason': '元日本代表、ワールドカップ出場'},
            '香川真司': {'occupation': 'サッカー選手', 'reason': '元日本代表、ブンデスリーガ優勝'},
            
            # 水泳
            '古賀淳也': {'occupation': '水泳選手', 'reason': '世界水泳金メダリスト'},
            '北島康介': {'occupation': '水泳選手', 'reason': 'オリンピック金メダル4個'},
            '池江璃花子': {'occupation': '水泳選手', 'reason': '日本記録保持者、復活劇'},
            
            # バレーボール
            '古賀紗理那': {'occupation': 'バレーボール選手', 'reason': '日本代表エース'},
            '石川祐希': {'occupation': 'バレーボール選手', 'reason': '日本代表キャプテン'},
            
            # 女子プロレス（前回保護済み）
            'ブル中野': {'occupation': '女子プロレスラー', 'reason': 'WWF女子王者'},
            '北斗晶': {'occupation': '女子プロレスラー', 'reason': '女子プロレス界レジェンド'},
            'ジャガー横田': {'occupation': '女子プロレスラー', 'reason': '女子プロレス界レジェンド'},
            'アジャ・コング': {'occupation': '女子プロレスラー', 'reason': 'WWWA世界王者'},
            
            # その他著名人
            'HIKAKIN': {'occupation': 'YouTuber', 'reason': '日本トップYouTuber'},
            '米津玄師': {'occupation': '歌手', 'reason': '紅白出場、Lemon大ヒット'},
            '藤井聡太': {'occupation': '将棋棋士', 'reason': '最年少八冠'},
            '羽生結弦': {'occupation': 'フィギュアスケート選手', 'reason': 'オリンピック2連覇'},
        }
        
        # 英語/ローマ字表記の対応表
        self.name_variations = {
            'Nishikori Kei': '錦織圭',
            '錦織 圭': '錦織圭',
            'Kamada Daichi': '鎌田大地',
            '鎌田 大地': '鎌田大地',
            'Tomokazu Harimoto': '張本智和',
            '張本 智和': '張本智和',
            'Terunofuji Haruo': '照ノ富士',
            '照ノ富士 春雄': '照ノ富士',
            'Tamesue Dai': '為末大',
            '為末 大': '為末大',
            'Harimoto Isao': '張本勲',
            '張本 勲': '張本勲',
            'Koga Junya': '古賀淳也',
            '古賀 淳也': '古賀淳也',
            'Koga Sarina': '古賀紗理那',
            '古賀 紗理那': '古賀紗理那',
        }
        
        # 職業による自動保護条件
        self.occupation_protection = {
            'オリンピック': {'min_score': 30, 'reason': 'オリンピック選手'},
            '日本代表': {'min_score': 30, 'reason': '日本代表選手'},
            '世界': {'min_score': 40, 'reason': '世界大会出場'},
            'プロ': {'min_score': 20, 'reason': 'プロ選手'},
            '横綱': {'min_score': 80, 'reason': '横綱'},
            '大関': {'min_score': 60, 'reason': '大関'},
        }
    
    def is_protected(self, person_name: str, occupation: str = None) -> tuple[bool, str]:
        """
        保護対象かチェック
        
        Returns:
            (保護フラグ, 理由)
        """
        # 名前の正規化
        normalized_name = self._normalize_name(person_name)
        
        # 絶対保護リストチェック
        if normalized_name in self.absolute_protection:
            info = self.absolute_protection[normalized_name]
            return True, f"絶対保護リスト: {info['reason']}"
        
        # 職業ベースの保護チェック
        if occupation:
            for keyword, condition in self.occupation_protection.items():
                if keyword in occupation:
                    return True, f"職業保護: {condition['reason']}"
        
        return False, ""
    
    def _normalize_name(self, name: str) -> str:
        """名前の正規化（スペース除去、表記統一）"""
        # 英語/ローマ字表記の変換
        if name in self.name_variations:
            name = self.name_variations[name]
        
        # スペース除去
        name = name.replace(' ', '').replace('　', '')
        
        return name
    
    def get_protection_list(self) -> List[str]:
        """保護リスト取得"""
        return list(self.absolute_protection.keys())
    
    def add_protection(self, person_name: str, occupation: str, reason: str):
        """保護リストに追加"""
        normalized_name = self._normalize_name(person_name)
        self.absolute_protection[normalized_name] = {
            'occupation': occupation,
            'reason': reason
        }
        logger.info(f"✅ 保護リストに追加: {person_name} ({reason})")
    
    def generate_report(self) -> Dict:
        """保護リストレポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_protected': len(self.absolute_protection),
            'categories': {},
            'protection_list': self.absolute_protection
        }
        
        # カテゴリ別集計
        for name, info in self.absolute_protection.items():
            occ = info['occupation']
            if occ not in report['categories']:
                report['categories'][occ] = 0
            report['categories'][occ] += 1
        
        return report
    
    def save_to_file(self, filename: str = "protection_list.json"):
        """ファイルに保存"""
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 保護リスト保存: {filename}")


def test_protection_list():
    """保護リストのテスト"""
    protector = FamousPersonProtectionList()
    
    # テストケース
    test_cases = [
        ('張本勲', '野球選手'),
        ('Nishikori Kei', 'テニス選手'),
        ('照ノ富士', '大相撲力士'),
        ('リーチ三郎', 'ラグビー選手'),  # 保護されない
        ('高橋次郎', '野球選手'),  # 保護されない
    ]
    
    logger.info("=" * 60)
    logger.info("保護リストテスト")
    logger.info("=" * 60)
    
    for name, occupation in test_cases:
        protected, reason = protector.is_protected(name, occupation)
        if protected:
            logger.info(f"✅ {name}: 保護対象 - {reason}")
        else:
            logger.info(f"❌ {name}: 保護対象外")
    
    # レポート生成
    report = protector.generate_report()
    logger.info(f"\n📊 保護リスト統計:")
    logger.info(f"  総保護人数: {report['total_protected']}名")
    logger.info(f"  カテゴリ別:")
    for occ, count in report['categories'].items():
        logger.info(f"    {occ}: {count}名")
    
    # ファイル保存
    protector.save_to_file()


if __name__ == "__main__":
    test_protection_list()