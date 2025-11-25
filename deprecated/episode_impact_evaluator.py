#!/usr/bin/env python3
"""
エピソードインパクト評価システム
その人物の最も重要なエピソードを選定し、評価する
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class EpisodeCandidate:
    """エピソード候補"""
    actual_age: int  # 実際の年齢
    target_age: int  # 割り当て先の年齢カテゴリ（1,10,20,30,40,50,60）
    text: str  # エピソード本文
    impact_score: float  # インパクトスコア
    keywords: List[str]  # 含まれるキーワード
    historical_significance: str  # 歴史的意義の説明


class EpisodeImpactEvaluator:
    """エピソードインパクト評価システム"""

    def __init__(self):
        """初期化"""
        # インパクトキーワード辞書
        self.impact_keywords = {
            'historical': {
                'keywords': ['初', '史上', '記録', '革命', '歴史', '偉業', '快挙', '初めて', '世界初', '日本初', '史上最高', '前人未到'],
                'weight': 0.4,
                'score_per_keyword': 10
            },
            'social': {
                'keywords': ['話題', '注目', '世界', '社会', '影響', '衝撃', '騒然', 'ブーム', '現象', '旋風', '熱狂'],
                'weight': 0.3,
                'score_per_keyword': 10
            },
            'achievement': {
                'keywords': ['優勝', '受賞', 'MVP', '金メダル', 'ノーベル', 'アカデミー', '新記録', '達成', 'グランプリ', '最優秀', '殿堂'],
                'weight': 0.2,
                'score_per_keyword': 15
            },
            'turning_point': {
                'keywords': ['転機', 'デビュー', '引退', '独立', '結婚', '誕生', '死去', '移籍', '転身', '決断', '起業'],
                'weight': 0.1,
                'score_per_keyword': 10
            }
        }

        # 年齢カテゴリ
        self.age_categories = [1, 10, 20, 30, 40, 50, 60]

        # 年齢調整許容範囲
        self.age_adjustment_range = 3

    def calculate_impact_score(self, episode_text: str) -> Tuple[float, Dict[str, Any]]:
        """
        エピソードのインパクトスコアを計算

        Args:
            episode_text: エピソード本文

        Returns:
            (total_score, details)
        """
        details = {}
        total_score = 0

        for category, config in self.impact_keywords.items():
            category_score = 0
            found_keywords = []

            for keyword in config['keywords']:
                if keyword in episode_text:
                    category_score += config['score_per_keyword']
                    found_keywords.append(keyword)

            # カテゴリごとの上限を適用
            max_score = 100 * config['weight']
            category_score = min(category_score, max_score)

            details[category] = {
                'score': category_score,
                'keywords': found_keywords,
                'weight': config['weight']
            }

            total_score += category_score

        return total_score, details

    def evaluate_historical_significance(self, episode_text: str) -> str:
        """
        歴史的意義を評価

        Args:
            episode_text: エピソード本文

        Returns:
            歴史的意義の説明
        """
        significance_patterns = {
            '世界初': '世界で初めての偉業',
            '日本初': '日本で初めての快挙',
            '史上最': '歴史上最高の記録',
            '新記録': '従来の記録を更新',
            'ノーベル': 'ノーベル賞受賞の栄誉',
            'MVP': '最優秀選手に選出',
            '優勝': '頂点に立つ',
            '革命': '既存の概念を変革',
            'デビュー': 'キャリアの出発点',
            '引退': 'キャリアの集大成'
        }

        for pattern, description in significance_patterns.items():
            if pattern in episode_text:
                return description

        return '重要な出来事'

    def select_best_episodes_for_person(
        self,
        person_data: Dict[str, Any],
        all_episodes: List[Dict[str, Any]]
    ) -> List[EpisodeCandidate]:
        """
        人物に最適な7つのエピソードを選定

        Args:
            person_data: 人物データ
            all_episodes: すべてのエピソード候補

        Returns:
            選定された7つのエピソード
        """
        # エピソード候補をスコアリング
        candidates = []
        for episode in all_episodes:
            score, details = self.calculate_impact_score(episode['text'])

            candidate = EpisodeCandidate(
                actual_age=episode.get('actual_age', episode.get('age', 0)),
                target_age=0,  # 後で決定
                text=episode['text'],
                impact_score=score,
                keywords=[kw for cat in details.values() for kw in cat['keywords']],
                historical_significance=self.evaluate_historical_significance(episode['text'])
            )
            candidates.append(candidate)

        # スコアでソート
        candidates.sort(key=lambda x: x.impact_score, reverse=True)

        # 各年齢カテゴリに最適なエピソードを割り当て
        selected = []
        used_candidates = set()

        for target_age in self.age_categories:
            best_candidate = None
            best_score = -1

            for i, candidate in enumerate(candidates):
                if i in used_candidates:
                    continue

                # 年齢の差を計算
                age_diff = abs(candidate.actual_age - target_age)

                # 調整可能範囲内かチェック
                if age_diff <= self.age_adjustment_range:
                    # スコアと年齢の近さを考慮
                    adjusted_score = candidate.impact_score * (1 - age_diff * 0.1)

                    if adjusted_score > best_score:
                        best_candidate = candidate
                        best_score = adjusted_score
                        best_index = i

            if best_candidate:
                best_candidate.target_age = target_age
                selected.append(best_candidate)
                used_candidates.add(best_index)
            else:
                # 該当なしの場合、デフォルトエピソードを作成
                selected.append(self._create_default_episode(target_age, person_data))

        return selected

    def _create_default_episode(self, age: int, person_data: Dict[str, Any]) -> EpisodeCandidate:
        """
        デフォルトエピソードを作成

        Args:
            age: 年齢
            person_data: 人物データ

        Returns:
            デフォルトエピソード
        """
        person_name = person_data.get('person_name_display', '人物')

        default_texts = {
            1: f"あなたと同じ1歳のとき、{person_name}は家族の愛情に包まれて成長していました。",
            10: f"あなたと同じ10歳のとき、{person_name}は将来の夢に向かって努力を始めていました。",
            20: f"あなたと同じ20歳のとき、{person_name}はキャリアの第一歩を踏み出していました。",
            30: f"あなたと同じ30歳のとき、{person_name}は専門分野で実績を積み重ねていました。",
            40: f"あなたと同じ40歳のとき、{person_name}は円熟期を迎え、更なる高みを目指していました。",
            50: f"あなたと同じ50歳のとき、{person_name}は後進の育成にも力を注いでいました。",
            60: f"あなたと同じ60歳のとき、{person_name}はこれまでの功績が評価され、多くの人に影響を与えていました。"
        }

        return EpisodeCandidate(
            actual_age=age,
            target_age=age,
            text=default_texts.get(age, f"あなたと同じ{age}歳のとき、{person_name}は活動していました。"),
            impact_score=0,
            keywords=[],
            historical_significance='通常のエピソード'
        )

    def adjust_episode_for_age(self, candidate: EpisodeCandidate) -> str:
        """
        年齢調整を含むエピソードテキストを生成

        Args:
            candidate: エピソード候補

        Returns:
            調整後のエピソードテキスト
        """
        if candidate.actual_age == candidate.target_age:
            # 年齢調整不要
            return candidate.text

        # 年齢調整が必要な場合
        age_diff = candidate.actual_age - candidate.target_age

        if age_diff > 0:
            # 実際はより後の出来事
            adjustment_text = f"（実際には{candidate.actual_age}歳での出来事）"
        else:
            # 実際はより前の出来事
            adjustment_text = f"（実際には{candidate.actual_age}歳での出来事）"

        # エピソードテキストの調整
        # "あなたと同じX歳のとき"の部分を target_age に変更
        adjusted_text = re.sub(
            r'あなたと同じ\d+歳のとき',
            f'あなたと同じ{candidate.target_age}歳のとき',
            candidate.text
        )

        # 実年齢の記載がある場合は調整
        adjusted_text = re.sub(
            f'{candidate.actual_age}歳',
            f'{candidate.target_age}歳{adjustment_text}',
            adjusted_text,
            count=1  # 最初の1箇所のみ
        )

        return adjusted_text

    def generate_impact_report(self, candidates: List[EpisodeCandidate]) -> str:
        """
        インパクトレポートを生成

        Args:
            candidates: エピソード候補リスト

        Returns:
            レポート文字列
        """
        report = []
        report.append("="*60)
        report.append("📊 エピソードインパクト評価レポート")
        report.append("="*60)
        report.append("")

        total_impact = sum(c.impact_score for c in candidates)
        avg_impact = total_impact / len(candidates) if candidates else 0

        report.append(f"総合インパクトスコア: {total_impact:.1f}")
        report.append(f"平均インパクトスコア: {avg_impact:.1f}")
        report.append("")

        # グレード判定
        if avg_impact >= 70:
            grade = "S級（極めて重要）"
        elif avg_impact >= 50:
            grade = "A級（非常に重要）"
        elif avg_impact >= 30:
            grade = "B級（重要）"
        else:
            grade = "C級（改善が必要）"

        report.append(f"総合評価: {grade}")
        report.append("")

        # 個別エピソード評価
        report.append("## 個別エピソード評価")
        for candidate in sorted(candidates, key=lambda x: x.target_age):
            report.append("")
            report.append(f"### {candidate.target_age}歳")
            report.append(f"インパクトスコア: {candidate.impact_score:.1f}点")
            report.append(f"歴史的意義: {candidate.historical_significance}")
            if candidate.keywords:
                report.append(f"キーワード: {', '.join(candidate.keywords[:5])}")
            if candidate.actual_age != candidate.target_age:
                report.append(f"年齢調整: {candidate.actual_age}歳 → {candidate.target_age}歳")
            report.append(f"本文: {candidate.text[:100]}...")

        return "\n".join(report)


def test_impact_evaluator():
    """テスト実行"""
    evaluator = EpisodeImpactEvaluator()

    # テスト用の人物データ
    person_data = {
        'person_name_display': '大谷翔平',
        'person_id': 'TEST001'
    }

    # テスト用のエピソード候補
    all_episodes = [
        {
            'actual_age': 1,
            'text': 'あなたと同じ1歳のとき、大谷翔平は岩手県で生まれました。'
        },
        {
            'actual_age': 18,
            'text': 'あなたと同じ18歳のとき、大谷翔平は日本ハムに入団し、プロ野球選手としてのキャリアをスタートしました。'
        },
        {
            'actual_age': 20,
            'text': 'あなたと同じ20歳のとき、大谷翔平は日本プロ野球史上初の「2桁勝利・2桁本塁打」を達成しました。'
        },
        {
            'actual_age': 23,
            'text': 'あなたと同じ23歳のとき、大谷翔平はメジャーリーグに移籍し、エンゼルスで二刀流として新人王を獲得しました。'
        },
        {
            'actual_age': 27,
            'text': 'あなたと同じ27歳のとき、大谷翔平はアメリカンリーグMVPを満票で受賞し、日本人として2人目の快挙を達成しました。'
        },
        {
            'actual_age': 28,
            'text': 'あなたと同じ28歳のとき、大谷翔平はWBC日本代表として世界一に貢献し、大会MVPに選出されました。'
        }
    ]

    # 最適なエピソードを選定
    selected = evaluator.select_best_episodes_for_person(person_data, all_episodes)

    # レポート生成
    report = evaluator.generate_impact_report(selected)
    print(report)

    # 年齢調整の例を表示
    print("\n" + "="*60)
    print("年齢調整の例")
    print("="*60)
    for candidate in selected:
        if candidate.actual_age != candidate.target_age:
            adjusted_text = evaluator.adjust_episode_for_age(candidate)
            print(f"\n{candidate.target_age}歳カテゴリ:")
            print(f"元の年齢: {candidate.actual_age}歳")
            print(f"調整後: {adjusted_text[:150]}...")


if __name__ == "__main__":
    test_impact_evaluator()
