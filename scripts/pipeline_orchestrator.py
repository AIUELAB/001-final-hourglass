#!/usr/bin/env python3
"""
3層パイプライン オーケストレーター

Layer1（高速生成）→ Layer2（バッチ評価）→ Layer3（集中改稿）を
一気通貫で実行する統合スクリプト。

使用方法:
    # テスト実行（10件生成）
    python scripts/pipeline_orchestrator.py --target 10 --dry-run

    # 本番実行（100件目標）
    python scripts/pipeline_orchestrator.py --target 100 --execute

    # 年齢フィルター付き
    python scripts/pipeline_orchestrator.py --target 50 --ages 25,30,35 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 各Layerのインポート
from scripts.pipeline_layer1_generate import run_layer1
from scripts.pipeline_layer2_evaluate import run_layer2
from scripts.pipeline_layer3_improve import run_layer3
from scripts.episode_validator import validate_episodes, load_episodes, ValidationResult

# 追加検出ツール
try:
    from scripts.detect_problematic_episodes import analyze_episode, is_future_episode

    PROBLEMATIC_DETECTION_AVAILABLE = True
except ImportError:
    PROBLEMATIC_DETECTION_AVAILABLE = False

REPORT_DIR = PROJECT_ROOT / "reports"
GENERATED_DIR = PROJECT_ROOT / "generated"
REJECTED_CSV = GENERATED_DIR / "pipeline_rejected.csv"


def filter_critical_episodes(
    episodes: List[Dict], validation_result: ValidationResult
) -> tuple[List[Dict], List[Dict]]:
    """
    CRITICALエピソードを分離

    Args:
        episodes: エピソードリスト
        validation_result: バリデーション結果

    Returns:
        (クリーンなエピソード, 除外エピソード)
    """
    critical_ids = {issue.episode_id for issue in validation_result.issues if issue.severity == "CRITICAL"}

    clean = [ep for ep in episodes if ep.get("episode_id") not in critical_ids]
    rejected = [ep for ep in episodes if ep.get("episode_id") in critical_ids]

    # 除外エピソードに問題情報を付与
    for ep in rejected:
        ep_id = ep.get("episode_id")
        issues = [i for i in validation_result.issues if i.episode_id == ep_id]
        ep["validation_issues"] = "; ".join(f"[{i.severity}] {i.issue_type}: {i.message}" for i in issues)

    return clean, rejected


def save_rejected_episodes(episodes: List[Dict], reason: str, append: bool = True) -> int:
    """
    除外エピソードをCSVに保存

    Args:
        episodes: 除外エピソードリスト
        reason: 除外理由 (layer2_pre_validation / layer3_post_validation / layer4_critical)
        append: 追記モード

    Returns:
        保存件数
    """
    if not episodes:
        return 0

    GENERATED_DIR.mkdir(exist_ok=True)

    # 除外情報を追加
    timestamp = datetime.now().isoformat()
    for ep in episodes:
        ep["rejection_reason"] = reason
        ep["rejected_at"] = timestamp

    # CSVフィールド（基本フィールド + 除外情報）
    fieldnames = [
        "episode_id",
        "person_name",
        "age",
        "category",
        "episode_type",
        "episode_text",
        "person_type",
        "rejection_reason",
        "rejected_at",
        "validation_issues",
    ]

    # 既存ファイルがあれば追記、なければ新規作成
    file_exists = REJECTED_CSV.exists()
    mode = "a" if append and file_exists else "w"

    with open(REJECTED_CSV, mode, encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")

        if mode == "w" or not file_exists:
            writer.writeheader()

        writer.writerows(episodes)

    print(f"  📝 除外エピソード保存: {len(episodes)}件 → {REJECTED_CSV}")
    return len(episodes)


def run_pipeline(
    target_count: int,
    ages: Optional[List[int]] = None,
    execute: bool = False,
) -> Dict:
    """
    3層パイプラインを実行

    Args:
        target_count: 目標エピソード数
        ages: 年齢フィルター（オプション）
        execute: 本番実行フラグ

    Returns:
        パイプライン実行結果
    """
    start_time = datetime.now()

    print("=" * 70)
    print("🚀 3層パイプライン オーケストレーター")
    print("=" * 70)
    print(f"  目標件数: {target_count}")
    print(f"  年齢フィルター: {ages if ages else '全年齢'}")
    print(f"  実行モード: {'本番' if execute else 'ドライラン'}")
    print("=" * 70)

    results = {
        "target_count": target_count,
        "ages": ages,
        "execute": execute,
        "start_time": start_time.isoformat(),
        "layers": {},
    }

    # ==========================================================================
    # Layer 1: 高速生成
    # ==========================================================================
    print("\n" + "=" * 70)
    print("📍 PHASE 1/4: Layer1 高速生成")
    print("=" * 70)

    # 目標の1.5倍を生成（棄却・改稿失敗を見越して）
    generate_count = int(target_count * 1.5)
    print(f"  生成目標: {generate_count}件（目標{target_count}×1.5）")

    layer1_result = run_layer1(generate_count, ages, execute)
    results["layers"]["layer1"] = layer1_result

    if not layer1_result.get("generated", 0):
        print("\n❌ Layer1で生成されたエピソードがありません。終了します。")
        return results

    # ==========================================================================
    # Layer 2: バッチ評価
    # ==========================================================================
    print("\n" + "=" * 70)
    print("📍 PHASE 2/4: Layer2 バッチ評価")
    print("=" * 70)

    layer2_result = run_layer2(None, execute)  # 全件評価
    results["layers"]["layer2"] = layer2_result

    # ==========================================================================
    # Layer 3: 集中改稿
    # ==========================================================================
    print("\n" + "=" * 70)
    print("📍 PHASE 3/4: Layer3 集中改稿")
    print("=" * 70)

    layer3_result = run_layer3(None, execute)  # 全件改稿
    results["layers"]["layer3"] = layer3_result

    # ==========================================================================
    # Layer 4: 品質バリデーション（品質ゲート強化版）
    # ==========================================================================
    print("\n" + "=" * 70)
    print("📍 PHASE 4/4: 品質バリデーション")
    print("=" * 70)

    staging_episodes = load_episodes("pipeline_staging")
    layer4_rejected_count = 0

    if staging_episodes:
        validation_result = validate_episodes(staging_episodes)
        validation_summary = validation_result.summary()

        print(f"  ✅ チェック件数: {validation_summary['total_checked']}")
        print(f"  🚨 CRITICAL: {validation_summary['critical_count']}")
        print(f"  ⚠️  WARNING: {validation_summary['warning_count']}")

        results["validation"] = validation_summary

        # CRITICALエピソードを分離・除外
        if validation_summary["critical_count"] > 0:
            print(f"\n  ❌ {validation_summary['critical_count']}件のCRITICAL問題を検出")
            for issue in [i for i in validation_result.issues if i.severity == "CRITICAL"][:5]:
                print(f"    [{issue.episode_id}] {issue.issue_type}: {issue.message}")

            # CRITICALエピソードをフィルタリング
            clean_episodes, rejected_episodes = filter_critical_episodes(staging_episodes, validation_result)

            print("\n  🔍 フィルタリング結果:")
            print(f"    ✅ 通過: {len(clean_episodes)}件")
            print(f"    ❌ 除外: {len(rejected_episodes)}件")

            # 除外エピソードをCSVに保存
            if execute and rejected_episodes:
                layer4_rejected_count = save_rejected_episodes(rejected_episodes, "layer4_critical")

            # ステージングを更新（クリーンなエピソードのみ残す）
            if execute and clean_episodes:
                staging_path = GENERATED_DIR / "pipeline_staging.csv"
                if staging_path.exists():
                    import pandas as pd

                    clean_ids = {ep.get("episode_id") for ep in clean_episodes}
                    df = pd.read_csv(staging_path, encoding="utf-8-sig")
                    df_clean = df[df["episode_id"].isin(clean_ids)]
                    df_clean.to_csv(staging_path, index=False, encoding="utf-8-sig")
                    print(f"  📦 ステージング更新: {len(df_clean)}件")

            results["layer4_rejected"] = layer4_rejected_count
        else:
            print("\n  ✅ CRITICALなし - 全エピソード通過")
    else:
        print("  ⚠️ バリデーション対象なし")

    # ==========================================================================
    # Layer 4.5: 追加問題検出（未来エピソード、曖昧内容など）
    # ==========================================================================
    problematic_count = 0
    if PROBLEMATIC_DETECTION_AVAILABLE and staging_episodes:
        print("\n" + "=" * 70)
        print("📍 追加チェック: 問題エピソード検出")
        print("=" * 70)

        import pandas as pd

        problematic_episodes = []

        for ep in staging_episodes:
            # pandas.Seriesに変換して分析
            row = pd.Series(ep)
            analysis = analyze_episode(row)

            if analysis["needs_review"] or analysis["needs_deletion"]:
                problematic_episodes.append(
                    {
                        **ep,
                        "validation_issues": "; ".join(analysis["issues"]),
                        "severity": analysis["severity"],
                    }
                )

        if problematic_episodes:
            print(f"  🚨 問題エピソード検出: {len(problematic_episodes)}件")

            # 削除推奨（severity >= 3）のみ除外
            deletion_candidates = [p for p in problematic_episodes if p.get("severity", 0) >= 3]
            review_candidates = [p for p in problematic_episodes if p.get("severity", 0) < 3]

            print(f"    削除推奨: {len(deletion_candidates)}件")
            print(f"    要レビュー: {len(review_candidates)}件")

            # 削除推奨を除外エピソードとして保存
            if execute and deletion_candidates:
                problematic_count = save_rejected_episodes(deletion_candidates, "layer4_problematic")

            results["problematic_detected"] = {
                "deletion_recommended": len(deletion_candidates),
                "review_recommended": len(review_candidates),
                "rejected": problematic_count,
            }
        else:
            print("  ✅ 問題エピソードなし")

    # ==========================================================================
    # 最終結果サマリ
    # ==========================================================================
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # 最終統計（Layer4 + 問題検出の除外を反映）
    total_quality_rejected = layer4_rejected_count + problematic_count
    final_accepted = (
        layer2_result.get("auto_accepted", 0)
        + layer3_result.get("improved_accepted", 0)
        - total_quality_rejected  # 品質ゲートで除外された分を減算
    )
    total_rejected = (
        layer2_result.get("rejected", 0)
        + layer3_result.get("rejected", 0)
        + layer3_result.get("improvement_insufficient", 0)
        + total_quality_rejected  # 品質ゲートで除外された分を加算
    )

    results["final_stats"] = {
        "total_generated": layer1_result.get("generated", 0),
        "auto_accepted": layer2_result.get("auto_accepted", 0),
        "improved_accepted": layer3_result.get("improved_accepted", 0),
        "final_accepted": final_accepted,
        "total_rejected": total_rejected,
        "success_rate": round(final_accepted / max(1, layer1_result.get("generated", 1)) * 100, 1),
        "target_achievement": round(final_accepted / max(1, target_count) * 100, 1),
        "elapsed_seconds": round(elapsed, 1),
        "episodes_per_minute": round(final_accepted / max(1, elapsed / 60), 1),
    }
    results["end_time"] = end_time.isoformat()

    print("\n" + "=" * 70)
    print("🎉 パイプライン完了")
    print("=" * 70)
    print("\n📊 最終結果:")
    for k, v in results["final_stats"].items():
        print(f"  {k}: {v}")

    print("\n📈 達成状況:")
    print(f"  目標: {target_count}件")
    print(f"  達成: {final_accepted}件 ({results['final_stats']['target_achievement']}%)")

    if final_accepted < target_count:
        shortfall = target_count - final_accepted
        print(f"  ⚠️ 不足: {shortfall}件")

    # レポート保存
    if execute:
        REPORT_DIR.mkdir(exist_ok=True)
        report_path = REPORT_DIR / f"pipeline_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n📝 レポート保存: {report_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="3層パイプライン オーケストレーター")
    parser.add_argument("--target", type=int, default=10, help="目標エピソード数")
    parser.add_argument("--ages", type=str, help="年齢フィルター（カンマ区切り）")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    ages = None
    if args.ages:
        ages = [int(a.strip()) for a in args.ages.split(",")]

    execute = args.execute and not args.dry_run

    run_pipeline(args.target, ages, execute)


if __name__ == "__main__":
    main()
