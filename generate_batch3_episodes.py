#!/usr/bin/env python3
"""
第3バッチ：最後の9人の新規エピソード生成
第1・2バッチの教訓を活かし、高品質なエピソードを作成
"""

import pandas as pd
from datetime import datetime
from integrated_objective_system import IntegratedObjectiveSystem
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def create_batch3_episodes():
    """第3バッチ9人の新規エピソード作成"""

    print("="*70)
    print("📝 第3バッチ：最後の9人の新規エピソード生成")
    print("="*70)

    # 第3バッチの対象者と新規エピソード用データ
    batch3_data = [
        {
            "person_name": "HIKAKIN",
            "new_age": 22,
            "facts": [
                "YouTubeチャンネル登録者数100万人を突破した",
                "日本人YouTuberとして初のミリオン達成者となった",
                "ヒューマンビートボックス動画で月間1000万再生を記録した",
                "YouTube Japanの公式パートナーに選ばれた"
            ],
            "primary": "日本人初のYouTube登録者100万人を達成し、月間1000万再生を記録"
        },
        {
            "person_name": "新海誠",
            "new_age": 43,
            "facts": [
                "「君の名は。」で興行収入250.3億円を記録した",
                "日本映画歴代4位の大ヒットとなった",
                "世界135か国で公開され、アジア映画史上最高の興行収入を達成した",
                "日本アカデミー賞最優秀脚本賞を受賞した"
            ],
            "primary": "「君の名は。」で興行収入250.3億円、世界135か国公開の大記録"
        },
        {
            "person_name": "小田和正",
            "new_age": 29,
            "facts": [
                "オフコースとして「さよなら」がオリコン1位を獲得した",
                "130万枚を売り上げ、フォークからポップスへの転換点となった",
                "武道館3日間連続公演を成功させた",
                "日本レコード大賞金賞を受賞した"
            ],
            "primary": "「さよなら」で130万枚を売り上げ、武道館3日間連続公演を達成"
        },
        {
            "person_name": "内村航平",
            "new_age": 23,
            "facts": [
                "ロンドンオリンピック個人総合で金メダルを獲得した",
                "体操個人総合で28年ぶりの日本人金メダリストとなった",
                "6種目合計92.690点の高得点を記録した",
                "世界選手権3連覇中の実力を五輪でも証明した"
            ],
            "primary": "ロンドン五輪個人総合金メダル、28年ぶりの快挙で92.690点"
        },
        {
            "person_name": "浅田真央",
            "new_age": 20,
            "facts": [
                "バンクーバーオリンピックで銀メダルを獲得した",
                "トリプルアクセルを3回成功させ、ギネス世界記録に認定された",
                "フリーで131.72点の高得点を記録した",
                "五輪史上初めて3回のトリプルアクセル成功者となった"
            ],
            "primary": "バンクーバー五輪で3回のトリプルアクセル成功、ギネス記録認定"
        },
        {
            "person_name": "石川佳純",
            "new_age": 19,
            "facts": [
                "ロンドンオリンピック卓球女子団体で銀メダルを獲得した",
                "日本卓球史上初のオリンピックメダルに貢献した",
                "準決勝でシンガポールを3-0で破った",
                "決勝で中国と対戦し、日本卓球の新時代を切り開いた"
            ],
            "primary": "ロンドン五輪で日本卓球史上初のメダル獲得に貢献"
        },
        {
            "person_name": "高橋尚子",
            "new_age": 28,
            "facts": [
                "シドニーオリンピック女子マラソンで金メダルを獲得した",
                "日本陸上女子トラック&フィールド初の金メダリストとなった",
                "2時間23分14秒のオリンピック新記録を樹立した",
                "日本女子マラソン黄金時代の扉を開いた"
            ],
            "primary": "シドニー五輪マラソン金メダル、2時間23分14秒の五輪新記録"
        },
        {
            "person_name": "荒川静香",
            "new_age": 24,
            "facts": [
                "トリノオリンピックフィギュアスケートで金メダルを獲得した",
                "アジア選手初のフィギュア五輪金メダリストとなった",
                "イナバウアーで世界を魅了し、191.34点を記録した",
                "日本フィギュア界唯一の五輪金メダルを獲得した"
            ],
            "primary": "トリノ五輪でアジア初のフィギュア金メダル、191.34点でイナバウアー"
        },
        {
            "person_name": "松田聖子",
            "new_age": 20,
            "facts": [
                "「青い珊瑚礁」で2作連続オリコン1位を獲得した",
                "デビュー1年で60万枚を売り上げた",
                "聖子ちゃんカットが社会現象となり、全国で流行した",
                "日本レコード大賞新人賞を受賞した"
            ],
            "primary": "「青い珊瑚礁」で60万枚売上げ、聖子ちゃんカットが社会現象に"
        }
    ]

    # 客観的評価システムと内在的価値評価システムを初期化
    objective_system = IntegratedObjectiveSystem()
    intrinsic_evaluator = IntrinsicValueEvaluator()

    new_episodes = []

    for person_data in batch3_data:
        person_name = person_data["person_name"]
        new_age = person_data["new_age"]

        print(f"\n【{person_name}】")
        print(f"  新規エピソード年齢: {new_age}歳")

        # エピソード文の構築（具体的な数値を最初から含める）
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
    batch_file = f'batch3_episodes_{timestamp}.csv'

    with open(batch_file, 'w', encoding='utf-8-sig') as f:
        new_df.to_csv(f, index=False)

    print(f"\n💾 第3バッチ保存: {batch_file}")

    # 統計情報
    passed = sum(1 for e in new_episodes if e['quality_score'] >= 6.0)
    print(f"\n📊 第3バッチ結果:")
    print(f"  合格: {passed}/9件 ({passed/9*100:.0f}%)")
    print(f"  平均スコア: {sum(e['quality_score'] for e in new_episodes)/9:.1f}")

    # 合格率が低い場合の警告
    if passed < 6:
        print(f"\n⚠️ 合格率が低いため、改善が必要です")
        failed_names = [e['person_name'] for e in new_episodes if e['quality_score'] < 6.0]
        print(f"  不合格者: {', '.join(failed_names)}")

    return new_df

def main():
    batch3_df = create_batch3_episodes()

    print("\n" + "="*70)
    print("✅ 第3バッチ完了")
    print("="*70)

    # 次のステップを提示
    print("""
    次のステップ:
    1. 生成されたエピソードの品質確認
    2. 必要に応じて不合格分の改善
    3. 全58件のCSV統合と最終検証
    """)

if __name__ == "__main__":
    main()