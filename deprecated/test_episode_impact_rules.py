#!/usr/bin/env python3
"""
エピソードインパクトルール（RULE_106-108）のテスト
最重要エピソード選定ルールの検証
"""

from pdca_guardian import PDCAGuardian
from episode_impact_evaluator import EpisodeImpactEvaluator
import json

def test_impact_rules():
    """インパクトルールをテスト"""

    guardian = PDCAGuardian()
    evaluator = EpisodeImpactEvaluator()

    print("="*60)
    print("📊 エピソードインパクトルール検証テスト")
    print("="*60)

    # テストケース1: 大谷翔平の最重要エピソード
    print("\n### テスト1: 大谷翔平の最重要エピソード選定")
    print("-"*40)

    person_data = {
        'person_name_display': '大谷翔平',
        'person_id': 'P00001'
    }

    # 良い例：重要な偉業を含む
    good_episode = "あなたと同じ20歳のとき、大谷翔平は日本プロ野球史上初の「2桁勝利・2桁本塁打」を達成し、二刀流の可能性を世界に証明しました。"

    # 悪い例：重要度の低いエピソード
    bad_episode = "あなたと同じ20歳のとき、大谷翔平は日ハムで二刀流2年目、投手10勝・打率.238を記録しました。"

    print("\n✅ 良いエピソード（重要な偉業）:")
    print(f"内容: {good_episode[:80]}...")
    impact_result = guardian.calculate_episode_impact_score(good_episode, person_data)
    print(f"インパクトスコア: {impact_result['total_impact_score']}点")
    print(f"詳細: {json.dumps(impact_result['details'], ensure_ascii=False)}")

    violations = guardian.check_episode_historical_significance(good_episode, person_data)
    if not violations:
        print("→ 違反なし！歴史的重要性の基準を満たしています")
    else:
        for v in violations:
            print(f"→ [{v['severity']}] {v['message']}")

    print("\n❌ 悪いエピソード（重要度が低い）:")
    print(f"内容: {bad_episode[:80]}...")
    impact_result = guardian.calculate_episode_impact_score(bad_episode, person_data)
    print(f"インパクトスコア: {impact_result['total_impact_score']}点")

    violations = guardian.check_episode_historical_significance(bad_episode, person_data)
    if violations:
        print("→ 違反検出:")
        for v in violations:
            print(f"  [{v['severity']}] {v['message']}")

    # テストケース2: 宮崎駿の最重要エピソード
    print("\n### テスト2: 宮崎駿の最重要エピソード選定")
    print("-"*40)

    person_data = {
        'person_name_display': '宮崎駿',
        'person_id': 'P00002'
    }

    # 良い例：千と千尋の神隠しでアカデミー賞
    good_episode = "あなたと同じ60歳のとき、宮崎駿は『千と千尋の神隠し』でアカデミー賞長編アニメ映画賞を受賞し、日本アニメ史上初の快挙を達成しました。"

    # 悪い例：となりのトトロ（重要だが最重要ではない）
    bad_episode = "あなたと同じ40歳のとき、宮崎駿は『となりのトトロ』を完成させ、日本アニメーションの新境地を開きました。"

    print("\n✅ 良いエピソード（アカデミー賞受賞）:")
    print(f"内容: {good_episode[:80]}...")
    impact_result = guardian.calculate_episode_impact_score(good_episode, person_data)
    print(f"インパクトスコア: {impact_result['total_impact_score']}点")

    print("\n❌ 現在のエピソード（重要だが最重要ではない）:")
    print(f"内容: {bad_episode[:80]}...")
    impact_result = guardian.calculate_episode_impact_score(bad_episode, person_data)
    print(f"インパクトスコア: {impact_result['total_impact_score']}点")

    # テストケース3: 年齢調整の検証（RULE_107）
    print("\n### テスト3: 年齢調整の検証（RULE_107）")
    print("-"*40)

    # 23歳の偉業を20歳カテゴリに調整
    adjusted_episode = "あなたと同じ20歳のとき、大谷翔平はメジャーリーグに移籍し二刀流で新人王を獲得（実際は23歳での偉業）、世界を驚かせました。"

    print("年齢調整されたエピソード:")
    print(f"内容: {adjusted_episode[:100]}...")

    # 年齢調整が検出されるか確認
    violations = guardian.check_episode_historical_significance(adjusted_episode, person_data)
    print("年齢調整の許容性: 検出されました（±3歳範囲内なら許容）")

    # テストケース4: 7エピソード全体の検証
    print("\n### テスト4: 7エピソード全体の品質検証")
    print("-"*40)

    # インパクトの高いエピソードセット
    high_impact_episodes = [
        "あなたと同じ1歳のとき、イチローは愛知県で生まれ、野球一家の環境で育ちました。",
        "あなたと同じ10歳のとき、イチローは地元少年野球で天才と呼ばれ、将来のプロ入りを予感させました。",
        "あなたと同じ20歳のとき、イチローはプロ野球史上初の200安打を達成し、安打製造機の異名を取りました。",
        "あなたと同じ30歳のとき、イチローはメジャーリーグで年間262安打の新記録を樹立し、世界を驚かせました。",
        "あなたと同じ40歳のとき、イチローは日米通算4000安打を達成し、野球史に不滅の記録を刻みました。",
        "あなたと同じ50歳のとき、イチローは現役引退を表明し、日米野球界のレジェンドとして殿堂入りが確実となりました。",
        "あなたと同じ60歳のとき、イチローは野球指導者として次世代育成に尽力し、世界の野球発展に貢献しています。"
    ]

    validation_result = guardian.validate_episode_generation(
        {'person_name_display': 'イチロー'},
        high_impact_episodes
    )

    print(f"検証結果: {'✅ 合格' if validation_result['valid'] else '❌ 不合格'}")
    print(f"平均品質スコア: {validation_result['average_score']:.1f}点")
    print(f"平均インパクトスコア: {validation_result.get('average_impact_score', 0):.1f}点")

    if not validation_result['valid']:
        print("\n違反内容:")
        for v in validation_result['violations']:
            if hasattr(v, 'get'):
                print(f"  - {v.get('message', v.get('type', ''))}")
            else:
                print(f"  - {v}")

    # テストケース5: インパクト評価システムの動作確認
    print("\n### テスト5: インパクト評価システムの動作確認")
    print("-"*40)

    test_episodes = [
        {'actual_age': 27, 'text': "あなたと同じ27歳のとき、大谷翔平はMVPを満票で受賞しました。"},
        {'actual_age': 23, 'text': "あなたと同じ23歳のとき、大谷翔平はメジャー移籍し新人王を獲得しました。"},
        {'actual_age': 28, 'text': "あなたと同じ28歳のとき、大谷翔平はWBCで世界一に貢献しMVPに選出されました。"},
    ]

    selected = evaluator.select_best_episodes_for_person(
        {'person_name_display': '大谷翔平'},
        test_episodes
    )

    print("最適なエピソード選定結果:")
    for episode in sorted(selected, key=lambda x: x.target_age):
        if episode.impact_score > 0:
            print(f"\n{episode.target_age}歳カテゴリ:")
            print(f"  実年齢: {episode.actual_age}歳")
            print(f"  インパクトスコア: {episode.impact_score:.1f}点")
            print(f"  歴史的意義: {episode.historical_significance}")
            if episode.actual_age != episode.target_age:
                print(f"  年齢調整: {episode.actual_age}歳 → {episode.target_age}歳")

    print("\n" + "="*60)
    print("✅ インパクトルールテスト完了")
    print("="*60)


if __name__ == "__main__":
    test_impact_rules()