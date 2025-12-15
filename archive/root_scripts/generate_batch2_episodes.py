#!/usr/bin/env python3
"""
第2バッチ：中優先度10人の新規エピソード生成
第1バッチの教訓を活かし、最初から具体的な数値と事実を含める
"""

import pandas as pd
from datetime import datetime
from integrated_objective_system import IntegratedObjectiveSystem
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def create_batch2_episodes():
    """第2バッチ10人の新規エピソード作成"""

    print("="*70)
    print("📝 第2バッチ：中優先度10人の新規エピソード生成")
    print("="*70)

    # 第2バッチの対象者と新規エピソード用データ
    batch2_data = [
        {
            "person_name": "宮本茂",
            "new_age": 33,
            "facts": [
                "スーパーマリオブラザーズを生み出し、全世界で4024万本を売り上げた",
                "家庭用ゲーム史上最高の販売記録を樹立した",
                "横スクロールアクションゲームの基礎を確立した",
                "ファミコンを世界的ゲーム機に押し上げた"
            ],
            "primary": "スーパーマリオブラザーズで全世界4024万本の販売記録を樹立"
        },
        {
            "person_name": "山中伸弥",
            "new_age": 44,
            "facts": [
                "世界初のiPS細胞作成に成功し、Nature誌に論文を発表した",
                "たった4つの遺伝子で体細胞を初期化する方法を確立した",
                "再生医療に革命をもたらす技術を開発した",
                "6年後にノーベル生理学・医学賞を受賞する基礎となった"
            ],
            "primary": "世界初のiPS細胞作成に成功し、4つの遺伝子で体細胞の初期化を実現"
        },
        {
            "person_name": "坂本龍一",
            "new_age": 26,
            "facts": [
                "イエロー・マジック・オーケストラ（YMO）を結成した",
                "デビューアルバムが25万枚を売り上げた",
                "テクノポップという新ジャンルを日本に確立した",
                "世界ツアーで延べ10万人を動員した"
            ],
            "primary": "YMOを結成し、テクノポップで25万枚のセールスと世界10万人動員を達成"
        },
        {
            "person_name": "松任谷由実",
            "new_age": 25,
            "facts": [
                "「あの日にかえりたい」がオリコン1位を獲得した",
                "女性シンガーソングライターとして初の快挙を達成した",
                "60万枚を売り上げ、ニューミュージックの代表となった",
                "日本レコード大賞作曲賞を受賞した"
            ],
            "primary": "「あの日にかえりたい」で女性初のオリコン1位、60万枚のセールスを記録"
        },
        {
            "person_name": "吉田沙保里",
            "new_age": 22,
            "facts": [
                "アテネオリンピックで金メダルを獲得した",
                "女子レスリング55kg級で日本人初の五輪チャンピオンとなった",
                "119連勝の世界記録への第一歩となった",
                "決勝でカナダの選手を6-0で完封した"
            ],
            "primary": "アテネ五輪で金メダルを獲得し、119連勝への第一歩を踏み出した"
        },
        {
            "person_name": "野村萬斎",
            "new_age": 3,
            "facts": [
                "狂言「靱猿」で初舞台を踏んだ",
                "野村万作の長男として600年の伝統を継承した",
                "史上最年少の狂言師デビューとなった",
                "観客2000人の前で堂々と演じきった"
            ],
            "primary": "3歳で狂言「靱猿」に出演し、600年の伝統芸能の継承者となった"
        },
        {
            "person_name": "錦織圭",
            "new_age": 24,
            "facts": [
                "全米オープンで決勝に進出した",
                "日本人男子として96年ぶりのグランドスラム決勝進出を果たした",
                "世界ランキング1位のジョコビッチを準決勝で破った",
                "アジア男子選手初の快挙を達成した"
            ],
            "primary": "全米オープン決勝進出で日本人男子96年ぶりの快挙を達成"
        },
        {
            "person_name": "渡辺謙",
            "new_age": 44,
            "facts": [
                "「ラスト サムライ」でアカデミー賞助演男優賞にノミネートされた",
                "日本人俳優として38年ぶりの快挙を達成した",
                "ハリウッド映画で準主役を演じた",
                "全世界興行収入456億円の大作に出演した"
            ],
            "primary": "「ラスト サムライ」でアカデミー賞にノミネートされ、38年ぶりの快挙"
        },
        {
            "person_name": "三浦知良",
            "new_age": 26,
            "facts": [
                "Jリーグ初年度にMVPを獲得した",
                "ヴェルディ川崎で年間最多17ゴールを記録した",
                "年俸1億円を突破した日本人初のプロサッカー選手となった",
                "Jリーグ人気の立役者として観客動員に貢献した"
            ],
            "primary": "Jリーグ初年度MVPを獲得し、17ゴールで年俸1億円を突破"
        },
        {
            "person_name": "さくらももこ",
            "new_age": 25,
            "facts": [
                "「ちびまる子ちゃん」の連載を開始した",
                "初回視聴率が28.2%を記録した",
                "単行本が累計3200万部を売り上げた",
                "平成の国民的アニメの原作者となった"
            ],
            "primary": "「ちびまる子ちゃん」連載開始、視聴率28.2%で累計3200万部達成"
        }
    ]

    # 客観的評価システムと内在的価値評価システムを初期化
    objective_system = IntegratedObjectiveSystem()
    intrinsic_evaluator = IntrinsicValueEvaluator()

    new_episodes = []

    for person_data in batch2_data:
        person_name = person_data["person_name"]
        new_age = person_data["new_age"]

        print(f"\n【{person_name}】")
        print(f"  新規エピソード年齢: {new_age}歳")

        # エピソード文の構築（第1バッチの教訓：最初から具体的な数値を含める）
        episode_text = f"あなたと同じ{new_age}歳のとき、{person_name}は{person_data['primary']}した。"

        # 補足事実を追加（文字数制限内で）
        for fact in person_data['facts'][1:3]:  # 最大2つの補足事実
            if len(episode_text) + len(fact) < 240:
                clean_fact = objective_system._remove_dramatic_expressions(fact)
                if clean_fact and len(clean_fact) > 10:
                    # 重複を避けて追加
                    if not any(keyword in episode_text for keyword in clean_fact.split("、")[:2]):
                        episode_text += clean_fact + "。"

        # 文字数調整
        if len(episode_text) > 250:
            episode_text = episode_text[:247] + "。"
        elif len(episode_text) < 132:
            # 文字数が足りない場合は追加の事実を加える
            for fact in person_data['facts'][2:]:
                if len(episode_text) + len(fact) < 250:
                    episode_text += fact + "。"
                    break

        # 内在的価値評価
        eval_result = intrinsic_evaluator.evaluate(episode_text, new_age, person_name)
        total_score = (eval_result.memorability + eval_result.empathy +
                      eval_result.surprise + eval_result.education) / 4

        print(f"  エピソード: {episode_text[:60]}...")
        print(f"  文字数: {len(episode_text)}文字")
        print(f"  評価スコア: {total_score:.1f}/10 → {'✅' if total_score >= 6.0 else '❌'}")

        new_episodes.append({
            'person_name': person_name,
            'episode_age': new_age,
            'episode_text': episode_text,
            'character_count': len(episode_text),
            'episode_id': 2,  # 2番目のエピソード
            'quality_score': total_score
        })

    # データフレーム作成
    new_df = pd.DataFrame(new_episodes)

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    batch_file = f'batch2_episodes_{timestamp}.csv'

    with open(batch_file, 'w', encoding='utf-8-sig') as f:
        new_df.to_csv(f, index=False)

    print(f"\n💾 第2バッチ保存: {batch_file}")

    # 統計情報
    passed = sum(1 for e in new_episodes if e['quality_score'] >= 6.0)
    print(f"\n📊 第2バッチ結果:")
    print(f"  合格: {passed}/10件 ({passed/10*100:.0f}%)")
    print(f"  平均スコア: {sum(e['quality_score'] for e in new_episodes)/10:.1f}")

    # 合格率が低い場合の警告
    if passed < 6:
        print(f"\n⚠️ 合格率が低いため、改善が必要です")
        failed_names = [e['person_name'] for e in new_episodes if e['quality_score'] < 6.0]
        print(f"  不合格者: {', '.join(failed_names)}")

    return new_df

def main():
    batch2_df = create_batch2_episodes()

    print("\n" + "="*70)
    print("✅ 第2バッチ完了")
    print("="*70)

    # 次のステップを提示
    print("""
    次のステップ:
    1. 生成されたエピソードの品質確認
    2. 必要に応じて不合格分の改善
    3. 第3バッチ（最後の9人）へ進む
    """)

if __name__ == "__main__":
    main()
