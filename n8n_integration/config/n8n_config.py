"""
n8n統合システム設定

このファイルは、n8n統合システムの設定を管理します。
環境変数や設定ファイルから設定を読み込み、システム全体で使用できるようにします。
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

class N8nConfig:
    """n8n設定管理クラス"""

    def __init__(self):
        """設定を初期化"""
        self.load_config()

    def load_config(self):
        """設定を読み込み"""
        # 基本設定
        self.base_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
        self.api_key = os.getenv('N8N_API_KEY')
        self.timeout = int(os.getenv('N8N_TIMEOUT', '30'))
        self.retry_attempts = int(os.getenv('N8N_RETRY_ATTEMPTS', '3'))

        # セキュリティ設定
        self.verify_ssl = os.getenv('N8N_VERIFY_SSL', 'true').lower() == 'true'
        self.allow_insecure = os.getenv('N8N_ALLOW_INSECURE', 'false').lower() == 'true'

        # ログ設定
        self.log_level = os.getenv('N8N_LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('N8N_LOG_FILE', 'logs/n8n.log')

        # 監視設定
        self.monitoring_interval = int(os.getenv('N8N_MONITORING_INTERVAL', '10'))
        self.health_check_interval = int(os.getenv('N8N_HEALTH_CHECK_INTERVAL', '60'))

        # キャッシュ設定
        self.cache_enabled = os.getenv('N8N_CACHE_ENABLED', 'true').lower() == 'true'
        self.cache_ttl = int(os.getenv('N8N_CACHE_TTL', '300'))

        # 通知設定
        self.notifications_enabled = os.getenv('N8N_NOTIFICATIONS_ENABLED', 'false').lower() == 'true'
        self.slack_webhook = os.getenv('N8N_SLACK_WEBHOOK')
        self.email_notifications = os.getenv('N8N_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'

        # データベース設定
        self.db_enabled = os.getenv('N8N_DB_ENABLED', 'false').lower() == 'true'
        self.db_url = os.getenv('N8N_DB_URL', 'sqlite:///n8n_integration.db')

        # 認証設定
        self.auth_enabled = os.getenv('N8N_AUTH_ENABLED', 'false').lower() == 'true'
        self.jwt_secret = os.getenv('N8N_JWT_SECRET')
        self.session_timeout = int(os.getenv('N8N_SESSION_TIMEOUT', '3600'))

    def get_api_config(self) -> Dict[str, Any]:
        """API設定を取得"""
        return {
            'base_url': self.base_url,
            'api_key': self.api_key,
            'timeout': self.timeout,
            'retry_attempts': self.retry_attempts,
            'verify_ssl': self.verify_ssl,
            'allow_insecure': self.allow_insecure
        }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """監視設定を取得"""
        return {
            'monitoring_interval': self.monitoring_interval,
            'health_check_interval': self.health_check_interval,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl
        }

    def get_notification_config(self) -> Dict[str, Any]:
        """通知設定を取得"""
        return {
            'notifications_enabled': self.notifications_enabled,
            'slack_webhook': self.slack_webhook,
            'email_notifications': self.email_notifications
        }

    def get_database_config(self) -> Dict[str, Any]:
        """データベース設定を取得"""
        return {
            'db_enabled': self.db_enabled,
            'db_url': self.db_url
        }

    def get_auth_config(self) -> Dict[str, Any]:
        """認証設定を取得"""
        return {
            'auth_enabled': self.auth_enabled,
            'jwt_secret': self.jwt_secret,
            'session_timeout': self.session_timeout
        }

    def validate_config(self) -> bool:
        """設定の妥当性を検証"""
        errors = []

        # 必須設定のチェック
        if not self.base_url:
            errors.append("N8N_BASE_URLが設定されていません")

        if self.api_key and len(self.api_key) < 10:
            errors.append("N8N_API_KEYが短すぎます（最低10文字必要）")

        if self.timeout < 1 or self.timeout > 300:
            errors.append("N8N_TIMEOUTは1-300の範囲で設定してください")

        if self.monitoring_interval < 1 or self.monitoring_interval > 3600:
            errors.append("N8N_MONITORING_INTERVALは1-3600の範囲で設定してください")

        # セキュリティ設定のチェック
        if self.allow_insecure and self.verify_ssl:
            errors.append("N8N_ALLOW_INSECUREとN8N_VERIFY_SSLは同時に有効にできません")

        # 通知設定のチェック
        if self.notifications_enabled and not self.slack_webhook and not self.email_notifications:
            errors.append("通知が有効ですが、通知方法が設定されていません")

        # データベース設定のチェック
        if self.db_enabled and not self.db_url:
            errors.append("データベースが有効ですが、DB_URLが設定されていません")

        # 認証設定のチェック
        if self.auth_enabled and not self.jwt_secret:
            errors.append("認証が有効ですが、JWT_SECRETが設定されていません")

        if errors:
            print("設定エラー:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def print_config(self):
        """設定を表示"""
        print("n8n統合システム設定:")
        print("=" * 40)

        print(f"基本設定:")
        print(f"  - ベースURL: {self.base_url}")
        print(f"  - APIキー: {'設定済み' if self.api_key else '未設定'}")
        print(f"  - タイムアウト: {self.timeout}秒")
        print(f"  - リトライ回数: {self.retry_attempts}回")

        print(f"\nセキュリティ設定:")
        print(f"  - SSL検証: {'有効' if self.verify_ssl else '無効'}")
        print(f"  - 非セキュア許可: {'有効' if self.allow_insecure else '無効'}")

        print(f"\nログ設定:")
        print(f"  - ログレベル: {self.log_level}")
        print(f"  - ログファイル: {self.log_file}")

        print(f"\n監視設定:")
        print(f"  - 監視間隔: {self.monitoring_interval}秒")
        print(f"  - ヘルスチェック間隔: {self.health_check_interval}秒")
        print(f"  - キャッシュ: {'有効' if self.cache_enabled else '無効'}")
        print(f"  - キャッシュTTL: {self.cache_ttl}秒")

        print(f"\n通知設定:")
        print(f"  - 通知: {'有効' if self.notifications_enabled else '無効'}")
        print(f"  - Slack: {'設定済み' if self.slack_webhook else '未設定'}")
        print(f"  - メール: {'有効' if self.email_notifications else '無効'}")

        print(f"\nデータベース設定:")
        print(f"  - データベース: {'有効' if self.db_enabled else '無効'}")
        print(f"  - DB URL: {self.db_url}")

        print(f"\n認証設定:")
        print(f"  - 認証: {'有効' if self.auth_enabled else '無効'}")
        print(f"  - JWT秘密鍵: {'設定済み' if self.jwt_secret else '未設定'}")
        print(f"  - セッションタイムアウト: {self.session_timeout}秒")

# 設定インスタンス
config = N8nConfig()

# 環境変数の例
ENV_EXAMPLES = """
# n8n統合システム環境変数設定例

