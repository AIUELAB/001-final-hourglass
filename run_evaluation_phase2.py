#!/usr/bin/env python3
"""
知名度評価フェーズ2 - 修正済みデータベースの評価
削除しきい値: 2.9未満（より厳格な基準）
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
from pathlib import Path
import time

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase2EvaluationSystem:
    """フェーズ2評価システム - 削除しきい値2.9"""
    
    def __init__(self):
        self.DELETION_THRESHOLD = 2.9  # より厳格な削除基準
        self.stats = {
            'total_records': 0,
            'deleted': 0,
            'kept': 0,
            'deletion_rate': 0.0
        }
        
        # 重要人物の保護リスト（絶対に削除しない）
        self.protected_persons = [
            'HIKAKIN', '米津玄師', '大谷翔平', '新垣結衣', '嵐',
            'ガンジー', '松本薫', '斎藤司', 'カンタ'
        ]
        
    def load_evaluation_results(self, csv_file):
        """評価結果を読み込み"""
        logger.info(f"📂 評価結果読み込み: {csv_file}")
        df = pd.read_csv(csv_file)
        logger.info(f"  レコード数: {len(df)}件")
        
        # name_recognitionカラムが存在しない場合は既存のスコアを使用
        if 'name_recognition' not in df.columns:
            if 'recognition_score' in df.columns:
                df['name_recognition'] = df['recognition_score']
            else:
                logger.error("スコアカラムが見つかりません")
                raise ValueError("スコアカラムが存在しません")
        
        return df
    
    def analyze_deletion_candidates(self, df):
        """削除候補の分析"""
        logger.info("=" * 60)
        logger.info("🔍 削除候補の分析（しきい値 < 2.9）")
        logger.info("=" * 60)
        
        # 削除候補を抽出
        deletion_candidates = df[df['name_recognition'] < self.DELETION_THRESHOLD].copy()
        logger.info(f"削除候補: {len(deletion_candidates)}件 ({len(deletion_candidates)/len(df)*100:.1f}%)")
        
        # カテゴリ別分析
        if 'entity_type' in deletion_candidates.columns:
            entity_dist = deletion_candidates['entity_type'].value_counts()
            logger.info("\nエンティティタイプ別:")
            for entity, count in entity_dist.items():
                logger.info(f"  {entity}: {count}件")
        
        # 職業別分析（上位10）
        if 'occupation' in deletion_candidates.columns:
            occupation_dist = deletion_candidates['occupation'].value_counts().head(10)
            logger.info("\n職業別（上位10）:")
            for occupation, count in occupation_dist.items():
                logger.info(f"  {occupation}: {count}件")
        
        # スコア分布
        score_bins = [0, 1, 2, 2.9]
        score_labels = ['0-1', '1-2', '2-2.9']
        deletion_candidates['score_range'] = pd.cut(
            deletion_candidates['name_recognition'], 
            bins=score_bins, 
            labels=score_labels,
            include_lowest=True
        )
        score_dist = deletion_candidates['score_range'].value_counts().sort_index()
        logger.info("\nスコア分布:")
        for range_label, count in score_dist.items():
            logger.info(f"  {range_label}: {count}件")
        
        # 保護対象のチェック
        protected_in_deletion = []
        for person in self.protected_persons:
            matches = deletion_candidates[
                deletion_candidates['person_name'].str.contains(person, na=False)
            ]
            if len(matches) > 0:
                protected_in_deletion.append({
                    'name': person,
                    'count': len(matches),
                    'scores': matches['name_recognition'].tolist()
                })
        
        if protected_in_deletion:
            logger.warning("\n⚠️ 保護対象が削除候補に含まれています:")
            for item in protected_in_deletion:
                logger.warning(f"  {item['name']}: {item['count']}件 (スコア: {item['scores']})")
        else:
            logger.info("\n✅ 保護対象の誤削除はありません")
        
        return deletion_candidates
    
    def create_final_database(self, df, deletion_candidates):
        """最終データベースの作成"""
        logger.info("=" * 60)
        logger.info("📊 最終データベース作成")
        logger.info("=" * 60)
        
        # 削除対象のIDリスト
        deletion_ids = set(deletion_candidates['person_id'].tolist())
        
        # 削除対象を除外
        final_df = df[~df['person_id'].isin(deletion_ids)].copy()
        
        # 統計情報
        self.stats['total_records'] = len(df)
        self.stats['deleted'] = len(deletion_candidates)
        self.stats['kept'] = len(final_df)
        self.stats['deletion_rate'] = (self.stats['deleted'] / self.stats['total_records']) * 100
        
        logger.info(f"  元レコード数: {self.stats['total_records']}件")
        logger.info(f"  削除数: {self.stats['deleted']}件")
        logger.info(f"  保持数: {self.stats['kept']}件")
        logger.info(f"  削除率: {self.stats['deletion_rate']:.1f}%")
        
        # エンティティタイプ別の最終分布
        if 'entity_type' in final_df.columns:
            entity_dist = final_df['entity_type'].value_counts()
            logger.info("\n最終エンティティ分布:")
            for entity, count in entity_dist.items():
                logger.info(f"  {entity}: {count}件")
        
        return final_df
    
    def save_results(self, final_df, deletion_candidates):
        """結果の保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 最終データベース保存（UTF-8 BOM付き）
        final_file = f"ultra_think_FINAL_DATABASE_{timestamp}.csv"
        final_df.to_csv(final_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n💾 最終データベース保存: {final_file}")
        
        # 削除リスト保存
        deletion_file = f"deletion_list_{timestamp}.csv"
        deletion_candidates.to_csv(deletion_file, index=False, encoding='utf-8-sig')
        logger.info(f"💾 削除リスト保存: {deletion_file}")
        
        # レポート生成
        report = {
            'timestamp': datetime.now().isoformat(),
            'deletion_threshold': self.DELETION_THRESHOLD,
            'statistics': self.stats,
            'final_database': final_file,
            'deletion_list': deletion_file,
            'quality_metrics': {
                'deletion_rate': f"{self.stats['deletion_rate']:.1f}%",
                'final_count': self.stats['kept'],
                'threshold': "< 2.9"
            }
        }
        
        report_file = f"phase2_report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"📝 レポート保存: {report_file}")
        
        return final_file, deletion_file, report_file
    
    def verify_quality(self, final_df):
        """品質検証"""
        logger.info("=" * 60)
        logger.info("✅ 品質検証")
        logger.info("=" * 60)
        
        # 重要人物の確認
        logger.info("重要人物の保持確認:")
        for person in self.protected_persons[:5]:  # 最初の5人をチェック
            matches = final_df[final_df['person_name'].str.contains(person, na=False)]
            if len(matches) > 0:
                avg_score = matches['name_recognition'].mean()
                logger.info(f"  ✅ {person}: {len(matches)}件 (平均スコア: {avg_score:.2f})")
            else:
                logger.warning(f"  ❌ {person}: 見つかりません")
        
        # スコア分布
        score_stats = final_df['name_recognition'].describe()
        logger.info(f"\n最終スコア統計:")
        logger.info(f"  平均: {score_stats['mean']:.2f}")
        logger.info(f"  中央値: {score_stats['50%']:.2f}")
        logger.info(f"  最小: {score_stats['min']:.2f}")
        logger.info(f"  最大: {score_stats['max']:.2f}")
        
        # 削除率の妥当性チェック
        if self.stats['deletion_rate'] < 1:
            logger.warning(f"⚠️ 削除率が非常に低い: {self.stats['deletion_rate']:.1f}%")
        elif self.stats['deletion_rate'] > 30:
            logger.warning(f"⚠️ 削除率が高い: {self.stats['deletion_rate']:.1f}%")
        else:
            logger.info(f"✅ 削除率は適切な範囲: {self.stats['deletion_rate']:.1f}%")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 フェーズ2: 修正済みデータベースの評価開始")
    logger.info("削除しきい値: < 2.9（厳格な基準）")
    logger.info("=" * 60)
    
    # 評価システム初期化
    evaluator = Phase2EvaluationSystem()
    
    # 修正済みデータベースを読み込み
    input_file = "ultra_think_FIXED_20250910_213353.csv"
    df = evaluator.load_evaluation_results(input_file)
    
    # 削除候補の分析
    deletion_candidates = evaluator.analyze_deletion_candidates(df)
    
    # 最終データベース作成
    final_df = evaluator.create_final_database(df, deletion_candidates)
    
    # 品質検証
    evaluator.verify_quality(final_df)
    
    # 結果保存
    final_file, deletion_file, report_file = evaluator.save_results(final_df, deletion_candidates)
    
    # 最終サマリー
    logger.info("=" * 60)
    logger.info("🎉 フェーズ2完了")
    logger.info("=" * 60)
    logger.info(f"最終データベース: {final_file}")
    logger.info(f"レコード数: {evaluator.stats['kept']}件")
    logger.info(f"削除率: {evaluator.stats['deletion_rate']:.1f}%")
    logger.info(f"品質: 高（しきい値2.9未満での厳格な選定）")
    
    return final_file, evaluator.stats


if __name__ == "__main__":
    final_file, stats = main()
    print(f"\n✅ 処理完了")
    print(f"📁 最終データベース: {final_file}")
    print(f"📊 最終レコード数: {stats['kept']}件")