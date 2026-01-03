#!/usr/bin/env python3
"""
品質監視スクリプト

エピソードの品質指標をリアルタイムで監視し、
問題を早期検知するためのアラートを発行する。

使用方法:
    # 品質レポート表示
    python scripts/quality_monitor.py

    # JSONレポート出力
    python scripts/quality_monitor.py --output report.json

    # アラートチェックのみ
    python scripts/quality_monitor.py --alerts-only
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 埋め草検出モジュール
from scripts.validation.filler_detector import is_filler

# CSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
REPORT_DIR = PROJECT_ROOT / "reports"


# =============================================================================
# 品質監視設定
# =============================================================================

QUALITY_THRESHOLDS = {
    # 全体品質
    "composite_avg_target": 550,  # 超総合平均の目標値
    "composite_avg_alert": 500,  # 超総合平均のアラート閾値
    "composite_avg_critical": 450,  # 超総合平均の緊急閾値
    # スコア帯分布
    "high_quality_rate_target": 0.35,  # 600+率の目標（35%）
    "high_quality_rate_alert": 0.25,  # 600+率のアラート閾値（25%）
    "rejection_rate_alert": 0.20,  # 棄却率アラート閾値（20%）
    # 埋め草・エピソード制限
    "filler_count_critical": 1,  # 埋め草候補がこれ以上あればCRITICAL
    "episode_limit": 5,  # 1人あたりのエピソード上限
    "limit_violation_warning": 1,  # 制限超過がこれ以上あればWARNING
    # 軸別
    "axis_avg_alert": 5.0,  # 軸平均のアラート閾値
    "axis_avg_critical": 4.0,  # 軸平均の緊急閾値
    # 改善率
    "improvement_success_target": 0.90,  # 改善成功率目標（90%）
    "improvement_success_alert": 0.80,  # 改善成功率アラート（80%）
}

SEVEN_AXIS_FIELDS = [
    "記憶性スコア",
    "共感性スコア",
    "意外性スコア",
    "生成品質スコア",
    "教育的価値",
    "ストーリー品質",
    "事実密度",
]


def load_master_episodes() -> List[Dict]:
    """マスターCSVからエピソードを読み込む"""
    if not MASTER_CSV.exists():
        return []

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_staging_episodes() -> List[Dict]:
    """ステージングCSVからエピソードを読み込む"""
    if not STAGING_CSV.exists():
        return []

    with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def calculate_quality_metrics(episodes: List[Dict]) -> Dict:
    """品質メトリクスを計算"""
    metrics = {
        "total_count": len(episodes),
        "composite_scores": [],
        "axis_scores": {axis: [] for axis in SEVEN_AXIS_FIELDS},
        "score_distribution": defaultdict(int),
        "source_distribution": defaultdict(int),
        # 埋め草・制限関連
        "filler_candidates": [],
        "person_episode_counts": defaultdict(int),
    }

    for ep in episodes:
        # 超総合スコア
        composite = ep.get("composite_score", "")
        if composite:
            try:
                c = float(composite)
                metrics["composite_scores"].append(c)

                # スコア帯分布
                if c >= 800:
                    metrics["score_distribution"]["800+"] += 1
                elif c >= 700:
                    metrics["score_distribution"]["700-799"] += 1
                elif c >= 600:
                    metrics["score_distribution"]["600-699"] += 1
                elif c >= 500:
                    metrics["score_distribution"]["500-599"] += 1
                elif c >= 400:
                    metrics["score_distribution"]["400-499"] += 1
                else:
                    metrics["score_distribution"]["<400"] += 1
            except ValueError:
                pass

        # 軸別スコア
        for axis in SEVEN_AXIS_FIELDS:
            score = ep.get(axis, "")
            if score:
                try:
                    metrics["axis_scores"][axis].append(float(score))
                except ValueError:
                    pass

        # ソース分布
        source = ep.get("source", "unknown")
        metrics["source_distribution"][source] += 1

        # 人物名取得
        person_name = ep.get("person_name", "")

        # 埋め草チェック
        text = ep.get("episode_text", "")
        if text and is_filler(text):
            metrics["filler_candidates"].append(
                {
                    "episode_id": ep.get("episode_id", ""),
                    "person_name": person_name,
                    "text_preview": text[:50] + "...",
                }
            )

        # 人物別カウント
        if person_name:
            metrics["person_episode_counts"][person_name] += 1

    # 制限違反の計算
    episode_limit = QUALITY_THRESHOLDS["episode_limit"]
    metrics["limit_violations"] = [
        {"person_name": name, "count": count, "excess": count - episode_limit}
        for name, count in metrics["person_episode_counts"].items()
        if count > episode_limit
    ]
    metrics["filler_count"] = len(metrics["filler_candidates"])
    metrics["limit_violation_count"] = len(metrics["limit_violations"])

    # 統計計算
    if metrics["composite_scores"]:
        metrics["composite_avg"] = round(sum(metrics["composite_scores"]) / len(metrics["composite_scores"]), 1)
        metrics["composite_min"] = min(metrics["composite_scores"])
        metrics["composite_max"] = max(metrics["composite_scores"])
    else:
        metrics["composite_avg"] = 0
        metrics["composite_min"] = 0
        metrics["composite_max"] = 0

    # 軸別平均
    metrics["axis_averages"] = {}
    for axis, scores in metrics["axis_scores"].items():
        if scores:
            metrics["axis_averages"][axis] = round(sum(scores) / len(scores), 2)
        else:
            metrics["axis_averages"][axis] = 0

    # 600+率
    high_quality = (
        metrics["score_distribution"].get("800+", 0)
        + metrics["score_distribution"].get("700-799", 0)
        + metrics["score_distribution"].get("600-699", 0)
    )
    metrics["high_quality_rate"] = round(high_quality / max(1, metrics["total_count"]), 3)

    return metrics


def check_alerts(metrics: Dict) -> List[Dict]:
    """アラート条件をチェック"""
    alerts = []

    # 超総合平均チェック
    if metrics["composite_avg"] < QUALITY_THRESHOLDS["composite_avg_critical"]:
        alerts.append(
            {
                "level": "CRITICAL",
                "type": "composite_avg",
                "message": f"超総合平均が緊急閾値を下回っています: {metrics['composite_avg']} < {QUALITY_THRESHOLDS['composite_avg_critical']}",
                "action": "生成プロセスを即座に停止し、原因を調査してください",
            }
        )
    elif metrics["composite_avg"] < QUALITY_THRESHOLDS["composite_avg_alert"]:
        alerts.append(
            {
                "level": "WARNING",
                "type": "composite_avg",
                "message": f"超総合平均がアラート閾値を下回っています: {metrics['composite_avg']} < {QUALITY_THRESHOLDS['composite_avg_alert']}",
                "action": "プロンプトや品質ゲートの設定を見直してください",
            }
        )

    # 600+率チェック
    if metrics["high_quality_rate"] < QUALITY_THRESHOLDS["high_quality_rate_alert"]:
        alerts.append(
            {
                "level": "WARNING",
                "type": "high_quality_rate",
                "message": f"高品質率（600+）が低下: {metrics['high_quality_rate']*100:.1f}% < {QUALITY_THRESHOLDS['high_quality_rate_alert']*100}%",
                "action": "品質ゲートの閾値を見直すか、プロンプトを強化してください",
            }
        )

    # 軸別チェック
    for axis, avg in metrics["axis_averages"].items():
        if avg < QUALITY_THRESHOLDS["axis_avg_critical"]:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "type": "axis_collapse",
                    "message": f"{axis}が緊急閾値を下回っています: {avg} < {QUALITY_THRESHOLDS['axis_avg_critical']}",
                    "action": f"{axis}の改善プロンプトを強化してください",
                }
            )
        elif avg < QUALITY_THRESHOLDS["axis_avg_alert"]:
            alerts.append(
                {
                    "level": "WARNING",
                    "type": "axis_low",
                    "message": f"{axis}がアラート閾値を下回っています: {avg} < {QUALITY_THRESHOLDS['axis_avg_alert']}",
                    "action": f"{axis}に関するプロンプト指示を追加してください",
                }
            )

    # 埋め草チェック
    filler_count = metrics.get("filler_count", 0)
    if filler_count >= QUALITY_THRESHOLDS["filler_count_critical"]:
        filler_examples = metrics.get("filler_candidates", [])[:3]
        example_ids = [f["episode_id"] for f in filler_examples]
        alerts.append(
            {
                "level": "CRITICAL",
                "type": "filler_detected",
                "message": f"埋め草エピソードが検出されました: {filler_count}件 (例: {', '.join(example_ids)})",
                "action": "scripts/validation/check_episode_quality.py を実行し、埋め草を削除してください",
            }
        )

    # エピソード制限超過チェック
    limit_violation_count = metrics.get("limit_violation_count", 0)
    if limit_violation_count >= QUALITY_THRESHOLDS["limit_violation_warning"]:
        violation_examples = metrics.get("limit_violations", [])[:3]
        example_names = [f"{v['person_name']}({v['count']}件)" for v in violation_examples]
        alerts.append(
            {
                "level": "WARNING",
                "type": "episode_limit_exceeded",
                "message": f"エピソード制限超過: {limit_violation_count}人 (例: {', '.join(example_names)})",
                "action": "1人あたり5件以下になるよう、低品質エピソードを削除してください",
            }
        )

    return alerts


def generate_report(master_metrics: Dict, staging_metrics: Optional[Dict], alerts: List[Dict]) -> Dict:
    """品質レポートを生成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "master_data": {
            "total_count": master_metrics["total_count"],
            "composite_avg": master_metrics["composite_avg"],
            "composite_range": f"{master_metrics['composite_min']}-{master_metrics['composite_max']}",
            "high_quality_rate": f"{master_metrics['high_quality_rate']*100:.1f}%",
            "score_distribution": dict(master_metrics["score_distribution"]),
            "axis_averages": master_metrics["axis_averages"],
            "source_distribution": dict(master_metrics["source_distribution"]),
            # 埋め草・制限
            "filler_count": master_metrics.get("filler_count", 0),
            "limit_violation_count": master_metrics.get("limit_violation_count", 0),
        },
        "alerts": alerts,
        "thresholds": QUALITY_THRESHOLDS,
    }

    if staging_metrics and staging_metrics["total_count"] > 0:
        report["staging_data"] = {
            "total_count": staging_metrics["total_count"],
            "composite_avg": staging_metrics["composite_avg"],
            "score_distribution": dict(staging_metrics["score_distribution"]),
        }

    return report


