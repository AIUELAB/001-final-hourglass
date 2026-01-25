#!/usr/bin/env python3
"""
Generation Manager - データ世代管理システム

機能:
- 差分バックアップ作成
- 世代ローテーション（最大10世代保持）
- 特定時点への復元
- バックアップチェーン管理

使用方法:
    >>> from src.generation_manager import GenerationManager
    >>> manager = GenerationManager()
    >>> manager.create_generation("Feature X implementation")
    >>> manager.list_generations()
    >>> manager.restore_to_generation(3)
"""

import csv
import gzip
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.csv_path_resolver import get_master_csv_path, get_project_root

JsonDict = dict[str, Any]


class GenerationManager:
    """データ世代管理"""

    MAX_GENERATIONS = 10
    GENERATION_DIR_NAME = "generations"

    def __init__(
        self,
        master_csv: Optional[Path] = None,
        generation_dir: Optional[Path] = None,
    ):
        if master_csv is None:
            self.master_csv = get_master_csv_path()
        else:
            self.master_csv = master_csv

        if generation_dir is None:
            self.generation_dir = get_project_root() / "preserved" / self.GENERATION_DIR_NAME
        else:
            self.generation_dir = generation_dir

        self.generation_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.generation_dir / "generations_metadata.json"
        self._load_metadata()

    def _load_metadata(self) -> None:
        """メタデータを読み込み"""
        # なぜ: mypyで `Any` 扱いになり、戻り値が `Any` になるのを防ぐため
        self.metadata: JsonDict = {
            "current_generation": 0,
            "generations": [],
        }
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.metadata.update(loaded)

    def _save_metadata(self) -> None:
        """メタデータを保存"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def _compute_file_hash(self, file_path: Path) -> str:
        """ファイルのSHA256ハッシュを計算"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _count_rows(self, csv_path: Path) -> int:
        """CSVの行数をカウント"""
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f) - 1

    def _get_csv_stats(self, csv_path: Path) -> JsonDict:
        """CSVの統計情報を取得"""
        row_count = self._count_rows(csv_path)
        file_size = csv_path.stat().st_size
        file_hash = self._compute_file_hash(csv_path)

        return {
            "row_count": row_count,
            "file_size": file_size,
            "file_hash": file_hash,
        }

    def create_generation(self, description: str = "", compress: bool = True) -> JsonDict:
        """
        新しい世代を作成

        Args:
            description: 世代の説明
            compress: gzip圧縮するかどうか

        Returns:
            作成された世代の情報
        """
        generation_number = int(self.metadata.get("current_generation", 0)) + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ファイル名を決定
        if compress:
            backup_name = f"gen_{generation_number:04d}_{timestamp}.csv.gz"
        else:
            backup_name = f"gen_{generation_number:04d}_{timestamp}.csv"

        backup_path = self.generation_dir / backup_name

        # 統計情報取得
        stats = self._get_csv_stats(self.master_csv)

        # バックアップ作成
        if compress:
            with open(self.master_csv, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(self.master_csv, backup_path)

        # 世代情報
        generation_info = {
            "generation_number": generation_number,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "backup_file": backup_name,
            "compressed": compress,
            "stats": stats,
        }

        # メタデータ更新
        generations = self.metadata.get("generations")
        if not isinstance(generations, list):
            generations = []
            self.metadata["generations"] = generations
        generations.append(generation_info)
        self.metadata["current_generation"] = generation_number
        self._save_metadata()

        # 古い世代の削除
        self._rotate_generations()

        print(f"Generation {generation_number} created")
        print(f"  Description: {description}")
        print(f"  Rows: {stats['row_count']:,}")
        print(f"  File: {backup_name}")

        return generation_info

    def _rotate_generations(self) -> None:
        """古い世代を削除（MAX_GENERATIONSを超えた場合）"""
        generations = self.metadata.get("generations")
        if not isinstance(generations, list):
            return

        while len(generations) > self.MAX_GENERATIONS:
            oldest = generations.pop(0)
            oldest_file = self.generation_dir / oldest["backup_file"]
            if oldest_file.exists():
                oldest_file.unlink()
                print(f"  Rotated out: Generation {oldest['generation_number']}")

        self._save_metadata()

    def list_generations(self, limit: Optional[int] = None) -> list[JsonDict]:
        """
        世代一覧を取得

        Args:
            limit: 取得する最大数

        Returns:
            世代情報のリスト
        """
        generations = self.metadata.get("generations", [])
        if not isinstance(generations, list):
            return []
        typed = [g for g in generations if isinstance(g, dict)]
        if limit is not None:
            return typed[-limit:]
        return typed

    def get_generation(self, generation_number: int) -> Optional[JsonDict]:
        """指定した世代の情報を取得"""
        for gen in self.list_generations(limit=None):
            if int(gen.get("generation_number", -1)) == generation_number:
                return gen
        return None

    def restore_to_generation(self, generation_number: int) -> JsonDict:
        """
        指定した世代に復元

        Args:
            generation_number: 復元先の世代番号

        Returns:
            復元結果
        """
        gen = self.get_generation(generation_number)
        if gen is None:
            raise ValueError(f"Generation {generation_number} not found")

        backup_path = self.generation_dir / gen["backup_file"]
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # 現在の状態を一時保存
        current_stats = self._get_csv_stats(self.master_csv)

        # 復元
        if gen["compressed"]:
            with gzip.open(backup_path, "rb") as f_in:
                with open(self.master_csv, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_path, self.master_csv)

        result = {
            "restored_to": generation_number,
            "timestamp": datetime.now().isoformat(),
            "before_stats": current_stats,
            "after_stats": gen["stats"],
        }

        print(f"Restored to Generation {generation_number}")
        print(f"  Rows: {current_stats['row_count']:,} -> {gen['stats']['row_count']:,}")

        return result

    def get_generation_history(self) -> list[dict]:
        """世代履歴を取得（詳細情報付き）"""
        history = []
        for gen in self.metadata["generations"]:
            backup_path = self.generation_dir / gen["backup_file"]
            gen_info = {
                **gen,
                "exists": backup_path.exists(),
                "current_size": backup_path.stat().st_size if backup_path.exists() else 0,
            }
            history.append(gen_info)
        return history

    def get_diff_between_generations(
        self,
        gen_from: int,
        gen_to: int,
    ) -> dict:
        """
        2つの世代間の差分を取得

        Args:
            gen_from: 比較元の世代番号
            gen_to: 比較先の世代番号

        Returns:
            差分情報
        """
        from_gen = self.get_generation(gen_from)
        to_gen = self.get_generation(gen_to)

        if from_gen is None or to_gen is None:
            raise ValueError("One or both generations not found")

        diff = {
            "from_generation": gen_from,
            "to_generation": gen_to,
            "row_diff": to_gen["stats"]["row_count"] - from_gen["stats"]["row_count"],
            "size_diff": to_gen["stats"]["file_size"] - from_gen["stats"]["file_size"],
            "hash_changed": from_gen["stats"]["file_hash"] != to_gen["stats"]["file_hash"],
            "from_timestamp": from_gen["timestamp"],
            "to_timestamp": to_gen["timestamp"],
        }

        return diff

    def create_differential_backup(self, base_generation: Optional[int] = None) -> dict:
        """
        差分バックアップを作成

        Args:
            base_generation: ベースとなる世代（省略時は最新）

        Returns:
            差分バックアップ情報
        """
        if base_generation is None:
            if not self.metadata["generations"]:
                # 初回は完全バックアップ
                return self.create_generation("Initial full backup")
            base_generation = self.metadata["current_generation"]

        base_gen = self.get_generation(base_generation)
        if base_gen is None:
            raise ValueError(f"Base generation {base_generation} not found")

        # 現在の状態と比較
        current_stats = self._get_csv_stats(self.master_csv)

        if current_stats["file_hash"] == base_gen["stats"]["file_hash"]:
            print("No changes detected since last generation")
            return {
                "status": "no_changes",
                "base_generation": base_generation,
            }

        # 差分があれば新世代作成
        diff = {
            "row_diff": current_stats["row_count"] - base_gen["stats"]["row_count"],
            "size_diff": current_stats["file_size"] - base_gen["stats"]["file_size"],
        }

        description = f"Diff from gen {base_generation}: {diff['row_diff']:+d} rows"
        new_gen = self.create_generation(description)

        return {
            "status": "created",
            "base_generation": base_generation,
            "new_generation": new_gen["generation_number"],
            "diff": diff,
        }


def print_generation_status():
    """世代状態を表示"""
    manager = GenerationManager()

    print("=" * 60)
    print("Generation Manager - Status")
    print("=" * 60)

    print(f"\nCurrent generation: {manager.metadata['current_generation']}")
    print(f"Total generations: {len(manager.metadata['generations'])}")
    print(f"Max generations: {manager.MAX_GENERATIONS}")

    generations = manager.list_generations()
    if generations:
        print("\nGeneration History:")
        for gen in generations:
            backup_path = manager.generation_dir / gen["backup_file"]
            exists = "" if backup_path.exists() else " [MISSING]"
            print(f"\n  Gen {gen['generation_number']}: {gen['description']}{exists}")
            print(f"    Timestamp: {gen['timestamp']}")
            print(f"    Rows: {gen['stats']['row_count']:,}")
            print(f"    Compressed: {gen['compressed']}")
    else:
        print("\nNo generations created yet")


if __name__ == "__main__":
    print_generation_status()
