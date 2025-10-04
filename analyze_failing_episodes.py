#!/usr/bin/env python3
"""
内在的価値評価システムでも基準を満たさなかった4件のエピソードを詳細分析
"""

import pandas as pd
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def analyze_failing_episodes():
    """基準を満たさなかったエピソードをステップバイステップで分析"""

    # CSVファイル読み込み
    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')
    evaluator = IntrinsicValueEvaluator()

    print("="*70)
    print("📊 基準を満たさなかった4件のエピソードの詳細分析")
    print("="*70)

    # すべてのエピソードを評価して不合格のものを特定
    failing_episodes = []

    for idx, row in df.iterrows():
        person_name = row['person_name']
        age = row['episode_age']
        episode_text = row['episode_text']

        result = evaluator.evaluate(episode_text, age, person_name)
        total_score = (result.memorability + result.empathy +
                      result.surprise + result.education) / 4

        if total_score < 6.0:  # 基準未達
            failing_episodes.append({
                'person': person_name,
                'age': age,
                'episode': episode_text,
                'score': total_score,
                'result': result,
                'character_count': row['character_count']
            })

    # スコアの低い順にソート
    failing_episodes.sort(key=lambda x: x['score'])

    print(f"\n基準未達エピソード: {len(failing_episodes)}件\n")

    # 各エピソードの詳細分析
    for i, ep in enumerate(failing_episodes, 1):
        print(f"\n{'='*70}")
        print(f"【{i}. {ep['person']}（{ep['age']}歳）】")
        print(f"総合スコア: {ep['score']:.1f}/10 ❌ 不合格（基準6.0未満）")
        print(f"文字数: {ep['character_count']}文字")
        print("="*70)

        # エピソード本文
        print("\n📝 エピソード内容:")
        print("-"*50)
        # 50文字ごとに改行して表示
        text = ep['episode']
        for j in range(0, len(text), 50):
            print(f"  {text[j:j+50]}")

        # ステップ1: 各軸の評価
        print("\n🔍 ステップ1: 各評価軸の詳細分析")
        print("-"*50)

        result = ep['result']

        print(f"\n1) 記憶性: {result.memorability:.1f}/10")
        if result.reasons['memorability']:
            for reason in result.reasons['memorability']:
                print(f"   ✓ {reason}")
        else:
            print("   ✗ 特筆すべき要素なし")

        print(f"\n2) 共感性: {result.empathy:.1f}/10")
        if result.reasons['empathy']:
            for reason in result.reasons['empathy']:
                print(f"   ✓ {reason}")
        else:
            print("   ✗ 人間的要素、感情、選択の要素が不足")

        print(f"\n3) 意外性: {result.surprise:.1f}/10")
        if result.reasons['surprise']:
            for reason in result.reasons['surprise']:
                print(f"   ✓ {reason}")
        else:
            print("   ✗ 予想通りの展開、転換要素なし")

        print(f"\n4) 教育的価値: {result.education:.1f}/10")
        if result.reasons['education']:
            for reason in result.reasons['education']:
                print(f"   ✓ {reason}")
        else:
            print("   ✗ 教訓や学びの要素が不明確")

        # ステップ2: 問題点の特定
        print(f"\n🔍 ステップ2: 問題点の特定")
        print("-"*50)

        problems = []

        # 各軸のスコアをチェック
        if result.memorability < 5:
            problems.append("記憶性不足: 印象的な要素が弱い")
        if result.empathy < 5:
            problems.append("共感性不足: 人間的な要素や感情が見えない")
        if result.surprise < 5:
            problems.append("意外性不足: 予想通りの内容で驚きがない")
        if result.education < 6:
            problems.append("教育的価値不足: 明確な教訓や学びがない")

        for j, problem in enumerate(problems, 1):
            print(f"  問題{j}: {problem}")

        # ステップ3: 改善の可能性分析
        print(f"\n🔍 ステップ3: なぜ基準を満たさないか")
        print("-"*50)

        analyze_why_failing(ep['episode'], ep['age'])

        # ステップ4: 改善提案
        print(f"\n💡 ステップ4: 改善の方向性")
        print("-"*50)
        suggest_improvements(ep['person'], ep['age'], ep['episode'])

    return failing_episodes

def analyze_why_failing(episode, age):
    """なぜ基準を満たさないかを分析"""

    # 事実の種類を分析
    has_achievement = "達成" in episode or "記録" in episode or "獲得" in episode
    has_process = "続け" in episode or "努力" in episode or "積み重ね" in episode
    has_difficulty = "困難" in episode or "逆境" in episode or "乗り越え" in episode
    has_impact = "影響" in episode or "貢献" in episode or "変えた" in episode

    if has_achievement and not has_process:
        print("  • 結果のみで過程が見えない")
    if not has_difficulty:
        print("  • 困難や挑戦の要素がない")
    if not has_impact:
        print("  • 社会的影響や意義が不明確")

    # 年齢との関係
    if age < 30:
        if "最年少" not in episode and "若さ" not in episode:
            print("  • 若年での達成の特別さが表現されていない")
    elif age > 60:
        if "現役" not in episode and "なお" not in episode:
            print("  • 高齢での活躍の意義が表現されていない")

def suggest_improvements(person_name, age, episode):
    """具体的な改善提案"""

    improvements = {
        "イチロー": [
            "日本プロ野球平均引退年齢（29歳）との対比を追加",
            "毎日の練習・準備のルーティンについて言及",
            "後進への影響（イチロー杯など）を含める"
        ],
        "安倍晋三": [
            "歴代最長在任の意味（安定政権の価値）を強調",
            "国際社会での日本の地位向上の具体例",
            "政治的立場を超えた功績を示す"
        ],
        "大谷翔平": [
            "二刀流への周囲の反対と、それを覆した過程",
            "100年ぶりの偉業の歴史的意義を強調",
            "野球少年たちへの夢と希望の提供"
        ],
        "孫正義": [
            "震災支援100億円の決断の背景と覚悟",
            "アリババ投資時のリスクと先見性",
            "日本のIT革命における個人の役割"
        ]
    }

    if person_name in improvements:
        for suggestion in improvements[person_name]:
            print(f"  ✓ {suggestion}")
    else:
        print("  ✓ プロセスや困難の要素を追加")
        print("  ✓ 年齢との関連性を強化")
        print("  ✓ 社会的影響や教訓を明確化")

def main():
    failing_episodes = analyze_failing_episodes()

    print("\n" + "="*70)
    print("📊 総括")
    print("="*70)

    print(f"""
基準未達の4件に共通する問題:

1. **事実の羅列型**: 達成や記録の列挙に留まる
2. **プロセス欠如**: どうやって達成したかが見えない
3. **感情要素不足**: 人間的な側面が伝わらない
4. **教訓不明確**: 何を学べるかが曖昧

これらは内在的価値評価でも、事実から
十分な価値を読み取れなかったケースです。
    """)

if __name__ == "__main__":
    main()