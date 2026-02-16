#!/usr/bin/env python3
"""
ランキングチューニングシステム

機能:
    1. 参照ランキングを教師データとして重み最適化
    2. グリッドサーチ/ベイズ最適化による探索
    3. 品質ゲート（factual_density・生成品質の足切り）維持
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
    # iconic人物ブースト乗数（0で無効化、weight合計1.0制約の外）
    iconic_boost_multiplier: float = 0.0
    # 説明
    description: str = ""


@dataclass
class TuningResult:
    """チューニング結果"""

    config: TuningConfig
    ndcg_at_100: float  # Avg NDCG（複数ソース時は平均）
    overlap_at_100: float  # Avg Overlap（複数ソース時は平均）
    combined_score: float  # 最適化目標（Avg）
    # ソース別詳細（source名 → {ndcg, overlap, combined}）
    per_source: dict | None = None


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

        # iconic人物セット読み込み（iconic_achievements_master.jsonから）
        self._iconic_persons: set[str] = set()
        iconic_path = PROJECT_ROOT / "preserved/data/iconic_achievements_master.json"
        if iconic_path.exists():
            with open(iconic_path, encoding="utf-8") as f:
                iconic_data = json.load(f)
            self._iconic_persons = set(iconic_data.get("persons", {}).keys())

        # 数値変換
        self._prepare_data()

        # 正規化パラメータ計算
        self._compute_normalization()

    def _prepare_data(self):
        """データの前処理"""
        numeric_cols = [
            "celebrity_score_v2",
            "episode_fame_v6",
            "memorability_score",
            "surprise_score",
            "empathy_score",
            "educational_value",
            "story_quality",
            "factual_density",
            "generation_quality_score",
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

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        """安全にfloatに変換"""
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        try:
            result = float(value)
            return result if not math.isnan(result) else default
        except (ValueError, TypeError):
            return default

    def _robust_normalize(self, value: float, median: float, iqr: float) -> float:
        """ロバスト正規化（シグモイド）"""
        if value is None or (isinstance(value, float) and math.isnan(value)) or iqr == 0:
            return 0.5
        z = (value - median) / iqr
        return 1 / (1 + math.exp(-z))

    def _calc_quality_score(self, row: pd.Series, config: TuningConfig) -> float:
        """7軸加重平均による品質スコア"""
        weights = {
            "memorability_score": config.quality_memorability,
            "surprise_score": config.quality_surprise,
            "story_quality": config.quality_story,
            "educational_value": config.quality_educational,
            "factual_density": config.quality_factual,
            "empathy_score": config.quality_empathy,
            "generation_quality_score": config.quality_generation,
        }

        total_weight = 0
        weighted_sum = 0

        for field, weight in weights.items():
            raw_val = row.get(field)
            if raw_val is not None and not (isinstance(raw_val, float) and math.isnan(raw_val)) and pd.notna(raw_val):
                val = self._safe_float(raw_val)
                weighted_sum += val * weight
                total_weight += weight

        if total_weight == 0:
            return 0.5

        return (weighted_sum / total_weight) / 10  # 0-1に正規化

    def _calc_penalty(self, row: pd.Series, config: TuningConfig) -> float:
        """ペナルティ乗数を計算"""
        multiplier = 1.0

        # factual_densityソフトペナルティ
        fact = self._safe_float(row.get("factual_density"), 10)
        if config.min_factual_density <= fact < 7.0:
            multiplier *= 0.85

        # 生成品質ソフトペナルティ
        gen = self._safe_float(row.get("generation_quality_score"), 10)
        if config.min_generation_quality <= gen < 7.0:
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
        fact = self._safe_float(row.get("factual_density"), 0)
        gen = self._safe_float(row.get("generation_quality_score"), 0)

        if fact < config.min_factual_density:
            return 0
        if gen < config.min_generation_quality:
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

        # iconic人物ブースト（v2.1.0: weight合計1.0制約の外）
        person_name = row.get("person_name", "")
        if person_name in self._iconic_persons and config.iconic_boost_multiplier > 0:
            raw = raw * (1 + config.iconic_boost_multiplier)

        # ペナルティ
        penalty = self._calc_penalty(row, config)

        return raw * penalty * config.output_scale

    def _evaluate_single_source(self, df_sorted: pd.DataFrame, source: str) -> dict:
        """単一ソースに対する評価を実行（人物レベル）

        Args:
            df_sorted: スコア降順にソートされたDataFrame
            source: 参照ソース名（"claude" or "gemini"）

        Returns:
            {"ndcg": float, "overlap": float, "combined": float}
        """
        ref_data = self.reference_data.get(source, [])

        # 参照データを人物レベルに集約（matched_person_nameで重複排除）
        ref_rank_map: dict[str, int] = {}
        for r in ref_data:
            person = r.get("matched_person_name")
            if person:
                # 同一人物が複数回出現する場合、最も高い順位（小さい数値）を採用
                if person not in ref_rank_map or r["ref_rank"] < ref_rank_map[person]:
                    ref_rank_map[person] = r["ref_rank"]
        ref_persons = set(ref_rank_map.keys())

        if not ref_rank_map:
            return {"ndcg": 0.0, "overlap": 0.0, "combined": 0.0}

        # マスターCSVを人物レベルに集約（各人物のtuned_scoreが最高のエピソード1件）
        person_ranked = df_sorted.groupby("person_name", as_index=False).first()
        person_ranked = person_ranked.sort_values("tuned_score", ascending=False).reset_index(drop=True)

        # Overlap@100（人物ベース）
        top100_persons = set(person_ranked.head(100)["person_name"].dropna())
        overlap = len(top100_persons & ref_persons) / min(100, len(ref_persons))

        # NDCG@100（人物ベース）
        top100 = person_ranked.head(100)
        predicted_relevances = []
        for _, row in top100.iterrows():
            person = row["person_name"]
            if person in ref_rank_map:
                predicted_relevances.append((101 - ref_rank_map[person]) / 100)
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

        combined = 0.6 * ndcg + 0.4 * overlap
        return {"ndcg": ndcg, "overlap": overlap, "combined": combined}

    def evaluate_config(
        self, config: TuningConfig, source: str = "claude", sources: list[str] | None = None
    ) -> TuningResult:
        """設定を評価

        Args:
            config: チューニング設定
            source: 単一ソース名（sourcesが指定されていない場合に使用）
            sources: 評価ソースのリスト。指定時はAvg NDCGが最適化目標になる。
        """
        # 評価ソースを決定
        eval_sources = sources if sources else [source]

        # 全エピソードのスコア計算（1回だけ）
        self.df["tuned_score"] = self.df.apply(lambda row: self.calculate_score(row, config), axis=1)
        df_sorted = self.df.sort_values("tuned_score", ascending=False).reset_index(drop=True)
        df_sorted["tuned_rank"] = range(1, len(df_sorted) + 1)

        # 各ソースで評価
        per_source = {}
        for src in eval_sources:
            per_source[src] = self._evaluate_single_source(df_sorted, src)

        # 平均を計算
        avg_ndcg = sum(r["ndcg"] for r in per_source.values()) / len(per_source)
        avg_overlap = sum(r["overlap"] for r in per_source.values()) / len(per_source)
        avg_combined = sum(r["combined"] for r in per_source.values()) / len(per_source)

        return TuningResult(
            config=config,
            ndcg_at_100=avg_ndcg,
            overlap_at_100=avg_overlap,
            combined_score=avg_combined,
            per_source=per_source,
        )

    def grid_search(
        self,
        weight_ranges: dict,
        sources: list[str] | None = None,
    ) -> list[TuningResult]:
        """グリッドサーチで最適な重みを探索

        Args:
            weight_ranges: 探索範囲。"iconic_boost"はweight合計1.0制約の外。
            sources: 評価ソースのリスト（デフォルト: ["claude"]）
        """
        if sources is None:
            sources = ["claude"]
        results = []

        # 重みの組み合わせを生成
        celebrity_range = weight_ranges.get("celebrity", [0.30, 0.35, 0.40, 0.45])
        episode_fame_range = weight_ranges.get("episode_fame", [0.25, 0.30, 0.35])
        quality_range = weight_ranges.get("quality", [0.15, 0.20, 0.25])
        historical_range = weight_ranges.get("historical", [0.05, 0.10, 0.15])
        # iconic_boostはweight合計1.0制約の外で別ループ
        iconic_boost_range = weight_ranges.get("iconic_boost", [0.0])

        for celeb, fame, qual, hist, iconic in product(
            celebrity_range, episode_fame_range, quality_range, historical_range, iconic_boost_range
        ):
            # 重みの合計が1.0になるようにスキップ（iconic_boostは除外）
            if abs(celeb + fame + qual + hist - 1.0) > 0.01:
                continue

            config = TuningConfig(
                version=f"grid_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now().isoformat(),
                weight_celebrity=celeb,
                weight_episode_fame=fame,
                weight_quality=qual,
                weight_historical=hist,
                iconic_boost_multiplier=iconic,
            )

            result = self.evaluate_config(config, sources=sources)
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

    # 評価ソース
    eval_sources = ["claude", "gemini"]

    # 現行設定の評価（v2.1.0ベース）
    print("\n=== 現行設定の評価（v2.1.0） ===")
    current_config = TuningConfig(
        version="v2.1.0_current",
        created_at=datetime.now().isoformat(),
        weight_celebrity=0.05,
        weight_episode_fame=0.40,
        weight_quality=0.55,
        weight_historical=0.00,
        iconic_boost_multiplier=0.25,
        description="現行設定（v2.1.0）",
    )
    current_result = tuner.evaluate_config(current_config, sources=eval_sources)
    print(f"  Avg NDCG@100: {current_result.ndcg_at_100:.3f}")
    print(f"  Avg Overlap@100: {current_result.overlap_at_100:.1%}")
    print(f"  Avg Combined: {current_result.combined_score:.3f}")
    if current_result.per_source:
        for src, metrics in current_result.per_source.items():
            print(f"    [{src}] NDCG={metrics['ndcg']:.3f}, Overlap={metrics['overlap']:.1%}")

    # グリッドサーチ（Phase C: v2.2.0探索）
    print("\n=== グリッドサーチ実行（Phase C: v2.2.0） ===")
    weight_ranges = {
        "celebrity": [0.05],  # 固定（v2.1.0と同じ）
        "episode_fame": [0.30, 0.35, 0.40],
        "quality": [0.40, 0.45, 0.50],
        "historical": [0.10, 0.15, 0.20],
        "iconic_boost": [0.25, 0.50, 0.75, 1.00],
    }

    results = tuner.grid_search(weight_ranges, sources=eval_sources)
    print(f"  探索した組み合わせ: {len(results)}件")

    # 上位5件を表示
    print("\n=== Top 5 設定 ===")
    for i, r in enumerate(results[:5], 1):
        c = r.config
        print(f"\n  {i}. Avg Combined: {r.combined_score:.3f}")
        print(f"     Avg NDCG@100: {r.ndcg_at_100:.3f}, Avg Overlap@100: {r.overlap_at_100:.1%}")
        print(f"     重み: celebrity={c.weight_celebrity}, fame={c.weight_episode_fame}, ")
        print(f"           quality={c.weight_quality}, historical={c.weight_historical}")
        print(f"     iconic_boost_multiplier={c.iconic_boost_multiplier}")
        if r.per_source:
            for src, metrics in r.per_source.items():
                print(f"       [{src}] NDCG={metrics['ndcg']:.3f}, Overlap={metrics['overlap']:.1%}")

    # 最良設定を保存
    best_result = results[0]
    best_config = best_result.config
    best_config.version = "v2.2.0_tuned"
    best_config.description = "参照ランキング（Claude + Gemini Best100）に最適化した設定（Phase C）"

    output = {
        "best_config": asdict(best_config),
        "evaluation": {
            "avg_ndcg_at_100": best_result.ndcg_at_100,
            "avg_overlap_at_100": best_result.overlap_at_100,
            "avg_combined_score": best_result.combined_score,
            "per_source": best_result.per_source,
        },
        "comparison_with_current": {
            "current_version": "v2.1.0",
            "current_avg_ndcg": current_result.ndcg_at_100,
            "current_avg_overlap": current_result.overlap_at_100,
            "current_avg_combined": current_result.combined_score,
            "current_per_source": current_result.per_source,
            "improvement_avg_ndcg": best_result.ndcg_at_100 - current_result.ndcg_at_100,
            "improvement_avg_overlap": best_result.overlap_at_100 - current_result.overlap_at_100,
            "improvement_avg_combined": best_result.combined_score - current_result.combined_score,
        },
        "search_params": {
            "weight_ranges": weight_ranges,
            "eval_sources": eval_sources,
            "iconic_persons_count": len(tuner._iconic_persons),
        },
        "all_results": [
            {
                "config": asdict(r.config),
                "avg_ndcg_at_100": r.ndcg_at_100,
                "avg_overlap_at_100": r.overlap_at_100,
                "avg_combined_score": r.combined_score,
                "per_source": r.per_source,
            }
            for r in results[:20]
        ],
    }

    output_path = PROJECT_ROOT / "src/reports/tuning_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n結果を保存: {output_path}")

    # 改善率
    print("\n=== 改善率（v2.1.0 → v2.2.0） ===")
    print(
        f"  Avg NDCG: {current_result.ndcg_at_100:.3f} → {best_result.ndcg_at_100:.3f} ({best_result.ndcg_at_100 - current_result.ndcg_at_100:+.3f})"
    )
    print(
        f"  Avg Overlap: {current_result.overlap_at_100:.1%} → {best_result.overlap_at_100:.1%} ({(best_result.overlap_at_100 - current_result.overlap_at_100) * 100:+.1f}pp)"
    )
    print(
        f"  iconic_boost_multiplier: {current_config.iconic_boost_multiplier} → {best_config.iconic_boost_multiplier}"
    )


if __name__ == "__main__":
    main()
