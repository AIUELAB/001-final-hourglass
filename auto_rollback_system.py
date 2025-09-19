#!/usr/bin/env python3
"""
自動ロールバックシステム - 品質ゲート失敗時の自動復元
変更を監視し、品質違反時に自動的に前の状態に戻す
"""

import os
import sys
import json
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileSnapshot:
    """ファイルスナップショット管理"""
    
    def __init__(self, backup_dir: str = ".rollback_snapshots"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.snapshot_index = self.backup_dir / "snapshot_index.json"
        self.snapshots = self._load_index()
    
    def _load_index(self) -> Dict:
        """スナップショットインデックスを読み込み"""
        if self.snapshot_index.exists():
            with open(self.snapshot_index, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """スナップショットインデックスを保存"""
        with open(self.snapshot_index, 'w') as f:
            json.dump(self.snapshots, f, indent=2)
    
    def _calculate_hash(self, file_path: str) -> str:
        """ファイルのハッシュ値を計算"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def create_snapshot(self, file_path: str) -> str:
        """ファイルのスナップショットを作成"""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"ファイルが存在しません: {file_path}")
            return None
        
        # ハッシュ値でユニークなバックアップ名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = self._calculate_hash(file_path)[:8]
        backup_name = f"{file_path.stem}_{timestamp}_{file_hash}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        # ファイルをバックアップ
        shutil.copy2(file_path, backup_path)
        
        # インデックスに記録
        if str(file_path) not in self.snapshots:
            self.snapshots[str(file_path)] = []
        
        self.snapshots[str(file_path)].append({
            "backup_path": str(backup_path),
            "timestamp": timestamp,
            "hash": file_hash,
            "original_size": file_path.stat().st_size
        })
        
        self._save_index()
        logger.info(f"📸 スナップショット作成: {backup_name}")
        return str(backup_path)
    
    def rollback(self, file_path: str, version: int = -1) -> bool:
        """指定バージョンにロールバック"""
        file_path_str = str(Path(file_path))
        
        if file_path_str not in self.snapshots:
            logger.error(f"スナップショットが存在しません: {file_path}")
            return False
        
        snapshots = self.snapshots[file_path_str]
        if not snapshots:
            logger.error(f"スナップショットが空です: {file_path}")
            return False
        
        # バージョン指定（-1は最新）
        if version < 0:
            version = len(snapshots) + version
        
        if version < 0 or version >= len(snapshots):
            logger.error(f"無効なバージョン: {version}")
            return False
        
        snapshot = snapshots[version]
        backup_path = Path(snapshot["backup_path"])
        
        if not backup_path.exists():
            logger.error(f"バックアップファイルが見つかりません: {backup_path}")
            return False
        
        # ロールバック実行
        shutil.copy2(backup_path, file_path)
        logger.info(f"✅ ロールバック完了: {file_path} -> version {version}")
        return True
    
    def list_snapshots(self, file_path: str) -> List[Dict]:
        """ファイルのスナップショット一覧"""
        file_path_str = str(Path(file_path))
        return self.snapshots.get(file_path_str, [])


class GitRollback:
    """Git連携ロールバック"""
    
    @staticmethod
    def is_git_repo() -> bool:
        """Gitリポジトリかどうか確認"""
        return Path(".git").exists()
    
    @staticmethod
    def get_current_branch() -> str:
        """現在のブランチを取得"""
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    
    @staticmethod
    def create_checkpoint(message: str = "Quality checkpoint") -> str:
        """品質チェックポイントを作成"""
        if not GitRollback.is_git_repo():
            return None
        
        try:
            # 現在の変更をステージング
            subprocess.run(["git", "add", "-A"], check=True)
            
            # コミット作成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            commit_message = f"[CHECKPOINT] {message} - {timestamp}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # コミットハッシュを取得
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True
                )
                commit_hash = hash_result.stdout.strip()[:8]
                logger.info(f"🔖 Gitチェックポイント作成: {commit_hash}")
                return commit_hash
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Gitチェックポイント作成失敗: {e}")
        
        return None
    
    @staticmethod
    def rollback_to_checkpoint(commit_hash: str) -> bool:
        """指定のチェックポイントにロールバック"""
        if not GitRollback.is_git_repo():
            return False
        
        try:
            # 現在の変更を破棄
            subprocess.run(["git", "reset", "--hard", commit_hash], check=True)
            logger.info(f"✅ Gitロールバック完了: {commit_hash}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Gitロールバック失敗: {e}")
            return False


class AutoRollbackSystem:
    """自動ロールバックシステム統合"""
    
    def __init__(self):
        self.snapshot_manager = FileSnapshot()
        self.rollback_history = []
        self.quality_gate_path = Path("quality_gates.py")
        self.pdca_guardian_path = Path("pdca_guardian.py")
    
    def protect_file(self, file_path: str) -> Optional[str]:
        """ファイルを保護（スナップショット作成）"""
        # ファイルスナップショット
        snapshot_path = self.snapshot_manager.create_snapshot(file_path)
        
        # Git連携
        if GitRollback.is_git_repo():
            commit_hash = GitRollback.create_checkpoint(f"Protect {Path(file_path).name}")
            
            self.rollback_history.append({
                "timestamp": datetime.now().isoformat(),
                "file": file_path,
                "snapshot": snapshot_path,
                "git_commit": commit_hash
            })
        else:
            self.rollback_history.append({
                "timestamp": datetime.now().isoformat(),
                "file": file_path,
                "snapshot": snapshot_path,
                "git_commit": None
            })
        
        return snapshot_path
    
    def execute_with_protection(self, script_path: str) -> Tuple[bool, Optional[Dict]]:
        """保護付きでスクリプトを実行"""
        logger.info(f"🛡️ 保護付き実行開始: {script_path}")
        
        # 実行前にスナップショット作成
        snapshot = self.protect_file(script_path)
        
        # 品質ゲートチェック
        if self.quality_gate_path.exists():
            from quality_gates import QualityGateSystem
            
            gate_system = QualityGateSystem()
            passed, results = gate_system.check_script(script_path)
            
            if not passed:
                logger.error("❌ 品質ゲート失敗 - ロールバック実行")
                
                # 自動ロールバック
                if self.snapshot_manager.rollback(script_path):
                    logger.info("✅ ファイルロールバック完了")
                
                # Git連携ロールバック
                if self.rollback_history and self.rollback_history[-1]["git_commit"]:
                    GitRollback.rollback_to_checkpoint(
                        self.rollback_history[-1]["git_commit"]
                    )
                
                return False, {
                    "status": "rolled_back",
                    "reason": "quality_gate_failure",
                    "details": results
                }
        
        # PDCAガーディアンチェック
        if self.pdca_guardian_path.exists():
            from pdca_guardian import PDCAGuardian
            
            guardian = PDCAGuardian()
            
            # 実装チェック
            with open(script_path, 'r') as f:
                implementation = {"code": f.read()}
            
            violations = guardian.validate_implementation(implementation)
            
            if violations:
                critical_violations = [v for v in violations if v.severity.value == "CRITICAL"]
                
                if critical_violations:
                    logger.error(f"❌ CRITICAL違反検出 - ロールバック実行")
                    
                    # 自動ロールバック
                    if self.snapshot_manager.rollback(script_path):
                        logger.info("✅ ファイルロールバック完了")
                    
                    return False, {
                        "status": "rolled_back",
                        "reason": "pdca_violation",
                        "violations": [v.to_dict() for v in critical_violations]
                    }
        
        logger.info("✅ 品質チェック通過 - 実行許可")
        return True, {
            "status": "approved",
            "snapshot": snapshot,
            "timestamp": datetime.now().isoformat()
        }
    
    def monitor_directory(self, directory: str = ".", interval: int = 5):
        """ディレクトリを監視して自動保護"""
        logger.info(f"👁️ ディレクトリ監視開始: {directory}")
        
        watched_files = {}
        directory = Path(directory)
        
        try:
            while True:
                # Pythonファイルを監視
                for py_file in directory.glob("*.py"):
                    current_mtime = py_file.stat().st_mtime
                    
                    if str(py_file) not in watched_files:
                        watched_files[str(py_file)] = current_mtime
                        self.protect_file(str(py_file))
                    elif watched_files[str(py_file)] != current_mtime:
                        logger.info(f"📝 変更検出: {py_file}")
                        
                        # 品質チェック付き保護
                        success, result = self.execute_with_protection(str(py_file))
                        
                        if success:
                            watched_files[str(py_file)] = current_mtime
                        else:
                            logger.warning(f"⚠️ 品質違反のため変更を拒否: {py_file}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("👋 監視終了")
    
    def generate_report(self) -> Dict:
        """ロールバック履歴レポート生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_protections": len(self.rollback_history),
            "history": self.rollback_history,
            "snapshots": self.snapshot_manager.snapshots
        }
        
        # レポート保存
        report_path = f"rollback_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 レポート生成: {report_path}")
        return report


