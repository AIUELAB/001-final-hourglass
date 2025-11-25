from src.secure_config import config
#!/usr/bin/env python3
"""
Google Drive容量チェックツール
"""

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

def check_drive_space():
    """Driveの容量を確認"""
    try:
        # 認証
        SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
        credentials = Credentials.from_service_account_file(
            config.google_credentials_path, scopes=SCOPES
        )

        # Drive APIクライアント作成
        service = build('drive', 'v3', credentials=credentials)

        # About情報を取得
        about = service.about().get(fields="storageQuota").execute()

        quota = about.get('storageQuota', {})

        # 容量情報を表示
        total = int(quota.get('limit', 0))
        used = int(quota.get('usage', 0))

        if total > 0:
            remaining = total - used
            percentage = (used / total) * 100

            print(f"📊 Google Drive容量情報")
            print(f"━━━━━━━━━━━━━━━━━━━━")
            print(f"総容量: {total / (1024**3):.2f} GB")
            print(f"使用量: {used / (1024**3):.2f} GB")
            print(f"空き容量: {remaining / (1024**3):.2f} GB")
            print(f"使用率: {percentage:.1f}%")
        else:
            print("サービスアカウントには容量制限がありません")

    except Exception as e:
        print(f"エラー: {e}")
        print("\nサービスアカウントを使用している場合、")
        print("個人のGoogleドライブとは別の容量が割り当てられます。")

if __name__ == "__main__":
    check_drive_space()
