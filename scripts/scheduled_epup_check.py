#!/usr/bin/env python3
"""
Scheduled EPUP Health Check

日次・週次でEPUPの品質をチェックし、アラートを出力する。

Usage:
    python scripts/scheduled_epup_check.py [--daily|--weekly] [--output report.json]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


def convert_to_serializable(obj):
    """numpy型などをJSON serializable型に変換"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


from src.monitoring.kpi_definitions import EPUPKPICalculator
from src.validators.import_pipeline import ImportValidationPipeline, ValidationLevel


CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"


def run_daily_check(csv_path: str) -> dict:
    """
    日次チェック（軽量）

    チェック項目:
    - グループ名混入
    - nan ID
    - 表記ゆれ
    - 削除済みID混入
    - 組織名・肩書き混入
    - 英字別名検出
    - 後置詞型パターン検出（ERR-006）
    """
    calculator = EPUPKPICalculator(csv_path)
    report = calculator.calculate_all()

    # 日次は特定KPIのみ
    daily_kpis = [
        "グループ名混入率",
        "表記ゆれ率",
        "nan ID率",
        "削除済みID混入率",
        "組織名・肩書き混入率",
        "英字別名検出率",
        "後置詞型パターン検出率",  # KPI 10: ERR-006
    ]
    filtered_kpis = [k for k in report.kpis if k.name in daily_kpis]

    return {
        "check_type": "daily",
        "timestamp": report.timestamp,
        "total_records": report.total_records,
        "kpis": [
            {
                "name": k.name,
                "value": k.value,
                "target": k.target,
                "status": k.status,
                "details": k.details,
            }
            for k in filtered_kpis
        ],
        "alerts": [{"name": k.name, "status": k.status, "value": k.value} for k in filtered_kpis if k.status != "OK"],
    }


def run_weekly_check(csv_path: str) -> dict:
    """
    週次チェック（完全）

    チェック項目:
    - 全KPI
    - ImportValidationPipeline
    """
    # KPI計算
    calculator = EPUPKPICalculator(csv_path)
    kpi_report = calculator.calculate_all()

    # ImportValidationPipeline
    pipeline = ImportValidationPipeline(level=ValidationLevel.NORMAL)
    pipeline_result = pipeline.validate_file(csv_path)

    return {
        "check_type": "weekly",
        "timestamp": kpi_report.timestamp,
        "total_records": kpi_report.total_records,
        "overall_status": kpi_report.overall_status,
        "overall_score": kpi_report.overall_score,
        "kpis": [
            {
                "name": k.name,
                "value": k.value,
                "target": k.target,
                "status": k.status,
                "details": k.details,
            }
            for k in kpi_report.kpis
        ],
        "validation": {
            "success": pipeline_result.success,
            "valid_rows": pipeline_result.valid_rows,
            "invalid_rows": pipeline_result.invalid_rows,
            "error_count": pipeline_result.error_count,
            "warning_count": pipeline_result.warning_count,
        },
        "alerts": [{"name": k.name, "status": k.status, "value": k.value} for k in kpi_report.kpis if k.status != "OK"],
    }


def print_report(report: dict):
    """レポートを出力"""
    print("=" * 60)
    print(f"EPUP Health Check ({report['check_type'].upper()})")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total Records: {report['total_records']:,}")

    if "overall_status" in report:
        status_icon = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌"}.get(report["overall_status"], "?")
        print(f"Overall Status: {status_icon} {report['overall_status']}")
        print(f"Overall Score: {report['overall_score']:.1%}")

    print("\nKPI Results:")
    print("-" * 60)
    for kpi in report["kpis"]:
        status_icon = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌"}.get(kpi["status"], "?")
        if kpi["target"] == 0:
            value_str = f"{kpi['value']:.2%}"
        else:
            value_str = f"{kpi['value']:.2%} / {kpi['target']:.0%}"
        print(f"{status_icon} {kpi['name']}: {value_str}")

    if "validation" in report:
        print("\nValidation Results:")
        print("-" * 60)
        v = report["validation"]
        print(f"Valid: {v['valid_rows']:,} / {v['valid_rows'] + v['invalid_rows']:,}")
        print(f"Errors: {v['error_count']}, Warnings: {v['warning_count']}")

    if report["alerts"]:
        print("\n🚨 ALERTS:")
        print("-" * 60)
        for alert in report["alerts"]:
            print(f"  ⚠️ {alert['name']}: {alert['status']} ({alert['value']:.2%})")
    else:
        print("\n✅ No alerts - all KPIs within thresholds")


def main():
    parser = argparse.ArgumentParser(description="Scheduled EPUP Health Check")
    parser.add_argument(
        "--daily",
        action="store_true",
        help="日次チェック（軽量）",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="週次チェック（完全）",
    )
    parser.add_argument(
        "--csv",
        default=CSV_PATH,
        help="対象CSVファイル",
    )
    parser.add_argument(
        "--output",
        help="レポート出力ファイル（JSON）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="出力を抑制",
    )

    args = parser.parse_args()

    # デフォルトは日次
    if not args.daily and not args.weekly:
        args.daily = True

    # チェック実行
    if args.weekly:
        report = run_weekly_check(args.csv)
    else:
        report = run_daily_check(args.csv)

    # 出力
    if not args.quiet:
        print_report(report)

    # ファイル出力（numpy型を変換）
    serializable_report = convert_to_serializable(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(serializable_report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Report saved: {args.output}")
    else:
        # デフォルトでreportsディレクトリに保存
        os.makedirs(REPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        check_type = report["check_type"]
        output_path = f"{REPORT_DIR}/epup_{check_type}_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_report, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"\n📄 Report saved: {output_path}")

    # アラートがある場合は終了コード1
    if report["alerts"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
