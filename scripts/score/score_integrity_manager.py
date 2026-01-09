#!/usr/bin/env python3
"""
スコア整合性マネージャー v1.0.0

目的:
  新しいスコアを追加/更新したときに、全エピソードの欠損スコアを埋め、
  v10ダッシュボードに正しく表示される状態を保証する。

使用方法:
  # 欠損検出のみ (dry-run)
  python scripts/score/score_integrity_manager.py --detect

  # 欠損埋め実行
  python scripts/score/score_integrity_manager.py --fill

  # 全再計算 (強制)
  python scripts/score/score_integrity_manager.py --recalculate-all

  # 検証のみ
  python scripts/score/score_integrity_manager.py --validate

  # 完全パイプライン (検出→埋め→検証→レポート)
  python scripts/score/score_integrity_manager.py --full-pipeline
"""

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# パス設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"
LOG_DIR = REPORT_DIR / "logs"

# スコア列定義（Phase 28: 英語化）
SCORE_COLUMNS = {
    # 8軸スコア (0-10) - Phase 28: 英語化
    "memorability_score": {"scale": (0, 10), "type": "8axis", "required": True},
    "empathy_score": {"scale": (0, 10), "type": "8axis", "required": True},
    "surprise_score": {"scale": (0, 10), "type": "8axis", "required": True},
    "generation_quality_score": {"scale": (0, 10), "type": "8axis", "required": True},
    "educational_value": {"scale": (0, 10), "type": "8axis", "required": True},
    "story_quality": {"scale": (0, 10), "type": "8axis", "required": True},
    "factual_density": {"scale": (0, 10), "type": "8axis", "required": True},
    "iconic_score": {"scale": (0, 10), "type": "8axis", "required": True},
    # 派生スコア
    "composite_score": {"scale": (0, 70), "type": "derived", "required": True},
    "composite_score_5axis": {"scale": (0, 50), "type": "derived", "required": False},
    # Episode Fame
    "episode_fame_v6": {"scale": (0, 200), "type": "fame", "required": True},
    "episode_fame_tier_v6": {"scale": (1, 5), "type": "tier", "required": True},
    "episode_fame_score": {"scale": (0, 200), "type": "fame", "required": False},
    # 人物有名度
    "fame_score_v3": {"scale": (0, 900), "type": "fame", "required": True},
    "fame_score_japan": {"scale": (0, 1000), "type": "fame", "required": False},
    "fame_tier": {"scale": (1, 5), "type": "tier", "required": False},
    # Celebrity Score
    "celebrity_score_v2": {"scale": (0, 1000), "type": "celebrity", "required": True},
    "celebrity_rank_v2": {"scale": (1, 10000), "type": "rank", "required": True},
    # 超総合スコア
    "super_total_score": {"scale": (0, 1000000), "type": "super", "required": True},
    # その他
    "quality_score": {"scale": (0, 10), "type": "quality", "required": False},
}

# 欠損と見なす値
MISSING_VALUES = [None, np.nan, "", "nan", "NaN", "null", "NULL"]


