#!/usr/bin/env python3
"""
事実の構造をより深く分析し、なぜ3軸バランスが取れないのかを解明する
"""

import pandas as pd
from pdca_guardian import PDCAGuardian
import re

def analyze_fact_structure():
    """エピソードの事実構造を詳細に分析"""

    print("="*70)
    print("🔬 エピソードの深層構造分析")
    print("="*70)

    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')
    guardian = PDCAGuardian()

    # サンプルエピソードの詳細分析
    samples = [
        ("イチロー", 45),
        ("スティーブ・ジョブズ", 52),
        ("Ado", 21)
    ]

    for person_name, age in samples:
        episode_row = df[(df['person_name'] == person_name) & (df['episode_age'] == age)]
        if episode_row.empty:
            continue

        episode = episode_row.iloc[0]['episode_text']

        print(f"\n【{person_name}（{age}歳）】")
        print(f"エピソード: {episode}")

        # 事実のタイプ別分類
        facts = analyze_fact_types(episode)

        print("\n📊 事実のタイプ分析:")
        for fact_type, items in facts.items():
            if items:
                print(f"  {fact_type}: {len(items)}件")
                for item in items[:2]:  # 最初の2つを表示
                    print(f"    - {item}")

        # 3軸の詳細評価
        axis_evaluation = evaluate_three_axes_detailed(episode)

        print("\n🎯 3軸の詳細評価:")
        for axis, score in axis_evaluation.items():
            status = "✅" if score['score'] >= 3 else "❌"
            print(f"  {status} {axis}: {score['score']}/5点")
            print(f"     理由: {score['reason']}")

        # 構造的問題の診断
        structural_issues = diagnose_structural_issues(facts, axis_evaluation)

        print("\n⚠️ 構造的問題:")
        for issue in structural_issues:
            print(f"  - {issue}")

        print("-"*50)

    # 改善の方向性を提示
    suggest_improvement_strategy()

def analyze_fact_types(episode):
    """事実をタイプ別に分類"""

    facts = {
        "数値的記録": [],
        "達成・成功": [],
        "時系列事実": [],
        "社会的反響": [],
        "人間的要素": [],
        "困難・挑戦": [],
        "意外性要素": [],
        "教訓的要素": []
    }

    # 数値的記録
    numbers = re.findall(r'\d+[万億千百]?', episode)
    for num in numbers:
        facts["数値的記録"].append(num)

    # 達成・成功
    achievement_keywords = ["樹立", "達成", "成功", "突破", "獲得", "記録", "完売"]
    for keyword in achievement_keywords:
        if keyword in episode:
            # キーワードを含む文節を抽出
            sentences = episode.split("。")
            for sent in sentences:
                if keyword in sent:
                    facts["達成・成功"].append(sent[:30] + "...")
                    break

    # 人間的要素（感情、努力、姿勢）
    human_keywords = ["涙", "愛", "努力", "挑戦", "困難", "苦労", "喜び", "感動"]
    for keyword in human_keywords:
        if keyword in episode:
            facts["人間的要素"].append(f"'{keyword}'を含む記述あり")

    # 困難・挑戦
    difficulty_keywords = ["闘病", "克服", "乗り越え", "苦難", "逆境"]
    for keyword in difficulty_keywords:
        if keyword in episode:
            facts["困難・挑戦"].append(f"'{keyword}'の記述あり")

    # 意外性要素
    surprise_keywords = ["実は", "しかし", "にもかかわらず", "意外", "驚く"]
    for keyword in surprise_keywords:
        if keyword in episode:
            facts["意外性要素"].append(f"'{keyword}'を使用")

    # 教訓的要素
    lesson_keywords = ["証明", "示した", "教えてくれる", "大切さ", "重要性"]
    for keyword in lesson_keywords:
        if keyword in episode:
            facts["教訓的要素"].append(f"'{keyword}'の表現あり")

    return facts

