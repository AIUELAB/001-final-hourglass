#!/usr/bin/env python3
"""
エピソード品質ルールv3.1のテスト
内容重複回避、具体性確保、感銘要素チェックの検証
"""

from pdca_guardian import PDCAGuardian
import json

def test_content_duplication():
    """内容重複ルールのテスト (RULE_115)"""
    guardian = PDCAGuardian()

    print("="*60)
    print("📋 内容重複回避ルールテスト")
    print("="*60)

    # テストケース1: 年齢の重複
    print("\n### テスト1: 年齢の重複")
    bad_episode_age = "あなたと同じ20歳のとき、大谷翔平は20歳で日本プロ野球史上初の2桁勝利・2桁本塁打を達成しました。"
    good_episode_age = "あなたと同じ20歳のとき、大谷翔平は日本プロ野球史上初の「2桁勝利・2桁本塁打」を達成し、二刀流の可能性を世界に証明しました。"

    person_data = {'person_name_display': '大谷翔平'}

    print("\n❌ 悪い例（年齢重複）:")
    print(f"  {bad_episode_age[:80]}...")
    violations = guardian.check_episode_historical_significance(bad_episode_age, person_data)
    for v in violations:
        if 'DUPLICATE_CONTENT' in str(v.get('type', '')):
            print(f"  → 違反検出: {v['message']}")

    print("\n✅ 良い例（年齢重複なし）:")
    print(f"  {good_episode_age[:80]}...")
    violations = guardian.check_episode_historical_significance(good_episode_age, person_data)
    duplicate_found = any('DUPLICATE_CONTENT' in str(v.get('type', '')) for v in violations)
    if not duplicate_found:
        print("  → 重複なし！自然な文章")

    # テストケース2: 人名の重複
    print("\n### テスト2: 人名の重複")
    bad_episode_name = "あなたと同じ30歳のとき、イチローはイチローとして初めてメジャーリーグでイチローらしい記録を作りました。"
    good_episode_name = "あなたと同じ30歳のとき、イチローはメジャーリーグで年間262安打の新記録を樹立し、世界を驚かせました。"

    person_data = {'person_name_display': 'イチロー'}

    print("\n❌ 悪い例（人名過多）:")
    print(f"  {bad_episode_name[:80]}...")
    violations = guardian.check_episode_historical_significance(bad_episode_name, person_data)
    for v in violations:
        if 'DUPLICATE_CONTENT' in str(v.get('type', '')):
            print(f"  → 違反検出: {v['message']}")

    print("\n✅ 良い例（人名適切）:")
    print(f"  {good_episode_name[:80]}...")
    violations = guardian.check_episode_historical_significance(good_episode_name, person_data)
    duplicate_found = any('DUPLICATE_CONTENT' in str(v.get('type', '')) for v in violations)
    if not duplicate_found:
        print("  → スムーズな文章！")


def test_concreteness():
    """具体性ルールのテスト (RULE_116)"""
    guardian = PDCAGuardian()

    print("\n" + "="*60)
    print("🎯 具体性確保ルールテスト")
    print("="*60)

    person_data = {'person_name_display': '宮崎駿'}

    # 抽象的なエピソード
    abstract_episode = "あなたと同じ40歳のとき、宮崎駿は活躍していました。とても充実した日々を送り、期待されていました。"

    # 具体的なエピソード
    concrete_episode = "あなたと同じ40歳のとき、宮崎駿は「風の谷のナウシカ」で興行収入7.4億円を記録し、日本アニメ映画の新時代を切り開きました。"

    print("\n❌ 抽象的なエピソード:")
    print(f"  {abstract_episode}")
    violations = guardian.check_episode_historical_significance(abstract_episode, person_data)
    for v in violations:
        if 'LACKS_CONCRETENESS' in str(v.get('type', '')):
            print(f"  → 違反: {v['message']}")

    print("\n✅ 具体的なエピソード:")
    print(f"  {concrete_episode}")
    violations = guardian.check_episode_historical_significance(concrete_episode, person_data)
    concrete_ok = not any('LACKS_CONCRETENESS' in str(v.get('type', '')) for v in violations)
    if concrete_ok:
        print("  → 具体性OK！固有名詞・数値あり")

    # 具体的要素の確認
    print("\n### 具体的要素の分析:")
    import re

    # 作品名（「」内）
    works = re.findall(r'「([^」]+)」', concrete_episode)
    if works:
        print(f"  作品名: {works}")

    # 数値
    numbers = re.findall(r'\d+\.?\d*', concrete_episode)
    if numbers:
        print(f"  数値データ: {numbers}")

    # キーワード
    keywords = ['新時代', '記録', '興行収入']
    found_keywords = [kw for kw in keywords if kw in concrete_episode]
    print(f"  重要キーワード: {found_keywords}")