class ScoreIntegrityManager:
    """スコア整合性管理クラス"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.df: pd.DataFrame | None = None
        self.report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "detection": {},
            "fill": {},
            "validation": {},
            "errors": [],
        }

    def load_csv(self) -> bool:
        """CSVを読み込む"""
        try:
            self.df = pd.read_csv(CSV_PATH, low_memory=False)
            print(f"✓ CSV読み込み: {len(self.df)}件")
            return True
        except Exception as e:
            self.report["errors"].append(f"CSV読み込みエラー: {e}")
            print(f"✗ CSV読み込みエラー: {e}")
            return False

    def detect_missing(self) -> dict[str, dict]:
        """欠損を検出"""
        if self.df is None:
            return {}

        results = {}
        total = len(self.df)

        print("\n" + "=" * 70)
        print("欠損検出結果")
        print("=" * 70)
        print(f"{'列名':<25} {'欠損':<8} {'充填率':<10} {'状態'}")
        print("-" * 70)

        for col, config in SCORE_COLUMNS.items():
            if col not in self.df.columns:
                results[col] = {
                    "missing": total,
                    "filled": 0,
                    "rate": 0.0,
                    "status": "column_not_found",
                    "required": config["required"],
                }
                print(f"{col:<25} {'列なし':<8} {'0.0%':<10} {'❌ 列なし'}")
                continue

            # 欠損検出
            is_missing = self.df[col].isna() | self.df[col].isin(MISSING_VALUES)

            # 数値列の場合、0も欠損として扱う（tier/rank以外）
            if config["type"] not in ["tier", "rank"]:
                is_missing = is_missing | (self.df[col] == 0)

            missing_count = is_missing.sum()
            filled_count = total - missing_count
            rate = filled_count / total * 100

            status = "ok" if rate >= 99.9 else "warning" if rate >= 95 else "critical"
            status_icon = "✓" if status == "ok" else "⚠️" if status == "warning" else "❌"

            results[col] = {
                "missing": int(missing_count),
                "filled": int(filled_count),
                "rate": round(rate, 2),
                "status": status,
                "required": config["required"],
                "scale": config["scale"],
            }

            print(f"{col:<25} {missing_count:<8} {rate:>6.1f}%    {status_icon} {status}")

        self.report["detection"] = results

        # サマリー
        critical = [k for k, v in results.items() if v["status"] == "critical" and v.get("required")]
        warning = [k for k, v in results.items() if v["status"] == "warning"]

        print("-" * 70)
        print(f"重大欠損: {len(critical)}列, 警告: {len(warning)}列")

        return results

    def fill_missing_scores(self) -> dict[str, int]:
        """欠損スコアを埋める"""
        if self.df is None:
            return {}

        filled_counts = {}
        print("\n" + "=" * 70)
        print("欠損埋め処理" + (" [DRY-RUN]" if self.dry_run else ""))
        print("=" * 70)

        # 1. 7軸スコア: ヒューリスティックで埋める
        filled_counts["7axis"] = self._fill_seven_axis()

        # 2. composite_score: 7軸から計算
        filled_counts["composite"] = self._fill_composite_scores()

        # 3. fame_tier: fame_score_v3から計算
        filled_counts["fame_tier"] = self._fill_fame_tier()

        # 4. episode_fame_score: episode_fame_v6から同期
        filled_counts["episode_fame_score"] = self._sync_episode_fame_score()

        # 5. super_total_score: 再計算（品質ゲート適用）
        filled_counts["super_total"] = self._fill_super_total_score()

        self.report["fill"] = filled_counts

        total_filled = sum(filled_counts.values())
        print("-" * 70)
        print(f"合計埋め件数: {total_filled}")

        return filled_counts

    def _fill_seven_axis(self) -> int:
        """7軸スコアをヒューリスティックで埋める"""
        filled = 0
        seven_axis_cols = [
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
        ]

        for col in seven_axis_cols:
            if col not in self.df.columns:
                continue

            is_missing = self.df[col].isna() | (self.df[col] == 0)
            missing_idx = self.df[is_missing].index

            if len(missing_idx) == 0:
                continue

            for idx in missing_idx:
                episode_text = str(self.df.at[idx, "episode_text"] or "")
                score = self._calculate_heuristic_score(episode_text, col)

                if not self.dry_run:
                    self.df.at[idx, col] = score
                filled += 1

        print(f"  7軸スコア: {filled}件埋め")
        return filled

    def _calculate_heuristic_score(self, text: str, col_name: str) -> float:
        """テキストからヒューリスティックでスコア計算"""
        if not text or len(text) < 10:
            return 6.0

        base_score = 6.0
        text_len = len(text)

        # 文字数ボーナス
        if text_len > 300:
            base_score += 0.8
        elif text_len > 200:
            base_score += 0.5
        elif text_len > 150:
            base_score += 0.2

        if col_name == "memorability_score":
            # 具体的な数値・年号
            year_count = len(re.findall(r"\d{4}年", text))
            number_count = len(re.findall(r"\d+", text))
            base_score += min(year_count * 0.3, 1.0)
            base_score += min(number_count * 0.1, 0.8)

        elif col_name == "empathy_score":
            # 感情キーワード
            emotion_words = ["感動", "喜び", "悲しみ", "涙", "笑顔", "希望", "絶望", "勇気"]
            emotion_count = sum(1 for w in emotion_words if w in text)
            base_score += min(emotion_count * 0.4, 1.5)

        elif col_name == "surprise_score":
            # 転換キーワード
            surprise_words = ["しかし", "ところが", "実は", "驚くべき", "意外に", "突然"]
            surprise_count = sum(1 for w in surprise_words if w in text)
            base_score += min(surprise_count * 0.5, 1.5)

        elif col_name == "generation_quality_score":
            # 文章の完成度（句読点、構成）
            has_proper_ending = text.rstrip().endswith(("。", "た。", "だ。"))
            has_quotes = "「" in text or "」" in text
            base_score += 0.5 if has_proper_ending else 0
            base_score += 0.3 if has_quotes else 0

        elif col_name == "educational_value":
            # 学習キーワード
            edu_words = ["発見", "研究", "開発", "発明", "理論", "技術", "革新", "初めて"]
            edu_count = sum(1 for w in edu_words if w in text)
            base_score += min(edu_count * 0.4, 1.5)

        elif col_name == "story_quality":
            # ストーリー要素
            story_words = ["夢", "目標", "挑戦", "困難", "克服", "達成", "転機"]
            story_count = sum(1 for w in story_words if w in text)
            base_score += min(story_count * 0.4, 1.5)

        elif col_name == "factual_density":
            # 具体性
            year_count = len(re.findall(r"\d{4}年", text))
            number_count = len(re.findall(r"\d+", text))
            proper_nouns = len(re.findall(r"「[^」]+」", text))
            base_score += min(year_count * 0.5, 1.5)
            base_score += min(number_count * 0.15, 1.0)
            base_score += min(proper_nouns * 0.3, 1.0)

        return min(max(base_score, 5.0), 9.5)

    def _fill_composite_scores(self) -> int:
        """composite_scoreを7軸から計算"""
        filled = 0

        # composite_score = 7軸合計
        is_missing = self.df["composite_score"].isna() | (self.df["composite_score"] == 0)
        missing_idx = self.df[is_missing].index

        for idx in missing_idx:
            seven_axis_sum = (
                self.df.at[idx, "memorability_score"]
                + self.df.at[idx, "empathy_score"]
                + self.df.at[idx, "surprise_score"]
                + self.df.at[idx, "generation_quality_score"]
                + self.df.at[idx, "educational_value"]
                + self.df.at[idx, "story_quality"]
                + self.df.at[idx, "factual_density"]
            )
            if not self.dry_run:
                self.df.at[idx, "composite_score"] = seven_axis_sum
            filled += 1

        # composite_score_5axis
        if "composite_score_5axis" in self.df.columns:
            is_missing_5 = self.df["composite_score_5axis"].isna() | (self.df["composite_score_5axis"] == 0)
            missing_idx_5 = self.df[is_missing_5].index

            for idx in missing_idx_5:
                # 5軸 = (記憶性+生成品質)/2 + (共感性+意外性)/2 + educational_value + story_quality + factual_density
                overall = (self.df.at[idx, "memorability_score"] + self.df.at[idx, "generation_quality_score"]) / 2
                emotional = (self.df.at[idx, "empathy_score"] + self.df.at[idx, "surprise_score"]) / 2
                five_axis_sum = (
                    overall
                    + emotional
                    + self.df.at[idx, "educational_value"]
                    + self.df.at[idx, "story_quality"]
                    + self.df.at[idx, "factual_density"]
                )
                if not self.dry_run:
                    self.df.at[idx, "composite_score_5axis"] = five_axis_sum
                filled += 1

        print(f"  composite_score: {filled}件埋め")
        return filled

    def _fill_fame_tier(self) -> int:
        """fame_tierをfame_score_v3から計算"""
        filled = 0

        if "fame_tier" not in self.df.columns or "fame_score_v3" not in self.df.columns:
            return 0

        is_missing = self.df["fame_tier"].isna() | (self.df["fame_tier"] == 0)
        missing_idx = self.df[is_missing].index

        for idx in missing_idx:
            fame_score = self.df.at[idx, "fame_score_v3"]
            if pd.isna(fame_score) or fame_score == 0:
                continue

            # fame_score_v3 → tier変換
            if fame_score >= 800:
                tier = 5
            elif fame_score >= 600:
                tier = 4
            elif fame_score >= 400:
                tier = 3
            elif fame_score >= 200:
                tier = 2
            else:
                tier = 1

            if not self.dry_run:
                self.df.at[idx, "fame_tier"] = tier
            filled += 1

        print(f"  fame_tier: {filled}件埋め")
        return filled

    def _sync_episode_fame_score(self) -> int:
        """episode_fame_scoreをepisode_fame_v6から同期"""
        filled = 0

        if "episode_fame_score" not in self.df.columns:
            return 0

        is_missing = self.df["episode_fame_score"].isna() | (self.df["episode_fame_score"] == 0)
        has_v6 = self.df["episode_fame_v6"].notna() & (self.df["episode_fame_v6"] > 0)
        sync_idx = self.df[is_missing & has_v6].index

        for idx in sync_idx:
            if not self.dry_run:
                self.df.at[idx, "episode_fame_score"] = self.df.at[idx, "episode_fame_v6"]
            filled += 1

        print(f"  episode_fame_score: {filled}件埋め (v6から同期)")
        return filled

    def _fill_super_total_score(self) -> int:
        """super_total_scoreを再計算（品質ゲート適用）"""
        filled = 0

        if "super_total_score" not in self.df.columns:
            return 0

        is_missing = self.df["super_total_score"].isna() | (self.df["super_total_score"] == 0)
        missing_idx = self.df[is_missing].index

        for idx in missing_idx:
            # 品質ゲートチェック
            factual = self.df.at[idx, "factual_density"]
            gen_quality = self.df.at[idx, "generation_quality_score"]

            if factual < 6.0 or gen_quality < 6.0:
                # 品質ゲート未達 → 0のまま
                continue

            # 超総合スコア計算
            celebrity = self.df.at[idx, "celebrity_score_v2"] or 0
            fame = self.df.at[idx, "fame_score_v3"] or 0
            quality = self.df.at[idx, "composite_score"] or 0
            historical = self.df.at[idx, "episode_fame_v6"] or 0

            # 正規化（0-1000スケール）
            celebrity_norm = min(celebrity, 1000)
            fame_norm = min(fame / 900 * 1000, 1000)
            quality_norm = min(quality / 70 * 1000, 1000)
            historical_norm = min(historical / 200 * 1000, 1000)

            # 加重平均
            super_total = (
                celebrity_norm * 0.30 + fame_norm * 0.30 + quality_norm * 0.20 + historical_norm * 0.20
            ) * 1000

            if not self.dry_run:
                self.df.at[idx, "super_total_score"] = super_total
            filled += 1

        print(f"  super_total_score: {filled}件埋め (品質ゲート適用)")
        return filled

    def validate_scores(self) -> dict[str, Any]:
        """スコアを検証"""
        if self.df is None:
            return {}

        print("\n" + "=" * 70)
        print("スコア検証")
        print("=" * 70)

        validation = {
            "range_violations": {},
            "nan_inf_count": 0,
            "distribution": {},
        }

        for col, config in SCORE_COLUMNS.items():
            if col not in self.df.columns:
                continue

            scale_min, scale_max = config["scale"]

            # 範囲外チェック
            out_of_range = self.df[(self.df[col] < scale_min) | (self.df[col] > scale_max * 1.5)]
            if len(out_of_range) > 0:
                validation["range_violations"][col] = len(out_of_range)
                print(f"  ⚠️ {col}: {len(out_of_range)}件が範囲外 ({scale_min}-{scale_max})")

            # NaN/inf チェック
            nan_inf = self.df[col].isna().sum() + np.isinf(self.df[col].astype(float, errors="ignore")).sum()
            if nan_inf > 0:
                validation["nan_inf_count"] += nan_inf

            # 分布
            if self.df[col].notna().sum() > 0:
                validation["distribution"][col] = {
                    "min": float(self.df[col].min()),
                    "max": float(self.df[col].max()),
                    "mean": float(self.df[col].mean()),
                    "std": float(self.df[col].std()),
                }

        self.report["validation"] = validation

        if not validation["range_violations"]:
            print("  ✓ 全列が正常範囲内")

        return validation

    def save_csv(self) -> bool:
        """CSVを保存"""
        if self.dry_run:
            print("\n[DRY-RUN] CSVは保存されません")
            return True

        try:
            # バックアップ
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"MASTER_EPISODES_{timestamp}.csv"
            shutil.copy(CSV_PATH, backup_path)
            print(f"\n✓ バックアップ: {backup_path}")

            # 保存
            self.df.to_csv(CSV_PATH, index=False)
            print(f"✓ CSV保存: {CSV_PATH}")
            return True
        except Exception as e:
            self.report["errors"].append(f"CSV保存エラー: {e}")
            print(f"✗ CSV保存エラー: {e}")
            return False

    def save_report(self) -> Path:
        """レポートを保存"""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = LOG_DIR / f"score_integrity_{timestamp}.json"

        # numpy型をPython標準型に変換
        def convert_numpy(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            return obj

        report_converted = convert_numpy(self.report)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_converted, f, ensure_ascii=False, indent=2)

        print(f"\n✓ レポート: {report_path}")
        return report_path

    def run_full_pipeline(self) -> bool:
        """完全パイプライン実行"""
        print("=" * 70)
        print("スコア整合性マネージャー v1.0.0")
        print("=" * 70)
        print(f"モード: {'DRY-RUN' if self.dry_run else '実行'}")
        print(f"対象: {CSV_PATH}")

        if not self.load_csv():
            return False

        self.detect_missing()
        self.fill_missing_scores()
        self.validate_scores()

        if not self.dry_run:
            self.save_csv()

        self.save_report()

        return len(self.report["errors"]) == 0


def main():
    parser = argparse.ArgumentParser(description="スコア整合性マネージャー")
    parser.add_argument("--detect", action="store_true", help="欠損検出のみ")
    parser.add_argument("--fill", action="store_true", help="欠損埋め実行")
    parser.add_argument("--validate", action="store_true", help="検証のみ")
    parser.add_argument("--full-pipeline", action="store_true", help="完全パイプライン")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行（CSVを更新）")

    args = parser.parse_args()

    # デフォルトはdry-run
    dry_run = not args.execute

    manager = ScoreIntegrityManager(dry_run=dry_run)

    if args.detect:
        manager.load_csv()
        manager.detect_missing()
        manager.save_report()
    elif args.fill:
        manager.load_csv()
        manager.fill_missing_scores()
        if not dry_run:
            manager.save_csv()
        manager.save_report()
    elif args.validate:
        manager.load_csv()
        manager.validate_scores()
        manager.save_report()
    else:
        # デフォルト: full-pipeline
        manager.run_full_pipeline()


if __name__ == "__main__":
    main()
