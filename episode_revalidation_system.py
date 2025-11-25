#!/usr/bin/env python3
"""
既存エピソード再検証システム
統合検証システムを使用して既存の30エピソードを再評価

Author: Claude Code
Date: 2025-10-01
Version: 1.0.0
"""

import csv
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from unified_validation_system import UnifiedValidationSystem, ValidationResult


class EpisodeRevalidationSystem:
    """既存エピソードの再検証システム"""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.validator = UnifiedValidationSystem()
        self.results: List[ValidationResult] = []

    def load_episodes(self) -> List[Dict]:
        """CSVファイルからエピソードを読み込む"""
        episodes = []

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, 1):
                episode = {
                    'episode_id': f"EP{idx:03d}",
                    'person_name': row.get('person_name', ''),
                    'person_display_name': row.get('person_name', ''),
                    'user_age': row.get('user_age', ''),
                    'episode_age': row.get('episode_age', ''),
                    'episode_text': row.get('episode_text', ''),
                    'category': row.get('category', ''),
                    'weighted_score': float(row.get('weighted_score', 0)),
                    'original_validation': row.get('is_valid', 'unknown')
                }
                episodes.append(episode)

        print(f"✅ {len(episodes)}件のエピソードを読み込みました")
        return episodes

    def validate_all(self, episodes: List[Dict]) -> List[ValidationResult]:
        """全エピソードの検証を実行"""
        print("\n" + "=" * 80)
        print("統合検証システムによる再検証開始")
        print("=" * 80)

        results = []

        for idx, episode in enumerate(episodes, 1):
            print(f"\n【{idx}/{len(episodes)}】{episode['person_name']} (EP{idx:03d})")
            result = self.validator.validate_episode(episode)
            results.append(result)

            # 結果の即座表示
            status = "✅ 合格" if result.is_valid else "❌ 不合格"
            print(f"  検証結果: {status}")
            print(f"  感銘スコア: {result.emotional_impact_score:.2f}")
            print(f"  具体性スコア: {result.specificity_score:.2f}")

            if result.violations:
                print(f"  🔴 違反: {len(result.violations)}件")
                for v in result.get_critical_violations():
                    print(f"    - {v.message}")

        self.results = results
        return results

    def generate_summary_report(self) -> Dict:
        """検証結果のサマリーレポート生成"""
        total = len(self.results)
        valid_count = sum(1 for r in self.results if r.is_valid)
        invalid_count = total - valid_count

        critical_violations = {}
        for result in self.results:
            for v in result.get_critical_violations():
                rule_name = v.rule_name
                critical_violations[rule_name] = critical_violations.get(rule_name, 0) + 1

        avg_emotional = sum(r.emotional_impact_score for r in self.results) / total
        avg_specificity = sum(r.specificity_score for r in self.results) / total

        return {
            "total_episodes": total,
            "valid_episodes": valid_count,
            "invalid_episodes": invalid_count,
            "compliance_rate": f"{(valid_count / total * 100):.1f}%",
            "average_emotional_score": f"{avg_emotional:.2f}",
            "average_specificity_score": f"{avg_specificity:.2f}",
            "critical_violations_by_rule": critical_violations
        }

    def export_detailed_report(self, output_path: str):
        """詳細レポートをJSON形式で出力"""
        report = {
            "validation_date": datetime.now().isoformat(),
            "source_file": str(self.csv_path),
            "summary": self.generate_summary_report(),
            "detailed_results": [r.to_dict() for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 詳細レポートを出力: {output_path}")

    def export_csv_with_validation(self, output_path: str, episodes: List[Dict]):
        """検証結果を含むCSVを出力"""
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'episode_id',
                'person_name',
                'user_age',
                'episode_age',
                'episode_text',
                'category',
                'original_score',
                'unified_validation_status',
                'emotional_impact_score',
                'specificity_score',
                'critical_violations',
                'total_violations',
                'warnings',
                'improvement_suggestions'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for episode, result in zip(episodes, self.results):
                writer.writerow({
                    'episode_id': result.episode_id,
                    'person_name': episode['person_name'],
                    'user_age': episode['user_age'],
                    'episode_age': episode['episode_age'],
                    'episode_text': episode['episode_text'],
                    'category': episode['category'],
                    'original_score': episode['weighted_score'],
                    'unified_validation_status': 'PASS' if result.is_valid else 'FAIL',
                    'emotional_impact_score': f"{result.emotional_impact_score:.2f}",
                    'specificity_score': f"{result.specificity_score:.2f}",
                    'critical_violations': len(result.get_critical_violations()),
                    'total_violations': len(result.violations),
                    'warnings': len(result.warnings),
                    'improvement_suggestions': ' | '.join(result.improvement_suggestions)
                })

        print(f"✅ 検証結果CSV出力: {output_path}")

    def print_summary(self):
        """サマリーレポートをコンソール出力"""
        summary = self.generate_summary_report()

        print("\n" + "=" * 80)
        print("📊 検証結果サマリー")
        print("=" * 80)
        print(f"総エピソード数: {summary['total_episodes']}件")
        print(f"合格: {summary['valid_episodes']}件")
        print(f"不合格: {summary['invalid_episodes']}件")
        print(f"準拠率: {summary['compliance_rate']}")
        print(f"\n平均感銘スコア: {summary['average_emotional_score']}")
        print(f"平均具体性スコア: {summary['average_specificity_score']}")

        if summary['critical_violations_by_rule']:
            print("\n【クリティカル違反の内訳】")
            for rule, count in sorted(summary['critical_violations_by_rule'].items(), key=lambda x: -x[1]):
                print(f"  - {rule}: {count}件")

        print("=" * 80)

    def identify_fix_priorities(self) -> List[Dict]:
        """修正優先順位の高いエピソードを特定"""
        priority_list = []

        for idx, (episode, result) in enumerate(zip(self.load_episodes(), self.results), 1):
            critical_count = len(result.get_critical_violations())

            if not result.is_valid and critical_count > 0:
                priority_list.append({
                    'episode_id': result.episode_id,
                    'person_name': episode['person_name'],
                    'priority': 'HIGH' if critical_count >= 2 else 'MEDIUM',
                    'critical_violations': critical_count,
                    'total_violations': len(result.violations),
                    'emotional_score': result.emotional_impact_score,
                    'suggestions': result.improvement_suggestions
                })

        # 優先度でソート（クリティカル違反数が多い順）
        priority_list.sort(key=lambda x: (-x['critical_violations'], -x['total_violations']))

        return priority_list

    def print_fix_priorities(self):
        """修正優先順位リストを表示"""
        priorities = self.identify_fix_priorities()

        print("\n" + "=" * 80)
        print("🔧 修正優先順位リスト")
        print("=" * 80)

        high_priority = [p for p in priorities if p['priority'] == 'HIGH']
        medium_priority = [p for p in priorities if p['priority'] == 'MEDIUM']

        if high_priority:
            print(f"\n【高優先度】{len(high_priority)}件")
            for p in high_priority:
                print(f"\n  {p['episode_id']} - {p['person_name']}")
                print(f"    クリティカル違反: {p['critical_violations']}件")
                print(f"    総違反数: {p['total_violations']}件")
                print(f"    改善提案:")
                for suggestion in p['suggestions'][:3]:  # 上位3件
                    print(f"      {suggestion}")

        if medium_priority:
            print(f"\n【中優先度】{len(medium_priority)}件")
            for p in medium_priority[:5]:  # 上位5件表示
                print(f"  - {p['episode_id']} - {p['person_name']} (違反{p['total_violations']}件)")

        print("=" * 80)


def main():
    """メイン実行関数"""
    # CSVファイルパス
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/master/episodes_master_current.csv"

    # 再検証システムのインスタンス化
    revalidator = EpisodeRevalidationSystem(csv_path)

    # エピソードの読み込み
    episodes = revalidator.load_episodes()

    # 全エピソードの検証
    results = revalidator.validate_all(episodes)

    # サマリーレポートの表示
    revalidator.print_summary()

    # 修正優先順位の表示
    revalidator.print_fix_priorities()

    # 詳細レポートのJSON出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_output = f"episode_validation_report_{timestamp}.json"
    revalidator.export_detailed_report(json_output)

    # 検証結果付きCSVの出力
    csv_output = f"episodes_with_validation_{timestamp}.csv"
    revalidator.export_csv_with_validation(csv_output, episodes)

    print("\n✅ 再検証完了")


if __name__ == "__main__":
    main()
