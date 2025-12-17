#!/usr/bin/env python3
"""
Stage 5: report - パイプライン統計レポート生成

各ステージのレポートファイルを読み込み、パイプライン全体の統計を生成します。

Input: reports/*_*.json
Output: reports/pipeline_summary_YYYYMMDD_HHMMSS.json
        reports/pipeline_summary_YYYYMMDD_HHMMSS.md
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# デフォルトパス
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def find_latest_report(pattern: str, reports_dir: Path) -> Optional[Path]:
    """
    最新のレポートファイルを検索

    Args:
        pattern: ファイル名パターン（例: "episode_curation_*"）
        reports_dir: レポートディレクトリ

    Returns:
        最新のレポートファイルパス、見つからない場合None
    """
    matching_files = sorted(reports_dir.glob(f"{pattern}.json"), reverse=True)
    return matching_files[0] if matching_files else None


def load_report(report_path: Path) -> Optional[Dict]:
    """
    レポートファイル読み込み

    Args:
        report_path: レポートファイルパス

    Returns:
        レポートデータ、読み込み失敗時None
    """
    if not report_path or not report_path.exists():
        return None

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load report {report_path}: {e}")
        return None


def generate_pipeline_report(reports_dir: Path) -> Dict:
    """
    パイプライン統計レポート生成

    Args:
        reports_dir: レポートディレクトリ

    Returns:
        統計レポート辞書
    """
    logger.info("Generating pipeline summary report...")

    # 各ステージの最新レポートを検索
    stage2_report_path = find_latest_report("source_verification_*", reports_dir)
    stage3_report_path = find_latest_report("episode_curation_*", reports_dir)
    stage4_report_path = find_latest_report("validate_and_merge_*", reports_dir)

    # レポート読み込み
    stage2_data = load_report(stage2_report_path)
    stage3_data = load_report(stage3_report_path)
    stage4_data = load_report(stage4_report_path)

    # パイプライン統計
    pipeline_stats = {
        "timestamp": datetime.now().isoformat(),
        "stages": {},
        "overall": {},
        "quality_metrics": {},
        "recommendations": [],
    }

    # Stage 2統計
    if stage2_data and "statistics" in stage2_data:
        stats = stage2_data["statistics"]
        pipeline_stats["stages"]["stage2_verify"] = {
            "name": "Stage 2: verify-sources",
            "total_sources": stats.get("total_sources", 0),
            "verified": stats.get("verified", 0),
            "rejected": stats.get("rejected", 0),
            "duplicates": stats.get("duplicates", 0),
            "quality_A": stats.get("quality_A", 0),
            "quality_B": stats.get("quality_B", 0),
            "quality_C": stats.get("quality_C", 0),
            "pass_rate": (
                stats.get("verified", 0) / stats.get("total_sources", 1) * 100
                if stats.get("total_sources", 0) > 0
                else 0
            ),
        }

    # Stage 3統計
    if stage3_data and "statistics" in stage3_data:
        stats = stage3_data["statistics"]
        pipeline_stats["stages"]["stage3_curate"] = {
            "name": "Stage 3: curate-episodes",
            "total_sources": stats.get("total_sources", 0),
            "successful": stats.get("successful", 0),
            "failed": stats.get("failed", 0),
            "age_extraction_failed": stats.get("age_extraction_failed", 0),
            "llm_conversion_failed": stats.get("llm_conversion_failed", 0),
            "success_rate": (
                stats.get("successful", 0) / stats.get("total_sources", 1) * 100
                if stats.get("total_sources", 0) > 0
                else 0
            ),
        }

    # Stage 4統計
    if stage4_data and "statistics" in stage4_data:
        stats = stage4_data["statistics"]
        pipeline_stats["stages"]["stage4_merge"] = {
            "name": "Stage 4: validate-and-merge",
            "total_episodes": stats.get("total_episodes", 0),
            "passed": stats.get("passed", 0),
            "review": stats.get("review", 0),
            "failed": stats.get("failed", 0),
            "duplicates": stats.get("duplicates", 0),
            "excellent": stats.get("excellent", 0),
            "good": stats.get("good", 0),
            "acceptable": stats.get("acceptable", 0),
            "poor": stats.get("poor", 0),
            "unacceptable": stats.get("unacceptable", 0),
            "pass_rate": (
                stats.get("passed", 0) / stats.get("total_episodes", 1) * 100
                if stats.get("total_episodes", 0) > 0
                else 0
            ),
        }

        # Before/After
        if "original_count" in stage4_data and "new_count" in stage4_data:
            pipeline_stats["stages"]["stage4_merge"]["before_count"] = stage4_data["original_count"]
            pipeline_stats["stages"]["stage4_merge"]["after_count"] = stage4_data["total_count"]
            pipeline_stats["stages"]["stage4_merge"]["new_episodes"] = stage4_data["new_count"]

    # 全体統計
    stage2_verified = (
        pipeline_stats["stages"]["stage2_verify"]["verified"] if "stage2_verify" in pipeline_stats["stages"] else 0
    )
    stage3_successful = (
        pipeline_stats["stages"]["stage3_curate"]["successful"] if "stage3_curate" in pipeline_stats["stages"] else 0
    )
    stage4_passed = (
        pipeline_stats["stages"]["stage4_merge"]["passed"] if "stage4_merge" in pipeline_stats["stages"] else 0
    )

    # Overall statistics - 基本フィールドを先に設定
    total_input_sources = (
        pipeline_stats["stages"]["stage2_verify"]["total_sources"] if "stage2_verify" in pipeline_stats["stages"] else 0
    )

    pipeline_stats["overall"] = {
        "total_input_sources": total_input_sources,
        "final_merged_episodes": stage4_passed,
    }

    # 派生フィールドを計算して追加
    pipeline_stats["overall"]["overall_success_rate"] = (
        stage4_passed / total_input_sources * 100 if total_input_sources > 0 else 0
    )
    pipeline_stats["overall"]["stage2_to_stage3_retention"] = (
        stage3_successful / stage2_verified * 100 if stage2_verified > 0 else 0
    )
    pipeline_stats["overall"]["stage3_to_stage4_retention"] = (
        stage4_passed / stage3_successful * 100 if stage3_successful > 0 else 0
    )

    # 品質メトリクス
    if "stage4_merge" in pipeline_stats["stages"]:
        stage4 = pipeline_stats["stages"]["stage4_merge"]
        total_validated = stage4["total_episodes"]
        if total_validated > 0:
            pipeline_stats["quality_metrics"] = {
                "excellent_rate": stage4["excellent"] / total_validated * 100,
                "good_rate": stage4["good"] / total_validated * 100,
                "acceptable_rate": stage4["acceptable"] / total_validated * 100,
                "poor_rate": stage4["poor"] / total_validated * 100,
                "unacceptable_rate": stage4["unacceptable"] / total_validated * 100,
            }

    # 推奨アクション
    recommendations = []

    # Stage 2推奨
    if "stage2_verify" in pipeline_stats["stages"]:
        stage2 = pipeline_stats["stages"]["stage2_verify"]
        if stage2["pass_rate"] < 80:
            recommendations.append("⚠️ Stage 2の通過率が80%未満です。ソース品質の改善を検討してください。")
        if stage2["quality_C"] > stage2["quality_A"] + stage2["quality_B"]:
            recommendations.append("⚠️ C品質のソースが多数あります。A/B品質のソース収集を強化してください。")

    # Stage 3推奨
    if "stage3_curate" in pipeline_stats["stages"]:
        stage3 = pipeline_stats["stages"]["stage3_curate"]
        if stage3["success_rate"] < 70:
            recommendations.append(
                "⚠️ Stage 3の成功率が70%未満です。年齢情報の明記またはLLMプロンプトの改善を検討してください。"
            )
        if stage3["age_extraction_failed"] > 0:
            recommendations.append(
                f"💡 {stage3['age_extraction_failed']}件の年齢抽出失敗があります。contextフィールドに年齢情報を明記してください。"
            )

    # Stage 4推奨
    if "stage4_merge" in pipeline_stats["stages"]:
        stage4 = pipeline_stats["stages"]["stage4_merge"]
        if stage4["review"] > 0:
            recommendations.append(
                f"📝 {stage4['review']}件のエピソードがレビュー待ちです。review_queue.csvを確認してください。"
            )
        if stage4["failed"] > 0:
            recommendations.append(
                f"❌ {stage4['failed']}件のエピソードが不合格です。failed_episodes.csvを確認してください。"
            )

    # 品質メトリクス推奨
    if "quality_metrics" in pipeline_stats and pipeline_stats["quality_metrics"]:
        metrics = pipeline_stats["quality_metrics"]
        if metrics["excellent_rate"] + metrics["good_rate"] >= 90:
            recommendations.append("✅ 品質メトリクスは良好です。EXCELLENT/GOOD率が90%以上を維持しています。")
        elif metrics["poor_rate"] + metrics["unacceptable_rate"] > 20:
            recommendations.append(
                "⚠️ POOR/UNACCEPTABLE率が20%を超えています。エピソード生成プロンプトの改善を検討してください。"
            )

    # 全体推奨
    if pipeline_stats["overall"]["overall_success_rate"] >= 50:
        recommendations.append(
            f"🎉 パイプライン全体の成功率は{pipeline_stats['overall']['overall_success_rate']:.1f}%です。良好な結果です。"
        )
    elif pipeline_stats["overall"]["overall_success_rate"] < 30:
        recommendations.append(
            f"⚠️ パイプライン全体の成功率が{pipeline_stats['overall']['overall_success_rate']:.1f}%と低いです。各ステージのログを確認してください。"
        )

    if not recommendations:
        recommendations.append("✅ 特に問題は検出されませんでした。")

    pipeline_stats["recommendations"] = recommendations

    return pipeline_stats


def generate_markdown_report(stats: Dict, output_path: Path):
    """
    Markdown形式のレポート生成

    Args:
        stats: 統計データ
        output_path: 出力ファイルパス
    """
    md_lines = [
        "# エピソード収集パイプライン 統計レポート",
        "",
        f"**生成日時**: {stats['timestamp']}",
        "",
        "## 📊 全体統計",
        "",
        f"- **総入力ソース数**: {stats['overall']['total_input_sources']:,}件",
        f"- **最終マージエピソード数**: {stats['overall']['final_merged_episodes']:,}件",
        f"- **全体成功率**: {stats['overall']['overall_success_rate']:.1f}%",
        f"- **Stage 2→3 保持率**: {stats['overall']['stage2_to_stage3_retention']:.1f}%",
        f"- **Stage 3→4 保持率**: {stats['overall']['stage3_to_stage4_retention']:.1f}%",
        "",
    ]

    # 各ステージ統計
    md_lines.append("## 🔄 各ステージ統計")
    md_lines.append("")

    for stage_key, stage_data in stats["stages"].items():
        md_lines.append(f"### {stage_data['name']}")
        md_lines.append("")

        if stage_key == "stage2_verify":  # gitleaks:allow
            md_lines.extend(
                [
                    f"- 総ソース数: {stage_data['total_sources']:,}件",
                    f"- 検証済み: {stage_data['verified']:,}件",
                    f"- 却下: {stage_data['rejected']:,}件",
                    f"- 重複: {stage_data['duplicates']:,}件",
                    f"- 品質A: {stage_data['quality_A']:,}件",
                    f"- 品質B: {stage_data['quality_B']:,}件",
                    f"- 品質C: {stage_data['quality_C']:,}件",
                    f"- **通過率**: {stage_data['pass_rate']:.1f}%",
                    "",
                ]
            )
        elif stage_key == "stage3_curate":  # gitleaks:allow
            md_lines.extend(
                [
                    f"- 総ソース数: {stage_data['total_sources']:,}件",
                    f"- 成功: {stage_data['successful']:,}件",
                    f"- 失敗: {stage_data['failed']:,}件",
                    f"  - 年齢抽出失敗: {stage_data['age_extraction_failed']:,}件",
                    f"  - LLM変換失敗: {stage_data['llm_conversion_failed']:,}件",
                    f"- **成功率**: {stage_data['success_rate']:.1f}%",
                    "",
                ]
            )
        elif stage_key == "stage4_merge":  # gitleaks:allow
            md_lines.extend(
                [
                    f"- 総エピソード数: {stage_data['total_episodes']:,}件",
                    f"- 合格（自動マージ）: {stage_data['passed']:,}件",
                    f"- レビュー必要: {stage_data['review']:,}件",
                    f"- 不合格: {stage_data['failed']:,}件",
                    f"- 重複: {stage_data['duplicates']:,}件",
                    "",
                    "**品質レベル分布**:",
                    f"- EXCELLENT: {stage_data['excellent']:,}件",
                    f"- GOOD: {stage_data['good']:,}件",
                    f"- ACCEPTABLE: {stage_data['acceptable']:,}件",
                    f"- POOR: {stage_data['poor']:,}件",
                    f"- UNACCEPTABLE: {stage_data['unacceptable']:,}件",
                    "",
                    f"- **合格率**: {stage_data['pass_rate']:.1f}%",
                    "",
                ]
            )

            if "before_count" in stage_data:
                md_lines.extend(
                    [
                        "**マスターCSV更新**:",
                        f"- 更新前: {stage_data['before_count']:,}件",
                        f"- 新規追加: {stage_data['new_episodes']:,}件",
                        f"- 更新後: {stage_data['after_count']:,}件",
                        "",
                    ]
                )

    # 品質メトリクス
    if stats.get("quality_metrics"):
        metrics = stats["quality_metrics"]
        md_lines.extend(
            [
                "## 📈 品質メトリクス",
                "",
                f"- EXCELLENT率: {metrics['excellent_rate']:.1f}%",
                f"- GOOD率: {metrics['good_rate']:.1f}%",
                f"- ACCEPTABLE率: {metrics['acceptable_rate']:.1f}%",
                f"- POOR率: {metrics['poor_rate']:.1f}%",
                f"- UNACCEPTABLE率: {metrics['unacceptable_rate']:.1f}%",
                "",
            ]
        )

    # 推奨アクション
    md_lines.extend(
        [
            "## 💡 推奨アクション",
            "",
        ]
    )
    for rec in stats["recommendations"]:
        md_lines.append(f"- {rec}")
    md_lines.append("")

    # ファイル書き込み
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    logger.info(f"Markdown report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Stage 5: Generate pipeline summary report")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=REPORTS_DIR,
        help="Reports directory path",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 Stage 5: report - パイプライン統計レポート生成")
    print("=" * 80)
    print()

    try:
        # レポート生成
        stats = generate_pipeline_report(args.reports_dir)

        # JSON保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = args.reports_dir / f"pipeline_summary_{timestamp}.json"
        args.reports_dir.mkdir(parents=True, exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON report saved: {json_path}")

        # Markdown保存
        md_path = args.reports_dir / f"pipeline_summary_{timestamp}.md"
        generate_markdown_report(stats, md_path)

        # サマリー表示
        print()
        print("📊 パイプライン統計サマリー:")
        print(f"  総入力ソース: {stats['overall']['total_input_sources']:,}件")
        print(f"  最終マージ: {stats['overall']['final_merged_episodes']:,}件")
        print(f"  全体成功率: {stats['overall']['overall_success_rate']:.1f}%")
        print()
        print("💡 推奨アクション:")
        for rec in stats["recommendations"]:
            print(f"  {rec}")
        print()
        print("✅ レポート生成完了:")
        print(f"  - JSON: {json_path.name}")
        print(f"  - Markdown: {md_path.name}")
        print("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
