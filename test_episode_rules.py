#!/usr/bin/env python3
"""
エピソードルールのテストスクリプト
PDCAガーディアンシステムのエピソード品質チェック機能をテスト
"""

from pdca_guardian import PDCAGuardian
import json

def test_episode_rules():
    """エピソードルールをテスト"""

    guardian = PDCAGuardian()

    print("="*60)
    print("📚 エピソードルール検証テスト")
    print("="*60)

    # テストケース1: 良いエピソード
    good_episode = {
        'text': "あなたと同じ20歳のとき、大谷翔平は日本ハムファイターズでプロ2年目を迎え、投手として10勝、打者として打率.238を記録。二刀流への挑戦が本格化し、「投げては160km/h、打っては特大ホームラン」と話題になりました。この年の経験が、後のメジャーリーグでの活躍の基礎となりました。",
        'age': 20,
        'person_name_display': '大谷翔平'
    }

    print("\n✅ 良いエピソードの例:")
    print(f"エピソード: {good_episode['text'][:100]}...")
    violations = guardian.check_episode_quality(
        good_episode['text'],
        good_episode['age'],
        good_episode['person_name_display']
    )

    if not violations:
        print("→ 違反なし！品質基準を満たしています")
    else:
        print("→ 違反あり:")
        for v in violations:
            print(f"  - {v['type'].value}: {v['message']}")

    # スコア計算
    score_data = guardian.calculate_episode_score(good_episode['text'], good_episode['age'])
    print(f"→ スコア: {score_data['total_score']}点 (グレード: {score_data['grade']})")
    print(f"  詳細: {json.dumps(score_data['scores'], ensure_ascii=False, indent=2)}")

    # テストケース2: 悪いエピソード（年齢重複）
    bad_episode_age = {
        'text': "あなたと同じ30歳のとき、HIKAKINは30歳でYouTubeチャンネル登録者数が500万人を突破しました。",
        'age': 30,
        'person_name_display': 'HIKAKIN'
    }

    print("\n❌ 悪いエピソードの例（年齢重複）:")
    print(f"エピソード: {bad_episode_age['text']}")
    violations = guardian.check_episode_quality(
        bad_episode_age['text'],
        bad_episode_age['age'],
        bad_episode_age['person_name_display']
    )

    if violations:
        print("→ 違反検出:")
        for v in violations:
            print(f"  - [{v['severity']}] {v['type'].value}: {v['message']}")

    # テストケース3: 悪いエピソード（具体性不足）
    bad_episode_vague = {
        'text': "あなたと同じ40歳のとき、田中さんは仕事を頑張っていました。とても充実した日々でした。",
        'age': 40,
        'person_name_display': '田中'
    }

    print("\n❌ 悪いエピソードの例（具体性不足）:")
    print(f"エピソード: {bad_episode_vague['text']}")
    violations = guardian.check_episode_quality(
        bad_episode_vague['text'],
        bad_episode_vague['age'],
        bad_episode_vague['person_name_display']
    )

    if violations:
        print("→ 違反検出:")
        for v in violations:
            print(f"  - [{v['severity']}] {v['type'].value}: {v['message']}")

    score_data = guardian.calculate_episode_score(bad_episode_vague['text'], bad_episode_vague['age'])
    print(f"→ スコア: {score_data['total_score']}点 (グレード: {score_data['grade']})")

    # テストケース4: エピソード生成検証
    print("\n📋 エピソード生成検証テスト:")

    person_data = {
        'person_name_display': 'イチロー',
        'person_id': 'P00001'
    }

    # 7つのエピソード（各年齢用）
    episodes = [
        "あなたと同じ1歳のとき、イチローは愛知県で生まれ、両親に愛情深く育てられました。",
        "あなたと同じ10歳のとき、イチローは地元の少年野球チームで4番打者として活躍し、「天才少年」と呼ばれました。",
        "あなたと同じ20歳のとき、イチローはオリックスで初の200安打を達成し、史上最年少での偉業を成し遂げました。",
        "あなたと同じ30歳のとき、イチローはメジャーリーグで年間262安打の新記録を樹立し、世界を驚かせました。",
        "あなたと同じ40歳のとき、イチローは日米通算4000安打を達成し、歴史に名を刻みました。",
        "あなたと同じ50歳のとき、イチローは現役を引退し、マリナーズの殿堂入りが決定しました。",
        "あなたと同じ60歳のとき、イチローは野球の普及活動に尽力し、次世代の育成に情熱を注いでいます。"
    ]

    validation_result = guardian.validate_episode_generation(person_data, episodes)

    print(f"検証結果: {'✅ 合格' if validation_result['valid'] else '❌ 不合格'}")
    print(f"平均スコア: {validation_result['average_score']:.1f}点")

    if validation_result['violations']:
        print("違反内容:")
        for v in validation_result['violations']:
            print(f"  - {v.get('type', v.get('message', ''))}")

    print("\n各エピソードのスコア:")
    for i, score in enumerate(validation_result['scores']):
        age = [1, 10, 20, 30, 40, 50, 60][i]
        print(f"  {age}歳: {score['total_score']}点 (グレード: {score['grade']})")

    print("\n" + "="*60)
    print("✅ エピソードルールテスト完了")
    print("="*60)

if __name__ == "__main__":
    test_episode_rules()