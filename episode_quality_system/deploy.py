#!/usr/bin/env python3
"""
本番環境への自動デプロイメントスクリプト
統一エピソードファクトリv2の安全なデプロイメントを実行
"""

import os
import sys
import json
import shutil
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import time

class ProductionDeployer:
    """本番環境デプロイメント管理"""

    def __init__(self, config_path: str = "deployment_config.json"):
        self.config = self._load_config(config_path)
        self.deployment_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"backups/{self.deployment_id}")
        self.deployment_log = []
        self.rollback_stack = []

    def _load_config(self, config_path: str) -> Dict:
        """デプロイメント設定をロード"""
        if not os.path.exists(config_path):
            return self._get_default_config()

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_default_config(self) -> Dict:
        """デフォルト設定を取得"""
        return {
            "production_path": "/opt/episode_factory/production",
            "staging_path": "/opt/episode_factory/staging",
            "backup_retention_days": 30,
            "health_check_url": "http://localhost:8000/health",
            "rollback_on_failure": True,
            "notification_webhook": None,
            "required_files": [
                "unified_episode_factory_v2.py",
                "optimized_validation_system.py",
                "expanded_episode_templates.py",
                "mandatory_pipeline.py",
                "complete_person_facts.json"
            ],
            "test_command": "python3 test_unified_factory_v2.py",
            "service_name": "episode-factory",
            "min_success_rate": 0.95,
            "max_response_time_ms": 100
        }

    def pre_deployment_checks(self) -> bool:
        """デプロイメント前の事前チェック"""
        self._log("=== デプロイメント前チェック開始 ===")

        checks = [
            self._check_required_files(),
            self._check_dependencies(),
            self._run_tests(),
            self._check_performance(),
            self._validate_database()
        ]

        if not all(checks):
            self._log("❌ 事前チェック失敗", level="ERROR")
            return False

        self._log("✅ すべての事前チェックをパス")
        return True

    def _check_required_files(self) -> bool:
        """必要なファイルの存在確認"""
        self._log("📁 必要ファイルチェック...")

        for file in self.config["required_files"]:
            if not os.path.exists(file):
                self._log(f"  ❌ {file} が見つかりません", level="ERROR")
                return False

            # ファイルハッシュを記録（ロールバック用）
            file_hash = self._calculate_file_hash(file)
            self.rollback_stack.append(("file", file, file_hash))
            self._log(f"  ✅ {file} (hash: {file_hash[:8]}...)")

        return True

    def _calculate_file_hash(self, filepath: str) -> str:
        """ファイルのSHA256ハッシュを計算"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _check_dependencies(self) -> bool:
        """依存関係のチェック"""
        self._log("📦 依存関係チェック...")

        # Python版バージョンチェック
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self._log("  ❌ Python3が利用できません", level="ERROR")
            return False

        python_version = result.stdout.strip()
        self._log(f"  ✅ {python_version}")

        # 必要なパッケージチェック
        required_packages = ["typing", "json", "dataclasses"]
        for package in required_packages:
            try:
                __import__(package)
                self._log(f"  ✅ {package} モジュール")
            except ImportError:
                self._log(f"  ❌ {package} モジュールが見つかりません", level="ERROR")
                return False

        return True

    def _run_tests(self) -> bool:
        """テストスイート実行"""
        self._log("🧪 テスト実行中...")

        test_command = self.config.get("test_command")
        if not test_command:
            self._log("  ⚠️ テストコマンドが設定されていません", level="WARN")
            return True

        result = subprocess.run(
            test_command.split(),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self._log("  ❌ テスト失敗", level="ERROR")
            self._log(f"  エラー: {result.stderr}", level="ERROR")
            return False

        self._log("  ✅ すべてのテストをパス")
        return True

    def _check_performance(self) -> bool:
        """パフォーマンス基準チェック"""
        self._log("⚡ パフォーマンスチェック...")

        # benchmark_results.jsonが存在する場合は読み込む
        if os.path.exists("benchmark_results.json"):
            with open("benchmark_results.json", 'r', encoding='utf-8') as f:
                results = json.load(f)

            sequential = results.get("sequential", {})
            avg_response = sequential.get("avg_response_time_ms", float('inf'))
            success_rate = sequential.get("success_rate", 0) / 100

            max_response = self.config.get("max_response_time_ms", 100)
            min_success = self.config.get("min_success_rate", 0.95)

            if avg_response > max_response:
                self._log(f"  ❌ レスポンスタイム {avg_response:.2f}ms > {max_response}ms",
                         level="ERROR")
                return False

            if success_rate < min_success:
                self._log(f"  ❌ 成功率 {success_rate:.1%} < {min_success:.1%}",
                         level="ERROR")
                return False

            self._log(f"  ✅ レスポンスタイム: {avg_response:.2f}ms")
            self._log(f"  ✅ 成功率: {success_rate:.1%}")
        else:
            self._log("  ⚠️ ベンチマーク結果がありません", level="WARN")

        return True

    def _validate_database(self) -> bool:
        """データベースの妥当性チェック"""
        self._log("🗄️ データベース検証...")

        db_file = "complete_person_facts.json"
        if not os.path.exists(db_file):
            self._log(f"  ❌ {db_file} が見つかりません", level="ERROR")
            return False

        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data.get("persons", {})
            person_count = len(persons)

            if person_count < 100:
                self._log(f"  ⚠️ 人物データが少ない: {person_count}人", level="WARN")
            else:
                self._log(f"  ✅ 人物データ: {person_count}人")

            # サンプルチェック
            sample_persons = ["大谷翔平", "新垣結衣", "山中伸弥"]
            for person in sample_persons:
                if person not in persons:
                    self._log(f"  ❌ {person} のデータが見つかりません", level="ERROR")
                    return False

            self._log("  ✅ サンプルデータ検証OK")
            return True

        except Exception as e:
            self._log(f"  ❌ データベース読み込みエラー: {e}", level="ERROR")
            return False

    def create_backup(self) -> bool:
        """現在の本番環境をバックアップ"""
        self._log("💾 バックアップ作成中...")

        production_path = Path(self.config["production_path"])

        # 本番環境が存在しない場合は新規デプロイメント
        if not production_path.exists():
            self._log("  📝 新規デプロイメント（バックアップ不要）")
            return True

        # バックアップディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # ファイルをバックアップ
            for file in self.config["required_files"]:
                src = production_path / file
                if src.exists():
                    dst = self.backup_dir / file
                    shutil.copy2(src, dst)
                    self._log(f"  ✅ {file} をバックアップ")

            # バックアップ情報を記録
            backup_info = {
                "deployment_id": self.deployment_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "files": self.config["required_files"],
                "production_path": str(production_path)
            }

            with open(self.backup_dir / "backup_info.json", 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            self._log("  ✅ バックアップ完了")
            return True

        except Exception as e:
            self._log(f"  ❌ バックアップ失敗: {e}", level="ERROR")
            return False

    def deploy_to_staging(self) -> bool:
        """ステージング環境へデプロイ"""
        self._log("🔧 ステージング環境へデプロイ中...")

        staging_path = Path(self.config["staging_path"])
        staging_path.mkdir(parents=True, exist_ok=True)

        try:
            # ファイルをコピー
            for file in self.config["required_files"]:
                src = Path(file)
                dst = staging_path / file
                shutil.copy2(src, dst)
                self._log(f"  ✅ {file} をステージングにコピー")

            # ステージング環境でテスト実行
            self._log("  🧪 ステージング環境でテスト中...")

            original_dir = os.getcwd()
            os.chdir(staging_path)

            result = subprocess.run(
                ["python3", "-c", "from unified_episode_factory_v2 import UnifiedEpisodeFactory; print('OK')"],
                capture_output=True,
                text=True
            )

            os.chdir(original_dir)

            if result.returncode != 0 or "OK" not in result.stdout:
                self._log("  ❌ ステージングテスト失敗", level="ERROR")
                return False

            self._log("  ✅ ステージングデプロイ完了")
            return True

        except Exception as e:
            self._log(f"  ❌ ステージングデプロイ失敗: {e}", level="ERROR")
            return False

    def deploy_to_production(self) -> bool:
        """本番環境へデプロイ"""
        self._log("🚀 本番環境へデプロイ中...")

        staging_path = Path(self.config["staging_path"])
        production_path = Path(self.config["production_path"])

        production_path.mkdir(parents=True, exist_ok=True)

        try:
            # アトミックなデプロイメント（シンボリックリンク切り替え）
            new_version_path = production_path / f"v_{self.deployment_id}"
            new_version_path.mkdir(parents=True, exist_ok=True)

            # ステージングから新バージョンディレクトリへコピー
            for file in self.config["required_files"]:
                src = staging_path / file
                dst = new_version_path / file
                shutil.copy2(src, dst)
                self._log(f"  ✅ {file} を本番にコピー")

            # currentシンボリックリンクを更新
            current_link = production_path / "current"
            new_link = production_path / "current_new"

            # 新しいリンクを作成
            if new_link.exists():
                new_link.unlink()
            new_link.symlink_to(new_version_path)

            # アトミックに切り替え
            if current_link.exists():
                self.rollback_stack.append(("symlink", str(current_link), str(current_link.readlink())))
            new_link.rename(current_link)

            self._log("  ✅ 本番デプロイ完了")
            return True

        except Exception as e:
            self._log(f"  ❌ 本番デプロイ失敗: {e}", level="ERROR")
            return False

    def health_check(self) -> bool:
        """本番環境のヘルスチェック"""
        self._log("🏥 ヘルスチェック実行中...")

        health_url = self.config.get("health_check_url")
        if not health_url:
            self._log("  ⚠️ ヘルスチェックURL未設定", level="WARN")
            return True

        # 簡易的なヘルスチェック（実際の環境では適切なHTTPリクエストを実装）
        try:
            production_path = Path(self.config["production_path"]) / "current"
            test_file = production_path / "unified_episode_factory_v2.py"

            if not test_file.exists():
                self._log("  ❌ デプロイされたファイルが見つかりません", level="ERROR")
                return False

            # インポートテスト
            sys.path.insert(0, str(production_path))
            from unified_episode_factory_v2 import UnifiedEpisodeFactory

            self._log("  ✅ ヘルスチェックOK")
            return True

        except Exception as e:
            self._log(f"  ❌ ヘルスチェック失敗: {e}", level="ERROR")
            return False

    def rollback(self) -> bool:
        """デプロイメントのロールバック"""
        self._log("⏪ ロールバック実行中...")

        if not self.rollback_stack:
            self._log("  ⚠️ ロールバック情報がありません", level="WARN")
            return False

        try:
            # ロールバックスタックを逆順で処理
            while self.rollback_stack:
                action_type, target, original = self.rollback_stack.pop()

                if action_type == "symlink":
                    # シンボリックリンクを元に戻す
                    link_path = Path(target)
                    if link_path.exists():
                        link_path.unlink()
                    link_path.symlink_to(Path(original))
                    self._log(f"  ✅ シンボリックリンクを復元: {target}")

                elif action_type == "file":
                    # バックアップからファイルを復元
                    if self.backup_dir.exists():
                        backup_file = self.backup_dir / Path(target).name
                        if backup_file.exists():
                            production_file = Path(self.config["production_path"]) / "current" / Path(target).name
                            shutil.copy2(backup_file, production_file)
                            self._log(f"  ✅ ファイルを復元: {target}")

            self._log("  ✅ ロールバック完了")
            return True

        except Exception as e:
            self._log(f"  ❌ ロールバック失敗: {e}", level="ERROR")
            return False

    def cleanup_old_versions(self) -> bool:
        """古いバージョンとバックアップをクリーンアップ"""
        self._log("🧹 古いバージョンのクリーンアップ...")

        retention_days = self.config.get("backup_retention_days", 30)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

        # バックアップディレクトリのクリーンアップ
        backup_base = Path("backups")
        if backup_base.exists():
            for backup_dir in backup_base.iterdir():
                if backup_dir.is_dir():
                    try:
                        # ディレクトリ名から日時を抽出
                        dir_date = datetime.datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
                        if dir_date < cutoff_date:
                            shutil.rmtree(backup_dir)
                            self._log(f"  🗑️ 削除: {backup_dir.name}")
                    except ValueError:
                        # 日付形式でないディレクトリはスキップ
                        pass

        self._log("  ✅ クリーンアップ完了")
        return True

    def _log(self, message: str, level: str = "INFO"):
        """ログメッセージを記録"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.deployment_log.append(log_entry)
        print(log_entry)

    def save_deployment_log(self):
        """デプロイメントログを保存"""
        log_file = f"deployment_logs/deploy_{self.deployment_id}.log"
        Path("deployment_logs").mkdir(exist_ok=True)

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.deployment_log))

        print(f"📝 ログを保存: {log_file}")

    def deploy(self) -> bool:
        """完全なデプロイメントプロセスを実行"""
        self._log(f"🚀 デプロイメント開始 (ID: {self.deployment_id})")
        self._log("=" * 60)

        steps = [
            ("事前チェック", self.pre_deployment_checks),
            ("バックアップ作成", self.create_backup),
            ("ステージングデプロイ", self.deploy_to_staging),
            ("本番デプロイ", self.deploy_to_production),
            ("ヘルスチェック", self.health_check),
            ("古いバージョンクリーンアップ", self.cleanup_old_versions)
        ]

        for step_name, step_func in steps:
            self._log(f"\n>>> {step_name}")

            if not step_func():
                self._log(f"\n❌ {step_name}で失敗しました", level="ERROR")

                if self.config.get("rollback_on_failure", True):
                    self._log("\n⏪ 自動ロールバック開始...")
                    if self.rollback():
                        self._log("✅ ロールバック成功")
                    else:
                        self._log("❌ ロールバック失敗", level="ERROR")

                self.save_deployment_log()
                return False

        self._log("\n" + "=" * 60)
        self._log("✅ デプロイメント成功！")
        self._log(f"🎉 バージョン v_{self.deployment_id} が本番環境で稼働中")

        self.save_deployment_log()
        return True


def main():
    """メイン処理"""
    deployer = ProductionDeployer()

    # デプロイメント実行
    if deployer.deploy():
        print("\n✨ デプロイメントが正常に完了しました")
        sys.exit(0)
    else:
        print("\n⚠️ デプロイメントに失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
