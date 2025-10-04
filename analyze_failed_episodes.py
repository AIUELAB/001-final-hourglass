#!/usr/bin/env python3
"""
不合格エピソード詳細分析システム
残り5件の不合格エピソードを詳細分析して修正案を提示

Author: Claude Code
Date: 2025-10-01
Version: 1.0.0
"""

import csv
from typing import Dict, List
from unified_validation_system import UnifiedValidationSystem


class FailedEpisodeAnalyzer:
    """不合格エピソード分析システム"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.validator = UnifiedValidationSystem()

    def load_failed_episodes(self) -> List[Dict]:
        """不合格エピソードのみ読み込む"""
        failed_episodes = []

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('is_valid') == 'False':
                    episode = {
                        'person_name': row['person_name'],
                        'user_age': row['user_age'],
                        'episode_age': row['episode_age'],
                        'episode_text': row['episode_text'],
                        'character_count': int(row['character_count']),
                        'category': row['category'],
                        'corrections_applied': row.get('corrections_applied', 'None')
                    }
                    failed_episodes.append(episode)

        return failed_episodes

    def analyze_episode(self, episode: Dict) -> Dict:
        """エピソードの詳細分析"""
        result = self.validator.validate_episode(episode)

        analysis = {
            'person_name': episode['person_name'],
            'current_text': episode['episode_text'],
            'character_count': episode['character_count'],
            'violations': [],
            'warnings': [],
            'scores': {
                'emotional_impact': result.emotional_impact_score,
                'specificity': result.specificity_score
            },
            'improvement_plan': []
        }

        # 違反の詳細分析
        for violation in result.violations:
            analysis['violations'].append({
                'rule': violation.rule_name,
                'severity': violation.severity.value,
                'message': violation.message,
                'suggestion': violation.suggestion,
                'details': violation.details
            })

        # 警告の収集
        for warning in result.warnings:
            analysis['warnings'].append({
                'rule': warning.rule_name,
                'message': warning.message,
                'suggestion': warning.suggestion
            })

        # 改善計画の生成
        analysis['improvement_plan'] = self._generate_improvement_plan(episode, result)

        return analysis

    def _generate_improvement_plan(self, episode: Dict, result) -> List[str]:
        """具体的な改善計画を生成"""
        plan = []
        text = episode['episode_text']
        char_count = len(text)

        # 文字数の問題
        if char_count < 130:
            shortage = 130 - char_count
            plan.append(f"【文字数不足】あと{shortage}文字追加が必要")
            plan.append("  → 具体的な数値データ（記録、賞金額、視聴率等）を追加")
            plan.append("  → 固有名詞（賞名、大会名、作品名）を2個以上追加")
            plan.append("  → 成果の規模や影響範囲を具体的に記述")
        elif char_count > 250:
            excess = char_count - 250
            plan.append(f"【文字数超過】{excess}文字削減が必要")
            plan.append("  → 冗長な表現を簡潔にする")
            plan.append("  → 重複する情報を統合する")

        # 感銘スコアが低い
        if result.emotional_impact_score < 0.6:
            plan.append(f"【感銘スコア低】現在{result.emotional_impact_score:.2f} → 0.6以上が目標")
            plan.append("  → 「史上初」「日本人初」「世界記録」などの独自性を強調")
            plan.append("  → 「世界」「全国」「国民」など規模を示す表現を追加")
            plan.append("  → 具体的な数値記録を前面に出す")

        # 具体性スコアが低い
        if result.specificity_score < 0.5:
            plan.append(f"【具体性低】現在{result.specificity_score:.2f} → 0.5以上が目標")
            plan.append("  → 数値データを追加（年齢、金額、回数、順位等）")
            plan.append("  → 固有名詞を最低2個追加（賞名、大会名、作品名）")
            plan.append("  → 抽象的表現を具体的表現に置き換える")

        # その他の違反
        for violation in result.violations:
            if violation.rule_name == 'duplicate_age':
                plan.append("【年齢重複】同じ年齢が複数回記載されています")
                plan.append("  → 各年齢は1回のみ記載してください")

        return plan

    def generate_correction_suggestion(self, episode: Dict, analysis: Dict) -> str:
        """修正案を生成"""
        text = episode['episode_text']
        char_count = len(text)

        suggestion = f"\n{'='*80}\n"
        suggestion += f"【{episode['person_name']}】修正提案\n"
        suggestion += f"{'='*80}\n\n"

        suggestion += f"【現在のテキスト】({char_count}文字)\n"
        suggestion += f"{text}\n\n"

        suggestion += f"【問題点】\n"
        for i, violation in enumerate(analysis['violations'], 1):
            suggestion += f"{i}. {violation['message']}\n"
            if violation['suggestion']:
                suggestion += f"   → {violation['suggestion']}\n"

        if analysis['warnings']:
            suggestion += f"\n【警告】\n"
            for i, warning in enumerate(analysis['warnings'], 1):
                suggestion += f"{i}. {warning['message']}\n"

        suggestion += f"\n【スコア】\n"
        suggestion += f"感銘: {analysis['scores']['emotional_impact']:.2f} / 1.00\n"
        suggestion += f"具体性: {analysis['scores']['specificity']:.2f} / 1.00\n"

        suggestion += f"\n【改善計画】\n"
        for i, plan_item in enumerate(analysis['improvement_plan'], 1):
            suggestion += f"{plan_item}\n"

        suggestion += f"\n{'='*80}\n"

        return suggestion

    def analyze_all_failed(self):
        """全不合格エピソードの分析"""
        episodes = self.load_failed_episodes()

        print(f"🔍 不合格エピソード: {len(episodes)}件\n")

        all_suggestions = []

        for episode in episodes:
            analysis = self.analyze_episode(episode)
            suggestion = self.generate_correction_suggestion(episode, analysis)
            print(suggestion)
            all_suggestions.append({
                'episode': episode,
                'analysis': analysis,
                'suggestion': suggestion
            })

        return all_suggestions


def main():
    """メイン実行"""
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/episodes_auto_corrected_20251001_134934.csv"

    analyzer = FailedEpisodeAnalyzer(csv_path)
    suggestions = analyzer.analyze_all_failed()

    print(f"\n✅ 分析完了: {len(suggestions)}件の修正提案を生成しました")


if __name__ == "__main__":
    main()
