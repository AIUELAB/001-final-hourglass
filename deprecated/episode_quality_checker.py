#!/usr/bin/env python3
"""
エピソード品質チェッカー
PDCA RULE 168・169に基づく品質検証システム
"""

import csv
import re
from typing import List, Dict, Tuple
from datetime import datetime

class EpisodeQualityChecker:
    """エピソード品質チェッカー"""

    def __init__(self):
        # RULE_168: 禁止表現パターン
        self.prohibited_patterns = [
            r'から\d+年',
            r'経っても',
            r'語り継が',
            r'評価され',
            r'認められ',
            r'美しさ',
            r'カリスマ',
            r'憧れ',
            r'象徴',
            r'君臨',
            r'レジェンド',
            r'伝説'
        ]

        # 必須動詞パターン
        self.required_verbs = [
            '達成した', '記録した', '獲得した', '創業した',
            '受賞した', '設立した', '開発した', '発表した',
            '優勝した', '突破した', '成功した', '完成させた'
        ]

        # 数値パターン
        self.number_pattern = re.compile(r'\d+[万億千百十]?[人円枚本%歳回]')

    def check_episode_quality(self, episode: Dict) -> Dict:
        """
        エピソードの品質をチェック

        Args:
            episode: エピソードデータ

        Returns:
            チェック結果
        """
        text = episode.get('episode_text', '')
        violations = []
        warnings = []
        score = 1.0

        # 1. 禁止表現チェック
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text):
                violations.append(f"禁止表現検出: {pattern}")
                score -= 0.2

        # 2. 必須動詞チェック
        has_active_verb = any(verb in text for verb in self.required_verbs)
        if not has_active_verb:
            violations.append("能動的達成動詞が不在")
            score -= 0.3

        # 3. 数値チェック
        numbers = self.number_pattern.findall(text)
        if not numbers:
            warnings.append("具体的数値が不足")
            score -= 0.1

        # 4. 間接的時期表現チェック
        if '10年' in text and '経って' in text:
            violations.append("間接的時期表現を検出")
            score -= 0.3

        # 5. 年齢整合性チェック
        episode_age = int(episode.get('episode_age', 0))
        if '歳' in text:
            age_mentions = re.findall(r'(\d+)歳', text)
            for age_str in age_mentions:
                mentioned_age = int(age_str)
                if mentioned_age != episode_age and 'あなたと同じ' in text:
                    violations.append(f"年齢不整合: {mentioned_age}歳 != {episode_age}歳")
                    score -= 0.5

        return {
            'person_name': episode.get('person_name'),
            'episode_age': episode_age,
            'quality_score': max(0, score),
            'violations': violations,
            'warnings': warnings,
            'needs_revision': len(violations) > 0
        }

    def check_batch_episodes(self, csv_path: str) -> Tuple[List[Dict], List[Dict]]:
        """
        CSVファイル内の全エピソードをチェック

        Args:
            csv_path: CSVファイルパス

        Returns:
            (問題エピソード, 全チェック結果)
        """
        all_results = []
        problematic = []

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            episodes = list(reader)

        print(f"\n📊 品質チェック開始: {len(episodes)}個のエピソード")
        print("=" * 60)

        for episode in episodes:
            result = self.check_episode_quality(episode)
            all_results.append(result)

            if result['needs_revision']:
                problematic.append({
                    'episode': episode,
                    'check_result': result
                })

        return problematic, all_results

    def generate_quality_report(self, all_results: List[Dict]) -> Dict:
        """
        品質レポートを生成

        Args:
            all_results: 全チェック結果

        Returns:
            レポート辞書
        """
        total = len(all_results)
        passed = sum(1 for r in all_results if not r['needs_revision'])
        failed = total - passed

        avg_score = sum(r['quality_score'] for r in all_results) / total if total > 0 else 0

        violation_types = {}
        for result in all_results:
            for violation in result['violations']:
                key = violation.split(':')[0]
                violation_types[key] = violation_types.get(key, 0) + 1

        return {
            'total_episodes': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'average_quality_score': avg_score,
            'violation_types': violation_types
        }

def main():
    """メイン実行"""
    checker = EpisodeQualityChecker()

    # 最新のエピソードファイルをチェック
    csv_path = 'episodes_final_expanded_20250921_210449.csv'

    problematic, all_results = checker.check_batch_episodes(csv_path)

    # レポート生成
    report = checker.generate_quality_report(all_results)

    print("\n📈 品質チェック結果サマリー:")
    print(f"  総エピソード数: {report['total_episodes']}")
    print(f"  合格: {report['passed']}個")
    print(f"  要修正: {report['failed']}個")
    print(f"  合格率: {report['pass_rate']:.1f}%")
    print(f"  平均品質スコア: {report['average_quality_score']:.2f}")

    if report['violation_types']:
        print("\n⚠️ 違反タイプ別集計:")
        for vtype, count in sorted(report['violation_types'].items(),
                                  key=lambda x: x[1], reverse=True):
            print(f"  - {vtype}: {count}件")

    # 問題エピソードの詳細
    if problematic:
        print(f"\n❌ 要修正エピソード TOP10:")
        for item in problematic[:10]:
            episode = item['episode']
            result = item['check_result']
            print(f"\n【{episode['person_name']}】{episode['episode_age']}歳")
            print(f"  品質スコア: {result['quality_score']:.2f}")
            for v in result['violations']:
                print(f"  ❌ {v}")
            print(f"  テキスト冒頭: {episode['episode_text'][:50]}...")

    # 修正が必要なエピソードをCSVに出力
    if problematic:
        output_file = f'episodes_needing_revision_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            if problematic:
                fieldnames = list(problematic[0]['episode'].keys()) + ['violations', 'quality_score']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for item in problematic:
                    row = item['episode'].copy()
                    row['violations'] = '; '.join(item['check_result']['violations'])
                    row['quality_score'] = item['check_result']['quality_score']
                    writer.writerow(row)

        print(f"\n📁 要修正エピソードを保存: {output_file}")

    return report

if __name__ == "__main__":
    main()