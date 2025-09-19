#!/usr/bin/env python3
"""
最適化システムのテスト実行
テストデータで4日目標の実現可能性を検証
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_optimized_system():
    """最適化システムのテスト"""
    
    # Create test data
    test_data = pd.DataFrame([
        # Ultra famous (should be quickly identified by ML)
        {"person_id": "P001", "person_name": "HIKAKIN", "person_name_ja": "ヒカキン", 
         "category": "YouTuber", "birth_year": 1989},
        {"person_id": "P002", "person_name": "Yonezu Kenshi", "person_name_ja": "米津玄師", 
         "category": "歌手", "birth_year": 1991},
        {"person_id": "P003", "person_name": "Ohtani Shohei", "person_name_ja": "大谷翔平", 
         "category": "野球選手", "birth_year": 1994},
        
        # Fictional characters (protected)
        {"person_id": "P004", "person_name": "Doraemon", "person_name_ja": "ドラえもん", 
         "category": "架空", "birth_year": None},
        {"person_id": "P005", "person_name": "Son Goku", "person_name_ja": "孫悟空", 
         "category": "架空", "birth_year": None},
        
        # Medium famous
        {"person_id": "P006", "person_name": "Suda Masaki", "person_name_ja": "菅田将暉", 
         "category": "俳優", "birth_year": 1993},
        {"person_id": "P007", "person_name": "Aimyon", "person_name_ja": "あいみょん", 
         "category": "歌手", "birth_year": 1995},
        
        # Less famous
        {"person_id": "P008", "person_name": "Tanaka Taro", "person_name_ja": "田中太郎", 
         "category": None, "birth_year": None},
        {"person_id": "P009", "person_name": "Test User", "person_name_ja": "テストユーザー", 
         "category": None, "birth_year": None},
        
        # Politicians (News priority)
        {"person_id": "P010", "person_name": "Kishida Fumio", "person_name_ja": "岸田文雄", 
         "category": "政治家", "birth_year": 1957},
    ])
    
    # Save test data
    test_csv = "test_data_optimized.csv"
    test_data.to_csv(test_csv, index=False, encoding='utf-8-sig')
    logger.info(f"✅ テストデータ作成: {len(test_data)}件")
    
    # Import optimized system
    from optimized_recognition_system import OptimizedRecognitionSystem
    
    # Initialize system in test mode
    system = OptimizedRecognitionSystem(test_mode=True)
    
    print("\n" + "=" * 70)
    print("🧪 最適化システムテスト開始")
    print("=" * 70)
    print(f"テストデータ: {len(test_data)}件")
    print("期待される最適化:")
    print("  - HIKAKIN, 米津玄師, 大谷翔平: ML判定でAPI不要")
    print("  - ドラえもん, 孫悟空: 架空キャラ保護でAPI不要")
    print("  - 田中太郎, テストユーザー: 一般人判定で簡易評価")
    print("  - その他: 階層評価で適切なAPI選択")
    print("=" * 70)
    
    # Run test
    try:
        output_csv = f"test_optimized_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        result_df = await system.process_database(
            csv_path=test_csv,
            output_path=output_csv
        )
        
        # Display results
        print("\n📊 テスト結果:")
        print("=" * 70)
        
        for _, row in result_df.iterrows():
            name = row['person_name_ja']
            score = row.get('final_score', 'N/A')
            skip = row.get('skip_api', False)
            ml_score = row.get('ml_score', 'N/A')
            
            status = "🚫 API不要" if skip else "✅ API実行"
            print(f"{status} {name}: 最終スコア={score}, ML予測={ml_score}")
        
        # Verify optimization metrics
        if system.metrics:
            print(f"\n📈 最適化メトリクス:")
            print(f"  API削減率: {system.metrics.api_reduction_rate:.1f}%")
            print(f"  キャッシュヒット率: {system.metrics.cache_hit_rate:.1f}%")
            print(f"  並列化高速化: {system.metrics.parallel_speedup:.1f}x")
            print(f"  実行時間: {system.metrics.actual_time_hours*3600:.1f}秒")
        
        # Extrapolate to full database
        full_records = 4702
        if system.metrics and system.metrics.actual_time_hours > 0:
            scale_factor = full_records / len(test_data)
            estimated_full_time = system.metrics.actual_time_hours * scale_factor
            
            print(f"\n🎯 フルデータベース推定:")
            print(f"  レコード数: {full_records}件")
            print(f"  推定時間: {estimated_full_time:.1f}時間 ({estimated_full_time/24:.1f}日)")
            
            if estimated_full_time/24 <= 4:
                print("  ✅ 4日目標達成可能！")
            else:
                print(f"  ⚠️ 追加最適化が必要（目標まで{(estimated_full_time/24 - 4):.1f}日超過）")
        
        print("=" * 70)
        print("✅ テスト完了")
        
        return result_df
        
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_optimized_system())