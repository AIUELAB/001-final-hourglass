#!/usr/bin/env python3
"""
エピソード年齢選択評価システム
各年齢の成果の重要度を評価し、最適な年齢を選択する
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgeAchievement:
    """年齢ごとの成果データ"""
    age: int
    achievement: str
    importance_score: float
    category: str
    impact_level: str  # 'world', 'asia', 'japan', 'industry', 'personal'

class AgeSelectionEvaluator:
    """年齢選択評価システム"""

    def __init__(self):
        """初期化"""
        # 重要度キーワードと得点
        self.importance_keywords = {
            # 世界的成果（最高点）
            '世界初': 10.0,
            '史上初': 10.0,
            'ノーベル賞': 10.0,
            'アカデミー賞': 9.5,
            'グラミー賞': 9.0,
            '世界記録': 9.5,
            '世界一': 9.0,
            'オリンピック': 9.0,
            '五輪': 9.0,
            '金メダル': 9.0,

            # アジア・国際的成果
            'アジア初': 9.0,
            'アジア人初': 9.0,
            '日本人初': 8.5,
            '日本初': 8.0,
            '国民栄誉賞': 8.5,
            '文化勲章': 8.0,

            # 国内最高レベル
            '最年少': 8.0,
            '最多': 8.0,
            '新記録': 7.5,
            '1位': 7.0,
            '受賞': 6.5,
            'デビュー': 6.0,

            # 商業的成功
            '億円': 7.5,
            '万部': 7.0,
            '万枚': 7.0,
            '大ヒット': 7.0,
            'ベストセラー': 7.0,

            # 社会的影響
            '社会現象': 8.0,
            '革命': 7.5,
            '革新': 7.0,
            '先駆者': 7.0,
            '開拓': 7.0,

            # アマチュア時代（低スコア）
            'アマチュア': 3.0,
            '学生': 3.0,
            '高校': 2.5,
            '大学': 3.0,
        }

        # コンテキスト依存キーワード（前後の文脈で意味が変わる）
        self.context_keywords = {
            # メジャー大会関連
            ('マスターズ', '優勝'): 10.0,  # プロとしての優勝
            ('マスターズ', 'アマチュア'): 6.0,  # アマチュア賞
            ('メジャー', '制覇'): 10.0,
            ('メジャー', '優勝'): 10.0,
            ('PGA', '優勝'): 8.0,
            ('優勝', 'アマチュア'): 5.0,  # アマチュアでの優勝は価値を下げる
        }

        # カテゴリ別の重み付け
        self.category_weights = {
            'sports': {
                'オリンピック': 10.0,
                'メジャー': 10.0,
                'マスターズ': 10.0,
                'ワールドカップ': 9.5,
                'プロ': 6.0,
                'アマチュア': 4.0,
            },
            'business': {
                '創業': 8.0,
                'IPO': 9.0,
                '売上': 7.0,
                '革新': 8.5,
            },
            'entertainment': {
                '紅白': 8.0,
                'アカデミー': 10.0,
                '主演': 7.5,
                'デビュー': 6.0,
            },
            'science': {
                'ノーベル': 10.0,
                '発見': 9.0,
                '発明': 8.5,
                '論文': 6.0,
            }
        }

    def evaluate_single_achievement(self, age: int, achievement: str, category: str = 'general') -> float:
        """
        単一の成果の重要度を評価

        Returns:
            重要度スコア（0-10）
        """
        score = 5.0  # 基本スコア

        # コンテキスト依存キーワードを先にチェック
        for (keyword1, keyword2), points in self.context_keywords.items():
            if keyword1 in achievement and keyword2 in achievement:
                score = max(score, points)

        # 通常のキーワードマッチング
        for keyword, points in self.importance_keywords.items():
            if keyword in achievement:
                # アマチュアキーワードは他のポジティブキーワードを打ち消す
                if keyword == 'アマチュア' and any(k in achievement for k in ['優勝', 'マスターズ', 'メジャー']):
                    # アマチュアでの成果は価値を下げる
                    score = min(score, points + 2.0)
                else:
                    score = max(score, points)

        # カテゴリ特有の重み付け
        if category in self.category_weights:
            for keyword, points in self.category_weights[category].items():
                if keyword in achievement:
                    # アマチュアの場合は価値を下げる
                    if 'アマチュア' in achievement:
                        points = points * 0.6
                    score = max(score, points)

        # 特定の組み合わせに対する追加評価
        if 'マスターズ' in achievement and '優勝' in achievement and 'アマチュア' not in achievement:
            score = 10.0  # マスターズ優勝（プロ）は最高点
        elif 'メジャー' in achievement and '制覇' in achievement:
            score = 10.0  # メジャー制覇も最高点
        elif 'アジア人' in achievement and ('初' in achievement or '史上初' in achievement):
            if '優勝' in achievement or '制覇' in achievement:
                score = max(score, 9.5)

        # 複数の重要キーワードが含まれる場合はボーナス（アマチュアを除く）
        important_keywords = [k for k in self.importance_keywords if k != 'アマチュア' and k in achievement]
        if len(important_keywords) >= 2:
            score += 0.3 * min(len(important_keywords) - 1, 2)  # 最大+0.6

        # スコアを0-10に正規化
        return min(score, 10.0)

    def select_best_age(
        self,
        person_name: str,
        achievements: Dict[str, str],
        notable_ages: List[int] = None,
        category: str = 'general'
    ) -> Tuple[int, str, float]:
        """
        最適な年齢を選択

        Args:
            person_name: 人物名
            achievements: {年齢: 成果} の辞書
            notable_ages: 注目すべき年齢のリスト（省略可）
            category: カテゴリ

        Returns:
            (選択された年齢, 理由, スコア)
        """
        evaluations = []

        # すべての成果を評価
        for age_str, achievement in achievements.items():
            age = int(age_str)
            score = self.evaluate_single_achievement(age, achievement, category)
            evaluations.append({
                'age': age,
                'achievement': achievement,
                'score': score
            })

        # notable_agesが指定されている場合、それらを優先的に考慮
        if notable_ages:
            for eval_item in evaluations:
                if eval_item['age'] in notable_ages:
                    eval_item['score'] += 0.5  # ボーナス

        # スコアでソート（降順）
        evaluations.sort(key=lambda x: x['score'], reverse=True)

        # 最高スコアの成果を選択
        if evaluations:
            best = evaluations[0]

            # 選択理由を生成
            reason = self._generate_selection_reason(
                person_name, best, evaluations
            )

            return best['age'], reason, best['score']

        # デフォルト
        return 30, "デフォルト年齢", 5.0

    def _generate_selection_reason(
        self,
        person_name: str,
        selected: Dict,
        all_evaluations: List[Dict]
    ) -> str:
        """選択理由を生成"""

        reasons = []

        # なぜこの年齢が選ばれたか
        if selected['score'] >= 9.0:
            reasons.append(f"世界的・歴史的に最も重要な成果（スコア: {selected['score']:.1f}）")
        elif selected['score'] >= 8.0:
            reasons.append(f"国際的に重要な成果（スコア: {selected['score']:.1f}）")
        elif selected['score'] >= 7.0:
            reasons.append(f"国内で重要な成果（スコア: {selected['score']:.1f}）")
        else:
            reasons.append(f"キャリアの重要な節目（スコア: {selected['score']:.1f}）")

        # 他の選択肢との比較
        if len(all_evaluations) > 1:
            second_best = all_evaluations[1]
            if selected['score'] - second_best['score'] >= 2.0:
                reasons.append("他の年齢と比較して圧倒的に重要")
            elif selected['score'] - second_best['score'] >= 1.0:
                reasons.append("複数の選択肢から最も影響力のある成果を選択")

        # 具体的な成果の特徴
        if 'マスターズ' in selected['achievement']:
            reasons.append("ゴルフ最高峰の大会での歴史的快挙")
        elif 'ノーベル' in selected['achievement']:
            reasons.append("人類への貢献が認められた最高の栄誉")
        elif 'オリンピック' in selected['achievement'] or '五輪' in selected['achievement']:
            reasons.append("世界最高の舞台での偉業")
        elif '世界初' in selected['achievement'] or '史上初' in selected['achievement']:
            reasons.append("前人未到の記録")

        return " / ".join(reasons)

    def validate_existing_episodes(self, csv_file: str) -> List[Dict]:
        """
        既存エピソードの年齢選択を検証

        Returns:
            問題のあるエピソードのリスト
        """
        import csv

        issues = []

        # CSVファイルを読み込み
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                person_name = row['person_name']
                current_age = int(row['user_age'])
                episode_text = row['episode_text']

                # この人物の他の可能性を調査する必要がある
                # （実際の実装では、データベースや別ファイルから取得）

                # 簡易的な評価
                score = self.evaluate_single_achievement(
                    current_age, episode_text, row.get('category', 'general')
                )

                if score < 7.0:
                    issues.append({
                        'person_name': person_name,
                        'current_age': current_age,
                        'score': score,
                        'episode': episode_text[:100] + '...',
                        'recommendation': '他の年齢の成果を検討すべき'
                    })

        return issues

# デモ実行
if __name__ == "__main__":
    evaluator = AgeSelectionEvaluator()

    # 松山英樹の例
    print("=" * 60)
    print("松山英樹の年齢選択評価")
    print("=" * 60)

    matsuyama_achievements = {
        "19": "2011年マスターズでアマチュア最優秀（日本人初）",
        "21": "2013年PGAツアー初優勝（メモリアル・トーナメント）",
        "29": "2021年マスターズ優勝（日本人男子初のメジャー制覇）"
    }

    best_age, reason, score = evaluator.select_best_age(
        "松山英樹",
        matsuyama_achievements,
        notable_ages=[19, 21, 29],
        category='sports'
    )

    print(f"\n選択された年齢: {best_age}歳")
    print(f"選択理由: {reason}")
    print(f"重要度スコア: {score:.1f}/10.0")
    print(f"\n成果: {matsuyama_achievements[str(best_age)]}")

    # 全年齢の評価を表示
    print("\n全年齢の評価:")
    for age_str, achievement in matsuyama_achievements.items():
        score = evaluator.evaluate_single_achievement(
            int(age_str), achievement, 'sports'
        )
        print(f"  {age_str}歳: スコア {score:.1f} - {achievement}")
