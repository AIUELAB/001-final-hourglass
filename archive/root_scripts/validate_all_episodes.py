#!/usr/bin/env python3
"""
全エピソード検証スクリプト
EpisodeGuardian v1.2.0で全100エピソードを検証
"""

import csv
import sys
from typing import Dict, List
from episode_guardian import create_episode_guardian, ValidationResult, Severity

def load_episodes(csv_path: str) -> List[Dict]:
    """CSVファイルから全エピソードを読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append({
                'episode_id': row['episode_id'],
                'person_name': row['person_name'],
                'episode_age': int(row['episode_age']),
                'episode_text': row['episode_text'],
                'category': row['category']
            })
    return episodes

def validate_all_episodes(episodes: List[Dict]) -> Dict:
    """全エピソードを検証"""
    guardian = create_episode_guardian()

    results = {
        'total': len(episodes),
        'passed': 0,
        'failed': 0,
        'violations': []
    }

    print(f"{'='*80}")
    print(f"EpisodeGuardian v1.2.0 全エピソード検証")
    print(f"{'='*80}")
    print(f"総エピソード数: {results['total']}")
    print(f"{'='*80}\n")

    for episode in episodes:
        result = guardian.validate_episode(episode)

        if result.is_valid:
            results['passed'] += 1
            print(f"✅ {episode['episode_id']} {episode['person_name']} - 合格")
        else:
            results['failed'] += 1
            print(f"❌ {episode['episode_id']} {episode['person_name']} - 失格")
            print(f"   重要度: {result.severity}")
            print(f"   失敗ルール: {', '.join(result.failed_rules)}")
            print(f"   メッセージ: {result.message[:100]}...")
            print()

            results['violations'].append({
                'episode_id': episode['episode_id'],
                'person_name': episode['person_name'],
                'episode_age': episode['episode_age'],
                'severity': result.severity,
                'failed_rules': result.failed_rules,
                'message': result.message,
                'episode_text': episode['episode_text']
            })

    return results

def print_summary(results: Dict):
    """検証結果サマリーを表示"""
    print(f"\n{'='*80}")
    print(f"検証結果サマリー")
    print(f"{'='*80}")
    print(f"総エピソード数: {results['total']}")
    print(f"合格: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"失格: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print(f"{'='*80}\n")

    if results['failed'] > 0:
        print(f"{'='*80}")
        print(f"違反エピソード詳細 ({results['failed']}件)")
        print(f"{'='*80}\n")

        # 重要度別にグループ化
        critical_violations = [v for v in results['violations'] if v['severity'] == Severity.CRITICAL]
        warning_violations = [v for v in results['violations'] if v['severity'] == Severity.WARNING]

        if critical_violations:
            print(f"🔴 CRITICAL違反 ({len(critical_violations)}件):")
            for v in critical_violations:
                print(f"  {v['episode_id']} {v['person_name']} ({v['episode_age']}歳)")
                print(f"  失敗ルール: {', '.join(v['failed_rules'])}")
                print(f"  メッセージ: {v['message'][:150]}...")
                print()

        if warning_violations:
            print(f"🟡 WARNING違反 ({len(warning_violations)}件):")
            for v in warning_violations:
                print(f"  {v['episode_id']} {v['person_name']} ({v['episode_age']}歳)")
                print(f"  失敗ルール: {', '.join(v['failed_rules'])}")
                print(f"  メッセージ: {v['message'][:150]}...")
                print()

        # ルール別集計
        rule_counts = {}
        for v in results['violations']:
            for rule in v['failed_rules']:
                rule_counts[rule] = rule_counts.get(rule, 0) + 1

        print(f"{'='*80}")
        print(f"ルール別違反集計")
        print(f"{'='*80}")
        for rule, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {rule}: {count}件")
        print()

def save_violations_report(results: Dict, output_path: str):
    """違反エピソードレポートをCSVに保存"""
    if not results['violations']:
        print("違反エピソードなし")
        return

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['episode_id', 'person_name', 'episode_age', 'severity',
                      'failed_rules', 'message', 'episode_text']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for v in results['violations']:
            writer.writerow({
                'episode_id': v['episode_id'],
                'person_name': v['person_name'],
                'episode_age': v['episode_age'],
                'severity': v['severity'].name,
                'failed_rules': '|'.join(v['failed_rules']),
                'message': v['message'],
                'episode_text': v['episode_text']
            })

    print(f"違反レポート保存: {output_path}")

if __name__ == '__main__':
    csv_path = '/Users/admin/Documents/AIUELAB/001-final-hourglass/episodes_complete_100_20251001.csv'
    output_path = '/Users/admin/Documents/AIUELAB/001-final-hourglass/violations_report_20251001.csv'

    # 全エピソード読み込み
    episodes = load_episodes(csv_path)

    # 検証実行
    results = validate_all_episodes(episodes)

    # サマリー表示
    print_summary(results)

    # 違反レポート保存
    if results['failed'] > 0:
        save_violations_report(results, output_path)

    sys.exit(0 if results['failed'] == 0 else 1)
