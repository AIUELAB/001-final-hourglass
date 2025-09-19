#!/usr/bin/env python3
"""
高度な分析とレポート生成
知名度評価システムの詳細分析
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path
from collections import Counter
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """高度な分析クラス"""
    
    def __init__(self):
        self.results = {}
        self.csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
        self.evaluation_results_path = None
        
    def load_data(self):
        """データ読み込み"""
        if Path(self.csv_path).exists():
            self.df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
            logger.info(f"✅ データ読み込み完了: {len(self.df)}件")
            return True
        else:
            logger.error(f"❌ ファイルが見つかりません: {self.csv_path}")
            return False
    
    def analyze_data_quality(self):
        """データ品質分析"""
        logger.info("📊 データ品質分析開始")
        
        quality_metrics = {
            'total_records': len(self.df),
            'columns': list(self.df.columns),
            'missing_values': {},
            'data_types': {},
            'unique_counts': {}
        }
        
        # Missing values analysis
        for col in self.df.columns:
            missing_count = self.df[col].isna().sum()
            if missing_count > 0:
                quality_metrics['missing_values'][col] = {
                    'count': int(missing_count),
                    'percentage': float((missing_count / len(self.df)) * 100)
                }
        
        # Data types
        for col in self.df.columns:
            quality_metrics['data_types'][col] = str(self.df[col].dtype)
        
        # Unique values for key columns
        key_columns = ['person_id', 'category', 'nationality', 'occupation']
        for col in key_columns:
            if col in self.df.columns:
                quality_metrics['unique_counts'][col] = int(self.df[col].nunique())
        
        self.results['data_quality'] = quality_metrics
        
        logger.info(f"  総レコード: {quality_metrics['total_records']}")
        logger.info(f"  カラム数: {len(quality_metrics['columns'])}")
        logger.info(f"  欠損値のあるカラム: {len(quality_metrics['missing_values'])}")
        
        return quality_metrics
    
    def analyze_category_distribution(self):
        """カテゴリ分布分析"""
        logger.info("📊 カテゴリ分布分析開始")
        
        if 'category' not in self.df.columns:
            logger.warning("カテゴリカラムが見つかりません")
            return None
        
        category_dist = self.df['category'].value_counts().to_dict()
        
        # Calculate percentages
        total = sum(category_dist.values())
        category_analysis = {
            'distribution': {},
            'top_5': {},
            'total_categories': len(category_dist)
        }
        
        for category, count in category_dist.items():
            category_analysis['distribution'][str(category)] = {
                'count': int(count),
                'percentage': float((count / total) * 100)
            }
        
        # Top 5 categories
        top_5 = dict(list(category_dist.items())[:5])
        for category, count in top_5.items():
            category_analysis['top_5'][str(category)] = {
                'count': int(count),
                'percentage': float((count / total) * 100)
            }
        
        self.results['category_analysis'] = category_analysis
        
        logger.info(f"  カテゴリ総数: {category_analysis['total_categories']}")
        logger.info(f"  上位カテゴリ: {list(category_analysis['top_5'].keys())}")
        
        return category_analysis
    
    def analyze_ml_candidates(self):
        """ML判定候補の分析"""
        logger.info("📊 ML判定候補の分析開始")
        
        ml_patterns = {
            'ultra_famous': [
                'HIKAKIN', '米津玄師', '大谷翔平', '嵐', '新垣結衣',
                'イチロー', '羽生結弦', '錦織圭', '本田圭佑', '香川真司'
            ],
            'fictional_protected': [
                'ドラえもん', '孫悟空', 'ピカチュウ', 'ルフィ', 'ナルト',
                'エヴァンゲリオン', 'セーラームーン', 'アンパンマン',
                '竈門炭治郎', 'サザエさん'
            ],
            'general_patterns': [
                'test', 'テスト', '山田太郎', '田中', 'sample'
            ]
        }
        
        ml_candidates = {
            'ultra_famous': [],
            'fictional_protected': [],
            'general_patterns': [],
            'total_ml_candidates': 0
        }
        
        # Check each pattern
        for idx, row in self.df.iterrows():
            person_name = str(row.get('person_name_ja', row.get('person_name', '')))
            
            for category, patterns in ml_patterns.items():
                if any(pattern in person_name for pattern in patterns):
                    ml_candidates[category].append({
                        'person_id': row.get('person_id'),
                        'name': person_name
                    })
                    break
        
        # Count totals
        for category in ['ultra_famous', 'fictional_protected', 'general_patterns']:
            ml_candidates[f'{category}_count'] = len(ml_candidates[category])
            ml_candidates['total_ml_candidates'] += len(ml_candidates[category])
        
        ml_candidates['ml_skip_rate'] = (ml_candidates['total_ml_candidates'] / len(self.df)) * 100
        
        self.results['ml_analysis'] = ml_candidates
        
        logger.info(f"  ML判定候補総数: {ml_candidates['total_ml_candidates']}")
        logger.info(f"  ML判定率: {ml_candidates['ml_skip_rate']:.1f}%")
        logger.info(f"  超有名人: {ml_candidates['ultra_famous_count']}件")
        logger.info(f"  架空キャラ: {ml_candidates['fictional_protected_count']}件")
        
        return ml_candidates
    
    def analyze_optimization_impact(self):
        """最適化の影響分析"""
        logger.info("📊 最適化影響分析開始")
        
        total_records = len(self.df)
        
        # Optimization parameters
        ml_skip_rate = 0.35
        cache_hit_rate = 0.15
        parallel_workers = 5
        
        # Calculate impact
        optimization_impact = {
            'baseline': {
                'total_api_calls': total_records * 5,  # 5 APIs per record
                'estimated_time_hours': (total_records * 5 * 30) / 3600,  # 30s per API
                'estimated_time_days': (total_records * 5 * 30) / (3600 * 24)
            },
            'optimized': {
                'ml_filtered': int(total_records * ml_skip_rate),
                'cache_hits': int(total_records * cache_hit_rate),
                'api_calls_needed': int(total_records * (1 - ml_skip_rate) * (1 - cache_hit_rate)),
                'parallel_speedup': parallel_workers,
                'estimated_time_hours': 0,
                'estimated_time_days': 0
            },
            'improvement': {}
        }
        
        # Calculate optimized time
        api_calls = optimization_impact['optimized']['api_calls_needed']
        # Tiered evaluation
        tier1 = api_calls * 0.4 * 2  # 40% tier 1, 2 APIs
        tier2 = api_calls * 0.4 * 3  # 40% tier 2, 3 APIs
        tier3 = api_calls * 0.2 * 5  # 20% tier 3, 5 APIs
        total_api_calls = tier1 + tier2 + tier3
        
        # Time estimation (0.5 seconds per API with parallel processing)
        optimized_time_seconds = (total_api_calls * 0.5) / parallel_workers
        optimization_impact['optimized']['estimated_time_hours'] = optimized_time_seconds / 3600
        optimization_impact['optimized']['estimated_time_days'] = optimized_time_seconds / (3600 * 24)
        optimization_impact['optimized']['total_api_calls'] = int(total_api_calls)
        
        # Calculate improvement
        baseline_time = optimization_impact['baseline']['estimated_time_hours']
        optimized_time = optimization_impact['optimized']['estimated_time_hours']
        
        optimization_impact['improvement'] = {
            'time_reduction_hours': baseline_time - optimized_time,
            'time_reduction_percentage': ((baseline_time - optimized_time) / baseline_time) * 100,
            'speedup_factor': baseline_time / optimized_time if optimized_time > 0 else 0,
            'api_call_reduction': optimization_impact['baseline']['total_api_calls'] - optimization_impact['optimized']['total_api_calls'],
            'api_call_reduction_percentage': ((optimization_impact['baseline']['total_api_calls'] - optimization_impact['optimized']['total_api_calls']) / optimization_impact['baseline']['total_api_calls']) * 100
        }
        
        self.results['optimization_impact'] = optimization_impact
        
        logger.info(f"  ベースライン時間: {baseline_time:.1f}時間")
        logger.info(f"  最適化後時間: {optimized_time:.1f}時間")
        logger.info(f"  高速化率: {optimization_impact['improvement']['speedup_factor']:.0f}倍")
        logger.info(f"  API削減率: {optimization_impact['improvement']['api_call_reduction_percentage']:.1f}%")
        
        return optimization_impact
    
    def generate_comprehensive_report(self):
        """包括的レポート生成"""
        print("\n" + "=" * 80)
        print("📊 知名度評価システム - 高度な分析レポート")
        print("=" * 80)
        print(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Data Quality
        if 'data_quality' in self.results:
            dq = self.results['data_quality']
            print(f"\n📈 データ品質:")
            print(f"  総レコード数: {dq['total_records']:,}")
            print(f"  カラム数: {len(dq['columns'])}")
            print(f"  欠損値のあるカラム: {len(dq['missing_values'])}")
            
            if dq['missing_values']:
                print(f"\n  主な欠損値:")
                for col, info in list(dq['missing_values'].items())[:5]:
                    print(f"    {col}: {info['count']}件 ({info['percentage']:.1f}%)")
        
        # Category Distribution
        if 'category_analysis' in self.results:
            ca = self.results['category_analysis']
            print(f"\n📊 カテゴリ分布:")
            print(f"  総カテゴリ数: {ca['total_categories']}")
            print(f"\n  上位5カテゴリ:")
            for category, info in ca['top_5'].items():
                print(f"    {category}: {info['count']}件 ({info['percentage']:.1f}%)")
        
        # ML Analysis
        if 'ml_analysis' in self.results:
            ml = self.results['ml_analysis']
            print(f"\n🤖 ML判定分析:")
            print(f"  ML判定候補: {ml['total_ml_candidates']}件")
            print(f"  ML判定率: {ml['ml_skip_rate']:.1f}%")
            print(f"  内訳:")
            print(f"    超有名人: {ml['ultra_famous_count']}件")
            print(f"    架空キャラ: {ml['fictional_protected_count']}件")
            print(f"    一般パターン: {ml['general_patterns_count']}件")
        
        # Optimization Impact
        if 'optimization_impact' in self.results:
            oi = self.results['optimization_impact']
            print(f"\n⚡ 最適化効果:")
            print(f"  ベースライン:")
            print(f"    処理時間: {oi['baseline']['estimated_time_days']:.1f}日")
            print(f"    API呼び出し: {oi['baseline']['total_api_calls']:,}回")
            print(f"\n  最適化後:")
            print(f"    処理時間: {oi['optimized']['estimated_time_days']:.3f}日")
            print(f"    API呼び出し: {oi['optimized']['total_api_calls']:,}回")
            print(f"\n  改善効果:")
            print(f"    高速化: {oi['improvement']['speedup_factor']:.0f}倍")
            print(f"    時間削減: {oi['improvement']['time_reduction_percentage']:.1f}%")
            print(f"    API削減: {oi['improvement']['api_call_reduction_percentage']:.1f}%")
        
        print("\n" + "=" * 80)
    
    def save_results(self, filename='advanced_analytics.json'):
        """結果を保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            # Convert any non-serializable objects
            serializable_results = {}
            for key, value in self.results.items():
                try:
                    json.dumps(value)
                    serializable_results[key] = value
                except:
                    serializable_results[key] = str(value)
            
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 分析結果を保存: {filename}")


def main():
    """メイン実行"""
    analytics = AdvancedAnalytics()
    
    # Load data
    if not analytics.load_data():
        return
    
    # Run analyses
    analytics.analyze_data_quality()
    analytics.analyze_category_distribution()
    analytics.analyze_ml_candidates()
    analytics.analyze_optimization_impact()
    
    # Generate report
    analytics.generate_comprehensive_report()
    
    # Save results
    analytics.save_results()
    
    return analytics.results


if __name__ == "__main__":
    results = main()