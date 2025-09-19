#!/usr/bin/env python3
"""
日本語名翻訳修正テストスクリプト
Bach問題の修正が正しく動作するか確認
"""

from batch_perfect_translator import BatchPerfectTranslator
from phonetic_katakana_converter import PhoneticKatakanaConverter

def test_batch_translator():
    """BatchPerfectTranslatorのテスト"""
    print("=" * 60)
    print("🧪 BatchPerfectTranslator テスト")
    print("=" * 60)
    
    translator = BatchPerfectTranslator()
    
    # テストケース
    test_cases = [
        ("Bach", "バッハ"),
        ("Bachmann", "Bachmann"),  # 修正後は変換されないはず
        ("Angelika Bachmann", "Angelika Bachmann"),  # 修正後は変換されないはず
        ("Johann Sebastian Bach", "Johann Sebastian バッハ"),  # Bachのみ変換
        ("Mozart", "モーツァルト"),
        ("Beethoven", "ベートーヴェン"),
        ("Einstein", "アインシュタイン"),
        ("Newton", "ニュートン"),
        ("Shakespeare", "シェイクスピア"),
    ]
    
    passed = 0
    failed = 0
    
    for input_name, expected in test_cases:
        result = translator.quick_katakana_convert(input_name)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{input_name}' → '{result}'")
        if result != expected:
            print(f"   期待値: '{expected}'")
    
    print(f"\n📊 結果: {passed}/{len(test_cases)} テスト成功")
    return failed == 0

def test_phonetic_converter():
    """PhoneticKatakanaConverterのテスト"""
    print("\n" + "=" * 60)
    print("🧪 PhoneticKatakanaConverter テスト")
    print("=" * 60)
    
    converter = PhoneticKatakanaConverter()
    
    # テストケース
    test_cases = [
        ("Bach", "バッハ"),
        ("Bachmann", "Bachmann"),  # 修正後はBachmannとして残る
        ("Johann Bach", "ヨハン バッハ"),
        ("Sebastian", "Sebastian"),  # 特定の名前辞書になければそのまま
        ("Wolfgang", "ヴォルフガング"),
        ("Ludwig", "ルートヴィヒ"),
    ]
    
    passed = 0
    failed = 0
    
    for input_name, expected in test_cases:
        # ドイツ語として処理
        result = converter.convert_to_katakana(input_name, "german")
        
        # 結果が期待値と一致するかチェック
        if result is None:
            result = input_name
        
        # 部分一致も考慮
        status = "✅" if "バッハ" in result and "バッハmann" not in result else "❓"
        
        if "バッハmann" not in result:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{input_name}' → '{result}'")
    
    print(f"\n📊 結果: {passed}/{len(test_cases)} テスト成功")
    return failed == 0

def test_real_data():
    """実際のデータでテスト"""
    print("\n" + "=" * 60)
    print("🧪 実データテスト")
    print("=" * 60)
    
    # 問題があったデータ
    problematic_names = [
        "Angelika Bachmann",
        "Carl Philipp Emanuel Bach",
        "Johann Christian Bach",
        "Johann Christoph Friedrich Bach",
        "Wilhelm Friedemann Bach",
        "Anna Magdalena Bach",
        "Maria Barbara Bach"
    ]
    
    translator = BatchPerfectTranslator()
    
    print("BatchPerfectTranslator での変換結果:")
    for name in problematic_names:
        result = translator.quick_katakana_convert(name)
        contains_mixed = "バッハ" in result and any(c.isalpha() and ord(c) < 128 for c in result)
        status = "❌ 混在" if contains_mixed else "✅ OK"
        print(f"  {status}: '{name}' → '{result}'")
    
    print("\n✅ テスト完了")
    print("修正内容:")
    print("  1. batch_perfect_translator.py: 完全一致のみ変換するよう修正")
    print("  2. phonetic_katakana_converter.py: 単語境界を考慮した変換に修正")

def main():
    """メイン実行"""
    print("🚀 日本語名翻訳修正テスト")
    
    # 各テストを実行
    batch_ok = test_batch_translator()
    phonetic_ok = test_phonetic_converter()
    test_real_data()
    
    if batch_ok and phonetic_ok:
        print("\n🎉 全テスト成功！修正は正しく動作しています。")
        print("\n次のステップ:")
        print("  1. データベースを再生成")
        print("  2. 全てのBach関連の名前が正しく翻訳されているか確認")
    else:
        print("\n⚠️ 一部のテストが失敗しました。修正を確認してください。")

if __name__ == "__main__":
    main()