def evaluate_three_axes_detailed(episode):
    """3軸を詳細に評価（各軸5点満点）"""

    evaluation = {
        "記憶性": {"score": 0, "reason": ""},
        "共感性": {"score": 0, "reason": ""},
        "意外性": {"score": 0, "reason": ""}
    }

    # 記憶性の評価
    numbers = re.findall(r'\d+', episode)
    large_numbers = [int(n) for n in numbers if n.isdigit() and int(n) > 1000]

    if len(large_numbers) > 3:
        evaluation["記憶性"]["score"] = 5
        evaluation["記憶性"]["reason"] = "豊富な具体的数字"
    elif len(large_numbers) > 1:
        evaluation["記憶性"]["score"] = 4
        evaluation["記憶性"]["reason"] = "複数の印象的な数字"
    elif len(numbers) > 2:
        evaluation["記憶性"]["score"] = 3
        evaluation["記憶性"]["reason"] = "いくつかの数字"
    else:
        evaluation["記憶性"]["score"] = 2
        evaluation["記憶性"]["reason"] = "数字が少ない"

    # 共感性の評価
    emotion_words = ["感動", "涙", "喜び", "苦労", "努力", "挑戦", "愛", "情熱"]
    human_elements = sum(1 for word in emotion_words if word in episode)

    if human_elements >= 3:
        evaluation["共感性"]["score"] = 4
        evaluation["共感性"]["reason"] = "豊富な感情表現"
    elif human_elements >= 1:
        evaluation["共感性"]["score"] = 2
        evaluation["共感性"]["reason"] = "わずかな感情要素"
    else:
        evaluation["共感性"]["score"] = 0
        evaluation["共感性"]["reason"] = "感情要素なし"

    # 意外性の評価
    surprise_words = ["実は", "しかし", "にもかかわらず", "意外", "驚く", "まさか"]
    contrast_elements = sum(1 for word in surprise_words if word in episode)

    if contrast_elements >= 2:
        evaluation["意外性"]["score"] = 4
        evaluation["意外性"]["reason"] = "転換や対比あり"
    elif contrast_elements >= 1:
        evaluation["意外性"]["score"] = 2
        evaluation["意外性"]["reason"] = "わずかな転換"
    else:
        evaluation["意外性"]["score"] = 0
        evaluation["意外性"]["reason"] = "予想通りの展開"

    return evaluation

def diagnose_structural_issues(facts, axis_evaluation):
    """構造的問題を診断"""

    issues = []

    # 事実の偏りチェック
    if len(facts["数値的記録"]) > 5 and len(facts["人間的要素"]) == 0:
        issues.append("数値偏重：人間的要素が完全に欠如")

    if len(facts["達成・成功"]) > 0 and len(facts["困難・挑戦"]) == 0:
        issues.append("結果偏重：プロセスや困難の記述なし")

    if len(facts["意外性要素"]) == 0:
        issues.append("単調な構成：転換や対比がない")

    if len(facts["教訓的要素"]) == 0:
        issues.append("表層的：深い意味や教訓の欠如")

    # 3軸のバランスチェック
    total_score = sum(axis["score"] for axis in axis_evaluation.values())
    if total_score < 9:  # 平均3点未満
        issues.append(f"3軸スコア不足：合計{total_score}/15点")

    # 最も弱い軸を特定
    weakest_axis = min(axis_evaluation.items(), key=lambda x: x[1]["score"])
    if weakest_axis[1]["score"] < 2:
        issues.append(f"致命的弱点：{weakest_axis[0]}がほぼゼロ")

    return issues

def suggest_improvement_strategy():
    """改善戦略の提案"""

    print("\n" + "="*70)
    print("💡 事実構造の改善戦略")
    print("="*70)

    print("""
現状の問題：
1. 事実が「結果の羅列」に偏っている
2. プロセス（どうやって達成したか）が見えない
3. 人物の内面や葛藤が伝わらない
4. 読者との接点（共通の経験）がない

改善の方向性：

【A. 事実の選択基準を変える】
  ✅ 結果だけでなくプロセスの事実を選ぶ
  ✅ 数字だけでなく行動や選択の事実を選ぶ
  ✅ 成功だけでなく失敗や困難の事実を選ぶ
  ✅ 個人だけでなく周囲への影響の事実を選ぶ

【B. 事実の組み合わせ方を工夫する】
  1. 対比構造：「一般的には○○だが、この人は△△」
  2. 因果構造：「○○したからこそ、△△を達成」
  3. 転換構造：「○○という困難があったが、△△で克服」
  4. 積み上げ構造：「○○から始まり、△△を経て、□□へ」

【C. 年齢との関連性を強化する】
  - その年齢だからこその意味を持つ事実を選ぶ
  - 同世代の一般的な状況との対比を含める
  - 人生のステージとの関連を示す

【D. 普遍的な価値を含める】
  - 誰もが共感できる普遍的テーマを含む事実
  - 時代を超えて価値を持つ事実
  - 人生の教訓となる事実
    """)

    print("\n📋 具体的なアクションプラン:")
    print("""
1. 各エピソードについて「プロセス」の事実を追加調査
2. 「困難→克服」の物語構造を持つ事実を選択
3. 年齢との関連性を示す比較データを追加
4. 人間的な選択や決断の瞬間を含める
5. 社会的影響や後世への影響を示す事実を追加
    """)

def main():
    analyze_fact_structure()

    print("\n" + "="*70)
    print("📝 結論")
    print("="*70)
    print("""
問題の本質：
現在のエピソードは「Wikipedia的な事実の羅列」になっている。
これは事実そのものの問題ではなく、
「どの事実を選び、どう組み合わせるか」の問題である。

解決策：
1. 事実の選択基準を「記録」から「物語」へシフト
2. 数字の羅列から、人間のドラマへ
3. 結果の列挙から、プロセスの描写へ
4. 個人の業績から、社会への影響へ

これは「言葉を足す」のではなく、
「より良い事実を選ぶ」ことで実現する。
    """)

if __name__ == "__main__":
    main()