def print_report(report: Dict):
    """レポートをコンソール出力"""
    print("=" * 70)
    print("📊 品質監視レポート")
    print("=" * 70)
    print(f"  生成日時: {report['timestamp']}")
    print()

    # マスターデータ
    print("【マスターデータ】")
    md = report["master_data"]
    print(f"  総エピソード数: {md['total_count']}")
    print(f"  超総合平均: {md['composite_avg']}")
    print(f"  超総合範囲: {md['composite_range']}")
    print(f"  高品質率（600+）: {md['high_quality_rate']}")
    print()

    print("  スコア帯分布:")
    for band, count in sorted(md["score_distribution"].items(), reverse=True):
        pct = count / max(1, md["total_count"]) * 100
        bar = "█" * int(pct / 2)
        print(f"    {band:>10}: {count:>5} ({pct:5.1f}%) {bar}")
    print()

    print("  7軸平均:")
    for axis, avg in md["axis_averages"].items():
        status = "✅" if avg >= 6.0 else "⚠️" if avg >= 5.0 else "❌"
        print(f"    {axis}: {avg:.2f} {status}")
    print()

    # 埋め草・制限チェック
    filler_count = md.get("filler_count", 0)
    limit_violation_count = md.get("limit_violation_count", 0)
    print("【品質ゲート】")
    print(f"  埋め草候補: {filler_count}件 {'✅' if filler_count == 0 else '❌'}")
    print(f"  5件超過人物: {limit_violation_count}人 {'✅' if limit_violation_count == 0 else '⚠️'}")
    print()

    # ステージングデータ
    if "staging_data" in report:
        print("【ステージングデータ】")
        sd = report["staging_data"]
        print(f"  待機エピソード数: {sd['total_count']}")
        print(f"  超総合平均: {sd['composite_avg']}")
        print()

    # アラート
    if report["alerts"]:
        print("【⚠️ アラート】")
        for alert in report["alerts"]:
            icon = "🚨" if alert["level"] == "CRITICAL" else "⚠️"
            print(f"  {icon} [{alert['level']}] {alert['type']}")
            print(f"     {alert['message']}")
            print(f"     対処: {alert['action']}")
            print()
    else:
        print("【✅ アラートなし】")
        print("  すべての品質指標が正常範囲内です。")
    print()


