"""
CSV Integrator - MASTER CSVへのエピソード統合（冪等性保証）

このモジュールは生成されたエピソードをMASTER CSVに統合します。
重複チェックにより冪等性を保証します。

主な機能:
- 重複チェック（person_name + age）
- episode_id, person_id の自動生成
- カラム構造の自動調整
- バックアップ自動作成
- Dry-runモード

使用方法:
    >>> from src.csv_integrator import CSVIntegrator
    >>> integrator = CSVIntegrator()
    >>> episodes = [{"person_name": "山中伸弥", "age": 47, ...}]
    >>> result = integrator.integrate_episodes(episodes, dry_run=False)
    >>> print(f"Added: {result['added']}, Skipped: {result['skipped']}")
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.backup_manager import BackupManager
from src.csv_path_resolver import get_master_csv_path

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVIntegrator:
    """MASTER CSVへの統合（冪等性保証）"""

    def __init__(self, master_csv_path: Optional[Path] = None):
        """
        初期化

        Args:
            master_csv_path: MASTER CSVのパス（省略時はデフォルト）
        """
        self.master_path = master_csv_path or get_master_csv_path()
        self.backup_manager = BackupManager()

    def integrate_episodes(self, episodes: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
        """
        エピソードをMASTER CSVに統合

        Args:
            episodes: エピソードのリスト
            dry_run: True の場合、実際には変更せずシミュレーションのみ

        Returns:
            統合結果の辞書:
            {
                'added': 追加件数,
                'skipped': スキップ件数,
                'would_add': dry-run時の追加予定件数,
                'backup_path': バックアップファイルのパス (dry-run時はNone)
            }

        Example:
            >>> integrator = CSVIntegrator()
            >>> episodes = [{"person_name": "山中伸弥", "age": 47, ...}]
            >>> result = integrator.integrate_episodes(episodes, dry_run=True)
            >>> print(f"Would add: {result['would_add']} episodes")
        """
        # MASTER CSV読み込み
        master_df = pd.read_csv(self.master_path, encoding="utf-8-sig")
        logger.info(f"Master CSV loaded: {len(master_df)} episodes")

        # 重複チェック（person_name + age）
        master_keys = set(zip(master_df["person_name"], master_df["age"].astype(str)))

        new_episodes = []
        skipped_count = 0

        for episode in episodes:
            key = (str(episode.get("person_name", "")), str(episode.get("age", "")))

            if key in master_keys:
                logger.debug(f"Skipped duplicate: {episode['person_name']} ({episode['age']}歳)")
                skipped_count += 1
                continue

            new_episodes.append(episode)

        # Dry-run モード
        if dry_run:
            logger.info(f"DRY-RUN: Would add {len(new_episodes)} episodes")
            return {
                "added": 0,
                "skipped": skipped_count,
                "would_add": len(new_episodes),
                "backup_path": None,
            }

        # 新規エピソードがない場合
        if not new_episodes:
            logger.info("No new episodes to add")
            return {"added": 0, "skipped": skipped_count, "backup_path": None}

        # バックアップ作成
        backup_path = self.backup_manager.create_backup(self.master_path)
        logger.info(f"Backup created: {backup_path}")

        # 新規エピソードをDataFrameに変換
        new_df = pd.DataFrame(new_episodes)

        # episode_id, person_id を付与
        new_df = self._add_ids(new_df)

        # 必須カラムをマスター構造に合わせる
        new_df = self._align_columns(new_df, master_df.columns)

        # 統合
        combined_df = pd.concat([master_df, new_df], ignore_index=True)

        # 保存
        combined_df.to_csv(self.master_path, index=False, encoding="utf-8-sig")

        logger.info(f"✅ Integrated {len(new_episodes)} episodes to MASTER CSV")

        return {
            "added": len(new_episodes),
            "skipped": skipped_count,
            "backup_path": backup_path,
        }

    def _add_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        episode_id, person_id を生成

        Args:
            df: エピソードDataFrame

        Returns:
            IDが追加されたDataFrame

        Example:
            >>> df = pd.DataFrame([{"person_name": "山中伸弥", "age": 47, "episode_text": "..."}])
            >>> df_with_ids = integrator._add_ids(df)
            >>> print(df_with_ids[["episode_id", "person_id"]])
        """

        def generate_episode_id(row: pd.Series) -> str:
            """episode_id生成（person_name + age + episode_textの一部）"""
            key = f"{row['person_name']}_{row['age']}_{str(row.get('episode_text', ''))[:50]}"
            hash_obj = hashlib.md5(key.encode("utf-8"), usedforsecurity=False)
            return "E" + hash_obj.hexdigest()[:8].upper()

        def generate_person_id(row: pd.Series) -> str:
            """person_id生成（person_nameからMD5ハッシュ）"""
            key = str(row["person_name"])
            hash_obj = hashlib.md5(key.encode("utf-8"), usedforsecurity=False)
            return "P" + hash_obj.hexdigest()[:7].upper()

        # IDカラムが存在しない場合は生成
        if "episode_id" not in df.columns or df["episode_id"].isna().any():
            df["episode_id"] = df.apply(generate_episode_id, axis=1)

        if "person_id" not in df.columns or df["person_id"].isna().any():
            df["person_id"] = df.apply(generate_person_id, axis=1)

        return df

    def _align_columns(self, new_df: pd.DataFrame, master_columns: pd.Index) -> pd.DataFrame:
        """
        新規DataFrameをマスター構造に合わせる

        Args:
            new_df: 新規エピソードのDataFrame
            master_columns: マスターCSVのカラム

        Returns:
            カラム構造が調整されたDataFrame

        Example:
            >>> new_df = pd.DataFrame([{"person_name": "山中伸弥", "age": 47}])
            >>> master_columns = pd.Index(["episode_id", "person_id", "person_name", "age", ...])
            >>> aligned_df = integrator._align_columns(new_df, master_columns)
        """
        # マスターにない列を削除
        for col in new_df.columns:
            if col not in master_columns:
                new_df = new_df.drop(columns=[col])
                logger.debug(f"Dropped column not in master: {col}")

        # マスターにある列で新規に不足している列を追加（空文字）
        for col in master_columns:
            if col not in new_df.columns:
                new_df[col] = ""
                logger.debug(f"Added missing column: {col}")

        # カラム順をマスターに統一
        new_df = new_df[master_columns]

        return new_df

    def verify_idempotency(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        冪等性の検証（同じエピソードを2回統合してもエラーにならないことを確認）

        Args:
            episodes: テスト用エピソードのリスト

        Returns:
            検証結果の辞書

        Example:
            >>> integrator = CSVIntegrator()
            >>> test_episodes = [{"person_name": "テスト太郎", "age": 25, ...}]
            >>> result = integrator.verify_idempotency(test_episodes)
            >>> print(result['is_idempotent'])
            True
        """
        # 1回目の統合（dry-run）
        result1 = self.integrate_episodes(episodes, dry_run=True)

        # 2回目の統合（dry-run）
        result2 = self.integrate_episodes(episodes, dry_run=True)

        # 2回目は全てスキップされるべき
        is_idempotent = result2["would_add"] == 0 and result2["skipped"] == len(episodes)

        return {
            "is_idempotent": is_idempotent,
            "first_run": result1,
            "second_run": result2,
        }


if __name__ == "__main__":
    # 動作確認用
    import sys

    integrator = CSVIntegrator()

    print("=== CSV Integrator Test ===\n")

    # テストエピソード
    test_episodes = [
        {
            "person_name": "テスト太郎",
            "age": 25,
            "episode_text": "あなたと同じ25歳のとき、テスト太郎は重要な決断を下しました。",
            "category": "テスト",
            "person_type": "REAL",
            "char_count": 200,
            "composite_score": 75.0,
        },
        {
            "person_name": "テスト花子",
            "age": 30,
            "episode_text": "あなたと同じ30歳のとき、テスト花子は新たな挑戦を始めました。",
            "category": "テスト",
            "person_type": "REAL",
            "char_count": 200,
            "composite_score": 80.0,
        },
    ]

    # Dry-runテスト
    print("1. Dry-run test:")
    result = integrator.integrate_episodes(test_episodes, dry_run=True)
    print(f"   Would add: {result['would_add']} episodes")
    print(f"   Skipped: {result['skipped']} episodes\n")

    # 冪等性テスト
    print("2. Idempotency test:")
    idempotency_result = integrator.verify_idempotency(test_episodes)
    print(f"   Is idempotent: {idempotency_result['is_idempotent']}")
    print(f"   First run: {idempotency_result['first_run']}")
    print(f"   Second run: {idempotency_result['second_run']}\n")

    # 実行確認
    print("⚠️  Execute integration? (y/n): ", end="")
    if input().lower() == "y":
        result = integrator.integrate_episodes(test_episodes, dry_run=False)
        print("\n✅ Integration complete:")
        print(f"   Added: {result['added']} episodes")
        print(f"   Skipped: {result['skipped']} episodes")
        print(f"   Backup: {result['backup_path']}")
    else:
        print("\nIntegration cancelled.")
