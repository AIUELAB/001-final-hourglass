#!/usr/bin/env python3
"""
Docker & n8n 監視ツール
シンプルなCLIベースの実装
"""

import json
import os
import subprocess
import time

from typing import Any, Dict, Union

class DockerN8nMonitor:
    """Docker & n8n監視クラス"""

    def __init__(self):
        self.docker_available = False
        self.n8n_available = False
        self.check_interval = 300  # 秒

    def _print_container_info(self, containers: list) -> None:
        """コンテナ情報を表示するヘルパー関数"""
        if containers and containers[0]:
            print(f"   📦 実行中コンテナ: {len(containers)}個")
            for container in containers[:3]:  # 最初の3つを表示
                if container.strip():
                    parts = container.split()
                    if len(parts) >= 7:
                        container_id = parts[0][:12]
                        image = parts[1]
                        status = parts[6]
                        print(f"      - {container_id} ({image}) - {status}")
        else:
            print("   📦 実行中コンテナ: なし")

    def check_docker_status(self) -> bool:
        """Dockerの状態を確認"""
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Docker: 起動中")
                # コンテナ一覧を表示
                containers = result.stdout.strip().split('\n')[1:]  # ヘッダーを除く
                self._print_container_info(containers)
                return True
            else:
                print("❌ Docker: 起動していません")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ Docker: タイムアウト")
            return False
        except FileNotFoundError:
            print("❌ Docker: インストールされていません")
            return False
        except Exception as e:
            print(f"❌ Docker: エラー - {e}")
            return False

    def check_n8n_status(self) -> bool:
        """n8nの状態を確認"""
        try:
            # curlコマンドでn8nに接続
            result = subprocess.run(['curl', '-s', '--connect-timeout', '5', 'http://localhost:5678'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                print("✅ n8n: 起動中")
                return True
            else:
                print("❌ n8n: 起動していません")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ n8n: タイムアウト")
            return False
        except FileNotFoundError:
            print("❌ curl: 利用できません")
            return False
        except Exception as e:
            print(f"❌ n8n: エラー - {e}")
            return False

    def get_docker_info(self) -> Dict[str, Any]:
        """Dockerの詳細情報を取得"""
        info = {}
        try:
            # Docker version
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['version'] = result.stdout.strip()

            # Docker system info
            result = subprocess.run(['docker', 'system', 'df'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info['system_df'] = result.stdout.strip()

        except Exception as e:
            info['error'] = str(e)

        return info

    def get_n8n_info(self) -> Dict[str, Union[str, int]]:
        """n8nの詳細情報を取得"""
        info: Dict[str, Union[str, int]] = {}
        try:
            # n8nのワークフロー情報を取得（APIキーがある場合）
            api_key = os.getenv('N8N_API_KEY')
            if api_key:
                result = subprocess.run([
                    'curl', '-s', '-H', f'X-N8N-API-KEY: {api_key}',
                    'http://localhost:5678/api/v1/workflows'
                ], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    try:
                        workflows = json.loads(result.stdout)
                        info['workflows'] = len(workflows) if isinstance(workflows, list) else 0
                    except json.JSONDecodeError:
                        info['workflows'] = 'JSON解析エラー'
        except Exception as e:
            info['error'] = str(e)

        return info

    def _display_docker_info(self) -> None:
        """Docker詳細情報を表示するヘルパー関数"""
        print("\n📊 Docker詳細情報:")
        docker_info = self.get_docker_info()
        self._print_info_if_exists(docker_info, 'version', 'バージョン')
        self._print_system_df_if_exists(docker_info)

    def _display_n8n_info(self) -> None:
        """n8n詳細情報を表示するヘルパー関数"""
        print("\n📊 n8n詳細情報:")
        n8n_info = self.get_n8n_info()
        self._print_workflows_if_exists(n8n_info)

    def _print_info_if_exists(self, info: Dict[str, Any], key: str, label: str) -> None:
        """指定されたキーが存在する場合に情報を表示するヘルパー関数"""
        if key in info:
            print(f"   {label}: {info[key]}")

    def _print_system_df_if_exists(self, docker_info: Dict[str, Any]) -> None:
        """システム使用量情報が存在する場合に表示するヘルパー関数"""
        if 'system_df' in docker_info:
            print("   システム使用量:")
            for line in docker_info['system_df'].split('\n')[:4]:  # 最初の4行を表示
                if line.strip():
                    print(f"     {line}")

    def _print_workflows_if_exists(self, n8n_info: Dict[str, Union[str, int]]) -> None:
        """ワークフロー情報が存在する場合に表示するヘルパー関数"""
        if 'workflows' in n8n_info:
            workflows = n8n_info['workflows']
            print(f"   ワークフロー数: {workflows}")

    def _display_summary_status(self) -> None:
        """総合ステータスを表示するヘルパー関数"""
        print("\n" + "=" * 60)
        self._print_status_message()
        print("=" * 60)

    def _print_status_message(self) -> None:
        """現在のステータスに応じたメッセージを表示するヘルパー関数"""
        if self.docker_available and self.n8n_available:
            print("🎉 すべてのサービスが正常に動作しています")
        elif self.docker_available:
            print("⚠️  Dockerは動作中、n8nに問題があります")
        elif self.n8n_available:
            print("⚠️  n8nは動作中、Dockerに問題があります")
        else:
            print("❌ すべてのサービスに問題があります")

    def display_status(self):
        """現在の状態を表示"""
        print("\n" + "=" * 60)
        print(f"🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Docker状態チェック
        self.docker_available = self.check_docker_status()

        # n8n状態チェック
        self.n8n_available = self.check_n8n_status()

        # 詳細情報の表示
        self._display_info_if_available(self.docker_available, self._display_docker_info)
        self._display_info_if_available(self.n8n_available, self._display_n8n_info)

        # 総合ステータス
        self._display_summary_status()

    def _display_info_if_available(self, is_available: bool, display_func) -> None:
        """サービスが利用可能な場合に詳細情報を表示するヘルパー関数"""
        if is_available:
            display_func()

    def run_monitor(self):
        """監視を開始"""
        print("🚀 Docker & n8n 監視ツールを開始します")
        print("💡 ヒント:")
        print("   - Docker Desktopを起動してください")
        print("   - n8nを起動してください: docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n")
        print("   - Ctrl+Cで終了")

        try:
            while True:
                self.display_status()
                print(f"\n⏳ {self.check_interval}秒後に再チェック... (Ctrl+Cで終了)")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n👋 監視を終了しました")
        except Exception as e:
            print(f"\n❌ 予期しないエラー: {e}")
            print("監視を終了します")

def main():
    """メイン関数"""
    monitor = DockerN8nMonitor()
    monitor.run_monitor()

if __name__ == "__main__":
    main()