def main():
    """メイン処理"""
    rollback_system = AutoRollbackSystem()
    
    # コマンドライン引数処理
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "protect" and len(sys.argv) > 2:
            # ファイル保護
            file_path = sys.argv[2]
            snapshot = rollback_system.protect_file(file_path)
            print(f"Protected: {file_path} -> {snapshot}")
            
        elif command == "execute" and len(sys.argv) > 2:
            # 保護付き実行
            script_path = sys.argv[2]
            success, result = rollback_system.execute_with_protection(script_path)
            print(json.dumps(result, indent=2))
            
        elif command == "monitor":
            # ディレクトリ監視
            directory = sys.argv[2] if len(sys.argv) > 2 else "."
            rollback_system.monitor_directory(directory)
            
        elif command == "report":
            # レポート生成
            report = rollback_system.generate_report()
            print(json.dumps(report, indent=2))
            
        else:
            print("Usage:")
            print("  protect <file>  - Create snapshot")
            print("  execute <script> - Execute with protection")
            print("  monitor [dir]   - Monitor directory")
            print("  report         - Generate report")
    else:
        # テスト実行
        logger.info("🧪 ロールバックシステムテスト")
        
        # apply_recognition_simple.pyの保護付き実行テスト
        test_file = "apply_recognition_simple.py"
        if Path(test_file).exists():
            success, result = rollback_system.execute_with_protection(test_file)
            
            print("\n" + "=" * 60)
            print("ロールバックシステムテスト結果:")
            print(f"  ファイル: {test_file}")
            print(f"  結果: {'✅ 承認' if success else '❌ ロールバック'}")
            if result:
                print(f"  ステータス: {result.get('status')}")
                print(f"  理由: {result.get('reason', 'N/A')}")
            print("=" * 60)


if __name__ == "__main__":
    main()