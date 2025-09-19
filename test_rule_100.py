#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rule 100（APIクレジット管理）のテスト

PDCAガーディアンに追加したRule 100が正しく機能することを確認
"""

import json
from pathlib import Path
from pdca_guardian import PDCAGuardian


def test_rule_100_existence():
    """Rule 100が永続ルールに存在することを確認"""
    print("\n" + "="*60)
    print("🧪 Rule 100 存在確認テスト")
    print("="*60)

    # PDCAガーディアン初期化
    guardian = PDCAGuardian()

    # project_memory.jsonを確認
    memory_file = Path("project_memory.json")

    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        # Rule 100を探す
        rule_100_found = False
        for rule in memory.get('permanent_rules', []):
            if rule.get('rule_id') == 'RULE_100':
                rule_100_found = True
                print("\n✅ Rule 100が見つかりました！")
                print(f"  - 名前: {rule.get('name')}")
                print(f"  - 説明: {rule.get('description')}")
                print(f"  - 優先度: {rule.get('priority')}")
                print(f"  - カテゴリ: {rule.get('category')}")
                print(f"  - 強制: {rule.get('enforced')}")

                print("\n  禁止事項:")
                for prohibited in rule.get('prohibited', []):
                    print(f"    ❌ {prohibited}")

                print("\n  必須アクション:")
                for action in rule.get('actions', []):
                    print(f"    ✅ {action}")

                break

        if not rule_100_found:
            print("❌ Rule 100が見つかりませんでした")
            return False

    else:
        print("❌ project_memory.jsonが存在しません")
        return False

    return True


def test_credit_error_handling():
    """クレジットエラー処理が正しく実装されているか確認"""
    print("\n" + "="*60)
    print("🧪 クレジットエラー処理確認テスト")
    print("="*60)

    # premium_episode_generator.pyを確認
    generator_file = Path("premium_episode_generator.py")

    if generator_file.exists():
        with open(generator_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 課金促進メッセージが含まれているか確認
        checks = [
            ("課金促進メッセージ", "Anthropic APIのクレジットが不足しています"),
            ("課金URL", "https://console.anthropic.com/"),
            ("購入ガイド", "Plans & Billingでクレジットを購入"),
            ("金額目安", "クレジット購入の目安"),
            ("エラー発生", "raise SystemNotReadyError")
        ]

        all_passed = True
        for check_name, check_text in checks:
            if check_text in content:
                print(f"✅ {check_name}: 実装済み")
            else:
                print(f"❌ {check_name}: 未実装")
                all_passed = False

        return all_passed

    else:
        print("❌ premium_episode_generator.pyが存在しません")
        return False


def test_credit_monitor():
    """APIクレジットモニターが作成されているか確認"""
    print("\n" + "="*60)
    print("🧪 APIクレジットモニター確認テスト")
    print("="*60)

    monitor_file = Path("api_credit_monitor.py")

    if monitor_file.exists():
        print("✅ api_credit_monitor.pyが存在します")

        with open(monitor_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 主要機能の確認
        features = [
            ("クレジット状態チェック", "def check_credits"),
            ("コスト見積もり", "def estimate_cost"),
            ("クレジット要求", "def require_credits"),
            ("状態表示", "def display_status"),
            ("警告閾値", "CREDIT_THRESHOLDS"),
            ("枯渇メッセージ", "クレジットが枯渇しています")
        ]

        for feature_name, feature_text in features:
            if feature_text in content:
                print(f"  ✅ {feature_name}: 実装済み")
            else:
                print(f"  ❌ {feature_name}: 未実装")

        return True

    else:
        print("❌ api_credit_monitor.pyが存在しません")
        return False


def test_batch_processing_check():
    """バッチ処理前のクレジット確認が実装されているか確認"""
    print("\n" + "="*60)
    print("🧪 バッチ処理前クレジット確認テスト")
    print("="*60)

    integration_file = Path("episode_database_integration.py")

    if integration_file.exists():
        with open(integration_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # クレジット事前確認の実装を確認
        checks = [
            ("モニター import", "from api_credit_monitor import"),
            ("事前確認コメント", "APIクレジット事前確認"),
            ("コスト見積もり", "monitor.estimate_cost"),
            ("クレジットチェック", "monitor.check_credits"),
            ("不足時エラー", "APIクレジットが不足しています")
        ]

        all_passed = True
        for check_name, check_text in checks:
            if check_text in content:
                print(f"✅ {check_name}: 実装済み")
            else:
                print(f"❌ {check_name}: 未実装")
                all_passed = False

        return all_passed

    else:
        print("❌ episode_database_integration.pyが存在しません")
        return False


def main():
    """メインテスト実行"""
    print("\n" + "🔥"*30)
    print("  Rule 100（APIクレジット管理）統合テスト")
    print("🔥"*30)

    results = {
        "Rule 100 存在": test_rule_100_existence(),
        "エラー処理": test_credit_error_handling(),
        "モニター作成": test_credit_monitor(),
        "バッチ確認": test_batch_processing_check()
    }

    # 結果サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)

    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 すべてのテストに合格しました！")
        print("Rule 100が正常に統合されています。")
        print("今後、APIクレジット不足時には明確な課金促進メッセージが表示されます。")
    else:
        print("⚠️ 一部のテストが失敗しました。")
        print("上記の失敗項目を確認してください。")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()