#!/usr/bin/env python3
"""
既存エピソードの年齢選択妥当性を検証
不適切な選択を検出し、改善案を提示
"""

import csv
import json
from pathlib import Path
from age_selection_evaluator import AgeSelectionEvaluator
from datetime import datetime

# 主要人物の代表的成果データ（検証用）
PERSON_ACHIEVEMENTS = {
    "石川遼": {
        "15": "2007年マンシングウェアオープンで史上最年少優勝（15歳245日）",
        "17": "2008年日本ツアー年間獲得賞金1億円突破（史上最年少）",
        "21": "2013年PGAツアー参戦、世界ランキング最高位17位"
    },
    "松井秀喜": {
        "22": "1996年巨人で本塁打王・打点王の二冠",
        "29": "2003年ヤンキース移籍、開幕戦満塁本塁打",
        "35": "2009年ワールドシリーズMVP（日本人初）"
    },
    "野茂英雄": {
        "26": "1995年MLBドジャースで新人王、最多奪三振王",
        "27": "1996年ノーヒットノーラン達成（日本人初）",
        "33": "2001年ボストン・レッドソックスでノーヒットノーラン（2度目）"
    },
    "荒川静香": {
        "24": "2006年トリノ五輪フィギュアスケート金メダル（アジア初）",
        "22": "2004年世界選手権優勝",
        "16": "1998年長野五輪出場（13位）"
    },
    "北島康介": {
        "21": "2004年アテネ五輪100m・200m平泳ぎ2冠",
        "25": "2008年北京五輪100m・200m平泳ぎ2冠（2大会連続）",
        "29": "2012年ロンドン五輪4×100mメドレーリレー銀メダル"
    },
    "伊調馨": {
        "20": "2004年アテネ五輪レスリング63kg級金メダル",
        "32": "2016年リオ五輪で4連覇達成（女子個人種目初）",
        "28": "2012年ロンドン五輪で3連覇、国民栄誉賞受賞"
    },
    "綾瀬はるか": {
        "18": "2004年『世界の中心で、愛をさけぶ』でブレイク",
        "28": "2013年大河ドラマ『八重の桜』主演",
        "31": "2016年映画『海街diary』で日本アカデミー賞最優秀主演女優賞"
    },
    "西野亮廣": {
        "19": "1999年キングコング結成、若手漫才師として活躍",
        "36": "2016年絵本『えんとつ町のプペル』が70万部突破",
        "40": "2020年映画『えんとつ町のプペル』興行収入24億円"
    },
    "サカナクション": {
        "2005": "バンド結成",
        "2010": "『アルクアラウンド』でメジャーブレイク",
        "2013": "『ミュージック』でオリコン1位獲得"
    }
}

