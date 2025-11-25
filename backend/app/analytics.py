"""データ分析モジュール

7軸スコアの統計分析・相関分析を提供
"""

import csv
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ScoreAnalytics:
    """7軸スコア分析クラス"""

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: CSVファイルパス
        """
        self.csv_path = Path(csv_path)
        self.score_columns = [
            "記憶性スコア",
            "共感性スコア",
            "意外性スコア",
            "生成品質スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
        ]

    def load_scores(self) -> Dict[str, List[float]]:
        """
        CSVから7軸スコアを読み込み

        Returns:
            各軸のスコアリスト
        """
        scores = {col: [] for col in self.score_columns}

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                for col in self.score_columns:
                    value = row.get(col, "").strip()
                    if value:
                        try:
                            score = float(value)
                            scores[col].append(score)
                        except ValueError:
                            pass

        return scores

    def calculate_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        各軸の統計値を計算

        Returns:
            各軸の統計情報（平均、中央値、標準偏差、最小値、最大値）
        """
        scores = self.load_scores()
        stats = {}

        for col, data in scores.items():
            if data:
                stats[col] = {
                    "count": len(data),
                    "mean": statistics.mean(data),
                    "median": statistics.median(data),
                    "stdev": statistics.stdev(data) if len(data) > 1 else 0.0,
                    "min": min(data),
                    "max": max(data),
                    "q1": statistics.median(sorted(data)[: len(data) // 2]),
                    "q3": statistics.median(sorted(data)[len(data) // 2 :]),
                }
            else:
                stats[col] = {
                    "count": 0,
                    "mean": 0.0,
                    "median": 0.0,
                    "stdev": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "q1": 0.0,
                    "q3": 0.0,
                }

        return stats

    def calculate_distribution(self, bin_size: float = 0.5) -> Dict[str, List[Dict[str, float]]]:
        """
        スコア分布をヒストグラム形式で計算

        Args:
            bin_size: ビンのサイズ（デフォルト: 0.5）

        Returns:
            各軸のヒストグラムデータ
        """
        scores = self.load_scores()
        distributions = {}

        for col, data in scores.items():
            if not data:
                distributions[col] = []
                continue

            # ビンの範囲を決定（0-10の範囲）
            bins = {}
            for score in data:
                bin_key = int(score / bin_size) * bin_size
                if bin_key not in bins:
                    bins[bin_key] = 0
                bins[bin_key] += 1

            # ヒストグラムデータに変換
            histogram = []
            for bin_start in sorted(bins.keys()):
                histogram.append(
                    {
                        "range": f"{bin_start:.1f}-{bin_start + bin_size:.1f}",
                        "bin_start": bin_start,
                        "bin_end": bin_start + bin_size,
                        "count": bins[bin_start],
                        "percentage": bins[bin_start] / len(data) * 100,
                    }
                )

            distributions[col] = histogram

        return distributions

    def calculate_correlation_matrix(self) -> List[Dict[str, any]]:
        """
        軸間の相関係数行列を計算

        Returns:
            相関マトリックス（行形式）
        """
        scores = self.load_scores()

        # 全軸でデータがあるレコードのみ抽出
        valid_records = []
        for i in range(max(len(data) for data in scores.values())):
            record = {}
            valid = True
            for col in self.score_columns:
                if i < len(scores[col]):
                    record[col] = scores[col][i]
                else:
                    valid = False
                    break
            if valid and len(record) == len(self.score_columns):
                valid_records.append(record)

        # 相関係数を計算
        correlation_matrix = []
        for axis1 in self.score_columns:
            row = {"axis": axis1}
            data1 = [r[axis1] for r in valid_records]

            for axis2 in self.score_columns:
                data2 = [r[axis2] for r in valid_records]

                if len(data1) > 1 and len(data2) > 1:
                    # Pearson相関係数
                    mean1 = statistics.mean(data1)
                    mean2 = statistics.mean(data2)
                    stdev1 = statistics.stdev(data1)
                    stdev2 = statistics.stdev(data2)

                    if stdev1 > 0 and stdev2 > 0:
                        covariance = sum((x - mean1) * (y - mean2) for x, y in zip(data1, data2)) / len(data1)
                        correlation = covariance / (stdev1 * stdev2)
                    else:
                        correlation = 0.0
                else:
                    correlation = 0.0

                row[axis2] = round(correlation, 3)

            correlation_matrix.append(row)

        return correlation_matrix

    def get_top_performers(self, top_n: int = 50) -> List[Dict[str, any]]:
        """
        総合スコア上位のエピソードを取得

        Args:
            top_n: 取得件数

        Returns:
            上位エピソードリスト
        """
        episodes = []

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 7軸スコアの平均を計算
                axis_scores = []
                for col in self.score_columns:
                    value = row.get(col, "").strip()
                    if value:
                        try:
                            axis_scores.append(float(value))
                        except ValueError:
                            pass

                if len(axis_scores) == 7:  # 全軸にスコアがある場合のみ
                    composite = statistics.mean(axis_scores)
                    episodes.append(
                        {
                            "person_name": row.get("person_name", ""),
                            "age": row.get("age", ""),
                            "episode": row.get("episode", "")[:100],  # 最初の100文字
                            "composite_score": round(composite, 2),
                            "memorability_score": float(row.get("記憶性スコア", 0)),
                            "empathy_score": float(row.get("共感性スコア", 0)),
                            "surprise_score": float(row.get("意外性スコア", 0)),
                            "generation_quality_score": float(row.get("生成品質スコア", 0)),
                            "educational_value": float(row.get("教育的価値", 0)),
                            "storytelling_quality": float(row.get("ストーリー品質", 0)),
                            "factual_density": float(row.get("事実密度", 0)),
                        }
                    )

        # 総合スコアでソート
        episodes.sort(key=lambda x: x["composite_score"], reverse=True)

        return episodes[:top_n]

    def get_score_summary(self) -> Dict[str, any]:
        """
        7軸スコアの総合サマリー

        Returns:
            総合統計情報
        """
        scores = self.load_scores()
        stats = self.calculate_statistics()

        # 全体統計
        all_scores = []
        for data in scores.values():
            all_scores.extend(data)

        summary = {"total_episodes": len(all_scores) // 7 if all_scores else 0, "axes": []}

        for col in self.score_columns:
            if col in stats:
                summary["axes"].append(
                    {
                        "name": col,
                        "count": stats[col]["count"],
                        "mean": round(stats[col]["mean"], 2),
                        "median": round(stats[col]["median"], 2),
                        "stdev": round(stats[col]["stdev"], 2),
                        "min": round(stats[col]["min"], 1),
                        "max": round(stats[col]["max"], 1),
                    }
                )

        return summary
