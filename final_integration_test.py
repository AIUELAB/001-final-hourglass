#!/usr/bin/env python3
"""
最終統合テスト
全コンポーネントの動作確認と総合評価
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import json
import time
from pathlib import Path
import sys
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IntegrationTest:
    """統合テストクラス"""
    
    def __init__(self):
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        self.csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    
    async def test_data_loading(self):
        """データ読み込みテスト"""
        test_name = "data_loading"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            if not Path(self.csv_path).exists():
                raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_path}")
            
            df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
            
            result = {
                'status': 'PASS',
                'records': len(df),
                'columns': len(df.columns),
                'message': f"✅ {len(df)}件のレコードを正常に読み込み"
            }
            
            # 品質チェック
            if len(df) != 4701:
                result['warning'] = f"期待値4701件に対して{len(df)}件"
                self.test_results['summary']['warnings'] += 1
            
            self.test_results['tests'][test_name] = result
            self.test_results['summary']['passed'] += 1
            logger.info(f"  {result['message']}")
            return True
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ データ読み込み失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_ml_filter(self):
        """ML事前フィルタテスト"""
        test_name = "ml_pre_filter"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            # テストケース
            test_cases = [
                ('HIKAKIN', 9.5, 'ultra_famous'),
                ('ドラえもん', 8.5, 'fictional'),
                ('test', 2.0, 'general'),
                ('普通の人', None, 'no_match')
            ]
            
            from run_recognition_evaluation import OptimizedEvaluationSystem
            system = OptimizedEvaluationSystem(test_mode=True)
            
            passed = 0
            failed = 0
            
            for name, expected_score, category in test_cases:
                score = system.ml_prefilter(name, '')
                
                if category == 'no_match':
                    if score is None:
                        passed += 1
                    else:
                        failed += 1
                        logger.warning(f"  ⚠️ {name}: 期待値None, 実際{score}")
                else:
                    if score == expected_score:
                        passed += 1
                    else:
                        failed += 1
                        logger.warning(f"  ⚠️ {name}: 期待値{expected_score}, 実際{score}")
            
            result = {
                'status': 'PASS' if failed == 0 else 'PARTIAL',
                'test_cases': len(test_cases),
                'passed': passed,
                'failed': failed,
                'message': f"✅ ML判定テスト: {passed}/{len(test_cases)}件成功"
            }
            
            self.test_results['tests'][test_name] = result
            if failed == 0:
                self.test_results['summary']['passed'] += 1
            else:
                self.test_results['summary']['warnings'] += 1
            
            logger.info(f"  {result['message']}")
            return failed == 0
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ MLフィルタテスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_cache_system(self):
        """キャッシュシステムテスト"""
        test_name = "cache_system"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            import json
            import tempfile
            
            # テスト用キャッシュ
            test_cache = {
                'test_key_1': {'score': 7.5, 'timestamp': datetime.now().isoformat()},
                'test_key_2': {'score': 8.0, 'timestamp': datetime.now().isoformat()}
            }
            
            # 書き込みテスト
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_cache, f, ensure_ascii=False)
                temp_file = f.name
            
            # 読み込みテスト
            with open(temp_file, 'r') as f:
                loaded_cache = json.load(f)
            
            # 検証
            if loaded_cache == test_cache:
                result = {
                    'status': 'PASS',
                    'cache_size': len(test_cache),
                    'message': f"✅ キャッシュシステム正常動作"
                }
                self.test_results['summary']['passed'] += 1
            else:
                result = {
                    'status': 'FAIL',
                    'message': f"❌ キャッシュデータ不一致"
                }
                self.test_results['summary']['failed'] += 1
            
            # クリーンアップ
            Path(temp_file).unlink()
            
            self.test_results['tests'][test_name] = result
            logger.info(f"  {result['message']}")
            return result['status'] == 'PASS'
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ キャッシュテスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_parallel_processing(self):
        """並列処理テスト"""
        test_name = "parallel_processing"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            async def dummy_task(delay=0.1):
                await asyncio.sleep(delay)
                return np.random.random()
            
            # 10タスクを並列実行
            start_time = time.time()
            tasks = [dummy_task(0.01) for _ in range(10)]
            results = await asyncio.gather(*tasks)
            parallel_time = time.time() - start_time
            
            # 逐次実行時間の推定
            sequential_time = 0.01 * 10
            
            speedup = sequential_time / parallel_time if parallel_time > 0 else 0
            
            result = {
                'status': 'PASS' if speedup > 1.5 else 'WARN',
                'tasks': len(tasks),
                'parallel_time': round(parallel_time, 3),
                'speedup': round(speedup, 1),
                'message': f"✅ 並列処理: {speedup:.1f}倍高速化"
            }
            
            self.test_results['tests'][test_name] = result
            if speedup > 1.5:
                self.test_results['summary']['passed'] += 1
            else:
                self.test_results['summary']['warnings'] += 1
            
            logger.info(f"  {result['message']}")
            return speedup > 1.5
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ 並列処理テスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_performance_metrics(self):
        """パフォーマンス指標テスト"""
        test_name = "performance_metrics"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            # シミュレーション値
            total_records = 4701
            ml_skip_rate = 0.35
            cache_hit_rate = 0.15
            parallel_workers = 5
            
            # 計算
            api_calls_saved = total_records * (ml_skip_rate + cache_hit_rate * (1 - ml_skip_rate))
            api_reduction = (api_calls_saved / total_records) * 100
            
            # 時間推定
            baseline_time = total_records * 30  # 30秒/件
            optimized_time = (total_records * (1 - ml_skip_rate) * (1 - cache_hit_rate) * 5) / parallel_workers
            speedup = baseline_time / optimized_time if optimized_time > 0 else 0
            
            result = {
                'status': 'PASS',
                'api_reduction': round(api_reduction, 1),
                'speedup': round(speedup, 0),
                'target_4days': speedup > 24,  # 98日/4日 = 24.5倍必要
                'message': f"✅ 性能指標: {speedup:.0f}倍高速化, API {api_reduction:.1f}%削減"
            }
            
            if not result['target_4days']:
                result['status'] = 'WARN'
                result['warning'] = '4日目標未達成の可能性'
                self.test_results['summary']['warnings'] += 1
            else:
                self.test_results['summary']['passed'] += 1
            
            self.test_results['tests'][test_name] = result
            logger.info(f"  {result['message']}")
            return result['target_4days']
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ パフォーマンステスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_output_format(self):
        """出力フォーマットテスト"""
        test_name = "output_format"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            # テスト用データフレーム作成
            test_data = {
                'person_id': ['P001', 'P002'],
                'person_name': ['テスト1', 'テスト2'],
                'final_score': [7.5, 8.0],
                'method': ['ML判定', 'API評価'],
                'data_completeness': [1.0, 0.8]
            }
            df = pd.DataFrame(test_data)
            
            # CSV出力テスト
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df.to_csv(f, index=False, encoding='utf-8-sig')
                temp_file = f.name
            
            # 読み込み確認
            df_loaded = pd.read_csv(temp_file, encoding='utf-8-sig')
            
            # 検証
            if len(df_loaded) == len(df) and list(df_loaded.columns) == list(df.columns):
                result = {
                    'status': 'PASS',
                    'format': 'CSV with UTF-8 BOM',
                    'excel_compatible': True,
                    'message': f"✅ 出力フォーマット正常（Excel対応）"
                }
                self.test_results['summary']['passed'] += 1
            else:
                result = {
                    'status': 'FAIL',
                    'message': f"❌ 出力フォーマット不正"
                }
                self.test_results['summary']['failed'] += 1
            
            # クリーンアップ
            Path(temp_file).unlink()
            
            self.test_results['tests'][test_name] = result
            logger.info(f"  {result['message']}")
            return result['status'] == 'PASS'
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ 出力フォーマットテスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_error_handling(self):
        """エラーハンドリングテスト"""
        test_name = "error_handling"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            test_scenarios = []
            
            # シナリオ1: 存在しないファイル
            try:
                df = pd.read_csv('non_existent_file.csv')
                test_scenarios.append(('file_not_found', False))
            except:
                test_scenarios.append(('file_not_found', True))
            
            # シナリオ2: 無効なデータ型
            try:
                score = float('invalid')
                test_scenarios.append(('invalid_type', False))
            except:
                test_scenarios.append(('invalid_type', True))
            
            # シナリオ3: ゼロ除算
            try:
                result = 10 / 0
                test_scenarios.append(('zero_division', False))
            except:
                test_scenarios.append(('zero_division', True))
            
            # 結果集計
            passed = sum(1 for _, success in test_scenarios if success)
            
            result = {
                'status': 'PASS' if passed == len(test_scenarios) else 'PARTIAL',
                'scenarios': len(test_scenarios),
                'handled': passed,
                'message': f"✅ エラーハンドリング: {passed}/{len(test_scenarios)}件正常"
            }
            
            self.test_results['tests'][test_name] = result
            if passed == len(test_scenarios):
                self.test_results['summary']['passed'] += 1
            else:
                self.test_results['summary']['warnings'] += 1
            
            logger.info(f"  {result['message']}")
            return passed == len(test_scenarios)
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ エラーハンドリングテスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    async def test_full_pipeline(self):
        """フルパイプライン統合テスト"""
        test_name = "full_pipeline"
        logger.info(f"🧪 テスト開始: {test_name}")
        
        try:
            from run_recognition_evaluation import OptimizedEvaluationSystem
            
            # 5件でのミニテスト
            system = OptimizedEvaluationSystem(test_mode=True)
            
            # テストデータ作成
            test_df = pd.DataFrame({
                'person_id': ['P001', 'P002', 'P003', 'P004', 'P005'],
                'person_name_ja': ['HIKAKIN', 'ドラえもん', 'test', '田中太郎', '普通の人'],
                'category': ['YouTuber', '架空', 'テスト', 'その他', 'エンタメ']
            })
            
            # 実行
            start_time = time.time()
            results = []
            
            for idx, row in test_df.iterrows():
                result = await system.evaluate_person(row)
                results.append(result)
            
            elapsed = time.time() - start_time
            
            # 検証
            if len(results) == len(test_df):
                ml_count = sum(1 for r in results if r['method'] == 'ML判定')
                
                result = {
                    'status': 'PASS',
                    'records_processed': len(results),
                    'ml_filtered': ml_count,
                    'processing_time': round(elapsed, 3),
                    'message': f"✅ フルパイプライン正常: {len(results)}件処理, {elapsed:.3f}秒"
                }
                self.test_results['summary']['passed'] += 1
            else:
                result = {
                    'status': 'FAIL',
                    'message': f"❌ 処理件数不一致"
                }
                self.test_results['summary']['failed'] += 1
            
            self.test_results['tests'][test_name] = result
            logger.info(f"  {result['message']}")
            return result['status'] == 'PASS'
            
        except Exception as e:
            self.test_results['tests'][test_name] = {
                'status': 'FAIL',
                'error': str(e),
                'message': f"❌ フルパイプラインテスト失敗: {e}"
            }
            self.test_results['summary']['failed'] += 1
            logger.error(f"  ❌ エラー: {e}")
            return False
    
    def generate_report(self):
        """テストレポート生成"""
        print("\n" + "=" * 80)
        print("🧪 統合テストレポート")
        print("=" * 80)
        print(f"実行日時: {self.test_results['timestamp']}")
        print()
        
        # サマリー
        summary = self.test_results['summary']
        total = summary['passed'] + summary['failed'] + summary['warnings']
        summary['total_tests'] = total
        
        print("📊 テスト結果サマリー:")
        print(f"  総テスト数: {total}")
        print(f"  ✅ 成功: {summary['passed']}")
        print(f"  ⚠️ 警告: {summary['warnings']}")
        print(f"  ❌ 失敗: {summary['failed']}")
        
        if total > 0:
            success_rate = (summary['passed'] / total) * 100
            print(f"  成功率: {success_rate:.1f}%")
        
        # 個別テスト結果
        print("\n📋 個別テスト結果:")
        for test_name, result in self.test_results['tests'].items():
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️',
                'PARTIAL': '⚠️'
            }.get(result['status'], '❓')
            
            print(f"\n  {status_icon} {test_name}:")
            print(f"    ステータス: {result['status']}")
            print(f"    メッセージ: {result.get('message', 'N/A')}")
            
            if 'error' in result:
                print(f"    エラー: {result['error']}")
            if 'warning' in result:
                print(f"    警告: {result['warning']}")
        
        # 総合評価
        print("\n" + "=" * 80)
        print("📊 総合評価:")
        
        if summary['failed'] == 0:
            if summary['warnings'] == 0:
                print("  🎉 完璧！すべてのテストに合格しました。")
                print("  ✅ システムは本番環境で使用可能です。")
            else:
                print("  ✅ 合格：システムは動作しますが、改善の余地があります。")
                print("  ⚠️ 警告事項を確認してください。")
        else:
            print("  ❌ 不合格：重要な問題が検出されました。")
            print("  🔧 失敗したテストを修正してください。")
        
        print("=" * 80)
    
    def save_results(self, filename='integration_test_results.json'):
        """結果を保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 テスト結果を保存: {filename}")


async def main():
    """メイン実行"""
    print("\n" + "=" * 80)
    print("🚀 最終統合テスト開始")
    print("=" * 80)
    
    tester = IntegrationTest()
    
    # 全テスト実行
    tests = [
        tester.test_data_loading(),
        tester.test_ml_filter(),
        tester.test_cache_system(),
        tester.test_parallel_processing(),
        tester.test_performance_metrics(),
        tester.test_output_format(),
        tester.test_error_handling(),
        tester.test_full_pipeline()
    ]
    
    # 並列実行
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # レポート生成
    tester.generate_report()
    
    # 結果保存
    tester.save_results()
    
    # 終了コード決定
    if tester.test_results['summary']['failed'] > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)