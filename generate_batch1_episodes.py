#!/usr/bin/env python3
"""
第1バッチ：高優先度10人の新規エピソード生成
客観的事実に基づき、演出を排除した感動要素抽出
"""

import pandas as pd
from datetime import datetime
from integrated_objective_system import IntegratedObjectiveSystem
from intrinsic_value_evaluator import IntrinsicValueEvaluator

def create_batch1_episodes():
    """第1バッチ10人の新規エピソード作成"""

    # 既存のCSVを読み込み
    existing_df = pd.read_csv('episodes_29_corrected_20250922_210220.csv', encoding='utf-8-sig')

    print("="*70)
    print("📝 第1バッチ：高優先度10人の新規エピソード生成")
    print("="*70)

    # 第1バッチの対象者と新規エピソード用データ
    batch1_data = [
        {
            "person_name": "イチロー",
            "new_age": 27,
            "facts": [
                "2001年にMLBで首位打者を獲得した",
                "日本人野手として初のMLBシーズンMVPを受賞した",
                "242安打でMLB新人最多安打記録を樹立した",
                "打率.350、56盗塁を記録した"
            ],
            "primary": "MLBで242安打を記録し首位打者とMVPを獲得"
        },
        {
            "person_name": "大谷翔平",
            "new_age": 23,
            "facts": [
                "日本ハムファイターズで投手と指名打者の二刀流を開始した",
                "10勝、22本塁打を記録した",
                "投手として最速165km/hを記録した",
                "パ・リーグMVPとベストナインのダブル受賞を達成した"
            ],
            "primary": "投手で10勝、打者で22本塁打の二刀流を実現"
        },
        {
            "person_name": "村上春樹",
            "new_age": 30,
            "facts": [
                "処女作「風の歌を聴け」で群像新人文学賞を受賞した",
                "ジャズ喫茶を経営しながら執筆活動を行った",
                "芥川賞候補になったが受賞を逃した",
                "3年間の二重生活の末にデビューを果たした"
            ],
            "primary": "ジャズ喫茶経営と執筆を両立させ群像新人文学賞を受賞"
        },
        {
            "person_name": "黒澤明",
            "new_age": 33,
            "facts": [
                "「姿三四郎」で監督デビューした",
                "戦時中の1943年に公開された",
                "検閲で18分カットされたが大ヒットした",
                "日本映画界に新風を吹き込んだ"
            ],
            "primary": "「姿三四郎」で監督デビューし戦時中にも関わらず大ヒット"
        },
        {
            "person_name": "宮崎駿",
            "new_age": 43,
            "facts": [
                "「風の谷のナウシカ」を映画化した",
                "興行収入14.8億円を記録した",
                "アニメージュ誌の連載漫画を自ら映画化した",
                "スタジオジブリ設立のきっかけとなった"
            ],
            "primary": "「風の谷のナウシカ」で14.8億円の興行収入を記録"
        },
        {
            "person_name": "安倍晋三",
            "new_age": 38,
            "facts": [
                "小渕内閣で官房副長官に就任した",
                "自民党内で最年少の官房副長官となった",
                "北朝鮮拉致問題を担当した",
                "政界のプリンスと呼ばれた"
            ],
            "primary": "38歳で最年少の官房副長官に就任"
        },
        {
            "person_name": "孫正義",
            "new_age": 24,
            "facts": [
                "日本ソフトバンクを設立した",
                "資本金1000万円でスタートした",
                "パソコン用ソフトの卸売業を開始した",
                "創業1年目で年商30億円を達成した"
            ],
            "primary": "資本金1000万円で起業し1年目で年商30億円を達成"
        },
        {
            "person_name": "北野武",
            "new_age": 42,
            "facts": [
                "「その男、凶暴につき」で映画監督デビューした",
                "主演も兼ねて暴力的な警官を演じた",
                "興行収入7億円を記録した",
                "ブルーリボン賞作品賞を受賞した"
            ],
            "primary": "「その男、凶暴につき」で監督デビューしブルーリボン賞受賞"
        },
        {
            "person_name": "羽生結弦",
            "new_age": 19,
            "facts": [
                "ソチオリンピックで金メダルを獲得した",
                "男子シングル日本人初の金メダリストとなった",
                "ショートプログラムで世界歴代最高得点を記録した",
                "東日本大震災の被災者として困難を乗り越えた"
            ],
            "primary": "19歳でソチ五輪金メダル、日本男子初の快挙"
        },
        {
            "person_name": "藤井聡太",
            "new_age": 19,
            "facts": [
                "史上最年少で五冠を達成した",
                "竜王、王位、叡王、王将、棋聖を保持した",
                "年間勝率8割3分を記録した",
                "賞金ランキング1位となった"
            ],
            "primary": "19歳で史上最年少五冠を達成し年間勝率8割3分"
        }
    ]

    # 客観的評価システムと内在的価値評価システムを初期化
    objective_system = IntegratedObjectiveSystem()
    intrinsic_evaluator = IntrinsicValueEvaluator()

    new_episodes = []

    for person_data in batch1_data:
        person_name = person_data["person_name"]
        new_age = person_data["new_age"]

        # 既存のエピソード年齢を確認
        existing_age = existing_df[existing_df['person_name'] == person_name]['episode_age'].iloc[0]

        print(f"\n【{person_name}】")
        print(f"  既存: {existing_age}歳 → 新規: {new_age}歳")

        # エピソード文の構築（客観的事実のみ）
        episode_text = f"あなたと同じ{new_age}歳のとき、{person_name}は{person_data['primary']}した。"

        # 補足事実を追加（文字数制限内で）
        for fact in person_data['facts'][1:3]:  # 最大2つの補足事実
            if len(episode_text) + len(fact) < 240:
                clean_fact = objective_system._remove_dramatic_expressions(fact)
                if clean_fact:
                    episode_text += clean_fact + "。"

        # 文字数調整
        if len(episode_text) > 250:
            episode_text = episode_text[:247] + "。"

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

    # 一時保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    batch_file = f'batch1_episodes_{timestamp}.csv'

    with open(batch_file, 'w', encoding='utf-8-sig') as f:
        new_df.to_csv(f, index=False)

    print(f"\n💾 第1バッチ保存: {batch_file}")

    # 統計情報
    passed = sum(1 for e in new_episodes if e['quality_score'] >= 6.0)
    print(f"\n📊 第1バッチ結果:")
    print(f"  合格: {passed}/10件 ({passed/10*100:.0f}%)")
    print(f"  平均スコア: {sum(e['quality_score'] for e in new_episodes)/10:.1f}")

    return new_df

def main():
    batch1_df = create_batch1_episodes()

    print("\n" + "="*70)
    print("✅ 第1バッチ完了")
    print("="*70)
    print("""
    次のステップ:
    1. 生成されたエピソードのファクトチェック
    2. 必要に応じて修正
    3. 第2バッチへ進む
    """)

if __name__ == "__main__":
    main()