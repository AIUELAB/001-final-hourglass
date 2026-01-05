#!/usr/bin/env python3
"""
ランキングチューニングシステム

機能:
    1. 参照ランキングを教師データとして重み最適化
    2. グリッドサーチ/ベイズ最適化による探索
    3. 品質ゲート（事実密度・生成品質の足切り）維持
    4. 説明可能な重み設定の保存・バージョン管理
"""

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TuningConfig:
    """チューニング設定"""

    version: str
    created_at: str
    # 重み（合計 = 1.0）
    weight_celebrity: float
    weight_episode_fame: float
    weight_quality: float
    weight_historical: float
    # ゲート閾値
    min_factual_density: float = 6.0
    min_generation_quality: float = 6.0
    # 品質の7軸重み
    quality_memorability: float = 0.25
    quality_surprise: float = 0.18
    quality_story: float = 0.15
    quality_educational: float = 0.15
    quality_factual: float = 0.12
    quality_empathy: float = 0.10
    quality_generation: float = 0.05
    # 出力スケール
    output_scale: int = 1_000_000
    # 偉業ブースト係数（0で無効化）
    achievement_boost_multiplier: float = 1.0
    # 説明
    description: str = ""


@dataclass
class TuningResult:
    """チューニング結果"""

    config: TuningConfig
    ndcg_at_100: float
    overlap_at_100: float
    combined_score: float  # 最適化目標


