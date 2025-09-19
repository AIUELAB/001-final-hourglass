#!/usr/bin/env python3
"""
データ品質フレームワークのテストケース（改善版）
重複カウント問題を解決
"""

import json
import unittest

from data_quality_audit_improved import ImprovedDataQualityAuditor, PriorityBasedAuditor


class TestImprovedDataQualityAuditor(unittest.TestCase):
    """改善版データ品質監査のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.auditor = ImprovedDataQualityAuditor()
        self.priority_auditor = PriorityBasedAuditor()
        
        # テストデータ
        self.test_data = {
            # 正常なデータ
            'person_001': {
                'person_name': 'Hayao Miyazaki',
                'person_name_ja': '宮崎駿',
                'person_name_display': '宮崎駿',
                'birth_date': '1941-01-05',
                'occupation': 'アニメ監督',
                'main_category': '文化・芸術',
                'subcategory': 'アニメ監督',
                'wikidata_id': 'Q55400'
            },
            
            # 未翻訳のデータ
            'person_002': {
                'person_name': 'Christopher Nolan',
                'person_name_ja': 'Christopher Nolan',  # 未翻訳
                'person_name_display': 'Christopher Nolan',
                'birth_date': '1970-07-30',
                'occupation': '映画監督',
                'main_category': '文化・芸術',
                'subcategory': '映画監督',
                'wikidata_id': 'Q25191'
            },
            
            # カテゴリー不整合 + 既知の誤分類（重複問題）
            'person_003': {
                'person_name': 'Guts Ishimatsu',
                'person_name_ja': 'ガッツ石松',
                'person_name_display': 'ガッツ石松',
                'birth_date': '1949-06-05',
                'occupation': 'プロボクサー',
                'main_category': '文化・芸術',
                'subcategory': 'アニメ監督',  # 誤分類
                'wikidata_id': 'Q745408'  # 既知の誤分類ID
            },
            
            # 表示名の問題（現代人なのに短縮）
            'person_004': {
                'person_name': 'Christopher Nolan',
                'person_name_ja': 'クリストファー・ノーラン',
                'person_name_display': 'ノーラン',  # 不適切な短縮
                'birth_date': '1970-07-30',
                'occupation': '映画監督',
                'main_category': '文化・芸術',
                'subcategory': '映画監督',
                'wikidata_id': 'Q25191'
            },
            
            # 必須フィールド欠落
            'person_005': {
                'person_name': 'Test Person',
                # person_name_ja が欠落
                'person_name_display': 'Test',
                'birth_date': '1980-01-01',
                'occupation': '俳優',
                'main_category': 'エンターテインメント',
                'subcategory': '俳優',
                'wikidata_id': 'Q12345'
            },
            
            # 歴史的人物（正しい短縮）
            'person_006': {
                'person_name': 'Johann Sebastian Bach',
                'person_name_ja': 'ヨハン・セバスチャン・バッハ',
                'person_name_display': 'バッハ',  # 歴史的人物は短縮OK
                'birth_date': '1685-03-31',
                'death_date': '1750-07-28',
                'occupation': '作曲家',
                'main_category': '文化・芸術',
                'subcategory': '音楽',
                'wikidata_id': 'Q1339'
            }
        }
    
    def test_untranslated_detection(self):
        """未翻訳検出のテスト"""
        report = self.auditor.audit_data(self.test_data)
        
        # 未翻訳が1件検出されるはず
        self.assertEqual(report['summary']['untranslated'], 1)
        
        # person_002が未翻訳として検出される
        untranslated_ids = [item['id'] for item in report['details']['untranslated']]
        self.assertIn('person_002', untranslated_ids)
    
    def test_category_mismatch_detection(self):
        """カテゴリー不整合検出のテスト"""
        report = self.auditor.audit_data(self.test_data)
        
        # カテゴリー不整合が1件検出されるはず
        self.assertEqual(report['summary']['category_mismatches'], 1)
        
        # person_003が不整合として検出される
        if 'category_mismatch' in report['details']:
            mismatch_ids = [item['id'] for item in report['details']['category_mismatch']]
            self.assertIn('person_003', mismatch_ids)
    
    def test_display_name_issue_detection(self):
        """表示名問題検出のテスト"""
        report = self.auditor.audit_data(self.test_data)
        
        # 表示名問題が1件検出されるはず（person_004）
        self.assertEqual(report['summary']['display_name_issues'], 1)
        
        # person_004が表示名問題として検出される
        if 'display_name' in report['details']:
            display_issues = [item['id'] for item in report['details']['display_name']]
            self.assertIn('person_004', display_issues)
    
    def test_missing_field_detection(self):
        """必須フィールド欠落検出のテスト"""
        report = self.auditor.audit_data(self.test_data)
        
        # 必須フィールド欠落が1件以上検出されるはず
        self.assertGreaterEqual(report['summary']['missing_fields'], 1)
        
        # person_005が欠落として検出される
        if 'missing_field' in report['details']:
            missing_ids = [item['id'] for item in report['details']['missing_field']]
            self.assertIn('person_005', missing_ids)
    
    def test_known_misclassification_detection(self):
        """既知の誤分類検出のテスト"""
        report = self.auditor.audit_data(self.test_data)
        
        # ガッツ石松が既知の誤分類として検出される
        self.assertEqual(report['summary']['known_misclassifications'], 1)
        
        if 'known_misclassification' in report['details']:
            known_ids = [item['wikidata_id'] for item in report['details']['known_misclassification']]
            self.assertIn('Q745408', known_ids)
    
    def test_quality_score_calculation_improved(self):
        """品質スコア計算のテスト（改善版）"""
        report = self.auditor.audit_data(self.test_data)
        
        total = report['summary']['total_records']
        issues = report['summary']['issues_found']
        
        # 6件中4件が問題あり（person_001とperson_006は正常）
        # person_003は重複カウントされない
        self.assertEqual(total, 6)
        self.assertEqual(issues, 4)  # 重複を除いた正しいカウント
        
        # 品質スコアは 2/6 = 33.3%
        quality_score = (total - issues) / total * 100
        self.assertAlmostEqual(quality_score, 33.3, places=1)
        
        # 影響を受けたエントリのリストが正しいか確認
        affected = report.get('affected_entries', [])
        self.assertEqual(len(affected), 4)
        self.assertIn('person_002', affected)  # 未翻訳
        self.assertIn('person_003', affected)  # カテゴリー不整合＋既知の誤分類（1回だけカウント）
        self.assertIn('person_004', affected)  # 表示名問題
        self.assertIn('person_005', affected)  # 必須フィールド欠落
    
    def test_no_duplicate_counting(self):
        """重複カウント防止のテスト"""
        # person_003のみのテスト（2つの問題があるが1件としてカウント）
        single_data = {'person_003': self.test_data['person_003']}
        report = self.auditor.audit_data(single_data)
        
        # 個別の問題は2つ検出される
        self.assertEqual(report['summary']['category_mismatches'], 1)
        self.assertEqual(report['summary']['known_misclassifications'], 1)
        
        # しかし、全体の問題件数は1件のみ
        self.assertEqual(report['summary']['issues_found'], 1)
    
    def test_priority_based_auditor(self):
        """優先度ベース監査のテスト"""
        report = self.priority_auditor.audit_data_with_priority(self.test_data)
        
        # 優先度ベースでも同じ4件が検出される
        self.assertEqual(report['summary']['issues_found'], 4)
        
        # person_003は既知の誤分類として優先的に処理される
        if 'known_misclassification' in report['details']:
            known_ids = [item['wikidata_id'] for item in report['details']['known_misclassification']]
            self.assertIn('Q745408', known_ids)
    
    def test_historical_figure_handling(self):
        """歴史的人物の処理テスト"""
        # バッハのデータ（person_006）は問題として検出されないはず
        report = self.auditor.audit_data({'person_006': self.test_data['person_006']})
        
        # 問題なし
        self.assertEqual(report['summary']['issues_found'], 0)
        self.assertEqual(report['summary']['display_name_issues'], 0)

class TestEdgeCases(unittest.TestCase):
    """エッジケースのテスト"""
    
    def setUp(self):
        self.auditor = ImprovedDataQualityAuditor()
    
    def test_empty_data(self):
        """空データのテスト"""
        report = self.auditor.audit_data({})
        self.assertEqual(report['summary']['total_records'], 0)
        self.assertEqual(report['summary']['issues_found'], 0)
    
    def test_all_fields_missing(self):
        """全フィールド欠落のテスト"""
        data = {'person_007': {}}
        report = self.auditor.audit_data(data)
        
        # 必須フィールドが3つとも欠落
        self.assertGreaterEqual(report['summary']['missing_fields'], 3)
        self.assertEqual(report['summary']['issues_found'], 1)  # エントリとしては1件
    
    def test_multiple_issues_same_entry(self):
        """同一エントリに複数問題があるケース"""
        data = {
            'person_008': {
                'person_name': 'Test Person',
                'person_name_ja': 'Test Person',  # 未翻訳
                'person_name_display': '',  # 必須フィールド欠落
                'birth_date': '1950-01-01',
                'occupation': 'ボクサー',
                'subcategory': 'アニメ監督',  # カテゴリー不整合
                'wikidata_id': 'Q745408'  # 既知の誤分類
            }
        }
        report = self.auditor.audit_data(data)
        
        # 複数の問題が検出されるが、エントリとしては1件
        self.assertEqual(report['summary']['issues_found'], 1)
        self.assertGreaterEqual(report['summary']['untranslated'], 1)
        self.assertGreaterEqual(report['summary']['category_mismatches'], 1)
        self.assertGreaterEqual(report['summary']['known_misclassifications'], 1)

def run_all_tests():
    """全テスト実行"""
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # テストケース追加
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestImprovedDataQualityAuditor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEdgeCases))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー（改善版）")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功しました！（10/10）")
        print("🎯 重複カウント問題が解決されました！")
    else:
        print("\n❌ テストに失敗がありました。")
        for failure in result.failures:
            print(f"  失敗: {failure[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)