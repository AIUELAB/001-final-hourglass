"""データ品質管理モジュール

重複検出、異常値検出、完全性チェック、品質スコア算出を提供
"""

import csv
import statistics
from typing import List, Dict, Tuple, Set
from pathlib import Path
from collections import defaultdict
from app.utils.score_calculator import (
    normalize_person_name,
    calculate_text_similarity,
    is_similar_episode
)


class DataQualityManager:
    """データ品質管理クラス"""

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: CSVファイルパス
        """
        self.csv_path = Path(csv_path)
        self.episodes: List[Dict] = []
        self.score_columns = [
            '記憶性スコア',
            '共感性スコア',
            '意外性スコア',
            '生成品質スコア',
            '教育的価値',
            'ストーリー品質',
            '事実密度'
        ]
        self.load_episodes()

    def load_episodes(self):
        """CSVからエピソードデータを読み込み"""
        self.episodes = []

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # ヘッダー行は1行目
                episode = dict(row)
                episode['row_number'] = row_num

                # スコアを数値化
                for col in self.score_columns:
                    value = row.get(col, '').strip()
                    if value:
                        try:
                            episode[col] = float(value)
                        except ValueError:
                            episode[col] = None
                    else:
                        episode[col] = None

                # 年齢を数値化
                try:
                    episode['age_numeric'] = float(row.get('age', '0'))
                except ValueError:
                    episode['age_numeric'] = None

                self.episodes.append(episode)

    def detect_duplicates(
        self,
        use_normalization: bool = True,
        check_text_similarity: bool = True,
        similarity_threshold: float = 0.8
    ) -> List[Dict]:
        """
        重複エピソードの検出（高度版）

        Args:
            use_normalization: 人物名正規化を使用するか
            check_text_similarity: テキスト類似度チェックを行うか
            similarity_threshold: 類似度の閾値（0.0-1.0）

        Returns:
            重複情報のリスト
        """
        duplicates = []
        seen: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

        # 人物名+年齢でグループ化（正規化オプション付き）
        for ep in self.episodes:
            person_name = ep.get('person_name', '').strip()
            age = ep.get('age', '').strip()

            if person_name and age:
                # 正規化を使用する場合
                if use_normalization:
                    normalized_name = normalize_person_name(person_name)
                else:
                    normalized_name = person_name

                key = (normalized_name, age)
                seen[key].append(ep)

        # 重複を抽出
        for key, episodes in seen.items():
            if len(episodes) > 1:
                normalized_name, age = key

                # テキスト類似度チェック（オプション）
                if check_text_similarity:
                    # 類似グループを検出
                    similar_groups = self._find_similar_text_groups(
                        episodes, similarity_threshold
                    )

                    for group in similar_groups:
                        if len(group) > 1:
                            duplicates.append({
                                'person_name': group[0].get('person_name', ''),
                                'normalized_name': normalized_name,
                                'age': age,
                                'count': len(group),
                                'row_numbers': [ep['row_number'] for ep in group],
                                'duplicate_type': 'exact_or_similar',
                                'similarity_checked': True
                            })
                else:
                    duplicates.append({
                        'person_name': episodes[0].get('person_name', ''),
                        'normalized_name': normalized_name,
                        'age': age,
                        'count': len(episodes),
                        'row_numbers': [ep['row_number'] for ep in episodes],
                        'duplicate_type': 'name_age_match',
                        'similarity_checked': False
                    })

        return duplicates

    def _find_similar_text_groups(
        self,
        episodes: List[Dict],
        threshold: float
    ) -> List[List[Dict]]:
        """
        エピソードテキストの類似度に基づいてグループ化

        Args:
            episodes: エピソードリスト
            threshold: 類似度閾値

        Returns:
            類似エピソードのグループリスト
        """
        if len(episodes) <= 1:
            return [episodes]

        # 類似グループを検出
        groups = []
        assigned = set()

        for i, ep1 in enumerate(episodes):
            if i in assigned:
                continue

            group = [ep1]
            assigned.add(i)

            text1 = ep1.get('episode_text', '')

            for j, ep2 in enumerate(episodes[i + 1:], start=i + 1):
                if j in assigned:
                    continue

                text2 = ep2.get('episode_text', '')

                if is_similar_episode(text1, text2, threshold):
                    group.append(ep2)
                    assigned.add(j)

            groups.append(group)

        return groups

    def detect_duplicates_simple(self) -> List[Dict]:
        """
        重複エピソードの検出（旧バージョン互換）

        Returns:
            重複情報のリスト
        """
        return self.detect_duplicates(
            use_normalization=False,
            check_text_similarity=False
        )

    def detect_outliers(self, threshold: float = 3.0) -> List[Dict]:
        """
        統計的外れ値の検出（平均±threshold標準偏差）

        Args:
            threshold: 標準偏差の倍数（デフォルト: 3.0）

        Returns:
            外れ値情報のリスト
        """
        outliers = []

        for col in self.score_columns:
            # 有効なスコアのみ抽出
            scores = [ep[col] for ep in self.episodes if ep.get(col) is not None]

            if len(scores) < 2:
                continue

            mean = statistics.mean(scores)
            stdev = statistics.stdev(scores)

            # 外れ値を検出
            for ep in self.episodes:
                score = ep.get(col)
                if score is None:
                    continue

                z_score = abs(score - mean) / stdev if stdev > 0 else 0

                if z_score > threshold:
                    outliers.append({
                        'person_name': ep.get('person_name', ''),
                        'age': ep.get('age', ''),
                        'row_number': ep['row_number'],
                        'axis': col,
                        'score': score,
                        'mean': mean,
                        'stdev': stdev,
                        'z_score': z_score
                    })

        return outliers

    def check_completeness(self) -> Dict:
        """
        データ完全性チェック

        Returns:
            完全性チェック結果
        """
        total = len(self.episodes)
        issues = []

        # 必須フィールドチェック
        required_fields = ['person_name', 'age', 'episode']
        for field in required_fields:
            missing_count = sum(1 for ep in self.episodes if not ep.get(field, '').strip())
            if missing_count > 0:
                issues.append({
                    'type': 'missing_required_field',
                    'field': field,
                    'count': missing_count,
                    'percentage': (missing_count / total) * 100
                })

        # スコア範囲チェック（0-10の範囲外）
        for col in self.score_columns:
            out_of_range = []
            for ep in self.episodes:
                score = ep.get(col)
                if score is not None and (score < 0 or score > 10):
                    out_of_range.append({
                        'person_name': ep.get('person_name', ''),
                        'age': ep.get('age', ''),
                        'row_number': ep['row_number'],
                        'score': score
                    })

            if out_of_range:
                issues.append({
                    'type': 'score_out_of_range',
                    'axis': col,
                    'count': len(out_of_range),
                    'examples': out_of_range[:5]  # 最初の5件のみ
                })

        # スコア欠損チェック
        for col in self.score_columns:
            missing_count = sum(1 for ep in self.episodes if ep.get(col) is None)
            if missing_count > 0:
                issues.append({
                    'type': 'missing_score',
                    'axis': col,
                    'count': missing_count,
                    'percentage': (missing_count / total) * 100
                })

        return {
            'total_episodes': total,
            'issues': issues,
            'issues_count': len(issues)
        }

    def calculate_quality_score(self) -> Dict:
        """
        データ品質スコアの算出

        Returns:
            品質スコア情報
        """
        total = len(self.episodes)
        duplicates = self.detect_duplicates()
        outliers = self.detect_outliers()
        completeness = self.check_completeness()

        # 品質スコア計算（0-100）
        score = 100.0

        # 重複ペナルティ（重複率 × 20）
        duplicate_rate = len(duplicates) / total if total > 0 else 0
        score -= duplicate_rate * 20

        # 外れ値ペナルティ（外れ値率 × 15）
        outlier_rate = len(outliers) / total if total > 0 else 0
        score -= outlier_rate * 15

        # 完全性ペナルティ（問題数 × 5）
        score -= min(completeness['issues_count'] * 5, 30)

        # 0-100の範囲に収める
        score = max(0, min(100, score))

        return {
            'quality_score': round(score, 2),
            'total_episodes': total,
            'duplicate_count': len(duplicates),
            'duplicate_rate': round(duplicate_rate * 100, 2),
            'outlier_count': len(outliers),
            'outlier_rate': round(outlier_rate * 100, 2),
            'completeness_issues': completeness['issues_count'],
            'grade': self._get_quality_grade(score)
        }

    def _get_quality_grade(self, score: float) -> str:
        """
        品質スコアからグレードを取得

        Args:
            score: 品質スコア（0-100）

        Returns:
            グレード（A+, A, B, C, D, F）
        """
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def get_quality_report(self) -> Dict:
        """
        総合品質レポート取得

        Returns:
            総合品質レポート
        """
        quality_score = self.calculate_quality_score()
        duplicates = self.detect_duplicates()
        outliers = self.detect_outliers()
        completeness = self.check_completeness()

        return {
            'summary': quality_score,
            'duplicates': {
                'count': len(duplicates),
                'details': duplicates[:10]  # 最初の10件
            },
            'outliers': {
                'count': len(outliers),
                'details': outliers[:10]  # 最初の10件
            },
            'completeness': completeness
        }
