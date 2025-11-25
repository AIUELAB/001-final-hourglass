#!/usr/bin/env python3
"""
Enhanced Episode Selection Algorithm
時代性と歴史的重要性を考慮した改善版選定アルゴリズム
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json


class EnhancedSelectionAlgorithm:
    """改善版エピソード選定アルゴリズム"""

    def __init__(self):
        self.current_year = datetime.now().year
        self.historical_keywords = [
            '史上初', '世界初', '唯一', '前人未到',
            'ワールドシリーズ', '金メダル', 'ノーベル賞',
            '50-50', 'MVP', '満票', '世界記録'
        ]
        self.recency_weight_factor = 0.02  # 年あたり2%のボーナス
        self.historical_bonus = 1.2  # 歴史的重要性20%ボーナス

        # 功績の主体性による重み付け
        self.ownership_multipliers = {
            'individual': 1.3,      # 個人功績（優先）
            'collaborative': 0.9,   # 共同功績
            'participation': 0.4,   # 参加功績（減点）
            'passive': 0.2         # 受動的功績（大幅減点）
        }

        # 国際的な賞の重み付け
        self.international_award_weights = {
            'ノーベル': 2.0,
            'グラミー': 1.5,
            'アカデミー': 1.4,
            'オリンピック': 1.3,
            'ワールドカップ': 1.2
        }

    def calculate_fact_score(self, fact: Dict, debug: bool = False) -> float:
        """
        改善版スコア計算（感動価値と歴史的重要性を重視）

        Args:
            fact: 事実データ
            debug: デバッグ出力を有効化

        Returns:
            調整済みスコア
        """
        # 基本スコア（感動価値を重視）
        emotional = fact.get('emotional_score', 0.5)
        educational = fact.get('educational_score', 0.5)

        # 感動価値の重み付けを強化（1.5倍）
        base_score = (emotional * 1.5) * educational

        # 時代性重み（新しさの影響を抑制）
        fact_year = self._extract_year(fact)
        years_diff = fact_year - 2000  # 2000年を基準
        recency_weight = 1 + (years_diff * self.recency_weight_factor * 0.5)  # 影響を半減
        recency_weight = max(0.8, min(1.2, recency_weight))  # 0.8-1.2の範囲に制限（狭める）

        # 歴史的重要性
        historical_importance = self._calculate_historical_importance(fact)

        # キーワード重要度（感動要素を追加）
        keyword_bonus = self._calculate_keyword_bonus(fact)

        # 感動要素による追加ボーナス
        fact_text = str(fact.get('fact', ''))
        keywords = fact.get('keywords', [])

        # オリンピック・世界大会ボーナス（RULE_141対応）
        olympic_keywords = ['オリンピック', '五輪', '世界選手権', 'ワールドカップ', 'ノーベル賞']
        olympic_bonus = 2.0 if any(k in fact_text or k in str(keywords) for k in olympic_keywords) else 1.0

        # ドラマ性ボーナス（RULE_142対応）
        drama_keywords = ['復活', '奇跡', '伝説', '涙', '挫折', '克服', '初', '史上',
                         '世界初', '日本初', '最年少', '最高齢', '唯一']
        drama_count = sum(1 for k in drama_keywords if k in fact_text or k in str(keywords))
        drama_bonus = 1 + (drama_count * 0.2)  # 各ドラマ要素で20%ボーナス

        # 功績の主体性による調整
        ownership_type = fact.get('ownership_type', 'individual')
        ownership_multiplier = self.ownership_multipliers.get(ownership_type, 1.0)

        # 国際的賞のボーナス
        international_bonus = self._calculate_international_award_bonus(fact)

        # 最終スコア計算（感動要素を含む）
        final_score = (base_score * recency_weight * historical_importance *
                      keyword_bonus * ownership_multiplier * international_bonus *
                      olympic_bonus * drama_bonus)

        if debug:
            print(f"[DEBUG] スコア計算詳細:")
            print(f"  - 基本スコア: {base_score:.3f} (感情:{emotional:.2f}×1.5 × 教育:{educational:.2f})")
            print(f"  - 時代性重み: {recency_weight:.3f} ({fact_year}年)")
            print(f"  - 歴史的重要性: {historical_importance:.3f}")
            print(f"  - キーワードボーナス: {keyword_bonus:.3f}")
            print(f"  - 功績主体性: {ownership_multiplier:.3f} ({ownership_type})")
            print(f"  - 国際的賞: {international_bonus:.3f}")
            print(f"  - オリンピック/世界大会: {olympic_bonus:.3f}")
            print(f"  - ドラマ性: {drama_bonus:.3f} ({drama_count}要素)")
            print(f"  - 最終スコア: {final_score:.3f}")

        return final_score

    def _extract_year(self, fact: Dict) -> int:
        """
        事実データから年を抽出

        Args:
            fact: 事実データ

        Returns:
            年（見つからない場合は推定）
        """
        # 直接的なyearフィールド
        if 'year' in fact:
            return fact['year']

        # キーワードから年を抽出
        keywords = fact.get('keywords', [])
        for keyword in keywords:
            if keyword.isdigit() and 1900 <= int(keyword) <= self.current_year:
                return int(keyword)
            # "2024年"のような形式
            if '年' in keyword:
                year_str = keyword.replace('年', '')
                if year_str.isdigit():
                    return int(year_str)

        # factテキストから年を推定
        fact_text = fact.get('fact', '')
        import re
        year_match = re.search(r'(19|20)\d{2}年', fact_text)
        if year_match:
            return int(year_match.group().replace('年', ''))

        # デフォルト（見つからない場合）
        return 2020

    def _calculate_historical_importance(self, fact: Dict) -> float:
        """
        歴史的重要性を計算

        Args:
            fact: 事実データ

        Returns:
            歴史的重要性スコア（1.0-1.5）
        """
        importance = 1.0

        # 明示的な歴史的重要性フィールド
        if 'historical_importance' in fact:
            return fact['historical_importance']

        # キーワードベースの評価
        keywords = fact.get('keywords', [])
        fact_text = fact.get('fact', '')

        # 特別な偉業のチェック
        special_achievements = {
            '史上初': 0.3,
            '世界初': 0.3,
            '唯一': 0.25,
            '前人未到': 0.25,
            'ワールドシリーズ': 0.2,
            '50-50': 0.3,
            '満票': 0.15,
            '世界記録': 0.2,
            'ノーベル賞': 0.25,
            '金メダル': 0.15
        }

        for achievement, bonus in special_achievements.items():
            if achievement in keywords or achievement in fact_text:
                importance += bonus

        return min(1.5, importance)  # 最大1.5倍

    def _calculate_keyword_bonus(self, fact: Dict) -> float:
        """
        キーワードに基づくボーナス計算

        Args:
            fact: 事実データ

        Returns:
            キーワードボーナス（1.0-1.3）
        """
        bonus = 1.0
        keywords = fact.get('keywords', [])

        # 重要キーワードのチェック
        important_keywords = {
            '史上初': 0.15,
            '世界初': 0.15,
            '唯一': 0.12,
            '革新': 0.08,
            '偉業': 0.08,
            '歴史的': 0.1
        }

        for keyword, value in important_keywords.items():
            if any(keyword in kw for kw in keywords):
                bonus += value

        return min(1.3, bonus)  # 最大1.3倍

    def _calculate_international_award_bonus(self, fact: Dict) -> float:
        """
        国際的賞のボーナス計算

        Args:
            fact: 事実データ

        Returns:
            国際的賞ボーナス（1.0-2.0）
        """
        bonus = 1.0
        fact_text = fact.get('fact', '')
        keywords = fact.get('keywords', [])

        # 国際的賞のチェック
        for award, weight in self.international_award_weights.items():
            if award in fact_text or any(award in kw for kw in keywords):
                bonus = max(bonus, weight)

        return bonus

    def evaluate_achievement_ownership(self, fact: Dict, person_name: str) -> float:
        """
        功績の主体性を評価

        Args:
            fact: 事実データ
            person_name: 人物名

        Returns:
            主体性スコア（0.0-1.3）
        """
        fact_text = fact.get('fact', '')

        # 受動的表現のチェック
        passive_indicators = [
            '参加', '選ばれ', '任命され', '誘われ',
            'メンバーとして', '一員として', '誘い'
        ]

        # 主導的表現のチェック
        active_indicators = [
            '創設', '設立', '開発', '作曲', '執筆',
            '発明', '発見', '受賞', '達成'
        ]

        # 特別なケース: YMOと坂本龍一
        if 'YMO' in fact_text and person_name == '坂本龍一':
            if '結成' in fact_text and '参加' not in fact_text and '誘い' not in fact_text:
                return 0.0  # 他人の功績として除外
            elif any(word in fact_text for word in ['参加', '誘い', 'メンバー']):
                return 0.4  # 参加功績として低評価

        # 一般的な評価
        if any(indicator in fact_text for indicator in passive_indicators):
            return self.ownership_multipliers['participation']
        elif any(indicator in fact_text for indicator in active_indicators):
            return self.ownership_multipliers['individual']
        else:
            return 1.0  # デフォルト

    def calculate_sensational_value(self, fact: Dict) -> float:
        """
        センセーショナル価値の計算

        Args:
            fact: 事実データ

        Returns:
            センセーショナル価値スコア（0-3.0）
        """
        sensational_score = 1.0
        fact_text = str(fact.get('fact', ''))
        keywords = fact.get('keywords', [])

        # ストーリー性要素（+0.5）
        story_keywords = ['転換', '初めて', 'きっかけ', '瞬間', '困難', '挫折',
                         '克服', '復活', '奇跡', '挑戦', '涙', '感動']
        if any(k in fact_text or k in str(keywords) for k in story_keywords):
            sensational_score += 0.5

        # 歴史的重要性（+0.5）
        historic_keywords = ['史上初', '世界初', '日本初', '最年少', '最高齢',
                            '唯一', '歴代', '記録', '前人未到']
        if any(k in fact_text or k in str(keywords) for k in historic_keywords):
            sensational_score += 0.5

        # 共感性要素（+0.5）
        empathy_keywords = ['勇気', '希望', '夢', '目標', '憧れ', '忘れられない',
                           '印象', '衝撃', '鮮烈', '感銘']
        if any(k in fact_text or k in str(keywords) for k in empathy_keywords):
            sensational_score += 0.5

        # 年齢による共感ボーナス（+0.5）
        age = fact.get('age', 30)
        if 7 <= age <= 12 or 18 <= age <= 25:
            sensational_score += 0.5

        return min(3.0, sensational_score)  # 最大3.0倍

    def select_best_fact(self, facts: List[Dict], top_n: int = 3, person_name: str = None) -> Tuple[Dict, List[Dict]]:
        """
        最適な事実を選定（上位候補も返す）

        Args:
            facts: 事実リスト
            top_n: 上位何件を返すか
            person_name: 人物名（功績主体性評価用）

        Returns:
            (最適な事実, 上位候補リスト)
        """
        if not facts:
            return None, []

        # 各事実のスコアを計算
        scored_facts = []
        for fact in facts:
            # 人物名が指定されている場合、功績主体性をチェック
            if person_name:
                ownership_score = self.evaluate_achievement_ownership(fact, person_name)
                if ownership_score == 0.0:
                    continue  # 他人の功績は除外

            base_score = self.calculate_fact_score(fact)
            sensational_multiplier = self.calculate_sensational_value(fact)
            final_score = base_score * sensational_multiplier

            scored_facts.append({
                'fact': fact,
                'score': final_score,
                'base_score': base_score,
                'sensational_multiplier': sensational_multiplier,
                'year': self._extract_year(fact)
            })

        # スコアでソート
        scored_facts.sort(key=lambda x: x['score'], reverse=True)

        if not scored_facts:
            return None, []

        # 最適な事実と上位候補
        best_fact = scored_facts[0]['fact']
        top_candidates = scored_facts[:top_n]

        return best_fact, top_candidates

    def compare_selections(self, old_fact: Dict, new_fact: Dict) -> Dict:
        """
        新旧の選定を比較

        Args:
            old_fact: 従来のアルゴリズムで選ばれた事実
            new_fact: 新アルゴリズムで選ばれた事実

        Returns:
            比較結果
        """
        old_score = old_fact.get('emotional_score', 0) * old_fact.get('educational_score', 0)
        new_score = self.calculate_fact_score(new_fact)

        improvement = ((new_score - old_score) / old_score) * 100 if old_score > 0 else 0

        return {
            'old_selection': {
                'fact': old_fact.get('fact', '')[:100] + '...',
                'year': self._extract_year(old_fact),
                'simple_score': old_score,
                'adjusted_score': self.calculate_fact_score(old_fact)
            },
            'new_selection': {
                'fact': new_fact.get('fact', '')[:100] + '...',
                'year': self._extract_year(new_fact),
                'score': new_score
            },
            'improvement_percent': improvement,
            'recommendation': 'USE_NEW' if improvement > 10 else 'KEEP_OLD'
        }


def demonstrate_improvement():
    """改善効果のデモンストレーション"""

    # 大谷翔平の例
    ohtani_facts = [
        {
            'age': 26,
            'fact': '2021年、投手で9勝、打者で46本塁打を記録し、満票でMVP受賞',
            'year': 2021,
            'emotional_score': 0.95,
            'educational_score': 0.9,
            'keywords': ['MVP', '46本塁打', '9勝', '2021年']
        },
        {
            'age': 30,
            'fact': '2024年、史上初の50本塁打50盗塁を達成（54本塁打、59盗塁）、さらにワールドシリーズ初優勝',
            'year': 2024,
            'emotional_score': 1.0,
            'educational_score': 1.0,
            'keywords': ['50-50', '54本塁打', '59盗塁', 'ワールドシリーズ優勝', '史上初', '2024年']
        }
    ]

    algorithm = EnhancedSelectionAlgorithm()

    print("=" * 60)
    print("Enhanced Episode Selection Algorithm - 大谷翔平デモ")
    print("=" * 60)

    # 従来のアルゴリズム
    old_best = max(ohtani_facts, key=lambda f: f['emotional_score'] * f['educational_score'])
    print("\n【従来のアルゴリズム】")
    print(f"選定: {old_best['fact']}")
    print(f"スコア: {old_best['emotional_score'] * old_best['educational_score']:.3f}")

    # 新アルゴリズム
    print("\n【新アルゴリズム】")
    best_fact, top_candidates = algorithm.select_best_fact(ohtani_facts, top_n=2)

    for i, candidate in enumerate(top_candidates, 1):
        print(f"\n{i}位: スコア {candidate['score']:.3f}")
        print(f"  {candidate['fact']['fact']}")
        algorithm.calculate_fact_score(candidate['fact'], debug=True)

    # 比較結果
    print("\n" + "=" * 60)
    print("比較結果")
    print("=" * 60)

    comparison = algorithm.compare_selections(old_best, best_fact)
    print(f"\n改善率: {comparison['improvement_percent']:.1f}%")
    print(f"推奨: {comparison['recommendation']}")

    if comparison['recommendation'] == 'USE_NEW':
        print("\n✅ 新アルゴリズムにより、より歴史的価値の高いエピソードを選定できます！")


if __name__ == "__main__":
    demonstrate_improvement()
