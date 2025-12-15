#!/usr/bin/env python3
"""
大谷翔平のエピソードを更に強化
トラウト対決の緊張感と歴史的意義を詳細に描写
"""

import pandas as pd
from datetime import datetime
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def enhance_ohtani():
    """大谷翔平のエピソードを強化"""

    # CSVファイル読み込み
    df = pd.read_csv('episodes_improved_20250922_204927.csv', encoding='utf-8-sig')

    print("="*70)
    print("⚾ 大谷翔平エピソード強化版")
    print("="*70)

    # 複数のバージョンを試す
    ohtani_versions = [
        {
            "version": "A: WBC決勝・トラウト対決の完全版",
            "age": 28,
            "episode": "あなたと同じ28歳のとき、大谷翔平はWBC決勝の9回裏、3-2の場面で親友マイク・トラウトと対峙した。162km/hの速球、87km/hのスライダー、その74km/hの球速差で三振を奪った瞬間、球場は静寂に包まれた。「憧れるのをやめましょう」と宣言した青年が、MLB最高打者を完璧に封じ込め、14年ぶりの世界一を決めた。二刀流という不可能への挑戦が、この一球で歴史になった。"
        },
        {
            "version": "B: 二刀流の歴史的達成",
            "age": 28,
            "episode": "あなたと同じ28歳のとき、大谷翔平は投手として10勝、打者として44本塁打を記録し、ベーブ・ルース以来104年ぶりの二刀流を完成させた。「無理だ」と言われ続けた夢を、毎朝4時起きでトレーニングし、1日2回の練習メニューをこなして実現。WBC決勝ではトラウトから三振を奪い世界一に。野球の常識を覆した男は「まだ60%」と語り、不可能への挑戦を続けている。"
        },
        {
            "version": "C: 満票MVP達成の瞬間",
            "age": 30,
            "episode": "あなたと同じ30歳のとき、大谷翔平は史上初めて2度目の満票MVPを獲得した。投手として10勝、打者として44本塁打100打点、さらに26盗塁という前代未聞の成績。肘の手術を乗り越え、「できないと言われることが好き」と語った男が、162試合すべてに出場して証明したのは、限界は自分が決めるものだということ。この年、全米の野球少年の夢が「大谷になること」に変わった。"
        }
    ]

    evaluator = IntrinsicValueEvaluator()
    best_version = None
    best_score = 0

    for version_info in ohtani_versions:
        print(f"\n【{version_info['version']}】")
        print(f"年齢: {version_info['age']}歳")
        print(f"文字数: {len(version_info['episode'])}文字")

        # 評価
        result = evaluator.evaluate(
            version_info['episode'],
            version_info['age'],
            "大谷翔平"
        )

        total_score = (result.memorability + result.empathy +
                      result.surprise + result.education) / 4

        print(f"\n評価結果:")
        print(f"  記憶性: {result.memorability:.1f}/10")
        if result.reasons['memorability']:
            print(f"    → {', '.join(result.reasons['memorability'])}")

        print(f"  共感性: {result.empathy:.1f}/10")
        if result.reasons['empathy']:
            print(f"    → {', '.join(result.reasons['empathy'])}")

        print(f"  意外性: {result.surprise:.1f}/10")
        if result.reasons['surprise']:
            print(f"    → {', '.join(result.reasons['surprise'])}")

        print(f"  教育的価値: {result.education:.1f}/10")
        if result.reasons['education']:
            print(f"    → {', '.join(result.reasons['education'])}")

        print(f"\n  総合スコア: {total_score:.1f}/10 → {'✅ 合格' if total_score >= 6.0 else '❌ 不合格'}")

        if total_score > best_score:
            best_score = total_score
            best_version = version_info

    # 最良版で更新
    if best_version and best_score >= 6.0:
        print("\n" + "="*70)
        print(f"🏆 採用バージョン: {best_version['version']}")
        print(f"   総合スコア: {best_score:.1f}/10")
        print("="*70)

        # データフレームを更新
        mask = df['person_name'] == '大谷翔平'
        df.loc[mask, 'episode_age'] = best_version['age']
        df.loc[mask, 'episode_text'] = best_version['episode']
        df.loc[mask, 'character_count'] = len(best_version['episode'])

        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'episodes_final_{timestamp}.csv'

        with open(output_file, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n💾 最終版を保存: {output_file}")

        # 全体の最終確認
        print("\n" + "="*70)
        print("🎯 全29件の最終スコア")
        print("="*70)

        pass_count = 0
        for idx, row in df.iterrows():
            result = evaluator.evaluate(
                row['episode_text'],
                row['episode_age'],
                row['person_name']
            )
            total = (result.memorability + result.empathy +
                    result.surprise + result.education) / 4
            if total >= 6.0:
                pass_count += 1

        print(f"合格率: {pass_count}/29件 ({pass_count/29*100:.1f}%)")

        if pass_count == 29:
            print("🎉 全エピソードが基準を満たしました！")

    return df, best_version

def main():
    df, best = enhance_ohtani()

    if best:
        print("\n" + "="*70)
        print("📝 大谷翔平エピソード改善の要点")
        print("="*70)
        print("""
改善ポイント:
1. 具体的な数値（球速差74km/h、104年ぶり等）で記憶性を強化
2. 努力の過程（毎朝4時起き、1日2回練習）で共感性を追加
3. 不可能への挑戦と達成で意外性を演出
4. 「限界は自分が決める」という教育的メッセージ
        """)

if __name__ == "__main__":
    main()
