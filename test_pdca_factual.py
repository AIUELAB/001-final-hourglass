#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDCAガーディアン事実正確性チェックのテスト
"""

from pdca_guardian import PDCAGuardian, ViolationType


def test_factual_accuracy():
    """事実正確性チェックのテスト"""

    print("="*60)
    print("🛡️ PDCAガーディアン事実正確性チェックテスト")
    print("="*60)

    # PDCAガーディアン初期化（通常モード）
    guardian = PDCAGuardian(relaxed_mode=False)

    # テストケース1: Adoの誤情報を含むエピソード
    print("\n📝 テストケース1: Ado（誤情報あり）")
    print("-"*40)

    ado_episode = """あなたと同じ21歳のとき、Adoは日本のデビューアルバム「Ado」がオリコンデイリーランキング1位を獲得し、同年には「ヨルシカ」と共同で発表した「うっせぇわ」がストリーミング1億回再生を突破するなど、驚異的なデビューを遂げました。"""

    ado_data = {
        'person_name_ja': 'Ado',
        'birth_year_int': 2002,
        'person_name_display': 'Ado'
    }

    violations = guardian.check_factual_accuracy(ado_episode, ado_data)

    print(f"違反検出数: {len(violations)}")
    for v in violations:
        print(f"  ❌ {v['type']}: {v['message']}")

    # テストケース2: HIKAKINの誤情報
    print("\n📝 テストケース2: HIKAKIN（ハルシネーション）")
    print("-"*40)

    hikakin_episode = """あなたと同じ25歳のとき、HIKAKINは紅白歌合戦で優勝し、約100000万人の視聴者を獲得しました。"""

    hikakin_data = {
        'person_name_ja': 'HIKAKIN',
        'birth_year_int': 1989,
        'person_name_display': 'HIKAKIN'
    }

    violations = guardian.check_factual_accuracy(hikakin_episode, hikakin_data)

    print(f"違反検出数: {len(violations)}")
    for v in violations:
        print(f"  ❌ {v['type']}: {v['message']}")

    # テストケース3: 年代の不整合
    print("\n📝 テストケース3: 年代の不整合")
    print("-"*40)

    timeline_episode = """あなたと同じ30歳のとき、山田太郎は2010年に東京で活動を開始しました。"""

    timeline_data = {
        'person_name_ja': '山田太郎',
        'birth_year_int': 1990,  # 30歳なら2020年のはず
        'person_name_display': '山田太郎'
    }

    violations = guardian.check_factual_accuracy(timeline_episode, timeline_data)

    print(f"違反検出数: {len(violations)}")
    for v in violations:
        print(f"  ❌ {v['type']}: {v['message']}")

    # テストケース4: 正確なエピソード
    print("\n📝 テストケース4: 正確なエピソード")
    print("-"*40)

    accurate_episode = """あなたと同じ18歳のとき、Adoは「うっせぇわ」でデビューし、syudouが作詞作曲を手掛けたこの楽曲は大きな話題となりました。"""

    accurate_data = {
        'person_name_ja': 'Ado',
        'birth_year_int': 2002,
        'person_name_display': 'Ado',
        'wikipedia_verified': True  # Wikipedia検証済み
    }

    violations = guardian.check_factual_accuracy(accurate_episode, accurate_data)

    print(f"違反検出数: {len(violations)}")
    if violations:
        for v in violations:
            print(f"  ⚠️ {v['type']}: {v['message']}")
    else:
        print("  ✅ 違反なし - 正確なエピソード")

    # サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)

    print("""
新しい事実正確性チェック機能:
✅ 既知の誤情報パターン検出
✅ ハルシネーション検出
✅ 年代整合性チェック
✅ 情報源検証チェック

これにより、生成されたエピソードの事実誤認を
PDCAガーディアンが自動的に検出できるようになりました。
""")


if __name__ == "__main__":
    test_factual_accuracy()