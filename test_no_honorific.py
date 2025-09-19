#!/usr/bin/env python3
"""
敬称なしの短縮名生成機能のテスト
"""

from japanese_name_shortener import JapaneseNameShortener, PersonInfo


def main():
    """メイン処理"""
    shortener = JapaneseNameShortener()

    # テストケース（エピソードデータ用）
    test_cases = [
        PersonInfo("安倍晋三", "政治家", 67, "male", "politics"),
        PersonInfo("山中伸弥", "科学者", 60, "male", "academia"),
        PersonInfo("三浦春馬", "俳優", 30, "male", "entertainment"),
        PersonInfo("大谷翔平", "野球選手", 29, "male", "sports"),
        PersonInfo("田中太郎", "会社員", 35, "male", "business"),
        PersonInfo("佐藤花子", "学生", 16, "female", "education"),
        PersonInfo("鈴木一郎", "医師", 45, "male", "medical"),
        PersonInfo("高橋美咲", "歌手", 25, "female", "entertainment"),
        PersonInfo("伊藤健太", "小学生", 10, "male", "education"),
        PersonInfo("渡辺真理", "作家", 55, "female", "arts")
    ]

    print("=== 敬称あり vs 敬称なし 比較テスト ===")
    print()

    for person in test_cases:
        # 敬称ありの短縮名
        with_honorific = shortener.generate_short_name(person)

        # 敬称なしの短縮名
        without_honorific = shortener.generate_short_name_no_honorific(person)

        print(f"名前: {person.name}")
        print(f"職業: {person.occupation or '不明'}")
        print(f"敬称あり: {with_honorific}")
        print(f"敬称なし: {without_honorific}")
        print("-" * 40)

    # 一括処理のテスト
    print("\n=== 敬称なし一括処理テスト ===")
    batch_results = shortener.generate_short_name_batch_no_honorific(test_cases)

    for original, short in batch_results:
        print(f"{original} → {short}")

    print("\n🔤 エピソードデータでは敬称なしの名前表示が適用されます")

if __name__ == "__main__":
    main()
