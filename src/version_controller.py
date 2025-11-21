#!/usr/bin/env python3
"""
バージョン管理システム
データの変更検出、バージョン履歴、ロールバック機能を提供

作成日: 2025-08-31
Ultra Think Mode対応
"""

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class VersionController:
    """
    バージョン管理システム
    - コンテンツハッシュベースの変更検出
    - タイムスタンプ管理（YYYYMMDD_HHMMSS形式）
    - バージョン履歴トラッキング
    - ロールバック機能
    """

    def __init__(self, versions_dir: str = "versions", max_versions: int = 10):
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(exist_ok=True)
        self.max_versions = max_versions
        self.logger = logging.getLogger(__name__)

        # バージョン管理ディレクトリ
        (self.versions_dir / "data").mkdir(exist_ok=True)
        (self.versions_dir / "metadata").mkdir(exist_ok=True)
        (self.versions_dir / "snapshots").mkdir(exist_ok=True)

        # バージョン履歴ファイル
        self.history_file = self.versions_dir / "version_history.json"
        self.current_file = self.versions_dir / "current_version.json"

        # バージョン履歴を読み込み
        self.version_history = self._load_history()

        self.logger.info("✅ VersionController初期化完了")

    def _load_history(self) -> List[Dict[str, Any]]:
        """バージョン履歴を読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"履歴読み込みエラー: {e}")
        return []

    def _save_history(self):
        """バージョン履歴を保存"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.version_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"履歴保存エラー: {e}")

    def calculate_hash(self, data: Any) -> str:
        """データのハッシュ値を計算"""
        if isinstance(data, pd.DataFrame):
            # DataFrameの場合はCSV形式でハッシュ化
            data_str = data.to_csv(index=False)
        elif isinstance(data, dict):
            # 辞書の場合はJSON形式でハッシュ化
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        else:
            # その他の場合は文字列化
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()

    def detect_changes(self, current_data: Any, previous_data: Any = None) -> Dict[str, Any]:
        """データの変更を検出"""
        current_hash = self.calculate_hash(current_data)

        # 前のデータがない場合は現在のバージョンと比較
        if previous_data is None:
            previous_version = self.get_current_version()
            if previous_version:
                previous_hash = previous_version.get("hash", "")
            else:
                previous_hash = ""
        else:
            previous_hash = self.calculate_hash(previous_data)

        is_changed = current_hash != previous_hash

        # 変更内容の詳細分析（DataFrameの場合）
        changes_detail = {}
        if is_changed and isinstance(current_data, pd.DataFrame):
            if previous_data is not None and isinstance(previous_data, pd.DataFrame):
                # 行数の変更
                changes_detail["rows_added"] = len(current_data) - len(previous_data)

                # カラムの変更
                cols_added = set(current_data.columns) - set(previous_data.columns)
                cols_removed = set(previous_data.columns) - set(current_data.columns)
                if cols_added:
                    changes_detail["columns_added"] = list(cols_added)
                if cols_removed:
                    changes_detail["columns_removed"] = list(cols_removed)

        return {
            "changed": is_changed,
            "current_hash": current_hash,
            "previous_hash": previous_hash,
            "details": changes_detail,
            "timestamp": datetime.now().isoformat(),
        }

    def create_version(
        self, data: Any, version_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """新しいバージョンを作成"""
        # タイムスタンプベースのバージョン名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if version_name:
            version_id = f"{version_name}_{timestamp}"
        else:
            version_id = f"v_{timestamp}"

        # データのハッシュ計算
        data_hash = self.calculate_hash(data)

        # バージョンメタデータ
        version_info = {
            "version_id": version_id,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "hash": data_hash,
            "metadata": metadata or {},
            "size": self._get_data_size(data),
        }

        # データを保存
        data_file = self.versions_dir / "data" / f"{version_id}.pkl"
        self._save_data(data, data_file)

        # メタデータを保存
        metadata_file = self.versions_dir / "metadata" / f"{version_id}.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

        # バージョン履歴に追加
        self.version_history.append(version_info)
        self._save_history()

        # 古いバージョンをクリーンアップ
        self._cleanup_old_versions()

        # 現在のバージョンとして設定
        self._set_current_version(version_info)

        self.logger.info(f"✅ バージョン作成: {version_id} (hash: {data_hash[:8]}...)")
        return version_id

    def get_version(self, version_id: str) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """特定のバージョンを取得"""
        data_file = self.versions_dir / "data" / f"{version_id}.pkl"
        metadata_file = self.versions_dir / "metadata" / f"{version_id}.json"

        if not data_file.exists() or not metadata_file.exists():
            self.logger.warning(f"バージョンが見つかりません: {version_id}")
            return None

        # データを読み込み
        data = self._load_data(data_file)

        # メタデータを読み込み
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return data, metadata

    def rollback(self, version_id: str) -> bool:
        """指定バージョンにロールバック"""
        version_data = self.get_version(version_id)
        if not version_data:
            self.logger.error(f"ロールバック失敗: バージョン {version_id} が見つかりません")
            return False

        data, metadata = version_data

        # 現在のデータをスナップショットとして保存
        self.create_snapshot("before_rollback")

        # 指定バージョンを現在のバージョンとして設定
        self._set_current_version(metadata)

        self.logger.info(f"✅ ロールバック完了: {version_id}")
        return True

    def create_snapshot(self, snapshot_name: str) -> str:
        """現在の状態のスナップショットを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snapshot_{snapshot_name}_{timestamp}"

        current = self.get_current_version()
        if current:
            snapshot_file = self.versions_dir / "snapshots" / f"{snapshot_id}.json"
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)

            self.logger.info(f"📸 スナップショット作成: {snapshot_id}")

        return snapshot_id

    def get_current_version(self) -> Optional[Dict[str, Any]]:
        """現在のバージョン情報を取得"""
        if self.current_file.exists():
            try:
                with open(self.current_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"現在のバージョン読み込みエラー: {e}")
        return None

    def _set_current_version(self, version_info: Dict[str, Any]):
        """現在のバージョンを設定"""
        with open(self.current_file, "w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

    def _save_data(self, data: Any, file_path: Path):
        """データを保存"""
        import pickle

        if isinstance(data, pd.DataFrame):
            # DataFrameの場合はCSVとPickleの両方で保存
            csv_path = file_path.with_suffix(".csv")
            data.to_csv(csv_path, index=False)

        # Pickle形式で保存
        with open(file_path, "wb") as f:
            pickle.dump(data, f)

    def _load_data(self, file_path: Path) -> Any:
        """データを読み込み"""
        import pickle

        # CSV版が存在する場合はDataFrameとして読み込み
        csv_path = file_path.with_suffix(".csv")
        if csv_path.exists():
            return pd.read_csv(csv_path)

        # Pickle形式で読み込み
        with open(file_path, "rb") as f:
            return pickle.load(f)

    def _get_data_size(self, data: Any) -> int:
        """データサイズを取得"""
        if isinstance(data, pd.DataFrame):
            return len(data)
        elif isinstance(data, (list, dict)):
            return len(data)
        else:
            return 1

    def _cleanup_old_versions(self):
        """古いバージョンをクリーンアップ"""
        if len(self.version_history) > self.max_versions:
            # 古いバージョンを削除
            versions_to_remove = self.version_history[: -self.max_versions]

            for version in versions_to_remove:
                version_id = version["version_id"]

                # データファイルを削除
                data_file = self.versions_dir / "data" / f"{version_id}.pkl"
                csv_file = self.versions_dir / "data" / f"{version_id}.csv"
                metadata_file = self.versions_dir / "metadata" / f"{version_id}.json"

                for file in [data_file, csv_file, metadata_file]:
                    if file.exists():
                        file.unlink()

                self.logger.info(f"🗑️ 古いバージョンを削除: {version_id}")

            # 履歴を更新
            self.version_history = self.version_history[-self.max_versions :]
            self._save_history()

    def get_version_diff(self, version1_id: str, version2_id: str) -> Dict[str, Any]:
        """2つのバージョン間の差分を取得"""
        v1_data = self.get_version(version1_id)
        v2_data = self.get_version(version2_id)

        if not v1_data or not v2_data:
            return {"error": "バージョンが見つかりません"}

        data1, meta1 = v1_data
        data2, meta2 = v2_data

        diff = {
            "version1": version1_id,
            "version2": version2_id,
            "hash_changed": meta1["hash"] != meta2["hash"],
            "size_diff": meta2.get("size", 0) - meta1.get("size", 0),
            "time_diff": (
                datetime.fromisoformat(meta2["created_at"]) - datetime.fromisoformat(meta1["created_at"])
            ).total_seconds(),
        }

        # DataFrameの場合は詳細な差分を計算
        if isinstance(data1, pd.DataFrame) and isinstance(data2, pd.DataFrame):
            diff["rows_diff"] = len(data2) - len(data1)
            diff["columns_diff"] = list(set(data2.columns) - set(data1.columns))

        return diff

    def list_versions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """バージョン一覧を取得"""
        versions = self.version_history[-limit:]
        versions.reverse()  # 新しい順に並び替え

        result = []
        for v in versions:
            result.append(
                {
                    "version_id": v["version_id"],
                    "created_at": v["created_at"],
                    "hash": v["hash"][:8] + "...",
                    "size": v.get("size", 0),
                    "metadata": v.get("metadata", {}),
                }
            )

        return result

    def validate_integrity(self, version_id: str) -> bool:
        """バージョンの整合性を検証"""
        version_data = self.get_version(version_id)
        if not version_data:
            return False

        data, metadata = version_data

        # ハッシュ値を再計算して検証
        calculated_hash = self.calculate_hash(data)
        stored_hash = metadata.get("hash", "")

        is_valid = calculated_hash == stored_hash

        if not is_valid:
            self.logger.error(f"❌ 整合性エラー: {version_id}")
            self.logger.error(f"  期待値: {stored_hash[:16]}...")
            self.logger.error(f"  実際値: {calculated_hash[:16]}...")
        else:
            self.logger.info(f"✅ 整合性OK: {version_id}")

        return is_valid

    def auto_version_on_change(self, data: Any, check_interval: int = 60, auto_create: bool = True) -> Optional[str]:
        """データ変更時に自動的にバージョンを作成"""
        # 変更を検出
        changes = self.detect_changes(data)

        if changes["changed"] and auto_create:
            # 変更があれば新しいバージョンを作成
            version_id = self.create_version(data, metadata={"auto_created": True, "changes": changes})
            return version_id

        return None


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)

    controller = VersionController()

    # テストデータ
    test_df = pd.DataFrame(
        {
            "person_id": ["P000399", "P000001"],
            "person_name": ["Kajisac", "Test User"],
            "person_name_display": ["カジサック", "テストユーザー"],
        }
    )

    # バージョン作成
    version_id = controller.create_version(test_df, "test_version")
    print(f"作成されたバージョン: {version_id}")

    # バージョン一覧
    versions = controller.list_versions()
    print(f"バージョン一覧: {json.dumps(versions, indent=2, ensure_ascii=False)}")

    # 整合性チェック
    is_valid = controller.validate_integrity(version_id)
    print(f"整合性: {'OK' if is_valid else 'NG'}")