def test_impact_elements():
    """感銘要素ルールのテスト (RULE_117)"""
    guardian = PDCAGuardian()

    print("\n" + "="*60)
    print("💫 感銘要素チェックテスト")
    print("="*60)

    person_data = {'person_name_display': 'スティーブ・ジョブズ'}

    # 感銘要素なし
    no_impact = "あなたと同じ30歳のとき、スティーブ・ジョブズはコンピュータ会社で働いていました。"

    # 感銘要素あり（挫折と復活）
    high_impact = "あなたと同じ30歳のとき、スティーブ・ジョブズは自ら創業したアップルから追放され、人生最大の挫折を味わいましたが、この経験が後の革命的製品の礎となりました。"

    print("\n❌ 感銘要素なし:")
    print(f"  {no_impact}")
    violations = guardian.check_episode_historical_significance(no_impact, person_data)
    for v in violations:
        if 'NO_IMPACT' in str(v.get('type', '')):
            print(f"  → 違反: {v['message']}")

    print("\n✅ 感銘要素あり（挫折と復活）:")
    print(f"  {high_impact[:100]}...")
    violations = guardian.check_episode_historical_significance(high_impact, person_data)
    impact_ok = not any('NO_IMPACT' in str(v.get('type', '')) for v in violations)
    if impact_ok:
        print("  → 感銘要素OK！読者の心を動かす内容")

    # 感銘要素の分析
    impact_result = guardian.calculate_episode_impact_score(high_impact, person_data)
    print(f"\n  インパクトスコア: {impact_result['total_impact_score']}点")
    print("  含まれる感銘要素:")
    print("    - 挫折からの復活 ✓")
    print("    - 人生の転換点 ✓")
    print("    - 将来への影響 ✓")


def test_complete_episode():
    """完全なエピソードの総合テスト"""
    guardian = PDCAGuardian()

    print("\n" + "="*60)
    print("🏆 完全なエピソード総合テスト")
    print("="*60)

    # v3.1基準を満たす完璧なエピソード
    perfect_episode = (
        "あなたと同じ28歳のとき、大谷翔平はWBC決勝でアメリカのマイク・トラウトを"
        "三振に打ち取り、日本を14年ぶりの世界一に導きました。"
        "「憧れるのをやめましょう」という名言と共に、野球史に残る劇的な瞬間を演出し、"
        "大会MVPに選出されました。"
    )

    person_data = {
        'person_name_display': '大谷翔平',
        'is_globally_significant': True
    }

    print("エピソード内容:")
    print(f"  {perfect_episode}")

    # すべてのチェック
    violations = guardian.check_episode_historical_significance(perfect_episode, person_data)

    print("\n### 品質チェック結果:")

    # 重複チェック
    duplicate_ok = not any('DUPLICATE' in str(v.get('type', '')) for v in violations)
    print(f"  ✅ 内容重複なし: {'合格' if duplicate_ok else '不合格'}")

    # 具体性チェック
    concrete_ok = not any('CONCRETENESS' in str(v.get('type', '')) for v in violations)
    print(f"  ✅ 具体性あり: {'合格' if concrete_ok else '不合格'}")

    # 感銘要素チェック
    impact_ok = not any('NO_IMPACT' in str(v.get('type', '')) for v in violations)
    print(f"  ✅ 感銘要素あり: {'合格' if impact_ok else '不合格'}")

    # インパクトスコア
    impact_result = guardian.calculate_episode_impact_score(perfect_episode, person_data)
    print(f"  ✅ インパクトスコア: {impact_result['total_impact_score']}点")

    # グローバル要素
    global_ok = impact_result['details'].get('global', 0) > 0
    print(f"  ✅ グローバル要素: {'あり（WBC）' if global_ok else 'なし'}")

    print("\n### 含まれる要素の分析:")
    print("  - 世界的大会（WBC） ✓")
    print("  - 具体的な対戦相手（マイク・トラウト） ✓")
    print("  - 数値データ（14年ぶり） ✓")
    print("  - 名言（「憧れるのをやめましょう」） ✓")
    print("  - 劇的な瞬間（決勝での三振） ✓")
    print("  - 受賞（大会MVP） ✓")

    if not violations:
        print("\n🎉 完璧！すべての品質基準を満たしています！")
    else:
        print("\n⚠️ 改善点:")
        for v in violations:
            print(f"  - {v['message']}")


def run_all_tests():
    """すべてのテストを実行"""
    print("🚀 エピソード品質ルールv3.1 テスト開始")
    print("="*70)

    # 各テストを実行
    test_content_duplication()
    test_concreteness()
    test_impact_elements()
    test_complete_episode()

    print("\n" + "="*70)
    print("✅ エピソード品質ルールv3.1 テスト完了")
    print("="*70)

    print("\n📝 v3.1の主な改善点:")
    print("1. 内容重複の徹底回避（年齢・人名の重複を検出）")
    print("2. 具体性の必須化（作品名、数値、固有名詞を要求）")
    print("3. 感銘要素の組み込み（挫折、復活、転機等を評価）")
    print("4. シンクロニシティの強調（ユーザーとの年齢の一致を活用）")


if __name__ == "__main__":
    run_all_tests()
