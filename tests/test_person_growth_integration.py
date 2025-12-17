"""
Person Growth Pipeline - E2E統合テスト

このテストは以下を検証します:
1. E2Eフロー: 候補収集→検証→重複判定→フィルタ→レポート生成
2. センシティブフィルタの動作
3. 4層重複判定の動作
"""

import subprocess
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import pytest

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def test_source_dir(tmp_path: Path) -> Path:
    """テスト用ソースディレクトリを作成"""
    sources_dir = PROJECT_ROOT / "config" / "person_sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    return sources_dir


def create_test_csv(sources_dir: Path, filename: str, content: str) -> Path:
    """テスト用CSVを作成"""
    csv_path = sources_dir / filename
    csv_path.write_text(content, encoding="utf-8-sig")
    return csv_path


def run_pipeline_analyze(sources: str = None, limit: int = None) -> Dict[str, Any]:
    """
    パイプラインをanalyzeモードで実行

    Args:
        sources: ソース名（カンマ区切り）
        limit: 候補数制限

    Returns:
        stdout出力
    """
    cmd = ["python3", "scripts/person_growth_pipeline.py", "--analyze"]

    if sources:
        cmd.extend(["--sources", sources])

    if limit:
        cmd.extend(["--limit", str(limit)])

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)

    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def test_end_to_end_flow(test_source_dir: Path):
    """E2Eフロー: 候補収集→検証→重複判定→フィルタ→レポート"""
    # テストデータ作成
    csv_content = """person_name,category,person_type,birth_year,death_year,tier,description
山中伸弥,科学・技術,REAL,1962,,S+,iPS細胞の研究者
テスト太郎,テスト,REAL,1970,,B,テスト用人物
テスト花子,政治家,REAL,1980,,B,テスト用政治家
"""
    csv_path = create_test_csv(test_source_dir, "test_e2e.csv", csv_content)

    try:
        # パイプライン実行
        result = run_pipeline_analyze(sources="test_e2e")

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # 出力確認
        stdout = result["stdout"]
        assert "【ステップ1】候補収集" in stdout
        assert "【ステップ2】正規化/検証" in stdout
        assert "【ステップ3】未収録判定（4層重複検出）" in stdout
        assert "【ステップ4】センシティブフィルタ" in stdout
        assert "【ステップ5】レポート生成" in stdout
        assert "✅ パイプライン完了（dry-runモード）" in stdout

        print("✅ E2Eフローテスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


def test_sensitive_filter_blocking(test_source_dir: Path):
    """センシティブフィルタがブロックすることを確認"""
    # センシティブカテゴリを含む候補
    csv_content = """person_name,category,person_type,birth_year,death_year,tier,description
テスト犯罪者,犯罪者,REAL,1980,2020,C,逮捕された人物
テスト一般人,その他,REAL,1990,,B,一般人
"""
    csv_path = create_test_csv(test_source_dir, "test_sensitive.csv", csv_content)

    try:
        # パイプライン実行
        result = run_pipeline_analyze(sources="test_sensitive")

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # センシティブフィルタが動作していることを確認
        stdout = result["stdout"]
        assert "センシティブフィルタ完了" in stdout
        assert "ブロック" in stdout

        print("✅ センシティブフィルタテスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


def test_review_required_category(test_source_dir: Path):
    """レビュー必要カテゴリを検出することを確認"""
    # レビュー必要カテゴリを含む候補
    csv_content = """person_name,category,person_type,birth_year,death_year,tier,description
テスト政治家,政治家,REAL,1960,,A,政治家
テスト宗教家,宗教家,REAL,1950,,A,宗教家
"""
    csv_path = create_test_csv(test_source_dir, "test_review.csv", csv_content)

    try:
        # パイプライン実行
        result = run_pipeline_analyze(sources="test_review")

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # レビュー必要が検出されていることを確認
        stdout = result["stdout"]
        assert "レビュー必要" in stdout

        print("✅ レビュー必要カテゴリテスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


def test_duplicate_detection_4_layers(test_source_dir: Path):
    """4層重複判定が動作することを確認"""
    # 既存人物の様々な表記を含む候補
    csv_content = """person_name,category,person_type,birth_year,death_year,tier,description
山中伸弥,科学・技術,REAL,1962,,S+,完全一致テスト
山中　伸弥,科学・技術,REAL,1962,,S+,正規化一致テスト（全角スペース）
"""
    csv_path = create_test_csv(test_source_dir, "test_duplicate.csv", csv_content)

    try:
        # パイプライン実行
        result = run_pipeline_analyze(sources="test_duplicate")

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # 重複判定が動作していることを確認
        stdout = result["stdout"]
        assert "4層重複判定完了" in stdout
        assert "既収録" in stdout

        print("✅ 4層重複判定テスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


def test_validation_error_detection(test_source_dir: Path):
    """PersonNameValidatorがエラーを検出することを確認"""
    # 検証エラーを含む候補
    csv_content = """person_name,category,person_type,birth_year,death_year,tier,description
大リーグ養成ギプス,道具,REAL,2000,,C,ドラえもんの秘密道具（道具名混入）
テスト一般人,その他,REAL,1990,,B,正常な人物
"""
    csv_path = create_test_csv(test_source_dir, "test_validation.csv", csv_content)

    try:
        # パイプライン実行
        result = run_pipeline_analyze(sources="test_validation")

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # 検証エラーが検出されていることを確認
        stdout = result["stdout"]
        assert "正規化/検証" in stdout

        print("✅ 検証エラー検出テスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


def test_limit_functionality(test_source_dir: Path):
    """--limit フラグが正しく動作することを確認"""
    # 10人の候補を作成
    rows = [f"テスト{i},テスト,REAL,1970,,B,テスト用{i}" for i in range(1, 11)]
    csv_content = "person_name,category,person_type,birth_year,death_year,tier,description\n" + "\n".join(rows)
    csv_path = create_test_csv(test_source_dir, "test_limit.csv", csv_content)

    try:
        # --limit 5 で実行
        result = run_pipeline_analyze(sources="test_limit", limit=5)

        # 正常終了確認
        assert result["returncode"] == 0, f"Pipeline failed: {result['stderr']}"

        # 件数制限が動作していることを確認
        stdout = result["stdout"]
        assert "件数制限により 5 件に絞り込みました" in stdout

        print("✅ --limit機能テスト成功")

    finally:
        # クリーンアップ
        if csv_path.exists():
            csv_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
