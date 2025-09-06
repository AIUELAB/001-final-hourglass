#!/usr/bin/env python3
"""
シンプル知名度スコア付与システム
Google Search APIのみを使用した高速版
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from googleapiclient.discovery import build
import time

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleRecognitionScorer:
    """シンプル知名度スコア評価"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.output_dir = Path("recognition_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Google Custom Search API設定
        self.google_key = os.getenv('GOOGLE_API_KEY')
        self.google_cx = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not self.google_key or not self.google_cx:
            raise SystemError("Google API設定が不足しています")
        
        self.service = build('customsearch', 'v1', developerKey=self.google_key)
        
        # 保護リスト（主要なもののみ）
        self.protected_names = {
            # 教科書人物
            "織田信長", "豊臣秀吉", "徳川家康", "聖徳太子", "紫式部",
            "チンギス・ハン", "ナポレオン", "アインシュタイン", "ガンジー",
            # 架空キャラクター
            "竈門炭治郎", "孫悟空", "ドラえもん", "ピカチュウ", "ルフィ",
            # 現代アイコン
            "HIKAKIN", "ヒカキン", "大谷翔平", "Ado", "YOASOBI", "米津玄師"
        }
        
        # カテゴリボーナス
        self.category_bonus = {
            'YouTuber': 2.0,
            'TikToker': 2.0,
            'VTuber': 1.8,
            'インフルエンサー': 1.5,
            'お笑い芸人': 1.2,
            '俳優': 1.0,
            '歌手': 1.0,
            'アイドル': 1.2,
            'スポーツ選手': 0.8,
            '歴史上の人物': 0.3,
            '架空キャラクター': 1.5
        }
    
    def search_google(self, query: str) -> int:
        """Google検索（結果数取得）"""
        try:
            result = self.service.cse().list(
                q=query,
                cx=self.google_cx,
                num=1  # 最小限のリクエスト
            ).execute()
            
            # 総結果数を取得
            if 'searchInformation' in result:
                total_results = result['searchInformation'].get('totalResults', '0')
                return int(total_results)
            
            return 0
            
        except Exception as e:
            logger.warning(f"Google検索エラー ({query}): {e}")
            return 0
    
    def calculate_score(self, row: pd.Series) -> Dict:
        """スコア計算"""
        name = row.get('person_name', '')
        name_ja = row.get('person_name_ja', '')
        category = str(row.get('category', ''))
        occupation = str(row.get('occupation', ''))
        
        # 保護チェック
        is_protected = False
        if name in self.protected_names or name_ja in self.protected_names:
            is_protected = True
            final_score = 10.0
            search_results = 999999999  # ダミー値
        else:
            # Google検索
            search_query = name_ja if name_ja else name
            search_results = self.search_google(search_query)
            
            # スコア計算（対数スケール）
            if search_results > 0:
                base_score = min(10, np.log10(search_results) * 1.2)
            else:
                base_score = 0
            
            # カテゴリボーナス
            bonus = 0
            for key, value in self.category_bonus.items():
                if key in category or key in occupation:
                    bonus = max(bonus, value)
            
            final_score = min(10.0, base_score + bonus)
        
        return {
            'recognition_score_2025': final_score,
            'google_results': search_results,
            'is_protected': is_protected,
            'deletion_recommendation': self._get_recommendation(final_score)
        }
    
    def _get_recommendation(self, score: float) -> str:
        """削除推奨判定"""
        if score >= 7.0:
            return '保持（高知名度）'
        elif score >= 5.0:
            return '保持（中知名度）'
        elif score >= 3.0:
            return '要検討'
        else:
            return '削除候補'
    
    def process_database(self):
        """データベース処理"""
        logger.info("📂 データベース読み込み中...")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        total = len(df)
        logger.info(f"✅ {total}件のレコードを読み込みました")
        
        # テストモード
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            df = df.head(100)
            logger.info("⚠️ テストモード: 最初の100件のみ処理")
            total = len(df)
        
        # 処理
        logger.info("🔄 知名度評価開始...")
        
        for idx, row in df.iterrows():
            if idx % 10 == 0:
                logger.info(f"  進捗: {idx+1}/{total} ({(idx+1)/total*100:.1f}%)")
            
            # スコア計算
            result = self.calculate_score(row)
            
            # DataFrameに反映
            for key, value in result.items():
                df.loc[idx, key] = value
            
            # レート制限対策（1秒に10リクエストまで）
            time.sleep(0.1)
        
        # 統計表示
        self._print_statistics(df)
        
        # 有名人検証
        self._validate_famous_persons(df)
        
        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"recognition_simple_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 結果を保存: {output_path}")
        
        return df
    
    def _print_statistics(self, df: pd.DataFrame):
        """統計情報出力"""
        logger.info("\n📊 評価結果統計:")
        
        stats = df['deletion_recommendation'].value_counts()
        total = len(df)
        
        for category, count in stats.items():
            percentage = (count / total) * 100
            logger.info(f"  {category}: {count}件 ({percentage:.1f}%)")
        
        # 削除率チェック
        deletion_count = df[df['deletion_recommendation'] == '削除候補'].shape[0]
        deletion_rate = (deletion_count / total) * 100
        
        if 10 <= deletion_rate <= 20:
            logger.info(f"✅ 削除率が適正範囲内: {deletion_rate:.1f}%")
        else:
            logger.warning(f"⚠️ 削除率が範囲外: {deletion_rate:.1f}%")
    
    def _validate_famous_persons(self, df: pd.DataFrame):
        """有名人検証"""
        logger.info("\n🔍 有名人検証:")
        
        test_persons = ['HIKAKIN', 'ヒカキン', '大谷翔平', 'Ado']
        
        for name in test_persons:
            matches = df[
                (df['person_name'].str.contains(name, na=False)) |
                (df['person_name_ja'].str.contains(name, na=False))
            ]
            
            if not matches.empty:
                for _, row in matches.head(1).iterrows():
                    score = row.get('recognition_score_2025', 0)
                    status = row.get('deletion_recommendation', '')
                    logger.info(f"  {name}: スコア={score:.2f}, 判定={status}")


def main():
    """メイン処理"""
    # 品質ゲートチェック（簡易版）
    from quality_gates import QualityGateSystem
    
    gate_system = QualityGateSystem()
    passed, _ = gate_system.check_script(__file__)
    
    if not passed:
        logger.error("品質ゲート失敗")
        sys.exit(1)
    
    # CSVファイル
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106.csv"
    
    if not Path(csv_path).exists():
        alt_files = list(Path(".").glob("ultra_think*EPISODE*.csv"))
        if alt_files:
            csv_path = str(alt_files[-1])
        else:
            logger.error("CSVファイルが見つかりません")
            sys.exit(1)
    
    # 評価実行
    scorer = SimpleRecognitionScorer(csv_path)
    scorer.process_database()
    
    logger.info("\n✨ 知名度評価完了！")


if __name__ == "__main__":
    main()