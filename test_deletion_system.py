#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知名度ベース統合削除システム - 非対話型テスト
"""

import pandas as pd
from pathlib import Path
from run_deletion_system import DeletionSystemRunner

def test_system_components():
    """システム各コンポーネントの個別テスト"""
    print("=== システム各コンポーネントのテスト ===\n")
    
    # 1. Wikipedia検証システムのテスト
    print("1. Wikipedia検証システムのテスト")
    try:
        from wikipedia_validator_ultimate import WikipediaValidator
        validator = WikipediaValidator()
        
        # テストケース
        test_result = validator.validate_person("タモリ", "森田一義")
        print(f"   タモリのWikipediaスコア: {test_result.validation_score:.2f}")
        print(f"   日本語版存在: {test_result.ja_exists}")
        print("   ✅ Wikipedia検証システム - OK\n")
    except Exception as e:
        print(f"   ❌ Wikipedia検証システム - エラー: {e}\n")
    
    # 2. メタデータ品質スコアリングのテスト
    print("2. メタデータ品質スコアリングのテスト")
    try:
        from metadata_quality_scorer import MetadataQualityScorer
        scorer = MetadataQualityScorer()
        
        test_record = {
            'person_id': 'P007713',
            'person_name': 'タモリ',
            'person_name_ja': '森田一義',
            'category': 'エンターテイメント',
            'nationality': '日本',
            'occupation': 'タレント',
            'name_recognition': 95,
            'episode_text': 'テストエピソード',
            'source': 'Wikipedia'
        }
        
        result = scorer.score_record(test_record)
        print(f"   タモリの品質スコア: {result.overall_quality_score:.2f}")
        print(f"   完全性スコア: {result.completeness_score:.2f}")
        print("   ✅ メタデータ品質スコアリング - OK\n")
    except Exception as e:
        print(f"   ❌ メタデータ品質スコアリング - エラー: {e}\n")
    
    # 3. 統合削除システムのテスト
    print("3. 統合削除システムのテスト")
    try:
        from integrated_deletion_system import IntegratedDeletionSystem
        system = IntegratedDeletionSystem()
        
        test_data = [
            {
                'person_id': 'P007713',
                'person_name': 'タモリ',
                'person_name_ja': '森田一義',
                'category': 'エンターテイメント',
                'nationality': '日本',
                'occupation': 'タレント',
                'name_recognition': 95,
                'episode_text': 'テストエピソード',
                'source': 'Wikipedia'
            },
            {
                'person_id': 'P_TEST_001',
                'person_name': 'テスト人物',
                'person_name_ja': 'テスト人物',
                'category': 'その他',
                'nationality': '不明',
                'occupation': '不明',
                'name_recognition': 0,
                'episode_text': 'テスト',
                'source': 'AI生成'
            }
        ]
        
        results = system.process_batch(test_data, "test_output")
        print(f"   処理件数: {len(results)}")
        
        for person_id, result in results.items():
            print(f"   {result.person_name}: スコア={result.integrated_score:.2f}, 推奨={result.deletion_recommendation}")
        
        print("   ✅ 統合削除システム - OK\n")
    except Exception as e:
        print(f"   ❌ 統合削除システム - エラー: {e}\n")

def test_prerequisites():
    """前提条件チェックのテスト"""
    print("=== 前提条件チェックのテスト ===\n")
    
    runner = DeletionSystemRunner()
    
    if runner.verify_prerequisites():
        print("✅ 前提条件チェック - すべて正常\n")
        return True
    else:
        print("❌ 前提条件チェック - 問題あり\n")
        return False

def test_with_sample_data():
    """サンプルデータでの実際のテスト"""
    print("=== サンプルデータでの実際のテスト ===\n")
    
    try:
        runner = DeletionSystemRunner()
        
        # 最新のデータファイルを検索
        input_file = runner.find_latest_data_file()
        print(f"使用するデータファイル: {input_file}")
        
        # 小規模テスト実行（10件）
        result = runner.run_test_mode(input_file, 10)
        
        print(f"\n=== テスト結果 ===")
        analysis = result['analysis']
        print(f"処理件数: {analysis['total_processed']}")
        print(f"削除率: {analysis['deletion_rate']:.1f}%")
        print(f"平均スコア: {analysis['score_distribution']['mean']:.2f}")
        
        if analysis['top_delete_candidates']:
            print(f"\n削除候補例:")
            for i, candidate in enumerate(analysis['top_delete_candidates'][:3]):
                print(f"  {i+1}. {candidate['person_name']} (スコア: {candidate['score']:.2f})")
                print(f"     理由: {', '.join(candidate['reasons'][:2])}")
        
        print("\n✅ サンプルデータテスト - 完了")
        
    except FileNotFoundError:
        print("❌ データファイルが見つかりません")
    except Exception as e:
        print(f"❌ サンプルデータテスト - エラー: {e}")

def main():
    """メイン実行"""
    print("知名度ベース統合削除システム - 非対話型テスト\n")
    
    # 1. システムコンポーネントのテスト
    test_system_components()
    
    # 2. 前提条件チェック
    if not test_prerequisites():
        return
    
    # 3. 実際のデータでのテスト
    test_with_sample_data()
    
    print("\n" + "="*50)
    print("テスト完了")
    print("="*50)

if __name__ == "__main__":
    main()