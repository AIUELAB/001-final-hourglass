#!/usr/bin/env python3
"""
エピソード選別スクリプト

機能:
1. 総合品質スコアの計算
2. 重複エピソードの検出
3. 低品質エピソードの特定
4. 選別結果のレポート生成

総合品質スコア計算式:
episode_quality_score = (
    factuality_score * 0.25 +
    drama_score * 0.20 +
    memorability_score * 0.15 +
    教育的価値 * 0.15 +
    ストーリー品質 * 0.15 +
    事実密度 * 0.10
)

選別閾値:
| 判定 | スコア | アクション |
|------|--------|-----------|
| 保持 | >= 6.5 | そのまま |
| 要改善 | 5.0-6.5 | LLM再生成候補 |
| 統合検討 | 3.5-5.0 | 他エピソードと統合 |
| 破棄候補 | < 3.5 | 手動確認後削除 |

使用方法:
    python scripts/episode_selection.py [--execute] [--report-only]
"""

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Dict, List, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"

# 品質スコア重み
QUALITY_WEIGHTS = {
    "quality_score": 0.25,  # factuality相当
    "記憶性スコア": 0.15,
    "教育的価値": 0.15,
    "ストーリー品質": 0.15,
    "事実密度": 0.10,
    "共感性スコア": 0.10,
    "意外性スコア": 0.10,
}

# 選別閾値
THRESHOLDS = {
    "keep": 6.5,
    "improve": 5.0,
    "merge": 3.5,
}


class SelectionResult(Enum):
    """選別結果"""

    KEEP = "keep"  # 保持
    IMPROVE = "improve"  # 要改善
    MERGE = "merge"  # 統合検討
    DISCARD = "discard"  # 破棄候補


@dataclass
class EpisodeQuality:
    """エピソード品質情報"""

    episode_id: str
    person_name: str
    age: int
    quality_score: float
    selection_result: SelectionResult
    component_scores: Dict[str, float]
    episode_text_preview: str


@dataclass
class DuplicateEpisode:
    """重複エピソード情報"""

    episode_id_1: str
    episode_id_2: str
    person_name: str
    age: int
    similarity: float
    text_1_preview: str
    text_2_preview: str


class EpisodeSelector:
    """エピソード選別クラス"""

    def __init__(self, csv_path: str = CSV_PATH):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.quality_results: List[EpisodeQuality] = []
        self.duplicate_results: List[DuplicateEpisode] = []

    def calculate_quality_score(self, row: pd.Series) -> Tuple[float, Dict[str, float]]:
        """
        総合品質スコアを計算

        Returns:
            (総合スコア, 各コンポーネントスコアの辞書)
        """
        total = 0.0
        components = {}

        for col, weight in QUALITY_WEIGHTS.items():
            value = row.get(col, 0)
            if pd.isna(value):
                value = 5.0  # デフォルト値
            else:
                value = float(value)
                # 0-100スケールを0-10に正規化
                if value > 10:
                    value = value / 10

            components[col] = value
            total += value * weight

        # 総合スコアを10点満点に正規化
        normalized = total / sum(QUALITY_WEIGHTS.values())

        return normalized, components

    def classify_episode(self, score: float) -> SelectionResult:
        """スコアに基づいて分類"""
        if score >= THRESHOLDS["keep"]:
            return SelectionResult.KEEP
        elif score >= THRESHOLDS["improve"]:
            return SelectionResult.IMPROVE
        elif score >= THRESHOLDS["merge"]:
            return SelectionResult.MERGE
        else:
            return SelectionResult.DISCARD

    def evaluate_all_episodes(self) -> List[EpisodeQuality]:
        """全エピソードを評価"""
        self.quality_results = []

        for _, row in self.df.iterrows():
            score, components = self.calculate_quality_score(row)
            result = self.classify_episode(score)

            episode_text = str(row.get("episode_text", ""))
            preview = episode_text[:100] + "..." if len(episode_text) > 100 else episode_text

            self.quality_results.append(
                EpisodeQuality(
                    episode_id=str(row.get("episode_id", "")),
                    person_name=str(row.get("person_name", "")),
                    age=int(row.get("age", 0)) if not pd.isna(row.get("age")) else 0,
                    quality_score=round(score, 2),
                    selection_result=result,
                    component_scores={k: round(v, 2) for k, v in components.items()},
                    episode_text_preview=preview,
                )
            )

        return self.quality_results

    def detect_duplicate_episodes(self, similarity_threshold: float = 0.7) -> List[DuplicateEpisode]:
        """
        重複エピソードを検出

        同一人物・同一年齢のエピソードで類似度が高いものを検出
        """
        self.duplicate_results = []

        # 人物・年齢でグループ化
        groups = self.df.groupby(["person_name", "age"])

        for (person_name, age), group_df in groups:
            if len(group_df) < 2:
                continue

            episodes = group_df.to_dict("records")
            n = len(episodes)

            for i in range(n):
                text_i = str(episodes[i].get("episode_text", ""))
                if not text_i:
                    continue

                for j in range(i + 1, n):
                    text_j = str(episodes[j].get("episode_text", ""))
                    if not text_j:
                        continue

                    # 類似度計算
                    similarity = SequenceMatcher(None, text_i, text_j).ratio()

                    if similarity >= similarity_threshold:
                        self.duplicate_results.append(
                            DuplicateEpisode(
                                episode_id_1=str(episodes[i].get("episode_id", "")),
                                episode_id_2=str(episodes[j].get("episode_id", "")),
                                person_name=str(person_name),
                                age=int(age),
                                similarity=round(similarity, 3),
                                text_1_preview=text_i[:50] + "...",
                                text_2_preview=text_j[:50] + "...",
                            )
                        )

        return self.duplicate_results

    def get_summary(self) -> Dict:
        """結果サマリーを取得"""
        # 品質別集計
        quality_counts = {
            "keep": 0,
            "improve": 0,
            "merge": 0,
            "discard": 0,
        }
        for r in self.quality_results:
            quality_counts[r.selection_result.value] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "total_episodes": len(self.df),
            "quality_distribution": quality_counts,
            "duplicate_pairs": len(self.duplicate_results),
            "average_quality": round(sum(r.quality_score for r in self.quality_results) / len(self.quality_results), 2)
            if self.quality_results
            else 0,
        }

    def generate_report(self) -> Dict:
        """詳細レポートを生成"""
        summary = self.get_summary()

        # 低品質エピソードTOP20
        low_quality = sorted(self.quality_results, key=lambda x: x.quality_score)[:20]

        # 高品質エピソードTOP20
        high_quality = sorted(self.quality_results, key=lambda x: x.quality_score, reverse=True)[:20]

        return {
            **summary,
            "low_quality_top20": [asdict(q) for q in low_quality],
            "high_quality_top20": [asdict(q) for q in high_quality],
            "duplicates": [asdict(d) for d in self.duplicate_results[:50]],
        }


