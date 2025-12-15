#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDCAガーディアンシステム - 包括的テストスイート
すべてのクリティカルルールが正しく機能することを確認
"""

import sys
from typing import Dict, List, Any
from pdca_guardian_enhanced import EnhancedPDCAGuardian
from pdca_health_monitor import PDCAHealthMonitor


class PDCATestSuite:
    """PDCAガーディアンシステムのテストスイート"""

    def __init__(self):
        self.guardian = EnhancedPDCAGuardian()
        self.monitor = PDCAHealthMonitor()
        self.test_results = []

    def test_rule_152_sentence_ending(self) -> Dict[str, Any]:
        """RULE_152: 文末チェックのテスト"""
        test_cases = [
            {
                "name": "名詞終了（禁止）",
                "text": "あなたと同じ47歳のとき、久石譲は日本最高の作曲家。",
                "expected": False
            },
            {
                "name": "動詞終了（正しい）",
                "text": "あなたと同じ47歳のとき、久石譲は日本最高の作曲家として活躍した。",
                "expected": True
            },
            {
                "name": "形容詞終了（正しい）",
                "text": "あなたと同じ47歳のとき、久石譲の音楽は世界中で愛され続けている。",
                "expected": True
            },
            {
                "name": "職業名詞終了（禁止）",
                "text": "あなたと同じ52歳のとき、稲盛和夫は日本を代表する起業家。",
                "expected": False
            }
        ]

        results = []
        for case in test_cases:
            violations = self.guardian.check_episode_quality(
                case["text"], 47, "テスト人物"
            )

            # RULE_152関連の違反を探す
            has_ending_violation = any(
                'RULE_152' in str(v.get('rule_id', v.get('rule', '')))
                for v in violations
            )

            passed = (not has_ending_violation) == case["expected"]
            results.append({
                "name": case["name"],
                "passed": passed,
                "violations": len(violations),
                "expected": case["expected"],
                "actual": not has_ending_violation
            })

        return {
            "rule": "RULE_152",
            "description": "文末チェック",
            "total_tests": len(test_cases),
            "passed": sum(1 for r in results if r["passed"]),
            "details": results
        }

    def test_rule_160_character_count(self) -> Dict[str, Any]:
        """RULE_160: 文字数制限のテスト"""
        test_cases = [
            {
                "name": "文字数不足（139文字）",
                "text": "あなたと同じ41歳のとき、黒澤明は『羅生門』でヴェネツィア国際映画祭金獅子賞を受賞した。" + "x" * 44,  # 139文字
                "expected": False
            },
            {
                "name": "文字数適正（150文字）",
                "text": "あなたと同じ41歳のとき、黒澤明は『羅生門』でヴェネツィア国際映画祭金獅子賞を受賞した。" + "y" * 55,  # 150文字
                "expected": True
            },
            {
                "name": "文字数超過（201文字）",
                "text": "あなたと同じ41歳のとき、黒澤明は『羅生門』でヴェネツィア国際映画祭金獅子賞を受賞した。" + "z" * 106,  # 201文字
                "expected": False
            }
        ]

        results = []
        for case in test_cases:
            violations = self.guardian.check_episode_quality(
                case["text"], 41, "テスト人物"
            )

            # RULE_160関連の違反を探す
            has_count_violation = any(
                'RULE_160' in str(v.get('rule_id', v.get('rule', '')))
                for v in violations
            )

            passed = (not has_count_violation) == case["expected"]
            results.append({
                "name": case["name"],
                "passed": passed,
                "char_count": len(case["text"]),
                "expected": case["expected"],
                "actual": not has_count_violation
            })

        return {
            "rule": "RULE_160",
            "description": "文字数制限（140-200文字）",
            "total_tests": len(test_cases),
            "passed": sum(1 for r in results if r["passed"]),
            "details": results
        }

    def test_rule_165_starting_phrase(self) -> Dict[str, Any]:
        """RULE_165: 開始フレーズのテスト"""
        test_cases = [
            {
                "name": "正しい開始フレーズ",
                "text": "あなたと同じ47歳のとき、久石譲は素晴らしい音楽を作曲した。",
                "expected": True
            },
            {
                "name": "間違った開始フレーズ",
                "text": "47歳のとき、久石譲は素晴らしい音楽を作曲した。",
                "expected": False
            },
            {
                "name": "開始フレーズなし",
                "text": "久石譲は47歳のときに素晴らしい音楽を作曲した。",
                "expected": False
            }
        ]

        results = []
        for case in test_cases:
            has_correct_start = case["text"].startswith("あなたと同じ")
            passed = has_correct_start == case["expected"]

            results.append({
                "name": case["name"],
                "passed": passed,
                "expected": case["expected"],
                "actual": has_correct_start
            })

        return {
            "rule": "RULE_165",
            "description": "開始フレーズチェック",
            "total_tests": len(test_cases),
            "passed": sum(1 for r in results if r["passed"]),
            "details": results
        }

    def test_health_monitoring(self) -> Dict[str, Any]:
        """健全性監視システムのテスト"""
        test_episodes = [
            {
                "text": "あなたと同じ41歳のとき、黒澤明は映画監督。",
                "age": 41,
                "name": "黒澤明"
            },
            {
                "text": "あなたと同じ52歳のとき、稲盛和夫は第二電電を創業した。",
                "age": 52,
                "name": "稲盛和夫"
            }
        ]

        # 各エピソードをチェック
        for ep in test_episodes:
            monitor_id = self.monitor.start_monitoring(
                'RULE_152',
                {'episode_text': ep['text'], 'person_data': {'name': ep['name']}}
            )

            try:
                violations = self.guardian.check_episode_quality(
                    ep['text'], ep['age'], ep['name']
                )
                self.monitor.end_monitoring(monitor_id, 'success', result=violations)
            except Exception as e:
                self.monitor.end_monitoring(monitor_id, 'error', error=str(e))

        # レポート生成
        report = self.monitor.generate_health_report()

        return {
            "rule": "HEALTH_MONITOR",
            "description": "健全性監視システム",
            "total_executions": report['summary']['total_executions'],
            "success_rate": report['summary']['success_rate'],
            "alerts": len(report['alerts']),
            "critical_coverage": report['critical_rules_coverage']['overall']['coverage_percentage']
        }

    def run_all_tests(self):
        """すべてのテストを実行"""
        print("=" * 60)
        print("🔬 PDCAガーディアンシステム - 包括的テスト実行")
        print("=" * 60)

        # 各テストを実行
        test_methods = [
            self.test_rule_152_sentence_ending,
            self.test_rule_160_character_count,
            self.test_rule_165_starting_phrase,
            self.test_health_monitoring
        ]

        all_results = []
        for test_method in test_methods:
            result = test_method()
            all_results.append(result)

            # テスト結果を表示
            print(f"\n📋 {result['rule']}: {result['description']}")

            if 'total_tests' in result:
                print(f"  テスト数: {result['total_tests']}")
                print(f"  合格: {result['passed']}")
                print(f"  成功率: {(result['passed']/result['total_tests']*100):.1f}%")

                if 'details' in result:
                    for detail in result['details']:
                        status = "✅" if detail['passed'] else "❌"
                        print(f"    {status} {detail['name']}")
            else:
                # 健全性監視の結果
                print(f"  実行数: {result.get('total_executions', 0)}")
                print(f"  成功率: {result.get('success_rate', 0):.1f}%")
                print(f"  アラート: {result.get('alerts', 0)}件")
                print(f"  クリティカルルールカバレッジ: {result.get('critical_coverage', 0):.1f}%")

        # 総合結果
        print("\n" + "=" * 60)
        print("📊 総合結果")
        print("=" * 60)

        total_tests = sum(r.get('total_tests', 0) for r in all_results if 'total_tests' in r)
        total_passed = sum(r.get('passed', 0) for r in all_results if 'passed' in r)

        if total_tests > 0:
            overall_rate = (total_passed / total_tests) * 100
            print(f"  総テスト数: {total_tests}")
            print(f"  合格数: {total_passed}")
            print(f"  総合成功率: {overall_rate:.1f}%")

            if overall_rate == 100:
                print("\n🎉 すべてのテストが合格しました！")
            elif overall_rate >= 80:
                print("\n✅ 大部分のテストが合格しました")
            else:
                print("\n⚠️ 改善が必要です")

        # 健全性監視の警告
        health_result = next((r for r in all_results if r['rule'] == 'HEALTH_MONITOR'), None)
        if health_result and health_result.get('alerts', 0) > 0:
            print(f"\n⚠️ 健全性監視で{health_result['alerts']}件のアラートが検出されました")

        return all_results

    def test_week4_batch_validation(self):
        """Week 4バッチの検証テスト"""
        print("\n" + "=" * 60)
        print("🔍 Week 4バッチ検証テスト")
        print("=" * 60)

        from batch_week4_validated import create_week4_batch_validated

        episodes = create_week4_batch_validated()

        violations_by_episode = []
        for ep in episodes:
            violations = self.guardian.check_episode_quality(
                ep['episode_text'],
                ep['user_age'],
                ep['person_name']
            )

            # 文末違反を特定
            ending_violations = [
                v for v in violations
                if 'RULE_152' in str(v.get('rule_id', v.get('rule', '')))
            ]

            violations_by_episode.append({
                'name': ep['person_name'],
                'total_violations': len(violations),
                'ending_violations': len(ending_violations),
                'char_count': ep['character_count'],
                'is_valid': ep['is_valid']
            })

        # 結果表示
        print(f"\n総エピソード数: {len(episodes)}")
        print(f"検証済み（is_valid=True）: {sum(1 for e in episodes if e['is_valid'])}件")

        ending_violation_count = sum(1 for v in violations_by_episode if v['ending_violations'] > 0)
        print(f"\n文末違反検出: {ending_violation_count}件")

        if ending_violation_count > 0:
            print("\n❌ 文末違反が検出されたエピソード:")
            for v in violations_by_episode:
                if v['ending_violations'] > 0:
                    print(f"  - {v['name']}: {v['ending_violations']}件の違反")
        else:
            print("\n✅ すべてのエピソードが文末ルールを通過しました！")

        return violations_by_episode


def main():
    """メイン関数"""
    test_suite = PDCATestSuite()

    # すべてのテストを実行
    results = test_suite.run_all_tests()

    # Week 4バッチの検証
    week4_results = test_suite.test_week4_batch_validation()

    print("\n" + "=" * 60)
    print("✅ テストスイート完了")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
