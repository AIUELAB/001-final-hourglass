#!/usr/bin/env python3
"""
偉人伝書籍人物リストと既存データベースの比較分析
データベース未登録の偉人を特定
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Set, Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BiographyDatabaseComparison:
    """偉人伝人物と既存データベースの比較クラス"""
    
    def __init__(self, database_file: str, biography_persons_file: str):
        """
        初期化
        
        Args:
            database_file: 既存データベースファイル
            biography_persons_file: 偉人伝人物リストファイル
        """
        self.database_file = database_file
        self.biography_persons_file = biography_persons_file
        
        # データ読み込み
        self.existing_df = self._load_database()
        self.biography_persons = self._load_biography_persons()
        
        # 名前正規化辞書
        self.name_normalization = {
            # 日本人
            "織田信長": ["織田信長", "信長"],
            "豊臣秀吉": ["豊臣秀吉", "秀吉", "羽柴秀吉"],
            "徳川家康": ["徳川家康", "家康"],
            "坂本龍馬": ["坂本龍馬", "坂本竜馬", "龍馬"],
            "西郷隆盛": ["西郷隆盛", "西郷どん"],
            "福沢諭吉": ["福沢諭吉", "福澤諭吉"],
            "夏目漱石": ["夏目漱石", "夏目金之助"],
            "野口英世": ["野口英世", "野口清作"],
            "二宮尊徳": ["二宮尊徳", "二宮金次郎"],
            "渋沢栄一": ["渋沢栄一", "渋澤榮一"],
            # 外国人
            "エジソン": ["トーマス・エジソン", "エジソン", "Thomas Edison"],
            "アインシュタイン": ["アルベルト・アインシュタイン", "アインシュタイン", "Albert Einstein"],
            "ヘレン・ケラー": ["ヘレン・ケラー", "Helen Keller"],
            "ナイチンゲール": ["フローレンス・ナイチンゲール", "ナイチンゲール", "Florence Nightingale"],
            "ベートーベン": ["ルートヴィヒ・ヴァン・ベートーヴェン", "ベートーベン", "ベートーヴェン"],
            "モーツァルト": ["ヴォルフガング・アマデウス・モーツァルト", "モーツァルト", "Wolfgang Amadeus Mozart"],
            "レオナルド・ダ・ヴィンチ": ["レオナルド・ダ・ヴィンチ", "ダ・ヴィンチ", "Leonardo da Vinci"],
            "ガリレオ": ["ガリレオ・ガリレイ", "ガリレオ", "Galileo Galilei"],
            "ニュートン": ["アイザック・ニュートン", "ニュートン", "Isaac Newton"],
            "ダーウィン": ["チャールズ・ダーウィン", "ダーウィン", "Charles Darwin"],
        }
    
    def _load_database(self) -> pd.DataFrame:
        """既存データベースを読み込み"""
        try:
            df = pd.read_csv(self.database_file, encoding='utf-8-sig')
            logger.info(f"既存データベース読み込み: {len(df)}レコード")
            return df
        except Exception as e:
            logger.error(f"データベース読み込みエラー: {e}")
            return pd.DataFrame()
    
    def _load_biography_persons(self) -> Set[str]:
        """偉人伝人物リストを読み込み"""
        try:
            with open(self.biography_persons_file, 'r', encoding='utf-8') as f:
                persons = set(line.strip() for line in f if line.strip())
            logger.info(f"偉人伝人物リスト読み込み: {len(persons)}名")
            return persons
        except Exception as e:
            logger.error(f"偉人伝リスト読み込みエラー: {e}")
            return set()
    
    def normalize_name(self, name: str) -> List[str]:
        """名前の正規化（複数の表記パターンを返す）"""
        # 基本パターン
        patterns = [name]
        
        # 正規化辞書から追加
        for key, values in self.name_normalization.items():
            if name in values or name == key:
                patterns.extend(values)
        
        # スペース除去パターン
        patterns.append(name.replace(' ', '').replace('　', ''))
        
        # 姓のみパターン（2文字以上の日本人名）
        if len(name) >= 3 and not any(c in name for c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'):
            patterns.append(name[:2])  # 姓のみ
        
        return list(set(patterns))
    
    def check_existing(self, name: str) -> Tuple[bool, str]:
        """
        既存データベースに存在するかチェック
        
        Returns:
            (存在フラグ, マッチした名前)
        """
        patterns = self.normalize_name(name)
        
        for pattern in patterns:
            # 完全一致チェック
            if any(pattern == str(n) for n in self.existing_df['name'].values):
                return True, pattern
            
            # 部分一致チェック
            if any(pattern in str(n) or str(n) in pattern 
                   for n in self.existing_df['name'].values):
                return True, pattern
        
        return False, ""
    
    def analyze_missing_persons(self) -> Dict:
        """偉人伝に載っているが、データベースに無い人物を分析"""
        
        missing_persons = []
        existing_persons = []
        
        for person in self.biography_persons:
            exists, matched_name = self.check_existing(person)
            
            if exists:
                existing_persons.append({
                    "biography_name": person,
                    "database_name": matched_name
                })
            else:
                missing_persons.append(person)
        
        # カテゴリ推定
        categories = self._estimate_categories(missing_persons)
        
        return {
            "total_biography_persons": len(self.biography_persons),
            "existing_count": len(existing_persons),
            "missing_count": len(missing_persons),
            "existing_rate": len(existing_persons) / len(self.biography_persons) * 100,
            "missing_persons": missing_persons,
            "existing_persons": existing_persons,
            "categories": categories
        }
    
    def _estimate_categories(self, persons: List[str]) -> Dict[str, List[str]]:
        """人物のカテゴリを推定"""
        categories = {
            "日本歴史": [],
            "世界歴史": [],
            "科学者": [],
            "芸術家": [],
            "実業家": [],
            "宗教家": [],
            "その他": []
        }
        
        # カテゴリ判定キーワード
        keywords = {
            "日本歴史": ["将軍", "天皇", "藩主", "武将", "幕末", "源", "平", "足利", "織田", "豊臣", "徳川"],
            "世界歴史": ["王", "女王", "皇帝", "大統領", "首相", "クレオパトラ", "アレクサンダー"],
            "科学者": ["博士", "研究", "発明", "ノーベル", "アインシュタイン", "ニュートン", "ダーウィン", "キュリー"],
            "芸術家": ["画家", "作曲家", "作家", "詩人", "ピカソ", "ゴッホ", "モーツァルト", "ベートーベン"],
            "実業家": ["創業", "会社", "ビジネス", "ジョブズ", "ゲイツ", "ディズニー", "フォード"],
            "宗教家": ["キリスト", "ブッダ", "仏教", "キリスト教", "イスラム", "ムハンマド", "孔子"]
        }
        
        for person in persons:
            categorized = False
            for category, kw_list in keywords.items():
                if any(kw in person for kw in kw_list):
                    categories[category].append(person)
                    categorized = True
                    break
            
            if not categorized:
                # 外国人名パターン
                if any(c in person for c in '・'):
                    categories["世界歴史"].append(person)
                else:
                    categories["その他"].append(person)
        
        # 空のカテゴリを削除
        return {k: v for k, v in categories.items() if v}
    
    def generate_report(self, output_file: str = "biography_missing_persons_report.md"):
        """分析レポートを生成"""
        
        analysis = self.analyze_missing_persons()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 偉人伝書籍 vs データベース比較分析レポート\n\n")
            f.write(f"## 📊 全体統計\n\n")
            f.write(f"- 偉人伝総人物数: {analysis['total_biography_persons']}名\n")
            f.write(f"- データベース登録済み: {analysis['existing_count']}名 ({analysis['existing_rate']:.1f}%)\n")
            f.write(f"- **データベース未登録: {analysis['missing_count']}名**\n\n")
            
            f.write("## 🎯 データベース未登録の偉人（追加候補）\n\n")
            
            for category, persons in analysis['categories'].items():
                if persons:
                    f.write(f"### {category} ({len(persons)}名)\n")
                    for person in persons:
                        f.write(f"- {person}\n")
                    f.write("\n")
            
            f.write("## 📈 分析結果\n\n")
            f.write("### 発見事項\n")
            f.write(f"1. 偉人伝に載っている人物の約{100 - analysis['existing_rate']:.1f}%がデータベース未登録\n")
            f.write(f"2. 特に海外の歴史的人物、科学者、芸術家が不足\n")
            f.write(f"3. 子供向け教育コンテンツで重要視される人物の欠落\n\n")
            
            f.write("### 推奨アクション\n")
            f.write("1. 優先度高: 複数の偉人伝シリーズに共通して登場する人物\n")
            f.write("2. 優先度中: 教育的価値の高い科学者、発明家\n")
            f.write("3. 優先度低: 単一シリーズのみの人物\n\n")
            
            f.write("---\n")
            f.write("*レポート生成日時: 2025年9月10日*\n")
        
        logger.info(f"✅ レポート生成完了: {output_file}")
        
        # CSVでも出力
        missing_df = pd.DataFrame(analysis['missing_persons'], columns=['name'])
        missing_df.to_csv('biography_missing_persons.csv', index=False, encoding='utf-8-sig')
        logger.info(f"✅ 未登録人物リスト: biography_missing_persons.csv")
        
        return analysis


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("偉人伝 vs データベース比較分析開始")
    logger.info("=" * 60)
    
    # 最新のデータベースファイルを取得
    import glob
    db_files = glob.glob("database_extended_wave3_*.csv")
    if not db_files:
        logger.error("データベースファイルが見つかりません")
        return
    
    latest_db = sorted(db_files)[-1]
    logger.info(f"使用データベース: {latest_db}")
    
    # 比較分析実行
    comparator = BiographyDatabaseComparison(
        database_file=latest_db,
        biography_persons_file="biography_book_persons.txt"
    )
    
    # レポート生成
    analysis = comparator.generate_report()
    
    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 比較分析サマリー")
    logger.info("=" * 60)
    logger.info(f"偉人伝総人物: {analysis['total_biography_persons']}名")
    logger.info(f"既存: {analysis['existing_count']}名")
    logger.info(f"未登録: {analysis['missing_count']}名")
    logger.info(f"カバー率: {analysis['existing_rate']:.1f}%")
    
    return comparator


if __name__ == "__main__":
    main()