# 基本設定
export N8N_BASE_URL="http://localhost:5678"
export N8N_API_KEY="your_api_key_here"
export N8N_TIMEOUT="30"
export N8N_RETRY_ATTEMPTS="3"

# セキュリティ設定
export N8N_VERIFY_SSL="true"
export N8N_ALLOW_INSECURE="false"

# ログ設定
export N8N_LOG_LEVEL="INFO"
export N8N_LOG_FILE="logs/n8n.log"

# 監視設定
export N8N_MONITORING_INTERVAL="10"
export N8N_HEALTH_CHECK_INTERVAL="60"
export N8N_CACHE_ENABLED="true"
export N8N_CACHE_TTL="300"

# 通知設定
export N8N_NOTIFICATIONS_ENABLED="true"
export N8N_SLACK_WEBHOOK="https://hooks.slack.com/services/..."
export N8N_EMAIL_NOTIFICATIONS="false"

# データベース設定
export N8N_DB_ENABLED="false"
export N8N_DB_URL="sqlite:///n8n_integration.db"

# 認証設定
export N8N_AUTH_ENABLED="false"
export N8N_JWT_SECRET="your_jwt_secret_here"
export N8N_SESSION_TIMEOUT="3600"
"""

if __name__ == "__main__":
    # 設定を表示
    config.print_config()

    # 設定の妥当性を検証
    if config.validate_config():
        print("\n✅ 設定は正常です")
    else:
        print("\n❌ 設定に問題があります")

    # 環境変数の例を表示
    print(f"\n環境変数設定例:")
    print(ENV_EXAMPLES)