def main():
    parser = argparse.ArgumentParser(description="エピソード選別")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    parser.add_argument("--report-only", action="store_true", help="レポートのみ生成")
    parser.add_argument("--similarity", type=float, default=0.7, help="重複検出の類似度閾値")
    args = parser.parse_args()

    print("=" * 70)
    print("エピソード選別スクリプト")
    print("=" * 70)

    selector = EpisodeSelector(args.csv)

    print(f"\n📂 CSV読み込み: {args.csv}")
    print(f"   総エピソード数: {len(selector.df):,}")

    print("\n🔍 品質評価中...")
    quality_results = selector.evaluate_all_episodes()

    # 品質分布
    counts = {"keep": 0, "improve": 0, "merge": 0, "discard": 0}
    for r in quality_results:
        counts[r.selection_result.value] += 1

    print("\n📊 品質分布:")
    print(f"   ✅ 保持 (>=6.5): {counts['keep']:,}件 ({100*counts['keep']/len(quality_results):.1f}%)")
    print(f"   ⚠️  要改善 (5.0-6.5): {counts['improve']:,}件 ({100*counts['improve']/len(quality_results):.1f}%)")
    print(f"   🔄 統合検討 (3.5-5.0): {counts['merge']:,}件 ({100*counts['merge']/len(quality_results):.1f}%)")
    print(f"   ❌ 破棄候補 (<3.5): {counts['discard']:,}件 ({100*counts['discard']/len(quality_results):.1f}%)")

    avg_score = sum(r.quality_score for r in quality_results) / len(quality_results)
    print(f"\n   平均品質スコア: {avg_score:.2f}")

    print(f"\n🔍 重複エピソード検出中 (類似度>={args.similarity})...")
    duplicates = selector.detect_duplicate_episodes(args.similarity)
    print(f"   検出: {len(duplicates)}ペア")

    # 低品質サンプル表示
    low_quality = sorted(quality_results, key=lambda x: x.quality_score)[:5]
    print("\n   【低品質サンプル (最も低い5件)】")
    for q in low_quality:
        print(f"      {q.episode_id}: {q.person_name} ({q.age}歳) - スコア: {q.quality_score}")

    # レポート生成
    report = selector.generate_report()
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"episode_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📄 レポート: {report_path}")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
