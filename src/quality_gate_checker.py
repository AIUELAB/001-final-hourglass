"""
Quality Gate Checker - 統合後の品質確認

このモジュールはCSV統合後にscheduled_epup_check.pyを実行し、
EPUP KPIを評価して品質ゲートの合否を判定します。

主な機能:
- scheduled_epup_check.py の自動実行
- EPUP KPIの取得と評価
- 品質ステータスの判定（PASS/WARNING/CRITICAL）
- ロールバック推奨の判断

使用方法:
    >>> from src.quality_gate_checker import QualityGateChecker
    >>> checker = QualityGateChecker()
    >>> result = checker.run_post_integration_check(master_csv_path)
    >>> if result['status'] == 'CRITICAL':
    ...     print("Quality gate failed! Rollback recommended.")
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from src.csv_path_resolver import get_project_root

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityGateChecker:
    """統合後の品質確認"""

    # KPI閾値（これを超えるとWARNINGまたはCRITICAL）
    WARNING_THRESHOLDS = {
        "meta_expression_rate": 0.5,  # 0.5%
        "placeholder_rate": 0.5,  # 0.5%
        "format_violation_rate": 1.0,  # 1.0%
        "age_mismatch_rate": 0.5,  # 0.5%
        "name_missing_rate": 0.5,  # 0.5%
        "length_anomaly_rate": 1.0,  # 1.0%
        "duplicate_rate": 1.0,  # 1.0%
        "organization_prefix_rate": 0.5,  # 0.5%
        "profession_prefix_rate": 0.5,  # 0.5%
        "group_inconsistency_rate": 0.5,  # 0.5%
    }

    CRITICAL_THRESHOLDS = {
        "meta_expression_rate": 1.0,  # 1.0%
        "placeholder_rate": 1.0,  # 1.0%
        "format_violation_rate": 2.0,  # 2.0%
        "age_mismatch_rate": 1.0,  # 1.0%
        "name_missing_rate": 1.0,  # 1.0%
        "length_anomaly_rate": 2.0,  # 2.0%
        "duplicate_rate": 2.0,  # 2.0%
        "organization_prefix_rate": 1.0,  # 1.0%
        "profession_prefix_rate": 1.0,  # 1.0%
        "group_inconsistency_rate": 1.0,  # 1.0%
    }

    def __init__(self, report_dir: Optional[Path] = None):
        """
        初期化

        Args:
            report_dir: レポート出力ディレクトリ（省略時はデフォルト）
        """
        self.report_dir = report_dir or (get_project_root() / "reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _make_error_result(self, error_message: str) -> Dict[str, Any]:
        """エラー結果を生成"""
        return {
            "status": "CRITICAL",
            "error": error_message,
            "kpis": {},
            "violations": [],
            "report_path": None,
        }

    def _run_epup_script(
        self, master_csv_path: Path, report_path: Path
    ) -> tuple[Optional[subprocess.CompletedProcess], Optional[str]]:
        """EPUPスクリプトを実行。戻り値: (result, error_message)"""
        try:
            result = subprocess.run(
                [
                    "python3",
                    "scripts/scheduled_epup_check.py",
                    "--daily",
                    "--csv",
                    str(master_csv_path),
                    "--output",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
            )
            if result.returncode != 0:
                logger.warning(f"EPUP check returned non-zero exit code: {result.returncode}")
            return result, None
        except subprocess.TimeoutExpired:
            logger.error("EPUP check timed out")
            return None, "EPUP check timed out after 5 minutes"
        except Exception as e:
            logger.error(f"EPUP check error: {e}")
            return None, f"EPUP check error: {e}"

    def _load_epup_report(self, report_path: Path) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """EPUPレポートを読み込み。戻り値: (report, error_message)"""
        if not report_path.exists():
            logger.error("EPUP report not generated - this indicates a script execution failure")
            return None, "EPUP report not generated"
        try:
            with open(report_path, encoding="utf-8") as f:
                return json.load(f), None
        except Exception as e:
            logger.error(f"Failed to read EPUP report: {e}")
            return None, f"Failed to read EPUP report: {e}"

    def run_post_integration_check(self, master_csv_path: Path) -> Dict[str, Any]:
        """
        統合後の品質確認を実行

        Args:
            master_csv_path: チェック対象のMASTER CSVパス

        Returns:
            品質確認結果の辞書:
            {
                'status': 'PASS' | 'WARNING' | 'CRITICAL',
                'kpis': {...},
                'violations': [...],
                'report_path': Path(...),
                'error': str (エラー時のみ)
            }

        Example:
            >>> checker = QualityGateChecker()
            >>> result = checker.run_post_integration_check(master_csv_path)
            >>> if result['status'] == 'CRITICAL':
            ...     print("Rollback recommended!")
        """
        logger.info("Running post-integration quality check...")
        report_path = self.report_dir / "epup_post_integration.json"

        # EPUPスクリプト実行
        result, error_msg = self._run_epup_script(master_csv_path, report_path)
        if result is None:
            return self._make_error_result(error_msg or "EPUP check failed")

        # レポート読み込み
        report, load_error = self._load_epup_report(report_path)
        if report is None:
            if load_error and "not generated" in load_error:
                return self._make_error_result(
                    f"EPUP report not generated. Exit code: {result.returncode}, stderr: {result.stderr}"
                )
            return self._make_error_result(load_error or "Failed to load EPUP report")

        # KPIを取得・評価
        kpis_list = report.get("kpis", [])
        if not kpis_list:
            logger.warning("No KPIs found in report")

        kpis_dict = {kpi["name"]: kpi for kpi in kpis_list}
        status, violations = self._evaluate_kpis(kpis_list)

        logger.info(f"Quality check complete: {status}")
        if violations:
            logger.warning(f"Violations detected: {violations}")

        return {
            "status": status,
            "kpis": kpis_dict,
            "violations": violations,
            "report_path": report_path,
        }

    def _evaluate_kpis(self, kpis_list: list[Dict[str, Any]]) -> tuple[str, list[str]]:
        """
        KPIを評価してステータスを返す

        Args:
            kpis_list: KPIリスト（scheduled_epup_check.pyの出力）

        Returns:
            (status, violations):
            - status: 'PASS' | 'WARNING' | 'CRITICAL'
            - violations: 違反リスト

        Example:
            >>> checker = QualityGateChecker()
            >>> kpis = [{"name": "削除済みID混入率", "value": 1.5, "status": "CRITICAL"}]
            >>> status, violations = checker._evaluate_kpis(kpis)
            >>> print(status)
            CRITICAL
        """
        violations = []
        has_critical = False
        has_warning = False

        for kpi in kpis_list:
            kpi_name = kpi.get("name", "unknown")
            kpi_value = kpi.get("value", 0.0)
            kpi_status = kpi.get("status", "OK")

            # scheduled_epup_check.pyのステータスを優先
            if kpi_status == "CRITICAL":
                violations.append(f"CRITICAL: {kpi_name}={kpi_value:.2f}% (status={kpi_status})")
                has_critical = True
            elif kpi_status == "WARNING":
                violations.append(f"WARNING: {kpi_name}={kpi_value:.2f}% (status={kpi_status})")
                has_warning = True

        # ステータス決定
        if has_critical:
            return ("CRITICAL", violations)
        elif has_warning:
            return ("WARNING", violations)
        else:
            return ("PASS", violations)

    def get_rollback_recommendation(self, result: Dict[str, Any]) -> bool:
        """
        ロールバックを推奨するかどうかを判定

        Args:
            result: run_post_integration_check()の結果

        Returns:
            True: ロールバック推奨, False: ロールバック不要

        Example:
            >>> checker = QualityGateChecker()
            >>> result = checker.run_post_integration_check(master_csv_path)
            >>> if checker.get_rollback_recommendation(result):
            ...     print("Rollback recommended!")
        """
        # CRITICALステータスの場合はロールバック推奨
        return result.get("status") == "CRITICAL"


if __name__ == "__main__":
    # 動作確認用
    from src.csv_path_resolver import get_master_csv_path

    checker = QualityGateChecker()

    print("=== Quality Gate Checker Test ===\n")

    # MASTER CSVのパスを取得
    master_csv_path = get_master_csv_path()
    print(f"Target CSV: {master_csv_path}")

    # 品質チェック実行
    print("\nRunning quality check...")
    result = checker.run_post_integration_check(master_csv_path)

    # 結果表示
    print("\n✅ Quality Check Results:")
    print(f"   Status: {result['status']}")
    print(f"   Report: {result.get('report_path')}")

    if result.get("kpis"):
        print(f"\n   KPIs ({len(result['kpis'])} items):")
        for kpi_name, kpi_data in list(result["kpis"].items())[:5]:  # 最初の5件のみ表示
            print(f"     - {kpi_name}: {kpi_data.get('value', 0):.2f}% ({kpi_data.get('status', 'OK')})")

    if result.get("violations"):
        print("\n   Violations:")
        for violation in result["violations"]:
            print(f"     - {violation}")

    # ロールバック推奨チェック
    if checker.get_rollback_recommendation(result):
        print("\n⚠️  ROLLBACK RECOMMENDED!")
    else:
        print("\n✅ Quality gate passed. No rollback needed.")
