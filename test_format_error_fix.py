#!/usr/bin/env python3
"""
修正されたFORMAT_ERRORチェックロジックのテスト
"""

from pdca_guardian import PDCAGuardian

# テストケース
test_cases = [
    {
        'name': '山中伸弥',
        'age': 50,
        'episode': '実はあなたと同じ50歳のとき、山中伸弥は長年の研究努力が実を結び、iPS細胞（人工多能性幹細胞）の作製に成功しました。'
    },
    {
        'name': 'イチロー',
        'age': 45,
        'episode': '実はあなたと同じ45歳のとき、イチローは史上最年長での日米通算4,367安打達成、世界記録を樹立しました。'
    },
    {
        'name': '羽生結弦',
        'age': 23,
        'episode': 'あなたと同じ23歳のとき、羽生結弦は2018年平昌オリンピックで金メダルを獲得しました。'
    },
    {
        'name': 'HIKAKIN',
        'age': 24,
        'episode': '実はあなたと同じ24歳のとき、HIKAKINはYouTubeチャンネル登録者数100万人を突破しました。'
    }
]

# PDCAガーディアンでテスト
guardian = PDCAGuardian()

print("=" * 60)
print("FORMAT_ERROR修正テスト")
print("=" * 60)

for i, case in enumerate(test_cases, 1):
    person_name = case['name']
    age = case['age']
    episode = case['episode']
    person_name_display = f"{person_name}（{age}歳）"

    print(f"\nテスト{i}: {person_name_display}")
    print(f"エピソード開始: {episode[:50]}...")

    # 違反チェック
    violations = guardian.check_episode_quality(
        episode_text=episode,
        age=age,
        person_name_display=person_name_display
    )

    # FORMAT_ERRORがあるか確認
    format_errors = [v for v in violations if v.get('type') == 'FORMAT_ERROR']

    if format_errors:
        print(f"❌ FORMAT_ERROR検出: {format_errors[0].get('message')}")
    else:
        print("✅ FORMAT_ERROR解消！")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)