"""高度な検索モジュール

7軸スコアによるフィルタリング、複数条件検索を提供
"""

import csv
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AdvancedSearchEngine:
    """高度な検索エンジン"""

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: CSVファイルパス
        """
        self.csv_path = Path(csv_path)
        self.episodes: List[Dict] = []
        self.load_episodes()

    def load_episodes(self):
        """CSVからエピソードデータを読み込み"""
        self.episodes = []

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 数値フィールドを変換
                episode = dict(row)

                # 年齢を数値化
                try:
                    episode["age_numeric"] = float(row.get("age", "0"))
                except ValueError:
                    episode["age_numeric"] = 0.0

                # 7軸スコアを数値化
                score_columns = [
                    "記憶性スコア",
                    "共感性スコア",
                    "意外性スコア",
                    "生成品質スコア",
                    "教育的価値",
                    "ストーリー品質",
                    "事実密度",
                ]

                # 各スコアを数値化
                scores = []
                for col in score_columns:
                    value = row.get(col, "").strip()
                    if value:
                        try:
                            score = float(value)
                            episode[col] = score
                            scores.append(score)
                        except ValueError:
                            episode[col] = 0.0
                    else:
                        episode[col] = 0.0

                # 総合スコアを計算
                if len(scores) == 7:
                    episode["composite_score"] = statistics.mean(scores)
                else:
                    episode["composite_score"] = 0.0

                self.episodes.append(episode)

    def search(
        self,
        query: Optional[str] = None,
        min_memorability_score: Optional[float] = None,
        max_memorability_score: Optional[float] = None,
        min_empathy_score: Optional[float] = None,
        max_empathy_score: Optional[float] = None,
        min_surprise_score: Optional[float] = None,
        max_surprise_score: Optional[float] = None,
        min_generation_quality: Optional[float] = None,
        max_generation_quality: Optional[float] = None,
        min_educational_value: Optional[float] = None,
        max_educational_value: Optional[float] = None,
        min_storytelling_quality: Optional[float] = None,
        max_storytelling_quality: Optional[float] = None,
        min_factual_density: Optional[float] = None,
        max_factual_density: Optional[float] = None,
        min_composite_score: Optional[float] = None,
        max_composite_score: Optional[float] = None,
        min_age: Optional[float] = None,
        max_age: Optional[float] = None,
        sort_by: str = "composite_score",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int]:
        """
        高度な検索

        Args:
            query: 検索クエリ（人物名、エピソード内容）
            min_memorability_score: 記憶性スコア最小値
            max_memorability_score: 記憶性スコア最大値
            min_empathy_score: 共感性スコア最小値
            max_empathy_score: 共感性スコア最大値
            min_surprise_score: 意外性スコア最小値
            max_surprise_score: 意外性スコア最大値
            min_generation_quality: 生成品質スコア最小値
            max_generation_quality: 生成品質スコア最大値
            min_educational_value: 教育的価値最小値
            max_educational_value: 教育的価値最大値
            min_storytelling_quality: ストーリー品質最小値
            max_storytelling_quality: ストーリー品質最大値
            min_factual_density: 事実密度最小値
            max_factual_density: 事実密度最大値
            min_composite_score: 総合スコア最小値
            max_composite_score: 総合スコア最大値
            min_age: 年齢最小値
            max_age: 年齢最大値
            sort_by: ソート基準
            order: 並び順（asc/desc）
            page: ページ番号
            page_size: ページサイズ

        Returns:
            (フィルタリング後のエピソードリスト, 総件数)
        """
        filtered = self.episodes.copy()

        # 全文検索（人物名、エピソード）
        if query:
            query_lower = query.lower()
            filtered = [
                ep
                for ep in filtered
                if query_lower in ep.get("person_name", "").lower() or query_lower in ep.get("episode", "").lower()
            ]

        # 7軸スコアフィルタリング
        if min_memorability_score is not None:
            filtered = [ep for ep in filtered if ep.get("記憶性スコア", 0) >= min_memorability_score]
        if max_memorability_score is not None:
            filtered = [ep for ep in filtered if ep.get("記憶性スコア", 10) <= max_memorability_score]

        if min_empathy_score is not None:
            filtered = [ep for ep in filtered if ep.get("共感性スコア", 0) >= min_empathy_score]
        if max_empathy_score is not None:
            filtered = [ep for ep in filtered if ep.get("共感性スコア", 10) <= max_empathy_score]

        if min_surprise_score is not None:
            filtered = [ep for ep in filtered if ep.get("意外性スコア", 0) >= min_surprise_score]
        if max_surprise_score is not None:
            filtered = [ep for ep in filtered if ep.get("意外性スコア", 10) <= max_surprise_score]

        if min_generation_quality is not None:
            filtered = [ep for ep in filtered if ep.get("生成品質スコア", 0) >= min_generation_quality]
        if max_generation_quality is not None:
            filtered = [ep for ep in filtered if ep.get("生成品質スコア", 10) <= max_generation_quality]

        if min_educational_value is not None:
            filtered = [ep for ep in filtered if ep.get("教育的価値", 0) >= min_educational_value]
        if max_educational_value is not None:
            filtered = [ep for ep in filtered if ep.get("教育的価値", 10) <= max_educational_value]

        if min_storytelling_quality is not None:
            filtered = [ep for ep in filtered if ep.get("ストーリー品質", 0) >= min_storytelling_quality]
        if max_storytelling_quality is not None:
            filtered = [ep for ep in filtered if ep.get("ストーリー品質", 10) <= max_storytelling_quality]

        if min_factual_density is not None:
            filtered = [ep for ep in filtered if ep.get("事実密度", 0) >= min_factual_density]
        if max_factual_density is not None:
            filtered = [ep for ep in filtered if ep.get("事実密度", 10) <= max_factual_density]

        # 総合スコアフィルタリング
        if min_composite_score is not None:
            filtered = [ep for ep in filtered if ep.get("composite_score", 0) >= min_composite_score]
        if max_composite_score is not None:
            filtered = [ep for ep in filtered if ep.get("composite_score", 10) <= max_composite_score]

        # 年齢フィルタリング
        if min_age is not None:
            filtered = [ep for ep in filtered if ep.get("age_numeric", 0) >= min_age]
        if max_age is not None:
            filtered = [ep for ep in filtered if ep.get("age_numeric", 999) <= max_age]

        # ソート
        reverse = order == "desc"
        if sort_by in [
            "composite_score",
            "記憶性スコア",
            "共感性スコア",
            "意外性スコア",
            "生成品質スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
            "age_numeric",
        ]:
            filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        elif sort_by == "person_name":
            filtered.sort(key=lambda x: x.get("person_name", ""), reverse=reverse)

        # 総件数
        total = len(filtered)

        # ページネーション
        offset = (page - 1) * page_size
        paginated = filtered[offset : offset + page_size]

        return paginated, total

    def get_search_stats(self) -> Dict:
        """
        検索統計情報取得

        Returns:
            統計情報
        """
        if not self.episodes:
            return {"total_episodes": 0, "score_ranges": {}}

        score_columns = [
            "記憶性スコア",
            "共感性スコア",
            "意外性スコア",
            "生成品質スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
            "composite_score",
        ]

        score_ranges = {}
        for col in score_columns:
            scores = [ep.get(col, 0) for ep in self.episodes if ep.get(col, 0) > 0]
            if scores:
                score_ranges[col] = {
                    "min": min(scores),
                    "max": max(scores),
                    "mean": statistics.mean(scores),
                    "median": statistics.median(scores),
                }

        # 年齢範囲
        ages = [ep.get("age_numeric", 0) for ep in self.episodes if ep.get("age_numeric", 0) > 0]
        age_range = {"min": min(ages) if ages else 0, "max": max(ages) if ages else 0}

        return {"total_episodes": len(self.episodes), "score_ranges": score_ranges, "age_range": age_range}
