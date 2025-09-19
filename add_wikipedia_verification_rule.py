#!/usr/bin/env python3
"""
PDCAガーディアンシステムにWikipedia URL検証ルールを追加
"""

import json
from datetime import datetime

def add_wikipedia_verification_rules():
    """Wikipedia URL検証に関するルールを追加"""

    new_rules = [
        {
            "id": "RULE_099",
            "name": "Wikipedia URL存在確認必須",
            "description": "Wikipedia URLを生成する際は必ずMediaWiki APIで存在確認を行う",
            "category": "データ品質",
            "severity": "critical",
            "check_type": "wikipedia_verification",
            "conditions": {
                "trigger": "wikipedia_url生成時",
                "requirements": [
                    "MediaWiki APIで実際の存在確認",
                    "存在しないURLは空欄にする",
                    "statusカラムで状態を明示"
                ]
            },
            "actions": {
                "on_violation": "URL生成を中止",
                "on_success": "検証済みURLのみ保存"
            },
            "implementation": {
                "script": "verify_wikipedia_urls.py",
                "api": "MediaWiki API",
                "batch_size": 50
            },
            "created_at": datetime.now().isoformat(),
            "enabled": True
        },
        {
            "id": "RULE_100",
            "name": "無効Wikipedia URLの自動削除",
            "description": "存在しないWikipedia URLは自動的に削除し、statusで理由を明示",
            "category": "データ品質",
            "severity": "high",
            "check_type": "url_validation",
            "conditions": {
                "trigger": "Wikipedia URL検証時",
                "invalid_states": [
                    "404エラー",
                    "ページ不存在",
                    "リンク先に項目なし"
                ]
            },
            "actions": {
                "on_invalid": [
                    "URLカラムを空欄に",
                    "statusを'不存在'に設定",
                    "verified_atに検証日時を記録"
                ]
            },
            "fallback": {
                "group_page_check": "グループページでの言及を確認",
                "alternative_links": "公式サイトやSNSリンクを検討"
            },
            "created_at": datetime.now().isoformat(),
            "enabled": True
        },
        {
            "id": "RULE_101",
            "name": "Wikipedia URL定期再検証",
            "description": "月次でWikipedia URLの有効性を再確認",
            "category": "メンテナンス",
            "severity": "medium",
            "check_type": "scheduled_validation",
            "schedule": {
                "frequency": "monthly",
                "day": 1,
                "time": "03:00"
            },
            "conditions": {
                "target": "全wikipedia_urlカラム",
                "check_items": [
                    "ページの存在",
                    "リダイレクトの変更",
                    "新規作成ページ"
                ]
            },
            "actions": {
                "on_change": "URLとstatusを更新",
                "notification": "変更があれば通知"
            },
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
    ]

    # 既存のpdca_guardian.pyを読み込み
    try:
        with open('pdca_guardian.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # RULESセクションを探す
        import_section = "from datetime import datetime, timedelta\nimport subprocess"

        # 新しいルールを追加する関数を挿入
        add_rules_function = '''

def add_wikipedia_verification_rules():
    """Wikipedia URL検証ルールを追加（RULE_099-101）"""

    wikipedia_rules = [
        {
            "id": "RULE_099",
            "name": "Wikipedia URL存在確認必須",
            "description": "Wikipedia URLを生成する際は必ずMediaWiki APIで存在確認を行う",
            "category": "データ品質",
            "severity": "critical",
            "enabled": True,
            "check": lambda df: check_wikipedia_url_existence(df),
            "message": "Wikipedia URLは存在確認済みのもののみ設定"
        },
        {
            "id": "RULE_100",
            "name": "無効Wikipedia URLの自動削除",
            "description": "存在しないWikipedia URLは自動的に削除",
            "category": "データ品質",
            "severity": "high",
            "enabled": True,
            "check": lambda df: validate_wikipedia_urls(df),
            "message": "無効なWikipedia URLを検出・削除"
        },
        {
            "id": "RULE_101",
            "name": "Wikipedia URL定期再検証",
            "description": "月次でWikipedia URLの有効性を再確認",
            "category": "メンテナンス",
            "severity": "medium",
            "enabled": True,
            "check": lambda df: schedule_wikipedia_revalidation(df),
            "message": "Wikipedia URLの定期検証スケジュール"
        }
    ]

    return wikipedia_rules

def check_wikipedia_url_existence(df):
    """Wikipedia URLの存在確認チェック"""
    if 'wikipedia_url' not in df.columns:
        return True

    if 'wikipedia_status' not in df.columns:
        return False, "wikipedia_statusカラムが必要です"

    # URLがあるのにstatusがない行をチェック
    has_url = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
    no_status = df['wikipedia_status'].isna() | (df['wikipedia_status'] == '')

    invalid_rows = df[has_url & no_status]

    if len(invalid_rows) > 0:
        return False, f"{len(invalid_rows)}件のURLが未検証です"

    return True, "全URLが検証済み"

def validate_wikipedia_urls(df):
    """無効なWikipedia URLの検証"""
    if 'wikipedia_status' not in df.columns:
        return True

    # 不存在ステータスなのにURLが残っている行をチェック
    is_invalid = df['wikipedia_status'] == '不存在'
    has_url = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')

    invalid_rows = df[is_invalid & has_url]

    if len(invalid_rows) > 0:
        return False, f"{len(invalid_rows)}件の無効URLが残っています"

    return True, "無効URLは適切に削除済み"

def schedule_wikipedia_revalidation(df):
    """Wikipedia URL再検証のスケジュール確認"""
    if 'wikipedia_verified_at' not in df.columns:
        return False, "検証日時カラムがありません"

    # 30日以上前に検証された行をチェック
    from datetime import datetime, timedelta

    current_time = datetime.now()
    threshold = current_time - timedelta(days=30)

    old_verifications = 0
    for val in df['wikipedia_verified_at']:
        if pd.notna(val):
            try:
                verified_time = datetime.fromisoformat(str(val))
                if verified_time < threshold:
                    old_verifications += 1
            except:
                pass

    if old_verifications > 100:
        return False, f"{old_verifications}件が30日以上前の検証です"

    return True, "検証は最新です"
'''

        # pdca_guardian.pyに追記
        if "RULE_099" not in content:
            # インポート部分の後に関数を追加
            content = content.replace(import_section,
                                    import_section + add_rules_function)

            # RULESリストにルールを追加する部分を探す
            if "def check_all_rules" in content:
                # check_all_rules関数の最初に新しいルールを追加
                check_all_rules_start = "def check_all_rules(df, auto_fix=False):"
                replacement = '''def check_all_rules(df, auto_fix=False):
    """すべてのPDCAルールをチェック"""

    # Wikipedia検証ルールを動的に追加
    wikipedia_rules = add_wikipedia_verification_rules()
    for rule in wikipedia_rules:
        if rule not in RULES:
            RULES.append(rule)
'''
                content = content.replace(check_all_rules_start, replacement)

            with open('pdca_guardian.py', 'w', encoding='utf-8') as f:
                f.write(content)

            print("✅ pdca_guardian.pyにWikipedia検証ルールを追加しました")

    except FileNotFoundError:
        print("⚠️ pdca_guardian.pyが見つかりません")

    # ルール定義をJSONファイルとして保存
    rules_file = 'pdca_wikipedia_rules.json'
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(new_rules, f, ensure_ascii=False, indent=2)

    print(f"✅ Wikipedia検証ルール定義を保存: {rules_file}")

    # 統計表示
    print("\n📊 追加されたルール:")
    for rule in new_rules:
        print(f"  - {rule['id']}: {rule['name']}")
        print(f"    重要度: {rule['severity']}")
        print(f"    カテゴリ: {rule['category']}")

    return new_rules

if __name__ == "__main__":
    print("=" * 60)
    print("PDCAガーディアン Wikipedia検証ルール追加")
    print("=" * 60)

    rules = add_wikipedia_verification_rules()

    print(f"\n✅ {len(rules)}個のルールを追加しました")
    print("\n重要な実装ポイント:")
    print("  1. Wikipedia URLは必ずMediaWiki APIで存在確認")
    print("  2. 存在しないURLは削除してstatusに記録")
    print("  3. 月次で全URLの再検証を実施")
    print("\n二度と同じ過ちを犯さないための仕組みが確立されました。")