"""
CSV Path Resolver - 単一マスターCSV原則の実装

このモジュールはプロジェクト全体でMASTER CSVへの統一されたパスアクセスを提供します。

使用方法:
    from src.csv_path_resolver import get_master_csv_path, get_project_root

    csv_path = get_master_csv_path()
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

設計原則:
    - 正規マスター: preserved/data/MASTER_EPISODES_CURRENT.csv
    - 相対パス: プロジェクトルートからの相対パスを常に使用
    - シンボリックリンク対応: data/MASTER_EPISODES_CURRENT.csv経由でもアクセス可能
"""

from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    プロジェクトルートディレクトリを取得

    Returns:
        Path: プロジェクトルートディレクトリの絶対パス

    Example:
        >>> root = get_project_root()
        >>> print(root)
        /Users/admin/Documents/AIUELAB/001-final-hourglass
    """
    # このファイルは src/ 配下にあるため、2階層上がプロジェクトルート
    return Path(__file__).parent.parent


def get_master_csv_path() -> Path:
    """
    MASTER CSVの正規パスを取得（単一マスター原則）

    Returns:
        Path: MASTER_EPISODES_CURRENT.csvの絶対パス

    Note:
        常に preserved/data/MASTER_EPISODES_CURRENT.csv を返す（正規マスター）
        data/MASTER_EPISODES_CURRENT.csv はシンボリックリンクのため使用しない

    Example:
        >>> csv_path = get_master_csv_path()
        >>> print(csv_path)
        /Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv
    """
    project_root = get_project_root()
    return project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def get_backup_dir() -> Path:
    """
    バックアップディレクトリを取得

    Returns:
        Path: バックアップディレクトリの絶対パス

    Example:
        >>> backup_dir = get_backup_dir()
        >>> print(backup_dir)
        /Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/backups
    """
    project_root = get_project_root()
    backup_dir = project_root / "preserved" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_config_dir() -> Path:
    """
    設定ファイルディレクトリを取得

    Returns:
        Path: config/ ディレクトリの絶対パス

    Example:
        >>> config_dir = get_config_dir()
        >>> print(config_dir)
        /Users/admin/Documents/AIUELAB/001-final-hourglass/config
    """
    project_root = get_project_root()
    return project_root / "config"


def get_reports_dir() -> Path:
    """
    レポート出力ディレクトリを取得

    Returns:
        Path: reports/ ディレクトリの絶対パス

    Example:
        >>> reports_dir = get_reports_dir()
        >>> print(reports_dir)
        /Users/admin/Documents/AIUELAB/001-final-hourglass/reports
    """
    project_root = get_project_root()
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def verify_master_csv_exists() -> bool:
    """
    MASTER CSVの存在を確認

    Returns:
        bool: ファイルが存在する場合True

    Example:
        >>> if not verify_master_csv_exists():
        ...     raise FileNotFoundError("MASTER CSV not found")
    """
    csv_path = get_master_csv_path()
    return csv_path.exists()


def get_person_sources_dir() -> Path:
    """
    人物候補ソースディレクトリを取得

    Returns:
        Path: config/person_sources/ ディレクトリの絶対パス

    Example:
        >>> sources_dir = get_person_sources_dir()
        >>> for csv_file in sources_dir.glob("*.csv"):
        ...     print(csv_file.name)
    """
    config_dir = get_config_dir()
    sources_dir = config_dir / "person_sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    return sources_dir


if __name__ == "__main__":
    # 動作確認用
    print(f"プロジェクトルート: {get_project_root()}")
    print(f"MASTER CSV: {get_master_csv_path()}")
    print(f"MASTER CSV存在確認: {verify_master_csv_exists()}")
    print(f"バックアップディレクトリ: {get_backup_dir()}")
    print(f"設定ディレクトリ: {get_config_dir()}")
    print(f"レポートディレクトリ: {get_reports_dir()}")
    print(f"人物ソースディレクトリ: {get_person_sources_dir()}")