def validate_episodes():
    """エピソードの年齢選択を検証"""

    evaluator = AgeSelectionEvaluator()
    csv_file = 'episodes_master_100_complete_20250923_133707.csv'

    print("=" * 60)
    print("既存エピソードの年齢選択検証")
    print("=" * 60)

    issues = []

    # CSVファイルを読み込み
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    print(f"\n検証対象: {len(episodes)}件のエピソード")

    # 各エピソードを検証
    for i, row in enumerate(episodes, 1):
        person_name = row['person_name']
        current_age = int(row['user_age'])
        episode_text = row['episode_text']
        category = row.get('category', 'general')

        # 現在のエピソードのスコアを評価
        current_score = evaluator.evaluate_single_achievement(
            current_age, episode_text, category
        )

        # この人物の他の選択肢があるか確認
        if person_name in PERSON_ACHIEVEMENTS:
            achievements = PERSON_ACHIEVEMENTS[person_name]

            # 最適な年齢を選択
            best_age, reason, best_score = evaluator.select_best_age(
                person_name, achievements, category=category
            )

            # 現在の選択と最適な選択を比較
            if best_age != current_age and best_score - current_score >= 2.0:
                issues.append({
                    'person_name': person_name,
                    'current_age': current_age,
                    'current_score': current_score,
                    'suggested_age': best_age,
                    'suggested_score': best_score,
                    'score_diff': best_score - current_score,
                    'current_achievement': episode_text[:80] + '...',
                    'suggested_achievement': achievements[str(best_age)],
                    'reason': reason
                })

        # 一般的な問題のチェック
        elif current_score < 6.0:
            # スコアが低すぎる場合は要確認
            issues.append({
                'person_name': person_name,
                'current_age': current_age,
                'current_score': current_score,
                'suggested_age': '要調査',
                'suggested_score': None,
                'score_diff': None,
                'current_achievement': episode_text[:80] + '...',
                'suggested_achievement': '他の年齢の成果を調査すべき',
                'reason': 'スコアが低すぎる（6.0未満）'
            })

    # 結果の表示
    print(f"\n検証完了: {len(issues)}件の潜在的問題を検出")

    if issues:
        print("\n" + "=" * 60)
        print("改善が必要なエピソード")
        print("=" * 60)

        # スコア差が大きい順にソート
        issues.sort(key=lambda x: x['score_diff'] if x['score_diff'] else 0, reverse=True)

        for issue in issues[:10]:  # TOP10を表示
            print(f"\n【{issue['person_name']}】")
            print(f"  現在: {issue['current_age']}歳（スコア: {issue['current_score']:.1f}）")
            if issue['suggested_score']:
                print(f"  推奨: {issue['suggested_age']}歳（スコア: {issue['suggested_score']:.1f}）")
                print(f"  改善幅: +{issue['score_diff']:.1f}ポイント")
            print(f"  理由: {issue['reason']}")
            print(f"  現在の内容: {issue['current_achievement']}")
            if issue['suggested_achievement'] != '他の年齢の成果を調査すべき':
                print(f"  推奨内容: {issue['suggested_achievement']}")

    # レポート保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'episode_age_validation_report_{timestamp}.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_episodes': len(episodes),
            'issues_found': len(issues),
            'issues': issues
        }, f, ensure_ascii=False, indent=2)

    print(f"\n📊 詳細レポート保存: {report_file}")

    return issues

def generate_improvement_script(issues):
    """改善スクリプトを生成"""

    if not issues:
        print("改善が必要なエピソードはありません。")
        return

    print("\n" + "=" * 60)
    print("改善スクリプト生成")
    print("=" * 60)

    # 改善が必要な上位エピソードを選択
    priority_issues = [i for i in issues if i['score_diff'] and i['score_diff'] >= 3.0]

    if priority_issues:
        print(f"\n優先度の高い改善対象: {len(priority_issues)}件")

        with open('improve_episode_ages.py', 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env python3\n')
            f.write('"""自動生成: エピソード年齢改善スクリプト"""\n\n')
            f.write('import csv\n')
            f.write('from datetime import datetime\n\n')
            f.write('# 改善対象\n')
            f.write('improvements = [\n')

            for issue in priority_issues[:5]:  # TOP5のみ
                f.write(f'    {{\n')
                f.write(f'        "person_name": "{issue["person_name"]}",\n')
                f.write(f'        "new_age": {issue["suggested_age"]},\n')
                f.write(f'        "new_achievement": "{issue["suggested_achievement"]}",\n')
                f.write(f'        "reason": "{issue["reason"]}"\n')
                f.write(f'    }},\n')

            f.write(']\n\n')
            f.write('# TODO: 実装を追加\n')

        print("✅ 改善スクリプト生成: improve_episode_ages.py")

if __name__ == "__main__":
    issues = validate_episodes()

    # 優先度の高い問題がある場合は改善スクリプトを生成
    if any(i['score_diff'] and i['score_diff'] >= 3.0 for i in issues if i['score_diff']):
        generate_improvement_script(issues)