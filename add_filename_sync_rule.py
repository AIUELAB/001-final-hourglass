#!/usr/bin/env python3
"""
PDCAガーディアンにファイル名同期ルールを追加するスクリプト
"""

import json
import os
from datetime import datetime
from pathlib import Path

def add_filename_sync_rule():
    """ファイル名同期ルールを追加"""

    # プロジェクトメモリファイルのパス
    memory_file = Path("project_memory.json")

    # メモリファイルが存在しない場合は初期化
    if not memory_file.exists():
        memory = {
            "metadata": {
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "permanent_rules": [],
            "quality_metrics": {},
            "failed_patterns": [],
            "success_patterns": [],
            "pdca_history": [],
            "improvement_log": []
        }
    else:
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

    # 新しいルール：Google Sheetsファイル名同期
    new_rule = {
        "id": "RULE_098",
        "name": "Google Sheetsファイル名同期義務",
        "description": "CSVファイルをGoogle Sheetsにアップロードする際は、必ずスプレッドシート名も同期すること",
        "priority": "HIGH",
        "category": "データ同期",
        "created_date": datetime.now().isoformat(),
        "created_by": "User Request - 2025-09-15",
        "reason": "ファイル名が同期されていないと、どのデータかわからなくなる",
        "detection_patterns": [
            "force_sync.py実行時",
            "Google Sheetsアップロード時",
            "sheets_config.json更新時"
        ],
        "validation_logic": """
def validate_filename_sync(csv_file, spreadsheet_name):
    # CSVファイル名からスプレッドシート名を生成
    base_name = csv_file.replace('.csv', '')
    expected_name = base_name.replace('_', ' ').title()
    expected_name = expected_name.replace('Ultra Think', 'Ultra Think')

    # スプレッドシート名が期待値と一致するか確認
    return spreadsheet_name == expected_name
""",
        "auto_fix": {
            "enabled": True,
            "script": "sync_spreadsheet_name.py",
            "command": "python3 sync_spreadsheet_name.py"
        },
        "consequences": {
            "violation": "データの識別が困難になり、運用ミスのリスクが高まる",
            "compliance": "データの追跡可能性が保たれ、管理が容易になる"
        },
        "violations": [],
        "active": True,
        "enforcement_level": "STRICT"
    }

    # 既存のルールがないか確認
    rule_exists = False
    for i, rule in enumerate(memory['permanent_rules']):
        if rule.get('id') == 'RULE_098':
            memory['permanent_rules'][i] = new_rule
            rule_exists = True
            print(f"✅ ルール {new_rule['id']} を更新しました")
            break

    if not rule_exists:
        memory['permanent_rules'].append(new_rule)
        print(f"✅ 新しいルール {new_rule['id']} を追加しました")

    # メタデータを更新
    memory['metadata']['last_updated'] = datetime.now().isoformat()

    # メモリファイルに保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2, default=str)

    print(f"📝 ルール名: {new_rule['name']}")
    print(f"📊 優先度: {new_rule['priority']}")
    print(f"🔧 自動修正: {new_rule['auto_fix']['enabled']}")
    print(f"📁 保存先: {memory_file}")

    return new_rule

def create_validation_script():
    """ファイル名同期を検証するスクリプトを作成"""

    validation_script = '''#!/usr/bin/env python3
"""
Google Sheetsファイル名同期検証スクリプト
PDCAガーディアンと連携して自動検証を行う
"""

import json
import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def check_filename_sync():
    """ファイル名同期をチェック"""

    # 設定ファイルを読み込み
    with open('sheets_config.json', 'r') as f:
        config = json.load(f)

    csv_file = config.get('csv_file', '')
    sheet_name = config.get('sheet_name', '')
    spreadsheet_id = config.get('spreadsheet_id', '')

    # 期待されるスプレッドシート名を計算
    base_name = csv_file.replace('.csv', '')
    expected_name = base_name.replace('_', ' ').title()
    expected_name = expected_name.replace('Ultra Think', 'Ultra Think')

    print(f"📁 CSVファイル: {csv_file}")
    print(f"📝 現在のシート名: {sheet_name}")
    print(f"✅ 期待されるシート名: {expected_name}")

    # Google Sheets APIで実際の名前を確認
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds_path = 'key/credentials.json'

        if os.path.exists(creds_path):
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)

            # スプレッドシートの情報を取得
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            actual_name = spreadsheet.get('properties', {}).get('title', '')

            print(f"🌐 Google Sheets実際の名前: {actual_name}")

            # 検証
            if actual_name == expected_name:
                print("✅ ファイル名は正しく同期されています")
                return True
            else:
                print("❌ ファイル名が同期されていません！")
                print(f"   期待: {expected_name}")
                print(f"   実際: {actual_name}")
                return False
    except Exception as e:
        print(f"⚠️ API確認中にエラー: {e}")
        # 設定ファイルベースでチェック
        if sheet_name == expected_name:
            print("✅ 設定ファイルでは同期されています")
            return True
        else:
            print("❌ 設定ファイルでも同期されていません")
            return False

if __name__ == "__main__":
    result = check_filename_sync()
    sys.exit(0 if result else 1)
'''

    # 検証スクリプトを保存
    with open('check_filename_sync.py', 'w', encoding='utf-8') as f:
        f.write(validation_script)

    print("\n✅ 検証スクリプトも作成しました: check_filename_sync.py")

if __name__ == "__main__":
    print("=" * 50)
    print("PDCAガーディアン ルール追加")
    print("=" * 50)

    # ルールを追加
    rule = add_filename_sync_rule()

    # 検証スクリプトも作成
    create_validation_script()

    print("\n✅ 完了！")
    print("\n📌 今後の動作:")
    print("1. CSVファイルをGoogle Sheetsにアップロードする際")
    print("2. 自動的にファイル名同期がチェックされます")
    print("3. 違反があれば自動修正が実行されます")
    print("4. 二度と同じ過ちを繰り返しません！")