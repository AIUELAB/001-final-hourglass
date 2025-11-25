#!/usr/bin/env python3
"""
大谷翔平のエピソードを再生成
2024年の歴史的偉業（50-50、ワールドシリーズ優勝）を反映
"""

import json
import csv
from datetime import datetime
import sys
import os

# PDCAガーディアンのインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pdca_guardian import PDCAGuardian

def regenerate_ohtani_episode():
    """大谷翔平のエピソードを最新の偉業で再生成"""

    # データベース読み込み
    with open('verified_facts_database_103persons.json', 'r', encoding='utf-8') as f:
        database = json.load(f)

    ohtani_data = database['verified_facts']['大谷翔平']

    # 2024年の50-50偉業を選択（最高スコア）
    best_fact = max(ohtani_data['facts'],
                   key=lambda f: f.get('emotional_score', 0) * f.get('educational_score', 0))

    print(f"選択された事実: {best_fact['fact']}")
    print(f"スコア: emotional={best_fact['emotional_score']}, educational={best_fact['educational_score']}")

    # エピソード生成
    age = best_fact['age']
    fact_text = best_fact['fact']

    episode_text = f"あなたと同じ{age}歳のとき、大谷翔平は{fact_text}。"

    # スポーツカテゴリの教育的文脈を追加
    episode_text += "この偉業は、野球史上誰も成し遂げたことのない前人未到の記録であり、"
    episode_text += "不可能を可能にする挑戦の象徴として、世界中の人々に勇気と希望を与えました。"

    # 特にキーワードを強調
    if "50-50" in best_fact.get('keywords', []):
        episode_text += "特に50本塁打50盗塁という組み合わせは、パワーとスピードの究極の融合であり、"
        episode_text += "その後のワールドシリーズ制覇と合わせて、スポーツ史に永遠に刻まれる偉業となりました。"

    print(f"\n生成されたエピソード（{len(episode_text)}文字）:")
    print(episode_text)

    # PDCAガーディアンでチェック
    pdca = PDCAGuardian()
    person_info = {
        'person_name_display': '大谷翔平',
        'person_id': 'P000068',
        'birth_year': 1994,
        'category': 'スポーツ'
    }

    violations = pdca.check_episode_completeness(episode_text, person_info)
    if violations:
        print(f"\n⚠️ PDCAガーディアン警告: {len(violations)}件")
        for v in violations:
            print(f"  - {v['type']}: {v['message']}")
    else:
        print("\n✅ PDCAガーディアンチェック: すべてクリア")

    # 新しいエピソードデータ
    new_episode = {
        'person_id': 'P000068',
        'person_name': '大谷翔平（2024年版）',
        'age': age,
        'episode_text': episode_text,
        'confidence': best_fact.get('confidence', 1.0),
        'sources': '|'.join(best_fact.get('sources', ['MLB公式記録'])),
        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 既存のCSVを読み込み
    with open('enhanced_episodes_20250921_080427.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    # P000068の既存エピソードを更新
    updated = False
    for i, ep in enumerate(episodes):
        if ep['person_id'] == 'P000068':
            episodes[i] = new_episode
            updated = True
            print(f"\n✅ エピソードID P000068を更新しました")
            break

    if not updated:
        episodes.append(new_episode)
        print(f"\n✅ 新規エピソードとして追加しました")

    # 更新されたCSVを保存
    output_file = f'enhanced_episodes_{datetime.now().strftime("%Y%m%d_%H%M%S")}_updated.csv'
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                     'confidence', 'sources', 'generation_date']
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(episodes)

    print(f"\n📄 更新済みCSVファイル: {output_file}")
    print(f"   エピソード総数: {len(episodes)}件")

    # 新旧の比較
    print("\n" + "=" * 60)
    print("📊 エピソード比較")
    print("=" * 60)

    old_episode = """あなたと同じ26歳のとき、大谷翔平は2021年、投手で9勝、打者で46本塁打を記録し、満票でMVP受賞。この偉業は、継続的な努力と才能の結晶であり、多くの人々に勇気と感動を与えました。特にMVPという点において、その功績は高く評価されています。"""

    print("\n【旧エピソード（2021年MVP）】")
    print(f"文字数: {len(old_episode)}")
    print(old_episode)

    print("\n【新エピソード（2024年50-50）】")
    print(f"文字数: {len(episode_text)}")
    print(episode_text)

    print("\n✨ 大谷翔平のエピソード再生成完了！")
    print("   より感銘的な2024年の歴史的偉業を反映しました。")

if __name__ == "__main__":
    regenerate_ohtani_episode()
