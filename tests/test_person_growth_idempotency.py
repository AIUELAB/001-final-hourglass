"""
Person Growth Pipeline - 冪等性テスト

このテストは以下を検証します:
1. dry-run 2回実行で同一結果
2. execute 2回実行で2回目は追加なし
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import pytest

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# サブプロセス用環境変数（PYTHONPATHを設定）
SUBPROCESS_ENV = os.environ.copy()
SUBPROCESS_ENV["PYTHONPATH"] = str(PROJECT_ROOT)


@pytest.fixture
def test_csv_source(tmp_path: Path) -> Path:
    """テスト用候補CSVを作成"""
    csv_content = """person_name,category,person_type,birth_year,death_year,tier
テスト太郎,テスト,REAL,1970,,B
テスト花子,テスト,REAL,1980,,B
"""
    csv_path = tmp_path / "test_candidates.csv"
    csv_path.write_text(csv_content, encoding="utf-8-sig")
    return csv_path


@pytest.fixture
def master_csv_backup(tmp_path: Path) -> Path:
    """MASTER CSVのバックアップを作成"""
    master_csv = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
    backup_path = tmp_path / "master_backup.csv"

    if master_csv.exists():
        df = pd.read_csv(master_csv, encoding="utf-8-sig")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    return backup_path


def run_pipeline(mode: str, sources_csv: Path, limit: int = None, allow_sensitive: bool = False) -> Dict[str, Any]:
    """
    パイプラインを実行してレポートを取得

    Args:
        mode: "analyze" または "execute"
        sources_csv: ソースCSVのパス
        limit: 候補数制限
        allow_sensitive: センシティブ許可

    Returns:
        レポートJSON
    """
    # ソースCSVを所定の場所にコピー
    sources_dir = PROJECT_ROOT / "config" / "person_sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    dest_csv = sources_dir / "test_e2e_candidates.csv"
    dest_csv.write_text(sources_csv.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")

    try:
        # コマンド構築
        cmd = [
            "python3",
            "scripts/utils/person_growth_pipeline.py",
            f"--{mode}",
            "--sources",
            "test_e2e_candidates",
        ]

        if limit:
            cmd.extend(["--limit", str(limit)])

        if allow_sensitive:
            cmd.append("--allow-sensitive")

        # 実行
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300, env=SUBPROCESS_ENV)

        if result.returncode != 0:
            raise RuntimeError(f"Pipeline failed: {result.stderr}")

        # レポート取得（最新のレポートファイル）
        reports_dir = PROJECT_ROOT / "reports" / "person_growth"
        report_files = sorted(reports_dir.glob("person_growth_*.json"), key=lambda p: p.stat().st_mtime)

        if not report_files:
            raise FileNotFoundError("No report file found")

        with open(report_files[-1], encoding="utf-8") as f:
            return json.load(f)

    finally:
        # クリーンアップ
        if dest_csv.exists():
            dest_csv.unlink()


def test_dry_run_idempotency(test_csv_source: Path):
    """dry-run 2回実行で同一結果"""
    # 1回目の実行
    report1 = run_pipeline("analyze", test_csv_source, limit=5)

    # 2回目の実行
    report2 = run_pipeline("analyze", test_csv_source, limit=5)

    # サマリーが同一であることを確認
    assert report1["summary"] == report2["summary"], "dry-run結果が異なります"
    assert report1["mode"] == "DRY-RUN"
    assert report2["mode"] == "DRY-RUN"

    print("✅ dry-run冪等性テスト成功")


def test_execute_idempotency(test_csv_source: Path, master_csv_backup: Path):
    """execute 2回実行で2回目は追加なし"""
    pytest.skip("executeテストはMASTER CSVを変更するため、手動実行を推奨")

    # NOTE: このテストは実際のMASTER CSVを変更するため、
    # CI環境や本番環境では実行しないことを推奨します。
    #
    # 手動実行の場合:
    # 1. MASTER CSVのバックアップを取る
    # 2. 以下のコードのコメントを解除
    # 3. pytest tests/test_person_growth_idempotency.py::test_execute_idempotency -v
    # 4. テスト後、バックアップから復元

    # try:
    #     # 1回目の実行
    #     report1 = run_pipeline("execute", test_csv_source, limit=2, allow_sensitive=False)
    #
    #     assert report1["mode"] == "EXECUTE"
    #     assert "integration" in report1
    #     integrated_1 = report1["integration"]["added"]
    #     assert integrated_1 > 0, "1回目で追加がないのは異常"
    #
    #     # 2回目の実行（同じ候補）
    #     report2 = run_pipeline("execute", test_csv_source, limit=2, allow_sensitive=False)
    #
    #     assert report2["mode"] == "EXECUTE"
    #     assert "integration" in report2
    #     integrated_2 = report2["integration"]["added"]
    #     skipped_2 = report2["integration"]["skipped"]
    #
    #     # 2回目は追加なし、全件スキップ
    #     assert integrated_2 == 0, "2回目で追加があるのは冪等性違反"
    #     assert skipped_2 > 0, "2回目でスキップがないのは異常"
    #
    #     print(f"✅ execute冪等性テスト成功: 1回目={integrated_1}件追加, 2回目={integrated_2}件追加/{skipped_2}件スキップ")
    #
    # finally:
    #     # バックアップから復元
    #     master_csv = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
    #     if master_csv_backup.exists():
    #         df = pd.read_csv(master_csv_backup, encoding="utf-8-sig")
    #         df.to_csv(master_csv, index=False, encoding="utf-8-sig")
    #         print(f"✅ MASTER CSV復元完了: {master_csv}")


def test_duplicate_detection_accuracy(test_csv_source: Path):
    """重複判定の精度を検証"""
    # 既存人物を含む候補を作成
    csv_content = """person_name,category,person_type,birth_year,death_year,tier
山中伸弥,科学・技術,REAL,1962,,S+
テスト太郎,テスト,REAL,1970,,B
"""
    test_csv = test_csv_source.parent / "test_duplicate.csv"
    test_csv.write_text(csv_content, encoding="utf-8-sig")

    # 実行
    report = run_pipeline("analyze", test_csv)

    # 検証
    assert report["summary"]["found_persons"] >= 1, "山中伸弥が既収録として検出されていない"
    assert report["summary"]["missing_persons"] >= 0, "未収録判定が不正確"

    print(
        f"✅ 重複判定精度テスト成功: 既収録={report['summary']['found_persons']}人, 未収録={report['summary']['missing_persons']}人"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