def main():
    parser = argparse.ArgumentParser(description="品質監視")
    parser.add_argument("--output", type=str, help="JSONレポート出力先")
    parser.add_argument("--alerts-only", action="store_true", help="アラートのみ表示")
    args = parser.parse_args()

    # データ読み込み
    master_episodes = load_master_episodes()
    staging_episodes = load_staging_episodes()

    if not master_episodes:
        print("❌ マスターCSVが見つからないか空です")
        sys.exit(1)

    # メトリクス計算
    master_metrics = calculate_quality_metrics(master_episodes)
    staging_metrics = calculate_quality_metrics(staging_episodes) if staging_episodes else None

    # アラートチェック
    alerts = check_alerts(master_metrics)

    # レポート生成
    report = generate_report(master_metrics, staging_metrics, alerts)

    # 出力
    if args.alerts_only:
        if alerts:
            for alert in alerts:
                icon = "🚨" if alert["level"] == "CRITICAL" else "⚠️"
                print(f"{icon} [{alert['level']}] {alert['message']}")
        else:
            print("✅ アラートなし")
    else:
        print_report(report)

    # JSON出力
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📝 レポート保存: {output_path}")

    # 終了コード（CRITICALアラートがあれば1）
    has_critical = any(a["level"] == "CRITICAL" for a in alerts)
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
