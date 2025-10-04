#!/usr/bin/env python3
"""
包括的エピソード検証システム
既存エピソードの品質問題を完全に検出・修正
"""

import csv
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path

class ComprehensiveEpisodeValidator:
    """包括的エピソード検証システム"""

    def __init__(self):
        """初期化"""
        # 定型文パターン（絶対に使用禁止）
        self.template_patterns = [
            # 一般的な定型文
            r'その後も.*続け',
            r'この偉業は.*記憶され',
            r'後世.*道標',
            r'多くの.*影響を与え',
            r'今も.*語り継が',
            r'永遠に.*残',

            # カテゴリ別定型文
            r'この活躍が.*新風を吹き込み',
            r'新たな可能性を切り開いた',
            r'日本.*界.*発展.*貢献',
            r'時代を.*象徴',
            r'この瞬間から始まった物語',
            r'夢と希望を与え',

            # 文字数調整用定型文
            r'その後も挑戦を続け.*記録を打ち立て',
            r'この才能は.*足跡を残し',
            r'この革新が.*基盤を支え',
            r'後進の.*目標となり'
        ]

        # 主観的表現（NGワード）
        self.subjective_words = [
            '偉大な', '素晴らしい', '驚異的', '圧倒的', '伝説の',
            '神様', '英雄', 'カリスマ', '天才', '鬼才',
            '最高の', '究極の', '完璧な', '奇跡の', '感動の',
            '愛される', '尊敬される', '憧れの', '国民的',
            '〜と言われる', '〜とされる', '〜と呼ばれる'
        ]

        # 文末チェックパターン
        self.noun_endings = [
            '革命児', '先駆者', '開拓者', '巨人', '天才',
            'レジェンド', 'カリスマ', '英雄', '巨匠', '名人',
            '達人', '偉人', '帝王', '女王', '王者', '覇者',
            '巨星', '怪物', '鬼才', '異才', '奇才', '秀才',
            '逸材', '名将', '闘将', '猛将', '智将', '勇将',
            '名手', '巧者', 'ヒーロー', 'ヒロイン'
        ]

    def validate_episode(self, episode_text: str) -> Dict:
        """
        エピソードを包括的に検証

        Returns:
            検証結果の辞書
        """
        issues = []
        score = 100  # 100点から減点方式

        # 1. 定型文チェック
        template_issues = self.check_templates(episode_text)
        if template_issues:
            issues.extend(template_issues)
            score -= len(template_issues) * 15  # 重大な違反

        # 2. 主観的表現チェック
        subjective_issues = self.check_subjectivity(episode_text)
        if subjective_issues:
            issues.extend(subjective_issues)
            score -= len(subjective_issues) * 10

        # 3. 文末チェック
        ending_issue = self.check_ending(episode_text)
        if ending_issue:
            issues.append(ending_issue)
            score -= 10

        # 4. 具体性チェック
        specificity_issues = self.check_specificity(episode_text)
        if specificity_issues:
            issues.extend(specificity_issues)
            score -= len(specificity_issues) * 5

        # 5. 文字数チェック
        char_count = len(episode_text)
        if char_count < 132:
            issues.append(f"文字数不足: {char_count}文字（最低132文字必要）")
            score -= 20
        elif char_count > 250:
            issues.append(f"文字数超過: {char_count}文字（最大250文字）")
            score -= 10

        return {
            'is_valid': len(issues) == 0,
            'score': max(0, score),
            'issues': issues,
            'character_count': char_count,
            'severity': self.calculate_severity(issues)
        }

    def check_templates(self, text: str) -> List[str]:
        """定型文をチェック"""
        issues = []
        for pattern in self.template_patterns:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                issues.append(f"定型文検出: '{match.group()}'")
        return issues

    def check_subjectivity(self, text: str) -> List[str]:
        """主観的表現をチェック"""
        issues = []
        for word in self.subjective_words:
            if word in text:
                issues.append(f"主観的表現: '{word}'")
        return issues

    def check_ending(self, text: str) -> str:
        """文末をチェック"""
        # 最後の句点を除いて文末を取得
        text_without_period = text.rstrip('。')

        # 名詞で終わっているかチェック
        for noun in self.noun_endings:
            if text_without_period.endswith(noun):
                return f"文末が名詞: '{noun}。'"

        # 体言止めの他のパターン
        if re.search(r'[^た]だった$', text_without_period):
            return None  # 「だった」は問題なし
        elif re.search(r'である$', text_without_period):
            return None  # 「である」は問題なし
        elif re.search(r'[たるくいつ]$', text_without_period):
            return None  # 動詞・形容詞の終止形は問題なし
        elif re.search(r'[あ-ん]$', text_without_period) and not re.search(r'[たるくいつ]$', text_without_period):
            # ひらがなで終わるが動詞・形容詞でない場合は要確認
            last_word = text_without_period[-10:]
            if any(noun in last_word for noun in ['こと', 'もの', 'ところ', 'ため']):
                return f"文末が体言的: '{last_word}'"

        return None

    def check_specificity(self, text: str) -> List[str]:
        """具体性をチェック"""
        issues = []

        # 数値の有無
        numbers = re.findall(r'\d+', text)
        if len(numbers) < 2:
            issues.append("具体的な数値が不足（2つ以上必要）")

        # 年代の有無
        years = re.findall(r'(19|20)\d{2}年', text)
        if len(years) < 1:
            issues.append("年代の記載がない")

        # 曖昧な表現
        vague_expressions = ['多く', 'いくつか', 'さまざま', '数々', 'たくさん']
        for expr in vague_expressions:
            if expr in text:
                issues.append(f"曖昧な表現: '{expr}'")

        return issues

    def calculate_severity(self, issues: List[str]) -> str:
        """問題の深刻度を計算"""
        if not issues:
            return "問題なし"

        critical_count = sum(1 for i in issues if '定型文' in i or '文字数不足' in i)
        major_count = sum(1 for i in issues if '主観的' in i or '文末' in i)

        if critical_count >= 2:
            return "重大"
        elif critical_count >= 1 or major_count >= 2:
            return "要修正"
        else:
            return "軽微"

    def validate_all_episodes(self, csv_file: str) -> Dict:
        """全エピソードを検証"""
        print("=" * 60)
        print("包括的エピソード品質検証")
        print("=" * 60)

        results = []
        severity_counts = {
            "重大": 0,
            "要修正": 0,
            "軽微": 0,
            "問題なし": 0
        }

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            episodes = list(reader)

        print(f"\n検証対象: {len(episodes)}件のエピソード\n")

        for i, row in enumerate(episodes, 1):
            person_name = row['person_name']
            episode_text = row['episode_text']

            validation = self.validate_episode(episode_text)

            result = {
                'index': i,
                'person_name': person_name,
                'age': row.get('user_age', 'N/A'),
                'validation': validation,
                'original_text': episode_text
            }
            results.append(result)

            severity_counts[validation['severity']] += 1

            # 問題があるエピソードは表示
            if validation['issues']:
                print(f"[{i}] {person_name} ({validation['severity']})")
                for issue in validation['issues'][:3]:  # 最初の3つの問題を表示
                    print(f"    - {issue}")

        # サマリー
        print("\n" + "=" * 60)
        print("検証結果サマリー")
        print("=" * 60)

        total = len(results)
        valid = sum(1 for r in results if r['validation']['is_valid'])

        print(f"\n✅ 問題なし: {severity_counts['問題なし']}件 ({severity_counts['問題なし']/total*100:.1f}%)")
        print(f"⚠️ 軽微: {severity_counts['軽微']}件 ({severity_counts['軽微']/total*100:.1f}%)")
        print(f"🔶 要修正: {severity_counts['要修正']}件 ({severity_counts['要修正']/total*100:.1f}%)")
        print(f"🔴 重大: {severity_counts['重大']}件 ({severity_counts['重大']/total*100:.1f}%)")

        # 平均スコア
        avg_score = sum(r['validation']['score'] for r in results) / total
        print(f"\n平均品質スコア: {avg_score:.1f}/100")

        # 最も多い問題
        all_issues = []
        for r in results:
            all_issues.extend(r['validation']['issues'])

        if all_issues:
            issue_types = {}
            for issue in all_issues:
                issue_type = issue.split(':')[0]
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

            print("\n問題タイプ別集計:")
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {issue_type}: {count}件")

        # 詳細レポート保存
        self.save_detailed_report(results)

        return {
            'total': total,
            'valid': valid,
            'severity_counts': severity_counts,
            'average_score': avg_score,
            'results': results
        }

    def save_detailed_report(self, results: List[Dict]):
        """詳細レポートを保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'episode_validation_report_{timestamp}.json'

        # 重大な問題があるエピソードのみ抽出
        critical_issues = [
            r for r in results
            if r['validation']['severity'] in ['重大', '要修正']
        ]

        report = {
            'timestamp': timestamp,
            'total_episodes': len(results),
            'critical_issues_count': len(critical_issues),
            'critical_episodes': critical_issues[:20]  # 上位20件
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 詳細レポート保存: {report_file}")

if __name__ == "__main__":
    validator = ComprehensiveEpisodeValidator()

    # 既存エピソードファイルを検証
    csv_file = 'episodes_master_100_complete_20250923_133707.csv'

    results = validator.validate_all_episodes(csv_file)

    # 修正が必要なエピソード数
    needs_fix = results['total'] - results['valid']

    if needs_fix > 0:
        print(f"\n⚠️ {needs_fix}件のエピソードに修正が必要です")
        print("次のステップ: 自動修正スクリプトを実行してください")