class RankingTuner:
    """ランキングチューナー"""

    # 回顧パターン
    RETROSPECTIVE_PATTERNS = [
        "人生を振り返",
        "自らの歩みを振り返",
        "静かな日々を送",
        "晩年.*回顧",
        "回想しながら",
    ]

    # 偉業ブースト
    ACHIEVEMENT_BOOST = {
        "ノーベル賞": 0.12,
        "世界初": 0.10,
        "史上初": 0.10,
        "オリンピック金メダル": 0.10,
        "50本塁打": 0.08,
        "MVP": 0.08,
        "金メダル": 0.05,
        "優勝": 0.05,
    }

    def __init__(self, df: pd.DataFrame, reference_data: dict):
        """
        Args:
            df: マスターCSV DataFrame
            reference_data: 参照ランキングデータ（マッピング済み）
        """
        self.df = df.copy()
        self.reference_data = reference_data

        # 数値変換
        self._prepare_data()

        # 正規化パラメータ計算
        self._compute_normalization()

    def _prepare_data(self):
        """データの前処理"""
        numeric_cols = [
            "celebrity_score_v2",
            "episode_fame_v6",
            "記憶性スコア",
            "意外性スコア",
            "共感性スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
            "生成品質スコア",
            "episode_importance_score",
            "super_total_score",
        ]
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

    def _compute_normalization(self):
        """正規化パラメータ（中央値・IQR）を計算"""

        def robust_stats(series):
            arr = series.dropna().values
            if len(arr) == 0:
                return 0, 1
            median = np.median(arr)
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            return median, max(iqr, 1)

        self.celeb_median, self.celeb_iqr = robust_stats(self.df["celebrity_score_v2"])
        self.fame_median, self.fame_iqr = robust_stats(self.df["episode_fame_v6"])
        self.imp_median, self.imp_iqr = robust_stats(self.df["episode_importance_score"])

    def _robust_normalize(self, value: float, median: float, iqr: float) -> float:
        """ロバスト正規化（シグモイド）"""
        if pd.isna(value) or iqr == 0:
            return 0.5
        z = (value - median) / iqr
        return 1 / (1 + math.exp(-z))

    def _calc_quality_score(self, row: pd.Series, config: TuningConfig) -> float:
        """7軸加重平均による品質スコア"""
        weights = {
            "記憶性スコア": config.quality_memorability,
            "意外性スコア": config.quality_surprise,
            "ストーリー品質": config.quality_story,
            "教育的価値": config.quality_educational,
            "事実密度": config.quality_factual,
            "共感性スコア": config.quality_empathy,
            "生成品質スコア": config.quality_generation,
        }

        total_weight = 0
        weighted_sum = 0

        for field, weight in weights.items():
            val = row.get(field)
            if pd.notna(val):
                weighted_sum += val * weight
                total_weight += weight

        if total_weight == 0:
            return 0.5

        return (weighted_sum / total_weight) / 10  # 0-1に正規化

    def _calc_penalty(self, row: pd.Series, config: TuningConfig) -> float:
        """ペナルティ乗数を計算"""
        multiplier = 1.0

        # 事実密度ソフトペナルティ
        fact = row.get("事実密度", 10)
        if pd.notna(fact) and config.min_factual_density <= fact < 7.0:
            multiplier *= 0.85

        # 生成品質ソフトペナルティ
        gen = row.get("生成品質スコア", 10)
        if pd.notna(gen) and config.min_generation_quality <= gen < 7.0:
            multiplier *= 0.85

        # 回顧パターン
        text = str(row.get("episode_text", ""))
        for pattern in self.RETROSPECTIVE_PATTERNS:
            if pattern in text:
                multiplier *= 0.80
                break

        return multiplier

    def _calc_achievement_boost(self, row: pd.Series, config: TuningConfig) -> float:
        """偉業キーワードブースト"""
        if config.achievement_boost_multiplier == 0:
            return 0

        text = str(row.get("episode_text", ""))
        boost = 0

        for keyword, boost_val in self.ACHIEVEMENT_BOOST.items():
            if keyword in text:
                boost = max(boost, boost_val)

        return boost * config.achievement_boost_multiplier

    def calculate_score(self, row: pd.Series, config: TuningConfig) -> float:
        """超総合スコアを計算"""
        # ゲートチェック
        fact = row.get("事実密度", 0)
        gen = row.get("生成品質スコア", 0)

        if pd.isna(fact) or fact < config.min_factual_density:
            return 0
        if pd.isna(gen) or gen < config.min_generation_quality:
            return 0

        # 正規化
        celeb_norm = self._robust_normalize(row.get("celebrity_score_v2", 0), self.celeb_median, self.celeb_iqr)
        fame_norm = self._robust_normalize(row.get("episode_fame_v6", 0), self.fame_median, self.fame_iqr)
        quality_norm = self._calc_quality_score(row, config)
        historical_norm = self._robust_normalize(row.get("episode_importance_score", 0), self.imp_median, self.imp_iqr)

        # 重み付き統合
        raw = (
            config.weight_celebrity * celeb_norm
            + config.weight_episode_fame * fame_norm
            + config.weight_quality * quality_norm
            + config.weight_historical * historical_norm
        )

        # 偉業ブースト
        boost = self._calc_achievement_boost(row, config)
        raw = raw * (1 + boost)

        # ペナルティ
        penalty = self._calc_penalty(row, config)

        return raw * penalty * config.output_scale

    def evaluate_config(self, config: TuningConfig, source: str = "claude") -> TuningResult:
        """設定を評価"""
        # 全エピソードのスコア計算
        self.df["tuned_score"] = self.df.apply(lambda row: self.calculate_score(row, config), axis=1)
        df_sorted = self.df.sort_values("tuned_score", ascending=False).reset_index(drop=True)
        df_sorted["tuned_rank"] = range(1, len(df_sorted) + 1)

        # 参照データとの比較
        ref_data = self.reference_data.get(source, [])
        ref_episode_ids = {r["matched_episode_id"] for r in ref_data if r["matched_episode_id"]}
        ref_rank_map = {r["matched_episode_id"]: r["ref_rank"] for r in ref_data if r["matched_episode_id"]}

        # Overlap@100
        top100_ids = set(df_sorted.head(100)["episode_id"])
        overlap = len(top100_ids & ref_episode_ids) / min(100, len(ref_episode_ids))

        # NDCG@100
        top100 = df_sorted.head(100)
        predicted_relevances = []
        for _, row in top100.iterrows():
            ep_id = row["episode_id"]
            if ep_id in ref_rank_map:
                predicted_relevances.append((101 - ref_rank_map[ep_id]) / 100)
            else:
                predicted_relevances.append(0)

        ideal_relevances = sorted([(101 - r) / 100 for r in ref_rank_map.values()], reverse=True)

        def dcg_at_k(rels, k):
            rels = np.array(rels[:k])
            if rels.size == 0:
                return 0
            discounts = np.log2(np.arange(2, rels.size + 2))
            return np.sum(rels / discounts)

        dcg = dcg_at_k(predicted_relevances, 100)
        idcg = dcg_at_k(ideal_relevances, 100)
        ndcg = dcg / idcg if idcg > 0 else 0

        # 統合スコア（NDCG 60% + Overlap 40%）
        combined = 0.6 * ndcg + 0.4 * overlap

        return TuningResult(config=config, ndcg_at_100=ndcg, overlap_at_100=overlap, combined_score=combined)

    def grid_search(
        self,
        weight_ranges: dict,
        source: str = "claude",
    ) -> list[TuningResult]:
        """グリッドサーチで最適な重みを探索"""
        results = []

        # 重みの組み合わせを生成
        celebrity_range = weight_ranges.get("celebrity", [0.30, 0.35, 0.40, 0.45])
        episode_fame_range = weight_ranges.get("episode_fame", [0.25, 0.30, 0.35])
        quality_range = weight_ranges.get("quality", [0.15, 0.20, 0.25])
        historical_range = weight_ranges.get("historical", [0.05, 0.10, 0.15])

        for celeb, fame, qual, hist in product(celebrity_range, episode_fame_range, quality_range, historical_range):
            # 重みの合計が1.0になるようにスキップ
            if abs(celeb + fame + qual + hist - 1.0) > 0.01:
                continue

            config = TuningConfig(
                version=f"grid_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now().isoformat(),
                weight_celebrity=celeb,
                weight_episode_fame=fame,
                weight_quality=qual,
                weight_historical=hist,
            )

            result = self.evaluate_config(config, source)
            results.append(result)

        # スコア順にソート
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results


