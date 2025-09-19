#!/usr/bin/env python3
"""
APIキー自動ローダー
永続的なAPIキー管理システム

すべてのAPIキーを自動的に環境変数に設定し、
二度と同じキーについて質問しないようにする
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# APIキーディレクトリ
API_KEY_DIR = Path("/Users/admin/Documents/key")

# APIキーマッピング（ファイル名 -> 環境変数名）
API_KEY_MAPPING = {
    "serpapi_API.txt": "SERPAPI_API_KEY",
    "news_api.txt": "NEWS_API_KEY",
    "anthropic_api_key.txt": "ANTHROPIC_API_KEY",
    "openai_key.txt": "OPENAI_API_KEY",
    "Brave Search API Key.txt": "BRAVE_API_KEY",
    "youtube-analyzer-api-key.txt": "YOUTUBE_API_KEY",
    "GITHUB_PAT_key.txt": "GITHUB_TOKEN",
    "SonarQube_token_new.txt": "SONARQUBE_TOKEN",
    "LINEAR_API_KEY.txt": "LINEAR_API_KEY",
    "NOTION_API_KEY.txt": "NOTION_API_KEY",
    "SENTRY_AUTH_TOKEN.txt": "SENTRY_AUTH_TOKEN",
    "gemini-api-key.txt": "GEMINI_API_KEY",
    "APIDOG_API_KEY.txt": "APIDOG_API_KEY",
    "APIDOG_PROJECT_ID.txt": "APIDOG_PROJECT_ID",
    "n8n-key.txt": "N8N_API_KEY",
    "Twitter Access Token Access Token Secret.txt": "TWITTER_CREDENTIALS",
    "x-Access-Token.txt": "X_ACCESS_TOKEN",
    "x-Access-Token-Secret.txt": "X_ACCESS_TOKEN_SECRET"
}

# 永続的なレジストリファイル
REGISTRY_FILE = Path(__file__).parent.parent / "api_key_registry.json"


class APIKeyManager:
    """APIキー管理クラス"""
    
    def __init__(self):
        self.registry = self.load_registry()
        self.loaded_keys = {}
        
    def load_registry(self) -> Dict:
        """レジストリをロード"""
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "api_keys": {},
            "last_updated": None,
            "version": "1.0.0"
        }
    
    def save_registry(self):
        """レジストリを保存"""
        from datetime import datetime
        self.registry["last_updated"] = datetime.now().isoformat()
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ レジストリを保存しました: {REGISTRY_FILE}")
    
    def load_api_key(self, file_name: str, env_var: str) -> Optional[str]:
        """APIキーをファイルから読み込み"""
        file_path = API_KEY_DIR / file_name
        
        if not file_path.exists():
            logger.warning(f"⚠️ APIキーファイルが見つかりません: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Twitter認証の特殊処理
            if "Twitter" in file_name:
                lines = content.split('\n')
                access_token = None
                access_token_secret = None
                
                for i, line in enumerate(lines):
                    if "Access Token" in line and i + 1 < len(lines):
                        if "Secret" not in line:
                            access_token = lines[i + 1].strip()
                        else:
                            access_token_secret = lines[i + 1].strip()
                
                if access_token and access_token_secret:
                    os.environ["TWITTER_API_KEY"] = access_token
                    os.environ["TWITTER_API_SECRET"] = access_token_secret
                    self.loaded_keys["TWITTER_API_KEY"] = access_token
                    self.loaded_keys["TWITTER_API_SECRET"] = access_token_secret
                    logger.info(f"✅ Twitter認証情報を設定しました")
                    return f"{access_token},{access_token_secret}"
            else:
                # 通常のAPIキー
                api_key = content.split('\n')[0].strip()
                if api_key:
                    os.environ[env_var] = api_key
                    self.loaded_keys[env_var] = api_key
                    
                    # レジストリに記録
                    self.registry["api_keys"][env_var] = {
                        "file": str(file_path),
                        "loaded": True,
                        "env_var": env_var
                    }
                    
                    logger.info(f"✅ {env_var}: 設定完了")
                    return api_key
                    
        except Exception as e:
            logger.error(f"❌ {file_name}の読み込みエラー: {e}")
            
        return None
    
    def load_all_keys(self):
        """すべてのAPIキーをロード"""
        logger.info("="*60)
        logger.info("🔑 APIキー自動ローダー起動")
        logger.info("="*60)
        
        success_count = 0
        failed_count = 0
        
        for file_name, env_var in API_KEY_MAPPING.items():
            if self.load_api_key(file_name, env_var):
                success_count += 1
            else:
                failed_count += 1
        
        # レジストリを保存
        self.save_registry()
        
        # .envファイルも生成
        self.generate_env_file()
        
        logger.info("="*60)
        logger.info(f"📊 ロード結果")
        logger.info(f"  ✅ 成功: {success_count}個")
        logger.info(f"  ❌ 失敗: {failed_count}個")
        logger.info("="*60)
        
        return success_count, failed_count
    
    def generate_env_file(self):
        """プロジェクト用.envファイルを生成"""
        env_file = Path(__file__).parent.parent / ".env"
        
        env_content = []
        env_content.append("# APIキー設定 (自動生成)")
        env_content.append("# Generated by scripts/load_api_keys.py")
        env_content.append("")
        
        for env_var, value in self.loaded_keys.items():
            # APIキーの先頭と末尾だけ表示（セキュリティ対策）
            if len(value) > 10:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***"
            env_content.append(f"# {env_var}={masked}")
            env_content.append(f"{env_var}={value}")
            env_content.append("")
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_content))
        
        logger.info(f"✅ .envファイルを生成しました: {env_file}")
    
    def verify_keys(self):
        """キーの設定状況を確認"""
        logger.info("\n📋 APIキー設定状況:")
        
        critical_keys = [
            "SERPAPI_API_KEY",
            "NEWS_API_KEY", 
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY"
        ]
        
        for key in critical_keys:
            if os.getenv(key):
                logger.info(f"  ✅ {key}: 設定済み")
            else:
                logger.warning(f"  ❌ {key}: 未設定")
        
        optional_keys = [
            "BRAVE_API_KEY",
            "YOUTUBE_API_KEY",
            "TWITTER_API_KEY",
            "GITHUB_TOKEN"
        ]
        
        logger.info("\n📋 オプションAPIキー:")
        for key in optional_keys:
            if os.getenv(key):
                logger.info(f"  ✅ {key}: 設定済み")
            else:
                logger.info(f"  ⚠️ {key}: 未設定（オプション）")


def main():
    """メイン処理"""
    manager = APIKeyManager()
    
    # すべてのキーをロード
    success, failed = manager.load_all_keys()
    
    # 設定状況を確認
    manager.verify_keys()
    
    if success > 0:
        logger.info("\n✨ APIキーの設定が完了しました")
        logger.info("品質優先知名度評価システムを実行できます")
        return 0
    else:
        logger.error("\n❌ APIキーの設定に失敗しました")
        return 1


if __name__ == "__main__":
    exit(main())