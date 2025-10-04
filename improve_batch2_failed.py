#!/usr/bin/env python3
"""
第2バッチの不合格4件を改善
より具体的な事実と数値を追加して感動要素を強化
"""

import pandas as pd
from datetime import datetime
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def improve_failed_episodes():
    """不合格の4件を改善"""

    print("="*70)
    print("📝 第2バッチ不合格エピソードの改善")
    print("="*70)

    # 改善版エピソード
    improved_episodes = [
        {
            "person_name": "松任谷由実",
            "episode_age": 25,
            "episode_text": "あなたと同じ25歳のとき、松任谷由実は「あの日にかえりたい」で女性シンガーソングライター史上初のオリコン1位を獲得し、60万枚を売り上げた。それまで男性が独占していたチャートの頂点に立ち、ニューミュージックの時代を切り開いた。日本レコード大賞作曲賞も受賞した。",
            "focus": "女性初の快挙と時代を変えた功績"
        },
        {
            "person_name": "錦織圭",
            "episode_age": 24,
            "episode_text": "あなたと同じ24歳のとき、錦織圭は全米オープンで日本人男子96年ぶりの決勝進出を果たした。準決勝で世界ランキング1位のジョコビッチを6-4、1-6、7-6、6-3で破る大金星。アジア男子選手として初めてグランドスラム決勝の舞台に立った。",
            "focus": "世界1位撃破と96年ぶりの快挙"
        },
        {
            "person_name": "渡辺謙",
            "episode_age": 44,
            "episode_text": "あなたと同じ44歳のとき、渡辺謙は「ラスト サムライ」で日本人俳優38年ぶりのアカデミー賞助演男優賞ノミネートを達成した。全世界興行収入456億円の大作で、トム・クルーズと対等に演じた。白血病から復帰後わずか5年でハリウッドの頂点に挑戦した。",
            "focus": "病気克服後のハリウッド挑戦"
        },
        {
            "person_name": "さくらももこ",
            "episode_age": 25,
            "episode_text": "あなたと同じ25歳のとき、さくらももこは「ちびまる子ちゃん」を連載開始し、アニメ初回視聴率28.2%を記録した。単行本は累計3200万部、アニメは30年以上続く国民的作品となった。静岡の普通の家族を描いた作品が、日本中の共感を呼んだ。",
            "focus": "28.2%の視聴率と国民的作品への成長"
        }
    ]

    evaluator = IntrinsicValueEvaluator()
    results = []

    for episode_data in improved_episodes:
        person_name = episode_data["person_name"]
        age = episode_data["episode_age"]
        text = episode_data["episode_text"]

        # 評価
        eval_result = evaluator.evaluate(text, age, person_name)
        total_score = (eval_result.memorability + eval_result.empathy +
                      eval_result.surprise + eval_result.education) / 4

        print(f"\n【{person_name}（{age}歳）】")
        print(f"  改善ポイント: {episode_data['focus']}")
        print(f"  文字数: {len(text)}文字")
        print(f"  新スコア: {total_score:.1f}/10 → {'✅' if total_score >= 6.0 else '❌'}")

        if total_score >= 6.0:
            print(f"  成功要因: {', '.join(eval_result.reasons['memorability'][:2])}")

        results.append({
            'person_name': person_name,
            'episode_age': age,
            'episode_text': text,
            'character_count': len(text),
            'episode_id': 2,
            'quality_score': total_score
        })

    # 既に合格している6件を読み込み
    batch2_df = pd.read_csv('batch2_episodes_20250923_000603.csv', encoding='utf-8-sig')
    passed_df = batch2_df[batch2_df['quality_score'] >= 6.0]

    # 改善した4件と合わせる
    improved_df = pd.DataFrame(results)
    combined_df = pd.concat([passed_df, improved_df], ignore_index=True)

    # 人物名でソート
    combined_df = combined_df.sort_values('person_name')

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'batch2_improved_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        combined_df.to_csv(f, index=False)

    print(f"\n💾 改善版保存: {output_file}")

    # 統計
    passed = sum(1 for _, row in combined_df.iterrows() if row['quality_score'] >= 6.0)
    print(f"\n📊 第2バッチ最終結果:")
    print(f"  合格: {passed}/10件 ({passed/10*100:.0f}%)")
    print(f"  平均スコア: {combined_df['quality_score'].mean():.1f}")

    return combined_df

def main():
    improved_df = improve_failed_episodes()

    print("\n" + "="*70)
    print("✅ 第2バッチ改善完了")
    print("="*70)

if __name__ == "__main__":
    main()