def main():
    """メイン処理"""
    # データ読み込み
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, dtype=str)

    mapping_path = PROJECT_ROOT / "src/reports/reference_mapping_results.json"
    with open(mapping_path, encoding="utf-8") as f:
        mapping_data = json.load(f)

    print("=" * 60)
    print("ランキングチューニングシステム")
    print("=" * 60)
    print(f"マスターCSV: {len(df)}件")
    print(f"参照データ: Claude {len(mapping_data['claude'])}件, Gemini {len(mapping_data['gemini'])}件")

    # チューナー初期化
    tuner = RankingTuner(df, mapping_data)

    # 現行設定の評価
    print("\n=== 現行設定の評価 ===")
    current_config = TuningConfig(
        version="v1.2.0_current",
        created_at=datetime.now().isoformat(),
        weight_celebrity=0.30,
        weight_episode_fame=0.30,
        weight_quality=0.20,
        weight_historical=0.20,
        description="現行設定（v1.2.0）",
    )
    current_result = tuner.evaluate_config(current_config, "claude")
    print(f"  NDCG@100: {current_result.ndcg_at_100:.3f}")
    print(f"  Overlap@100: {current_result.overlap_at_100:.1%}")
    print(f"  Combined: {current_result.combined_score:.3f}")

    # グリッドサーチ
    print("\n=== グリッドサーチ実行 ===")
    weight_ranges = {
        "celebrity": [0.35, 0.40, 0.45, 0.50],
        "episode_fame": [0.20, 0.25, 0.30],
        "quality": [0.15, 0.20, 0.25],
        "historical": [0.00, 0.05, 0.10],
    }

    results = tuner.grid_search(weight_ranges, "claude")
    print(f"  探索した組み合わせ: {len(results)}件")

    # 上位5件を表示
    print("\n=== Top 5 設定 ===")
    for i, r in enumerate(results[:5], 1):
        c = r.config
        print(f"\n  {i}. Combined: {r.combined_score:.3f}")
        print(f"     NDCG@100: {r.ndcg_at_100:.3f}, Overlap@100: {r.overlap_at_100:.1%}")
        print(f"     重み: celebrity={c.weight_celebrity}, fame={c.weight_episode_fame}, ")
        print(f"           quality={c.weight_quality}, historical={c.weight_historical}")

    # 最良設定を保存
    best_result = results[0]
    best_config = best_result.config
    best_config.version = "v2.0.0_tuned"
    best_config.description = "参照ランキング（Claude Best100）に最適化した設定"

    output = {
        "best_config": asdict(best_config),
        "evaluation": {
            "ndcg_at_100": best_result.ndcg_at_100,
            "overlap_at_100": best_result.overlap_at_100,
            "combined_score": best_result.combined_score,
        },
        "comparison_with_current": {
            "current_ndcg": current_result.ndcg_at_100,
            "current_overlap": current_result.overlap_at_100,
            "current_combined": current_result.combined_score,
            "improvement_ndcg": best_result.ndcg_at_100 - current_result.ndcg_at_100,
            "improvement_overlap": best_result.overlap_at_100 - current_result.overlap_at_100,
            "improvement_combined": best_result.combined_score - current_result.combined_score,
        },
        "all_results": [
            {
                "config": asdict(r.config),
                "ndcg_at_100": r.ndcg_at_100,
                "overlap_at_100": r.overlap_at_100,
                "combined_score": r.combined_score,
            }
            for r in results[:20]
        ],
    }

    output_path = PROJECT_ROOT / "src/reports/tuning_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n結果を保存: {output_path}")

    # 改善率
    print("\n=== 改善率 ===")
    print(
        f"  NDCG: {current_result.ndcg_at_100:.3f} → {best_result.ndcg_at_100:.3f} ({best_result.ndcg_at_100 - current_result.ndcg_at_100:+.3f})"
    )
    print(
        f"  Overlap: {current_result.overlap_at_100:.1%} → {best_result.overlap_at_100:.1%} ({(best_result.overlap_at_100 - current_result.overlap_at_100)*100:+.1f}pp)"
    )


if __name__ == "__main__":
    main()
