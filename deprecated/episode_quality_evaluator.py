#!/usr/bin/env python3
"""
エピソード品質評価システム

エピソード品質ルールv3.1に基づいて
生成されたエピソードの品質を詳細に評価するシステム

Author: Claude
Date: 2025-09-18
Version: 1.0.0
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import os

# ローカルインポート
try:
    from pdca_guardian import PDCAGuardian
except ImportError:
    PDCAGuardian = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QualityGrade(Enum):
    """品質グレード"""
    S = "S"  # 最高品質（スコア90以上）
    A = "A"  # 高品質（スコア75以上）
    B = "B"  # 標準品質（スコア60以上）
    C = "C"  # 低品質（スコア40以上）
    D = "D"  # 不適格（スコア40未満）

@dataclass
class QualityScore:
    """品質スコアの詳細"""
    total_score: float
    specificity_score: float
    impact_score: float
    emotional_score: float
    historical_accuracy_score: float
    readability_score: float
    uniqueness_score: float
    grade: QualityGrade
    violations: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

class EpisodeQualityEvaluator:
    """エピソード品質評価クラス"""

    def __init__(self, rules_path: str = "episode_quality_rules_v3_1.md"):
        """
        初期化

        Args:
            rules_path: 品質ルールファイルのパス
        """
        self.rules = self._load_quality_rules(rules_path)
        self.pdca_guardian = PDCAGuardian() if PDCAGuardian else None
        self.evaluation_cache = {}

    def _load_quality_rules(self, rules_path: str) -> Dict[str, Any]:
        """品質ルールの読み込み"""
        rules = {
            "required_format": "あなたと同じ{age}歳のとき、{person_name_display}は",
            "min_length": 100,
            "max_length": 500,
            "required_elements": {
                "specificity": {
                    "works": ["「", "」", "『", "』"],  # 作品名
                    "numbers": [r'\d+'],  # 数値
                    "proper_nouns": [r'[ァ-ヴー]{3,}', r'[A-Z][a-z]+'],  # 固有名詞
                },
                "impact": {
                    "achievement": ['優勝', '受賞', 'MVP', '金メダル', '新記録', '世界一', '日本一', '史上初'],
                    "challenge": ['困難', '逆境', '苦労', '努力', '克服', '乗り越え', '復活', '再起'],
                    "emotion": ['感動', '涙', '感謝', '喜び', '希望', '勇気', '決意', '覚悟'],
                    "milestone": ['デビュー', '転機', '独立', '結婚', '誕生', '引退', '卒業'],
                    "historical": ['初', '史上', '革命', '歴史的', '画期的', '伝説', '前人未到']
                }
            },
            "forbidden_patterns": {
                "duplication": ["享年", "◯◯歳の時", "◯◯歳で"],  # フォーマットとの重複
                "abstract": ["活躍", "頑張", "成長", "期待", "注目", "充実"],  # 抽象的表現
                "redundant": ["ました。ました。", "です。です。"]  # 文末重複
            }
        }

        # ルールファイルが存在すれば読み込み
        if os.path.exists(rules_path):
            # 実装は省略（Markdownパース）
            pass

        return rules

    def evaluate_episode(self, episode_text: str, person_data: Dict[str, Any]) -> QualityScore:
        """
        エピソードの品質を評価

        Args:
            episode_text: 評価するエピソードテキスト
            person_data: 人物データ

        Returns:
            品質スコアと評価詳細
        """
        # キャッシュチェック
        cache_key = f"{episode_text[:50]}_{person_data.get('person_id', '')}"
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        # 各項目のスコアを計算
        specificity = self._evaluate_specificity(episode_text)
        impact = self._evaluate_impact(episode_text)
        emotional = self._evaluate_emotional_resonance(episode_text)
        historical = self._evaluate_historical_accuracy(episode_text, person_data)
        readability = self._evaluate_readability(episode_text)
        uniqueness = self._evaluate_uniqueness(episode_text, person_data)

        # 違反チェック
        violations = self._check_violations(episode_text, person_data)

        # 総合スコア計算（重み付け）
        total_score = (
            specificity * 0.25 +  # 具体性 25%
            impact * 0.30 +       # インパクト 30%
            emotional * 0.20 +    # 感情的共鳴 20%
            historical * 0.10 +   # 歴史的正確性 10%
            readability * 0.10 +  # 読みやすさ 10%
            uniqueness * 0.05     # 独自性 5%
        )

        # 違反による減点
        if violations:
            total_score *= (1 - 0.1 * len(violations))  # 違反1つにつき10%減点

        # グレード判定
        grade = self._determine_grade(total_score)

        # 改善提案生成
        suggestions = self._generate_suggestions(
            specificity, impact, emotional, historical, readability, uniqueness, violations
        )

        result = QualityScore(
            total_score=total_score,
            specificity_score=specificity,
            impact_score=impact,
            emotional_score=emotional,
            historical_accuracy_score=historical,
            readability_score=readability,
            uniqueness_score=uniqueness,
            grade=grade,
            violations=violations,
            suggestions=suggestions
        )

        # キャッシュに保存
        self.evaluation_cache[cache_key] = result

        return result

    def _evaluate_specificity(self, text: str) -> float:
        """具体性の評価"""
        score = 0.0
        max_score = 100.0

        # 作品名チェック（30点）
        if re.search(r'「[^」]+」|『[^』]+』', text):
            score += 30.0

        # 数値データチェック（20点）
        numbers = re.findall(r'\d+[年月日時分秒人件個つ枚冊本話回目位円ドル万千億兆％%]', text)
        if numbers:
            score += min(20.0, len(numbers) * 5.0)

        # 固有名詞チェック（20点）
        proper_nouns = re.findall(r'[ァ-ヴー]{3,}|[A-Z][a-z]+', text)
        if proper_nouns:
            score += min(20.0, len(proper_nouns) * 4.0)

        # 具体的な事件・出来事（30点）
        event_keywords = [
            '大会', '選手権', '記録', '発表', '公開', '設立', '創業',
            '結婚', '離婚', '誕生', '死去', '引退', '就任', '辞任'
        ]
        event_count = sum(1 for keyword in event_keywords if keyword in text)
        if event_count:
            score += min(30.0, event_count * 10.0)

        return min(score, max_score)

    def _evaluate_impact(self, text: str) -> float:
        """インパクトの評価"""
        score = 0.0
        max_score = 100.0

        impact_categories = {
            'achievement': {
                'keywords': ['優勝', '受賞', 'MVP', '金メダル', '新記録', '世界一', '日本一', '史上初', '快挙'],
                'weight': 25.0
            },
            'challenge': {
                'keywords': ['困難', '逆境', '苦労', '努力', '克服', '乗り越え', '復活', '再起', '挑戦'],
                'weight': 20.0
            },
            'emotion': {
                'keywords': ['感動', '涙', '感謝', '喜び', '希望', '勇気', '決意', '覚悟', '情熱'],
                'weight': 20.0
            },
            'milestone': {
                'keywords': ['デビュー', '転機', '独立', '結婚', '誕生', '引退', '卒業', '開業', '創業'],
                'weight': 20.0
            },
            'historical': {
                'keywords': ['初', '史上', '革命', '歴史的', '画期的', '伝説', '前人未到', '偉業'],
                'weight': 15.0
            }
        }

        for category, info in impact_categories.items():
            if any(keyword in text for keyword in info['keywords']):
                score += info['weight']

        return min(score, max_score)

    def _evaluate_emotional_resonance(self, text: str) -> float:
        """感情的共鳴の評価"""
        score = 0.0
        max_score = 100.0

        # ストーリー性（40点）
        story_elements = {
            'setup': ['当時', 'その頃', 'それまで'],
            'conflict': ['しかし', 'ところが', 'だが'],
            'resolution': ['ついに', 'やがて', '結果']
        }

        story_score = sum(
            13.3 for elements in story_elements.values()
            if any(elem in text for elem in elements)
        )
        score += min(40.0, story_score)

        # 共感要素（30点）
        empathy_keywords = [
            '同じ', 'ような', '似た', '共通', 'あなた', '私たち',
            '誰もが', '皆', '多くの人'
        ]
        if any(keyword in text for keyword in empathy_keywords):
            score += 30.0

        # 感情表現（30点）
        emotion_expressions = [
            '喜び', '悲しみ', '怒り', '驚き', '感動', '感謝',
            '希望', '絶望', '勇気', '恐れ'
        ]
        emotion_count = sum(1 for expr in emotion_expressions if expr in text)
        if emotion_count:
            score += min(30.0, emotion_count * 10.0)

        return min(score, max_score)

    def _evaluate_historical_accuracy(self, text: str, person_data: Dict[str, Any]) -> float:
        """歴史的正確性の評価"""
        score = 100.0  # 減点方式

        # 明らかな矛盾チェック
        birth_year = person_data.get('birth_year')
        if birth_year:
            # 年代の整合性チェック
            year_mentions = re.findall(r'(\d{4})年', text)
            for year_str in year_mentions:
                year = int(year_str)
                if year < birth_year:
                    score -= 20.0  # 生まれる前の出来事

        # 一般的な歴史的誤りのパターン
        anachronisms = {
            'インターネット': 1990,
            'スマートフォン': 2007,
            'SNS': 2004,
            'AI': 1956
        }

        for term, min_year in anachronisms.items():
            if term in text and birth_year and birth_year < min_year - 50:
                score -= 10.0

        return max(0.0, score)

    def _evaluate_readability(self, text: str) -> float:
        """読みやすさの評価"""
        score = 100.0

        # 文長チェック
        sentences = re.split(r'[。！？]', text)
        for sentence in sentences:
            if len(sentence) > 100:  # 1文が長すぎる
                score -= 10.0
            elif len(sentence) < 10 and sentence:  # 短すぎる
                score -= 5.0

        # 漢字の割合チェック（適度な漢字使用）
        kanji_count = len(re.findall(r'[一-龠]', text))
        total_count = len(text)
        if total_count > 0:
            kanji_ratio = kanji_count / total_count
            if kanji_ratio > 0.5:  # 漢字が多すぎる
                score -= 15.0
            elif kanji_ratio < 0.1:  # 漢字が少なすぎる
                score -= 10.0

        # 句読点の適切さ
        comma_count = text.count('、')
        period_count = text.count('。')
        if comma_count < 2:  # 読点が少なすぎる
            score -= 10.0
        elif comma_count > 10:  # 読点が多すぎる
            score -= 10.0

        return max(0.0, score)

    def _evaluate_uniqueness(self, text: str, person_data: Dict[str, Any]) -> float:
        """独自性の評価"""
        score = 50.0  # 基本点

        # 一般的でない情報の含有
        common_phrases = [
            '生まれました', '亡くなりました', '活躍しました',
            '有名です', '知られています'
        ]

        for phrase in common_phrases:
            if phrase in text:
                score -= 10.0

        # 具体的で珍しいエピソード要素
        unique_elements = [
            '初めて', '唯一', 'たった一人', '前代未聞',
            '奇跡的', '偶然', '運命的'
        ]

        for element in unique_elements:
            if element in text:
                score += 10.0

        return min(100.0, max(0.0, score))

    def _check_violations(self, text: str, person_data: Dict[str, Any]) -> List[str]:
        """違反チェック"""
        violations = []

        # フォーマットチェック
        required_format = self.rules['required_format']
        age_pattern = r'あなたと同じ(\d+)歳のとき'
        age_match = re.search(age_pattern, text)

        if age_match:
            age = age_match.group(1)
            # 本文での年齢重複チェック
            main_text = text[age_match.end():]
            if f'{age}歳' in main_text:
                violations.append("RULE_115: 年齢の重複記載")

            # 人名の過度な繰り返しチェック
            person_name = person_data.get('person_name_ja', '')
            if person_name:
                name_count = main_text.count(person_name)
                if name_count > 2:
                    violations.append("RULE_115: 人名の過度な繰り返し")

        # 抽象的表現チェック
        abstract_patterns = self.rules['forbidden_patterns']['abstract']
        if any(pattern in text for pattern in abstract_patterns):
            violations.append("RULE_116: 抽象的な表現の使用")

        # 文長チェック
        if len(text) < self.rules['min_length']:
            violations.append("エピソードが短すぎます")
        elif len(text) > self.rules['max_length']:
            violations.append("エピソードが長すぎます")

        # PDCAガーディアンでのチェック（利用可能な場合）
        if self.pdca_guardian:
            # person_name_displayを追加（なければperson_name_jaを使用）
            person_name_display = person_data.get('person_name_display', person_data.get('person_name_ja', ''))
            pdca_violations = self.pdca_guardian.check_episode_quality(text, person_data, person_name_display)
            for violation in pdca_violations:
                # violationが辞書の場合とオブジェクトの場合の両方に対応
                if isinstance(violation, dict):
                    violations.append(f"PDCA: {violation.get('description', str(violation))}")
                else:
                    violations.append(f"PDCA: {violation.description}")

        return violations

    def _determine_grade(self, score: float) -> QualityGrade:
        """グレード判定"""
        if score >= 90:
            return QualityGrade.S
        elif score >= 75:
            return QualityGrade.A
        elif score >= 60:
            return QualityGrade.B
        elif score >= 40:
            return QualityGrade.C
        else:
            return QualityGrade.D

    def _generate_suggestions(self, specificity: float, impact: float, emotional: float,
                             historical: float, readability: float, uniqueness: float,
                             violations: List[str]) -> List[str]:
        """改善提案の生成"""
        suggestions = []

        # スコアが低い項目に対する提案
        if specificity < 60:
            suggestions.append("具体的な作品名、数値、固有名詞を追加してください")

        if impact < 60:
            suggestions.append("偉業、挑戦、転機などのインパクトある要素を含めてください")

        if emotional < 60:
            suggestions.append("読者が共感できるストーリー性を持たせてください")

        if historical < 80:
            suggestions.append("歴史的事実を再確認してください")

        if readability < 70:
            suggestions.append("文章を短く区切り、読みやすくしてください")

        if uniqueness < 50:
            suggestions.append("より独自性のあるエピソードを探してください")

        # 違反に対する提案
        if "RULE_115" in str(violations):
            suggestions.append("年齢や人名の重複を避け、代名詞を使用してください")

        if "RULE_116" in str(violations):
            suggestions.append("「活躍した」などの抽象的表現を具体的な内容に置き換えてください")

        return suggestions

    def batch_evaluate(self, episodes: List[Dict[str, Any]]) -> pd.DataFrame:
        """複数エピソードの一括評価"""
        results = []

        for episode in episodes:
            text = episode.get('episode_text', '')
            person_data = episode.get('person_data', {})

            score = self.evaluate_episode(text, person_data)

            results.append({
                'person_id': person_data.get('person_id', ''),
                'person_name': person_data.get('person_name_ja', ''),
                'age': episode.get('age', 0),
                'episode_text': text[:50] + '...',
                'total_score': score.total_score,
                'grade': score.grade.value,
                'specificity': score.specificity_score,
                'impact': score.impact_score,
                'emotional': score.emotional_score,
                'violations': ', '.join(score.violations),
                'suggestions': ', '.join(score.suggestions[:2])
            })

        return pd.DataFrame(results)

    def export_evaluation_report(self, evaluations: pd.DataFrame, output_path: str):
        """評価レポートのエクスポート"""
        # サマリー統計
        summary = {
            'total_episodes': len(evaluations),
            'average_score': evaluations['total_score'].mean(),
            'grade_distribution': evaluations['grade'].value_counts().to_dict(),
            'common_violations': evaluations['violations'].value_counts().head(5).to_dict()
        }

        # レポート作成
        report = {
            'summary': summary,
            'evaluations': evaluations.to_dict('records')
        }

        # JSON出力
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"評価レポートを{output_path}に出力しました")

        # CSV出力も
        csv_path = output_path.replace('.json', '.csv')
        evaluations.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"評価データを{csv_path}に出力しました")


def main():
    """テスト実行"""
    evaluator = EpisodeQualityEvaluator()

    # テストエピソード
    test_episodes = [
        {
            'episode_text': 'あなたと同じ30歳のとき、坂本龍馬は幕府の開国派であった勝海舟を討つつもりで、赤坂・氷川神社近くの屋敷を訪れました。ところが、勝が語った世界の情勢や海軍の必要性、日本の未来像に強い衝撃を受けます。龍馬はその場で考えを改め、勝に弟子入りを願い出ました。この出会いがきっかけとなり、やがて海援隊の設立や大政奉還へとつながっていきました。',
            'person_data': {'person_id': 'P000001', 'person_name_ja': '坂本龍馬', 'birth_year': 1836},
            'age': 30
        },
        {
            'episode_text': 'あなたと同じ25歳のとき、イチローはオリックス・ブルーウェーブで「振り子打法」を完成させ、シーズン210安打の日本記録を樹立しました。この年、打率.385、130打点で史上初のシーズン200安打を達成。パ・リーグMVPに輝き、「天才」と呼ばれるようになりました。',
            'person_data': {'person_id': 'P000002', 'person_name_ja': 'イチロー', 'birth_year': 1973},
            'age': 25
        }
    ]

    # 評価実行
    results = evaluator.batch_evaluate(test_episodes)

    # 結果表示
    print("\n=== エピソード品質評価結果 ===")
    print(results.to_string())

    # レポート出力
    evaluator.export_evaluation_report(results, "episode_evaluation_report.json")


if __name__ == "__main__":
    main()
