#!/usr/bin/env python3
"""
Ultimate Recognition System - 統合テストスイート
Comprehensive Test Suite for 96% Accuracy Validation

HIKAKINケースを含む包括的なテストで、システムの精度を検証
"""

import os
import sys
import json
from typing import Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

# 環境設定
load_dotenv()

# システムインポート
from ultimate_recognition_system import UltimateRecognitionSystem, PersonData, DeleteAction

# カラー出力用
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


class RecognitionSystemTester:
    """統合システムの包括的テスト"""
    
    def __init__(self):
        self.system = UltimateRecognitionSystem()
        self.test_results = []
        self.accuracy_metrics = {
            'true_positive': 0,  # 有名人を正しく保護
            'true_negative': 0,  # 非有名人を正しく削除対象
            'false_positive': 0,  # 非有名人を誤って保護
            'false_negative': 0   # 有名人を誤って削除対象
        }
    
    def create_test_cases(self) -> List[Dict]:
        """テストケース定義"""
        return [
            # ===== 絶対に保護すべき有名人 =====
            {
                'person_id': 'P000013',
                'name': 'HIKAKIN',
                'name_ja': 'ヒカキン',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/HIKAKIN',
                'category': 'YouTuber',
                'occupation': 'YouTuber/実業家',
                'birth_year': 1989,
                'expected': 'KEEP',
                'reason': '日本最大級のYouTuber、1000万人以上の登録者'
            },
            {
                'person_id': 'P000001',
                'name': '大谷翔平',
                'name_ja': '大谷翔平',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/大谷翔平',
                'category': 'スポーツ選手',
                'occupation': 'プロ野球選手',
                'birth_year': 1994,
                'expected': 'KEEP',
                'reason': 'MLB二刀流スーパースター'
            },
            {
                'person_id': 'P000002',
                'name': '安倍晋三',
                'name_ja': '安倍晋三',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/安倍晋三',
                'category': '政治家',
                'occupation': '元内閣総理大臣',
                'birth_year': 1954,
                'expected': 'KEEP',
                'reason': '日本最長期政権の元首相'
            },
            
            # ===== 架空キャラクター（文化的重要性） =====
            {
                'person_id': 'P100001',
                'name': '竈門炭治郎',
                'name_ja': '竈門炭治郎',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/竈門炭治郎',
                'category': '架空キャラクター',
                'occupation': '鬼滅の刃主人公',
                'birth_year': None,
                'expected': 'KEEP',
                'reason': '鬼滅の刃の主人公、社会現象級の人気'
            },
            {
                'person_id': 'P100002',
                'name': '孫悟空',
                'name_ja': '孫悟空',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/孫悟空_(ドラゴンボール)',
                'category': '架空キャラクター',
                'occupation': 'ドラゴンボール主人公',
                'birth_year': None,
                'expected': 'KEEP',
                'reason': 'ドラゴンボールの主人公、世界的人気'
            },
            
            # ===== 教科書掲載人物 =====
            {
                'person_id': 'P200001',
                'name': '織田信長',
                'name_ja': '織田信長',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/織田信長',
                'category': '歴史人物',
                'occupation': '戦国武将',
                'birth_year': 1534,
                'expected': 'KEEP',
                'reason': '日本史教科書の必須人物'
            },
            {
                'person_id': 'P200002',
                'name': '夏目漱石',
                'name_ja': '夏目漱石',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/夏目漱石',
                'category': '作家',
                'occupation': '小説家',
                'birth_year': 1867,
                'expected': 'KEEP',
                'reason': '国語教科書の定番作家'
            },
            
            # ===== 削除対象（知名度低） =====
            {
                'person_id': 'P900001',
                'name': 'テスト太郎',
                'name_ja': 'テスト太郎',
                'wikipedia_url': None,
                'category': None,
                'occupation': None,
                'birth_year': 1990,
                'expected': 'DELETE',
                'reason': 'Wikipedia無し、検索結果極少の架空人物'
            },
            {
                'person_id': 'P900002',
                'name': '架空研究者',
                'name_ja': '架空研究者',
                'wikipedia_url': None,
                'category': '研究者',
                'occupation': '研究者',
                'birth_year': 1980,
                'expected': 'DELETE',
                'reason': '存在しない研究者'
            },
            
            # ===== 境界線ケース =====
            {
                'person_id': 'P500001',
                'name': 'はじめしゃちょー',
                'name_ja': 'はじめしゃちょー',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/はじめしゃちょー',
                'category': 'YouTuber',
                'occupation': 'YouTuber',
                'birth_year': 1993,
                'expected': 'KEEP',
                'reason': 'トップYouTuber、1000万人登録者'
            },
            {
                'person_id': 'P500002',
                'name': 'フワちゃん',
                'name_ja': 'フワちゃん',
                'wikipedia_url': 'https://ja.wikipedia.org/wiki/フワちゃん',
                'category': 'タレント',
                'occupation': 'お笑いタレント/YouTuber',
                'birth_year': 1993,
                'expected': 'KEEP',
                'reason': 'TV・YouTube両方で活躍'
            }
        ]
    
    def run_test(self, test_case: Dict) -> Dict:
        """個別テストケース実行"""
        print(f"\n{Colors.CYAN}テスト: {test_case['name_ja']} ({test_case['person_id']}){Colors.END}")
        print(f"  期待結果: {Colors.BOLD}{test_case['expected']}{Colors.END}")
        print(f"  理由: {test_case['reason']}")
        
        # PersonDataオブジェクト作成
        person = PersonData(
            id=test_case['person_id'],
            name=test_case['name_ja'] or test_case['name'],
            name_en=test_case['name'],
            category=test_case['category'],
            birth_year=test_case['birth_year'],
            description=test_case.get('occupation'),
            is_fictional='架空キャラクター' in (test_case.get('category') or ''),
            is_textbook='教科書' in (test_case.get('reason') or '')
        )
        
        # システム評価実行
        try:
            score, action = self.system.evaluate_person(person)
            
            # 結果判定
            actual_action = 'KEEP' if action in [DeleteAction.KEEP, DeleteAction.PROTECT] else 'DELETE'
            is_correct = actual_action == test_case['expected']
            
            # メトリクス更新
            if test_case['expected'] == 'KEEP':
                if is_correct:
                    self.accuracy_metrics['true_positive'] += 1
                else:
                    self.accuracy_metrics['false_negative'] += 1
            else:
                if is_correct:
                    self.accuracy_metrics['true_negative'] += 1
                else:
                    self.accuracy_metrics['false_positive'] += 1
            
            # 結果表示
            if is_correct:
                status_icon = f"{Colors.GREEN}✅{Colors.END}"
                status_text = f"{Colors.GREEN}正解{Colors.END}"
            else:
                status_icon = f"{Colors.RED}❌{Colors.END}"
                status_text = f"{Colors.RED}不正解{Colors.END}"
            
            print(f"  {status_icon} 判定: {actual_action} {status_text}")
            print(f"  総合スコア: {score.total_score:.1f}/10")
            print(f"  信頼度: {score.confidence:.1%}")
            
            # 詳細スコア表示
            if not is_correct or test_case['person_id'] == 'P000013':  # HIKAKINは詳細表示
                print(f"\n  {Colors.YELLOW}詳細スコア:{Colors.END}")
                print(f"    Google検索数: {score.google_search_count:,}")
                print(f"    SNSフォロワー: {score.sns_followers:,}")
                print(f"    SNS影響力: {score.sns_influence_score:.1f}")
                print(f"    ニュース言及: {score.news_mentions:,}")
                print(f"    ニューススコア: {score.news_score:.1f}")
                print(f"    Wikipedia: {'あり' if score.wikipedia_exists else 'なし'}")
                print(f"    Googleトレンド: {score.google_trends_score:.1f}")
                print(f"    文化的影響: {score.cultural_impact:.1f}")
                print(f"    教育的重要性: {score.educational_importance:.1f}")
            
            # 削除理由表示
            if action == DeleteAction.DELETE:
                print(f"  {Colors.RED}削除判定: 知名度不足{Colors.END}")
            elif action == DeleteAction.PROTECT:
                print(f"  {Colors.GREEN}保護判定: {', '.join(score.protection_reasons) if score.protection_reasons else '高知名度'}{Colors.END}")
            elif action == DeleteAction.KEEP:
                print(f"  {Colors.GREEN}保持判定: 十分な知名度{Colors.END}")
            
            return {
                'test_case': test_case,
                'result': {
                    'score': score,
                    'action': action,
                    'actual': actual_action,
                    'is_correct': is_correct
                }
            }
            
        except Exception as e:
            print(f"  {Colors.RED}❌ エラー: {e}{Colors.END}")
            self.accuracy_metrics['false_negative'] += 1 if test_case['expected'] == 'KEEP' else 0
            return {
                'test_case': test_case,
                'result': {
                    'error': str(e),
                    'is_correct': False
                }
            }
    
    def calculate_accuracy(self) -> float:
        """精度計算"""
        total = sum(self.accuracy_metrics.values())
        if total == 0:
            return 0.0
        
        correct = self.accuracy_metrics['true_positive'] + self.accuracy_metrics['true_negative']
        return (correct / total) * 100
    
    def generate_report(self):
        """テスト結果レポート生成"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}テスト結果サマリー - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}")
        
        # 精度メトリクス
        accuracy = self.calculate_accuracy()
        print(f"\n{Colors.BLUE}📊 精度メトリクス:{Colors.END}")
        print(f"  全体精度: {Colors.BOLD}{accuracy:.1f}%{Colors.END}")
        print(f"  True Positive (有名人を正しく保護): {self.accuracy_metrics['true_positive']}")
        print(f"  True Negative (非有名人を正しく削除): {self.accuracy_metrics['true_negative']}")
        print(f"  False Positive (非有名人を誤って保護): {self.accuracy_metrics['false_positive']}")
        print(f"  False Negative (有名人を誤って削除): {self.accuracy_metrics['false_negative']}")
        
        # 精度判定
        if accuracy >= 96:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 目標精度96%達成！{Colors.END}")
            print(f"{Colors.GREEN}システムは本番運用可能な精度を達成しています。{Colors.END}")
        elif accuracy >= 90:
            print(f"\n{Colors.YELLOW}⚠️ 精度は良好ですが、目標の96%には届いていません。{Colors.END}")
        else:
            print(f"\n{Colors.RED}❌ 精度が不十分です。システムの調整が必要です。{Colors.END}")
        
        # HIKAKINケースの詳細
        hikakin_result = next((r for r in self.test_results if r['test_case']['person_id'] == 'P000013'), None)
        if hikakin_result and hikakin_result['result'].get('is_correct'):
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ HIKAKINケース: 正しく保護されました！{Colors.END}")
            print(f"{Colors.GREEN}バグ修正成功 - Web検索バリデータが正常に動作しています。{Colors.END}")
        
        # レポートファイル保存
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'accuracy': accuracy,
            'metrics': self.accuracy_metrics,
            'test_results': [
                {
                    'person_id': r['test_case']['person_id'],
                    'name': r['test_case']['name_ja'],
                    'expected': r['test_case']['expected'],
                    'actual': r['result'].get('actual', 'ERROR'),
                    'is_correct': r['result'].get('is_correct', False),
                    'score': r['result'].get('score').total_score if r['result'].get('score') else 0,
                    'confidence': r['result'].get('score').confidence if r['result'].get('score') else 0
                }
                for r in self.test_results
            ]
        }
        
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 詳細レポート保存: {report_file}")
        
        return accuracy
    
    def run_all_tests(self):
        """全テスト実行"""
        print(f"{Colors.BOLD}Ultimate Recognition System - 統合テスト開始{Colors.END}")
        print(f"テスト日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # API状態確認
        print(f"\n{Colors.BLUE}API接続状態確認:{Colors.END}")
        api_status = self.system._check_apis()
        
        all_available = all(api_status.values())
        if not all_available:
            print(f"{Colors.YELLOW}⚠️ 一部のAPIが利用できません:{Colors.END}")
            for api, available in api_status.items():
                if not available:
                    print(f"  {Colors.RED}❌ {api}{Colors.END}")
            print(f"\n{Colors.YELLOW}テストは続行しますが、精度が低下する可能性があります。{Colors.END}")
        else:
            print(f"{Colors.GREEN}✅ すべてのAPIが利用可能です{Colors.END}")
        
        # テストケース実行
        test_cases = self.create_test_cases()
        print(f"\n{Colors.BLUE}テストケース数: {len(test_cases)}{Colors.END}")
        
        for test_case in test_cases:
            result = self.run_test(test_case)
            self.test_results.append(result)
        
        # レポート生成
        accuracy = self.generate_report()
        
        return accuracy >= 96  # 96%以上で成功


def main():
    """メイン実行"""
    tester = RecognitionSystemTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ システムテスト成功！{Colors.END}")
        print(f"{Colors.GREEN}Ultimate Recognition Systemは本番運用可能です。{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ システムテスト失敗{Colors.END}")
        print(f"{Colors.RED}精度向上のための調整が必要です。{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()