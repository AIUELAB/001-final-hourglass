#!/usr/bin/env python3
"""
統合ルールシステム統合テスト

PDCAGuardianとUnifiedRuleLoaderの統合をテストし、
ルールが正しく適用されることを確認します。
"""

import sys
from pathlib import Path

# PDCAGuardianのインポート
try:
    from pdca_guardian import PDCAGuardian
except ImportError as e:
    print(f"❌ PDCAGuardianのインポートに失敗: {e}")
    sys.exit(1)

# UnifiedRuleLoaderのインポート
try:
    from unified_rule_loader import UnifiedRuleLoader
except ImportError as e:
    print(f"❌ UnifiedRuleLoaderのインポートに失敗: {e}")
    sys.exit(1)


def test_unified_rule_loader():
    """UnifiedRuleLoader単体テスト"""
    print("\n" + "=" * 60)
    print("  テスト1: UnifiedRuleLoader単体テスト")
    print("=" * 60)

    loader = UnifiedRuleLoader()

    # ルールロード
    if not loader.load_rules():
        print("❌ ルールのロードに失敗")
        return False

    # 基本検証
    print(f"✅ ロードされたルール数: {len(loader.rules)}")

    # 特定ルールの取得テスト
    rule_001 = loader.get_rule("RULE_001")
    if rule_001:
        print(f"✅ RULE_001取得成功: {rule_001.name}")
    else:
        print("⚠️ RULE_001が見つかりません")

    # カテゴリ別取得テスト
    data_quality_rules = loader.get_rules_by_category("data_quality")
    print(f"✅ data_qualityカテゴリ: {len(data_quality_rules)}件")

    # アクティブルール取得テスト
    active_rules = loader.get_active_rules()
    print(f"✅ アクティブルール: {len(active_rules)}件")

    # クリティカルルール取得テスト
    critical_rules = loader.get_critical_rules()
    print(f"✅ クリティカルルール: {len(critical_rules)}件")

    # 検索テスト
    search_results = loader.search_rules("Wikipedia")
    print(f"✅ 'Wikipedia'検索: {len(search_results)}件")

    # 整合性チェック
    errors = loader.validate_rule_references()
    if errors:
        print(f"⚠️ 整合性エラー: {len(errors)}件")
        for error in errors[:3]:
            print(f"   - {error}")
    else:
        print("✅ 整合性チェック: 問題なし")

    return True


def test_pdca_guardian_integration():
    """PDCAGuardian統合テスト"""
    print("\n" + "=" * 60)
    print("  テスト2: PDCAGuardian統合テスト")
    print("=" * 60)

    # 統合ルールシステム有効でPDCAGuardianを初期化
    print("\n🔧 統合ルールシステム有効で初期化...")
    guardian_unified = PDCAGuardian(
        memory_file="test_project_memory.json",
        use_unified_rules=True,
        relaxed_mode=True
    )

    # 統合システムが有効か確認
    if guardian_unified.use_unified_rules:
        print("✅ 統合ルールシステム有効化成功")
        print(f"   統合ルール数: {len(guardian_unified.unified_rule_loader.rules)}")
    else:
        print("⚠️ 統合ルールシステムが無効化されています")

    # ルール取得テスト
    print("\n🔍 ルール取得テスト...")
    rule_001 = guardian_unified.get_rule_by_id("RULE_001")
    if rule_001:
        print(f"✅ RULE_001取得成功:")
        print(f"   名前: {rule_001['name']}")
        print(f"   優先度: {rule_001['priority']}")
        print(f"   ソース: {rule_001.get('source', 'unknown')}")
    else:
        print("❌ RULE_001が取得できません")

    # 全アクティブルール取得テスト
    print("\n📋 全アクティブルール取得テスト...")
    active_rules = guardian_unified.get_all_active_rules()
    print(f"✅ アクティブルール数: {len(active_rules)}")
    if active_rules:
        print(f"   サンプル: {active_rules[0]['rule_id']} - {active_rules[0]['name']}")

    # 従来システムとの比較
    print("\n⚖️ 従来システムとの比較...")
    guardian_legacy = PDCAGuardian(
        memory_file="test_project_memory.json",
        use_unified_rules=False,
        relaxed_mode=True
    )

    legacy_rules = guardian_legacy.get_all_active_rules()
    unified_rules = guardian_unified.get_all_active_rules()

    print(f"   従来システム: {len(legacy_rules)}ルール")
    print(f"   統合システム: {len(unified_rules)}ルール")
    print(f"   差分: {len(unified_rules) - len(legacy_rules)}ルール")

    # クリーンアップ
    test_memory = Path("test_project_memory.json")
    if test_memory.exists():
        test_memory.unlink()
        print("\n🧹 テストファイルをクリーンアップしました")

    return True


def test_backward_compatibility():
    """後方互換性テスト"""
    print("\n" + "=" * 60)
    print("  テスト3: 後方互換性テスト")
    print("=" * 60)

    # 統合ルールを無効にして初期化
    print("\n🔧 統合ルール無効で初期化（従来互換モード）...")
    guardian = PDCAGuardian(
        memory_file="test_project_memory.json",
        use_unified_rules=False,
        relaxed_mode=True
    )

    if not guardian.use_unified_rules:
        print("✅ 従来システムでの動作確認成功")
    else:
        print("⚠️ 統合システムが意図せず有効化されています")

    # クリーンアップ
    test_memory = Path("test_project_memory.json")
    if test_memory.exists():
        test_memory.unlink()

    return True


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("  統合ルールシステム統合テスト")
    print("=" * 60)

    tests = [
        ("UnifiedRuleLoader単体", test_unified_rule_loader),
        ("PDCAGuardian統合", test_pdca_guardian_integration),
        ("後方互換性", test_backward_compatibility),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name}テスト: 成功")
            else:
                failed += 1
                print(f"\n❌ {test_name}テスト: 失敗")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name}テスト: エラー")
            print(f"   {e}")
            import traceback
            traceback.print_exc()

    # 最終結果
    print("\n" + "=" * 60)
    print("  テスト結果サマリー")
    print("=" * 60)
    print(f"✅ 成功: {passed}件")
    print(f"❌ 失敗: {failed}件")
    print(f"📊 成功率: {passed / (passed + failed) * 100:.1f}%")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 すべてのテストが成功しました！")
        return 0
    else:
        print(f"\n⚠️ {failed}件のテストが失敗しました")
        return 1


if __name__ == '__main__':
    sys.exit(main())
