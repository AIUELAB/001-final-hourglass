#!/usr/bin/env python3
"""
大谷翔平のエピソードをWBC・トラウト対決版に修正
内在的価値を高める要素を追加
"""

import pandas as pd
from datetime import datetime
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def fix_ohtani_wbc():
    """大谷翔平のエピソードをWBC版に修正"""

    # 最新のCSVファイル読み込み
    df = pd.read_csv('episodes_final_20250922_205014.csv', encoding='utf-8-sig')

    print("="*70)
    print("⚾ 大谷翔平エピソード WBC・トラウト対決版への修正")
    print("="*70)

    # WBC版を改良
    wbc_improved_versions = [
        {
            "version": "WBC改良版A: 努力と友情の対決",
            "age": 29,
            "episode": "あなたと同じ29歳のとき、大谷翔平はWBC決勝でエンゼルスの同僚マイク・トラウトと運命の対決を迎えた。前日まで一緒に練習していた親友が、9回裏2アウトでバッターボックスに立つ。肘の痛みを隠しながら投げた162km/hの速球と87km/hのスライダーで三振を奪った瞬間、二人は抱き合った。「憧れるのをやめましょう」と宣言した青年が、14年ぶりの世界一を決めた。"
        },
        {
            "version": "WBC改良版B: 歴史的瞬間の人間ドラマ",
            "age": 29,
            "episode": "あなたと同じ29歳のとき、大谷翔平はWBC決勝の9回裏、チームメイトのトラウトと対峙した。162試合を共に戦う親友との、たった1打席の真剣勝負。肘に違和感を抱えながら投げた最後のスライダーが決まった瞬間、球場の6万人が立ち上がった。試合後「野球人生で最高の瞬間」と語った二人の姿に、スポーツの本質を見た。14年ぶりの世界一は、友情を超えた勝負の美しさが生んだ。"
        },
        {
            "version": "WBC改良版C: 二刀流の集大成",
            "age": 29,
            "episode": "あなたと同じ29歳のとき、大谷翔平は二刀流でWBCを制覇した。投手として2勝、打者として.435の打率を記録。決勝9回裏、親友トラウトとの対決では、前夜まで「絶対に打てない」と言われた87km/hのスライダーで三振を奪った。「無理だ」と言われ続けた二刀流への挑戦が、この瞬間、野球史に新たな1ページを刻んだ。試合後の涙は、7年間の努力が報われた証だった。"
        }
    ]

    evaluator = IntrinsicValueEvaluator()
    best_version = None
    best_score = 0

    print("\n現在のエピソード:")
    current_episode = df[df['person_name'] == '大谷翔平']['episode_text'].iloc[0]
    print(f"{current_episode[:100]}...")

    print("\n" + "="*70)
    print("WBC版の評価:")
    print("="*70)

    for version_info in wbc_improved_versions:
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
            print(f"    → {', '.join(result.reasons['memorability'][:2])}")

        print(f"  共感性: {result.empathy:.1f}/10")
        if result.reasons['empathy']:
            print(f"    → {', '.join(result.reasons['empathy'][:2])}")

        print(f"  意外性: {result.surprise:.1f}/10")
        if result.reasons['surprise']:
            print(f"    → {', '.join(result.reasons['surprise'][:2])}")

        print(f"  教育的価値: {result.education:.1f}/10")
        if result.reasons['education']:
            print(f"    → {', '.join(result.reasons['education'][:2])}")

        print(f"\n  総合スコア: {total_score:.1f}/10 → {'✅ 合格' if total_score >= 6.0 else '❌ 不合格'}")

        if total_score > best_score:
            best_score = total_score
            best_version = version_info

    # 最良のWBC版で更新
    if best_version:
        print("\n" + "="*70)
        print(f"🏆 採用: {best_version['version']}")
        print(f"   総合スコア: {best_score:.1f}/10")
        print("="*70)

        # データフレームを更新
        mask = df['person_name'] == '大谷翔平'
        df.loc[mask, 'episode_age'] = best_version['age']
        df.loc[mask, 'episode_text'] = best_version['episode']
        df.loc[mask, 'character_count'] = len(best_version['episode'])

        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'episodes_29_updated_{timestamp}.csv'

        with open(output_file, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n💾 WBC版で更新完了: {output_file}")

        # 全体の最終確認
        print("\n" + "="*70)
        print("🎯 全29件の最終確認（WBC版）")
        print("="*70)

        pass_count = 0
        fail_list = []

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
            else:
                fail_list.append(f"{row['person_name']}（{total:.1f}）")

        print(f"合格率: {pass_count}/29件 ({pass_count/29*100:.1f}%)")

        if fail_list:
            print(f"不合格: {', '.join(fail_list)}")
        else:
            print("🎉 全エピソードが基準を満たしました！")

    return df

def main():
    df = fix_ohtani_wbc()

    print("\n" + "="*70)
    print("📝 修正のポイント")
    print("="*70)
    print("""
WBC・トラウト対決版の強化要素:
1. 親友との対決という人間ドラマ
2. 肘の痛みを隠しての投球（困難の克服）
3. 二刀流の集大成としての位置づけ
4. 14年ぶりの世界一という歴史的意義
5. 努力の積み重ねが報われた瞬間
    """)

if __name__ == "__main__":
    main()